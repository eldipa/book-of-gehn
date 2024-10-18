#!/usr/bin/env python3

import frontmatter
from frontmatter import Post

import sys, os, yaml

# Usage:
#   extract_front_matter  input-src-file  output-content-file  output-yml-file [input-yml-file...]
#
# From the input-src-file, extract the front matter (yaml) and merge it with, the possible empty,
# list of input-yml-files.
#
# This merge works as follows:
#  - The first input-yml-file works as a starting point
#  - The second input-yml-file is merged into the former, overriding anything that is present in both
#  - The third is merged into what was merged before
#  - This keeps working until no more input-yml-file left; then the yaml extracted
#    from input-src-file (the front matter) is merged into the former merged yamls.
#
# The program writes in output-yml-file the resulting of the merged yamls and
# in output-content-file the input-src-file but without the front matter.
#
# The input files (input-src-file and input-yml-file(s)) can be either normal files
# or yaml files. In the former case, the yamls are assumed to be in the front matter.
#
# If no front-matter exists, fail.
src_fpath, content_dst_fpath, yaml_dst_fpath, *more_yaml_src_fpaths = sys.argv[1:]

def extract_front_matter(fpath : str) -> Post:
    '''
    Extract the front matter (aka frontmatter.Post) from the given file.
    If the file is a yaml file, build a fake Post with an empty content
    and the yaml data as the Post's metadata.
    Otherwise, create a Post from the given file where the metadata
    and content are extracted from it.
    '''
    with open(fpath, 'rt') as f:
        if fpath.endswith('.yaml') or fpath.endswith('.yml'):
            # No content, fake a front matter from a yaml file
            yml = yaml.safe_load(f.read())
            return Post('', **yml)
        else:
            return frontmatter.loads(f.read())

def mergeinto(base: Post, override: Post):
    '''
    Merge the override front matter into the base inline.
    '''
    if override.content:
        base.content = override.content

    for k in override.keys():
        base[k] = override[k]

def extract_and_merge_front_matters(src_fpath, more_yaml_src_fpaths):
    '''
    Extract the front matter from src_fpath file and more_yaml_src_fpaths files
    (see extract_front_matter) and merge them (see mergeinto) as follows:
       - The front matter of the first file in more_yaml_src_fpaths works as a starting point
       - The second's front matter is merged into the former, overriding anything that is present in both
       - This keeps working until no more files left in more_yaml_src_fpaths list;
         then extract the front matter from src_fpath and merged into the former merged
         and return that.
    '''
    merged: Post = Post('')
    for fpath in more_yaml_src_fpaths:
        post = extract_front_matter(fpath)
        mergeinto(merged, post)

    post = extract_front_matter(src_fpath)
    mergeinto(merged, post)

    return merged

merged = extract_and_merge_front_matters(src_fpath, more_yaml_src_fpaths)

# Write the content without the front-matter
with open(content_dst_fpath, 'wt') as f:
    f.write(merged.content)

# Write the metadata in a separated file.
merged.content = ''
metadata = frontmatter.dumps(merged)

# strips the "---" that delimit a yaml document
metadata = '\n'.join(metadata.split('\n')[1:-1])
with open(yaml_dst_fpath, 'wt') as f:
    f.write(metadata)

