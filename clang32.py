#!/usr/bin/env python

from __future__ import print_function

import argparse
import fileinput
import io
import itertools
import json
import os
import re
import sys
import tarfile
from typing import Any, Dict, Tuple, List, Set, Iterable
from urllib.request import urlopen

from pacdb import pacdb

with urlopen("https://github.com/msys2/msys2-autobuild/releases/download/status/status.json") as f:
    x = json.load(f)

PKGBASE_BLACKLIST = frozenset(itertools.chain((
    "mingw-w64-rust",
), (pkg for pkg in x if "clang32" in x[pkg] and x[pkg]["clang32"]["status"] == "failed-to-build")))

del x

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Mark PKGBUILDs for clang32')
    parser.add_argument('--allclang64', action='store_true')
    parser.add_argument('--depth', type=int, default=1)
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
                if alldeps and p.base not in PKGBASE_BLACKLIST and \
                        p.name.replace('-x86_64-', '-i686-') not in sprovs:
                    bases.add(p.base)
                    newprovs.add(p.name.replace('-x86_64-', '-i686-'))
                    for prov in p.provides:
                        newprovs.add(prov.replace('-x86_64-', '-i686-'))
            sprovs.update(newprovs)
    else:
        bases = set(p.base for p in r if p.base not in PKGBASE_BLACKLIST)

    linere = re.compile(r"^mingw_arch=.*'mingw32'(?!.*'clang32').*$")
    for base in bases:
        if not os.path.exists(os.path.join(base, "PKGBUILD")):
            with urlopen("https://packages.msys2.org/api/search?query=%s&qtype=pkg" % base) as f:
                x = json.load(f)
            base = x["results"]["exact"]["source_url"].rsplit("/", 1)[1]
        if not os.path.exists(os.path.join(base, "PKGBUILD")):
            print('%s PKGBUILD not found!' % (base,), file=sys.stderr)
            continue
        with fileinput.input(os.path.join(base, "PKGBUILD"), inplace=True) as f:
            for line in f:
                if linere.match(line):
                    print(re.sub(r"'clang64'", "'clang64' 'clang32'", line), end="")
                else:
                    print(line, end="")
