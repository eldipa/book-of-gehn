#!/usr/bin/python3

import sys, os
from fontTools.ttLib import TTFont

try:
    srcfile, dstfile = sys.argv[1:]
except:
    print(f"Usage {sys.argv[0]} <input file> <output file>")
    print()
    print(f"Example: {sys.argv[0]} foo.ttf out/fonts/foo.woff2")
    sys.exit(1)

target = os.path.splitext(dstfile)[1][1:]

f = TTFont(srcfile)
f.flavor = target

dstfolder = os.path.dirname(dstfile)
if dstfolder:
    os.makedirs(dstfolder, exist_ok=True)

f.save(dstfile)
