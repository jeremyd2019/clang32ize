#!/usr/bin/env python

import sys
from collections import namedtuple

from pacdb import pacdb
import pkgbuild

_Repo = namedtuple('_Repo', ("db", "pkg_prefix"))

clangarm64 = _Repo(pacdb.mingw_db_by_name("clangarm64"), "mingw-w64-clang-aarch64")
clang64 = _Repo(pacdb.mingw_db_by_name("clang64"), "mingw-w64-clang-x86_64")

clang64_provides = {prov: pkg.name for pkg in clang64.db for prov in pkg.provides}

def xfrm_name(pkgname):
    return pkgname.replace(clang64.pkg_prefix, clangarm64.pkg_prefix, 1)

def do_pkg(pkgname, done=None):
    if done is None:
        done = set()
    pkg = clang64.db.get_pkg(clang64_provides.get(pkgname, pkgname))
    xfrmed_name = xfrm_name(pkg.name)

    if xfrmed_name not in clangarm64.db:
        base = pkg.base
        print(base)
        done.add(base)
        deps = pkg.depends.keys() | pkg.makedepends.keys()
        for dep in deps:
            dep = clang64_provides.get(dep, dep)
            xfrmed_dep = xfrm_name(dep)
            if xfrmed_dep not in clangarm64.db:
                if clang64.db.get_pkg(dep).base in done:
                    print("WARNING: circular dep found!", xfrmed_dep, file=sys.stderr)
                else:
                    do_pkg(dep, done)
    return done


pkgname = sys.argv[1]
if not pkgname.startswith(clang64.pkg_prefix):
    pkgname = "-".join((clang64.pkg_prefix, pkgname))
bases = do_pkg(pkgname)

pkgbuild.enable_arch(bases, "clangarm64", "clang64")
