#!/usr/bin/env python3

import sys, os, yaml

out_filename, main_filename, *posts_yamls = sys.argv[1:]

with open(main_filename, 'rt') as f:
    main = yaml.safe_load(f.read())

posts = []
for fname in posts_yamls:
    with open(fname, 'rt') as f:
        post = yaml.safe_load(f.read())

    posts.append(post)

posts.sort(key=lambda p: p['date'], reverse=True)
main['posts'] = posts

with open(out_filename, 'wt') as f:
    f.write(yaml.dump(main))
