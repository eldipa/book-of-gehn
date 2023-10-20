#!/usr/bin/python3

import sys, os, subprocess

try:
    srcfile, convert, tmpfolder, dstfile = sys.argv[1:]
except:
    print(f"Usage {sys.argv[0]} <input file> <convert> <tmpfolder> <output file>")
    print()
    print(f"Example: {sys.argv[0]} foo.png T:Q64-S50 tmp/ out/i/foo.png    (quantize 64 colors, resize to 50%)")
    print(f"Example: {sys.argv[0]} foo.png T:Q0-S0 tmp/ out/i/foo.png    (no quantize colors, no resize)")
    print(f"Example: {sys.argv[0]} foo.png T: tmp/ out/i/foo.png    (no quantize colors, no resize)")
    sys.exit(1)

assert convert.startswith("T:")

if not os.path.isfile(srcfile):
    raise Exception(f"File '{srcfile}' not found.")

if not os.path.isdir(tmpfolder):
    raise Exception(f"Directory '{tmpfolder}' not found.")

dstfolder = os.path.dirname(dstfile)
if dstfolder:
    os.makedirs(dstfolder, exist_ok=True)

try:
    convert = convert[2:]
    quantize_s, resize_s = convert.rsplit('-', 2)
except:
    quantize = resize = 0
else:
    assert quantize_s[0] == 'Q'
    assert resize_s[0] == 'S'

    quantize = int(quantize_s[1:])
    resize = int(resize_s[1:])


if not quantize and not resize:
    cmd = f"optipng -o7 --strip all -quiet -out '{dstfile}' '{srcfile}'"
    subprocess.check_call(cmd, shell=True)
    sys.exit(0)

# Ok we need to quantize and/or resize before running optipng

tmpfolder = os.path.join(tmpfolder, dstfolder)
if dstfolder:
    os.makedirs(tmpfolder, exist_ok=True)

tmpfile = os.path.join(tmpfolder, os.path.basename(dstfile))

cmd = f"cat '{srcfile}'"

if resize:
    cmd += f" | convert - -resize '{resize}%' -"

if quantize:
    cmd += f" | convert - -colors '{quantize}' -"

cmd += f" > '{tmpfile}'"

subprocess.check_call(cmd, shell=True)
srcfile = tmpfile

cmd = f"optipng -o7 --strip all -quiet -out '{dstfile}' '{srcfile}'"
subprocess.check_call(cmd, shell=True)
os.system(f"rm '{tmpfile}'")
