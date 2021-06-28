#!/usr/bin/env python

from __future__ import print_function

import argparse
import fileinput
import io
import json
import os
import re
import sys
import tarfile
from typing import Any, Dict, Tuple, List, Set, Iterable
from urllib.request import urlopen

import utils

def parse_desc(t: str) -> Dict[str, List[str]]:
    d: Dict[str, List[str]] = {}
    cat = None
    values: List[str] = []
    for l in t.splitlines():
        l = l.strip()
        if cat is None:
            cat = l
        elif not l:
            d[cat] = values
            cat = None
            values = []
        else:
            values.append(l)
    if cat is not None:
        d[cat] = values
    return d


def parse_repo(url: str) -> Dict[str, Dict[str, List[str]]]:
    sources: Dict[str, Dict[str, List[str]]] = {}
    print("Loading %r" % url, file=sys.stderr)

    with urlopen(url) as u:
        with io.BytesIO(u.read()) as f:
            with tarfile.open(fileobj=f, mode="r:gz") as tar:
                packages: Dict[str, list] = {}
                for info in tar.getmembers():
                    package_name = info.name.split("/", 1)[0]
                    infofile = tar.extractfile(info)
                    if infofile is None:
                        continue
                    with infofile:
                        packages.setdefault(package_name, []).append(
                            (info.name, infofile.read()))

    for package_name, infos in sorted(packages.items()):
        t = ""
        for name, data in sorted(infos):
            if name.endswith("/desc"):
                t += data.decode("utf-8")
            elif name.endswith("/depends"):
                t += data.decode("utf-8")
            elif name.endswith("/files"):
                t += data.decode("utf-8")
        desc = parse_desc(t)
        sources[package_name] = desc
    return sources

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Mark PKGBUILDs for clang32')
    parser.add_argument('--allclang64', action='store_true')
    args = parser.parse_args()

    r = parse_repo("https://repo.msys2.org/mingw/clang64/clang64.db")
    #json.dump(r, sys.stdout, sort_keys=True, indent=2)
    if not args.allclang64:
        s = parse_repo("https://repo.msys2.org/mingw/clang32/clang32.db")
        #json.dump(s, sys.stdout, sort_keys=True, indent=2)
        sprovs = set()
        for p in s.values():
            sprovs.add(p['%NAME%'][0])
            for prov in utils.split_depends(p.get('%PROVIDES%', list())):
                sprovs.add(prov)

        bases = set()
        mingwpkg = re.compile(r"^mingw-w64-clang-")
        for p in r.values():
            deps = utils.split_depends(p.get('%DEPENDS%', list()))
            deps.update(utils.split_depends(p.get('%MAKEDEPENDS%', list())))
            alldeps = True
            for d in deps:
                if mingwpkg.match(d) and d.replace('-x86_64-', '-i686-') not in sprovs:
                    alldeps = False
                    break
            if alldeps:
                bases.add(p['%BASE%'][0])
    else:
        bases = set((base for desc in r.values() for base in desc['%BASE%']))

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
