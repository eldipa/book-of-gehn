#!/usr/bin/env python3
import sys

# Extract the excerpt of the src_fpath and write it in dst_fpath.
#
# The excerpt is any (possibly empty) text from the begin of the file
# until the first location of the excerpt_token (not included).
#
# If no excerpt_token is given (it is empty), raise an error.
# If the excerpt_token is not found, assume an empty excerpt.
src_fpath, excerpt_token, dst_fpath = sys.argv[1:]

if not excerpt_token.strip():
    raise Exception("Empty excerpt_token")

with open(src_fpath, 'rt') as f:
    content = f.read()

excerpt_end = content.find(excerpt_token)
if excerpt_end > 0:
    excerpt = content[:excerpt_end]
else:
    excerpt = ''

with open(dst_fpath, 'wt') as f:
    f.write(excerpt)
