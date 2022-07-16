#!/usr/bin/env python3

import sys, os, yaml

combined_meta_filename, out_filename = sys.argv[1:]

with open(combined_meta_filename, 'rt') as f:
    main = yaml.safe_load(f.read())

with open(out_filename, 'wt') as f:
    for post in main['drafts']:
        f.write(post['public_html'] + '\n')

