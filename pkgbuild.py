#!/usr/bin/env python

import fileinput
import json
import os
import re
import sys

from urllib.request import urlopen

__all__ = ['enable_arch']

def enable_arch(bases, arch_to_enable, require_already_enabled_arch=None):
    if require_already_enabled_arch:
        require_already_enabled_arch = re.escape(f"'{require_already_enabled_arch}'")
    else:
        require_already_enabled_arch = ""

    arch_to_enable = re.escape(arch_to_enable)

    linere = re.compile(r"^mingw_arch=.*" + require_already_enabled_arch +
                        r"(?!.*'" + arch_to_enable + r"').*$")

    for base in bases:
        if not os.path.exists(os.path.join(base, "PKGBUILD")):
            with urlopen("https://packages.msys2.org/api/search?query=%s&qtype=pkg" % base) as f:
                x = json.load(f)
            base = x["results"]["exact"]["source_url"].rsplit("/", 1)[1]
            del x
        if not os.path.exists(os.path.join(base, "PKGBUILD")):
            print('%s PKGBUILD not found!' % (base,), file=sys.stderr)
            continue
        with fileinput.input(os.path.join(base, "PKGBUILD"), inplace=True) as f:
            for line in f:
                if linere.match(line):
                    print(re.sub(r"(\)\s*)$", r" '" + arch_to_enable + r"'\1", line), end="")
                else:
                    print(line, end="")
