import sys, os

# Usage:
#   py <drawio file> <dst folder>
#
# Take a PDF file (expected to be an exported diagram from Drawio, next
# to the given Drawio file)
# and convert it to SVG with pdf2svg.
# Then, hack it (patch) to to make its background transparent.
#
# The final patched SVG is saved in the destination folder.
#
# Also, it copies the Drawio file expected to be next the PDF file


dioname = sys.argv[1]
dstfolder = sys.argv[2]

dstfolder = os.path.abspath(dstfolder)

if not os.path.exists(dioname):
    raise Exception(f"File {dioname} not found")

basename, ext = os.path.splitext(dioname)
if ext != '.drawio':
    raise Exception(f"File {dioname} is not a drawio")

pdfname = basename + '.pdf'
if not os.path.exists(pdfname):
    raise Exception(f"File {pdfname} is not a PDF")

if not os.path.isdir(dstfolder):
    raise Exception(f"The destination folder {dstfolder} does not exist (or it is not a folder)")

tmpname = basename + '.tmp'
svgname = basename + '.svg'

svgname = os.path.join(dstfolder, os.path.split(svgname)[1])

assert "'" not in dioname
assert '"' not in dioname
assert '\\' not in dioname

# Copy the DrawIO file into the folder
os.system(f"cp '{dioname}' '{dstfolder}/'")
os.system(f"chmod 0644 {dstfolder}/*.drawio")

# Convert the PDF to SVG
os.system(f"pdf2svg '{pdfname}' '{tmpname}'")


# HACK: we are asumming that this is what defines the backgound of SVG
# We just remove it.
# <path style=" stroke:none;fill-rule:nonzero;fill:rgb(100%,100%,100%);fill-opacity:1;" d="M 0 0 L 391 0 L 391 241.945312 L 0 241.945312 Z M 0 0 "/>
found_cnt = 0
with open(tmpname, 'rt') as srcfile, open(svgname, 'wt') as dstfile:
    for line in srcfile:
        if (
                "stroke:none" in line   and \
                "fill-rule:nonzero" in line and \
                "fill:rgb(100%,100%,100%)" in line and \
                "fill-opacity:1" in line and \
                "d=\"M 0 0" in line and \
                line.startswith("<path ")
            ):
            found_cnt += 1
            assert line.endswith("/>\n")

            # drop the line
            continue

        dstfile.write(line)

if found_cnt == 0:
    print("WARNING: no background line was found!")
    sys.exit(1)
elif found_cnt >= 2:
    print(f"WARNING: {found_cnt} background lines were found!")
    sys.exit(1)
