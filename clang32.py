#!/usr/bin/env python

from __future__ import print_function

import fileinput
import io
import json
import os
import re
import sys
import tarfile
from typing import Any, Dict, Tuple, List, Set, Iterable
from urllib.request import urlopen

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
    r = parse_repo("https://repo.msys2.org/mingw/clang64/clang64.db")
    #json.dump(r, sys.stdout, sort_keys=True, indent=2)
    bases = set((base for desc in r.values() for base in desc['%BASE%']))

    linere = re.compile(r"^mingw_arch=(?!.*'clang32').*$")
    for base in bases:
        if not os.path.exists(os.path.join(base, "PKGBUILD")):
            with urlopen("https://packages.msys2.org/api/search?query=%s&qtype=pkg" % base) as f:
                x = json.load(f)
            base = x["results"]["exact"]["source_url"].rsplit("/", 1)[1]
        with fileinput.input(os.path.join(base, "PKGBUILD"), inplace=True) as f:
            for line in f:
                if linere.match(line):
                    print(re.sub(r"'clang64'", "'clang64' 'clang32'", line), end="")
                else:
                    print(line, end="")
