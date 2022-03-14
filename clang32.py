#!/usr/bin/env python

from __future__ import print_function

import argparse
import fileinput
import itertools
import json
import os
import re
import sys
from urllib.request import urlopen

import pacdb

import pkgbuild

with urlopen("https://github.com/msys2/msys2-autobuild/releases/download/status/status.json") as f:
    x = json.load(f)

PKGBASE_BLACKLIST = frozenset(itertools.chain((
    "mingw-w64-rust",
), (pkg for pkg in x if "clang32" in x[pkg] and x[pkg]["clang32"]["status"] == "failed-to-build")))

del x

def dep_tree(p, forward, reverse, level=0, seen=None):
    if seen is None:
        seen = set()
    print(f"{'│   ' * level}├── {p}{ f': blocked by {forward[p]}' if level == 0 and p in forward else ''}")
    seen.add(p)
    for p2 in reverse.get(p, []):
        if p2 not in seen:
            dep_tree(p2, forward, reverse, level+1, seen)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Mark PKGBUILDs for clang32')
    parser.add_argument('--allclang64', action='store_true')
    parser.add_argument('--depth', type=int, default=1)
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()

    r = pacdb.mingw_db_by_name('clang64')
    #json.dump(r, sys.stdout, sort_keys=True, indent=2)
    if not args.allclang64:
        s = pacdb.mingw_db_by_name('clang32')
        #json.dump(s, sys.stdout, sort_keys=True, indent=2)
        sprovs = set()
        for p in s:
            sprovs.add(p.name)
            for prov in p.provides:
                sprovs.add(prov)

        bases = set()
        mingwpkg = re.compile(r"^mingw-w64-clang-")
        forward = {}
        reverse = {}
        for _ in range(args.depth):
            newprovs = set()
            for p in r:
                deps = p.depends
                deps.update(p.makedepends)
                alldeps = True
                for d in deps:
                    if mingwpkg.match(d) and d.replace('-x86_64-', '-i686-') not in sprovs:
                        alldeps = False
                        break
                if args.verbose and not alldeps:
                    sname = p.name.replace('-x86_64-', '-i686-')
                    blockers = set(d.replace('-x86_64-', '-i686-') for d in deps if mingwpkg.match(d)) - sprovs
                    forward[sname] = blockers
                    for b in blockers:
                        reverse.setdefault(b, set()).add(sname)

                if alldeps and p.base not in PKGBASE_BLACKLIST and \
                        p.name.replace('-x86_64-', '-i686-') not in s:
                    bases.add(p.base)
                    newprovs.add(p.name.replace('-x86_64-', '-i686-'))
                    for prov in p.provides:
                        newprovs.add(prov.replace('-x86_64-', '-i686-'))
            sprovs.update(newprovs)
            if args.verbose:
                print("Blocked dependency tree for clang32:")
                for p in reverse:
                    if p not in forward or forward[p] == set((p,)):
                        dep_tree(p, forward, reverse)

    else:
        bases = set(p.base for p in r if p.base not in PKGBASE_BLACKLIST)

    pkgbuild.enable_arch(bases, "clang32", "mingw32")
