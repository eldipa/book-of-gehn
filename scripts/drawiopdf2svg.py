#!/bin/env python
import sys, os, glob

# Usage:
#   py <src folder> <dst folder>
#
# Take a DrawIO file from the src folder and find in the same folder
# one or more PDF files and convert them to SVG with pdf2svg.
# Then, hack them (patch) to to make theirs background transparent.
#
# The final patched SVG is saved in the destination folder.
#
# Also, it copies the Drawio file


srcfolder = sys.argv[1]
dstfolder = sys.argv[2]

srcfolder = os.path.abspath(srcfolder)
dstfolder = os.path.abspath(dstfolder)

if not os.path.isdir(srcfolder):
    raise Exception(f"The source folder {srcfolder} does not exist (or it is not a folder)")

if not os.path.isdir(dstfolder):
    raise Exception(f"The destination folder {dstfolder} does not exist (or it is not a folder)")

drawios= glob.glob(srcfolder + '/*.drawio')

if not drawios:
    raise Exception(f"No Drawio file was found in {srcfolder}")

if len(drawios) != 1:
    raise Exception(f"Found {len(drawios)} Drawio files but expected only 1")

dioname = drawios[0]
del drawios

assert "'" not in dioname
assert '"' not in dioname
assert '\\' not in dioname

pdfs = glob.glob(srcfolder + '/*.pdf')

if not pdfs:
    raise Exception(f"No PDF file was found in {srcfolder}")

# Copy the DrawIO file into the folder
os.system(f"cp '{dioname}' '{dstfolder}/'")
os.system(f"chmod 0644 {dstfolder}/*.drawio")

# Convert the PDFs to SVGs
for pdfname in pdfs:
    print(f"Processing {pdfname}")

    basename, _ = os.path.splitext(pdfname)
    tmpname = basename + '.tmp'
    svgname = basename + '.svg'

    # Write the SVG file directly in the destination folder
    svgname = os.path.join(dstfolder, os.path.split(svgname)[1])

    # Generate the SVG (not patched yet)
    os.system(f"pdf2svg '{pdfname}' '{tmpname}'")

    # HACK: we are asumming that this is what defines the backgound of SVG
    # We just remove it.
    # <path style=" stroke:none;fill-rule:nonzero;fill:rgb(100%,100%,100%);fill-opacity:1;" d="M 0 0 L 391 0 L 391 241.945312 L 0 241.945312 Z M 0 0 "/>
    # <rect x="0" y="0" width="312" height="156" style="fill:rgb(100%,100%,100%);fill-opacity:1;stroke:none;"/>
    found_cnt = 0
    with open(tmpname, 'rt') as srcfile, open(svgname, 'wt') as dstfile:
        for line in srcfile:
            if (
                    line.startswith("<path ")           and \
                    "stroke:none" in line               and \
                    "fill-rule:nonzero" in line         and \
                    "fill:rgb(100%,100%,100%)" in line  and \
                    "fill-opacity:1" in line            and \
                    "d=\"M 0 0" in line                 and \
                    1==1
               ) or (
                    line.startswith("<rect ")           and \
                    'x="0"' in line                     and \
                    'y="0"' in line                     and \
                    "stroke:none" in line               and \
                    "fill:rgb(100%,100%,100%)" in line  and \
                    "fill-opacity:1" in line            and \
                    1==1
                ):
                found_cnt += 1
                assert line.endswith("/>\n")

                # drop the line
                continue

            dstfile.write(line)

    if found_cnt == 0:
        print("WARNING: no background line was found!")
        #sys.exit(1)
    elif found_cnt >= 2:
        print(f"WARNING: {found_cnt} background lines were found!")
        #sys.exit(1)
