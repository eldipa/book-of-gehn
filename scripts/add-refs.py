#!/usr/bin/env python3

import sys, os, yaml

main_filename, out_filename, *flags = sys.argv[1:]

with open(main_filename, 'rt') as f:
    main = yaml.safe_load(f.read())

assert len(flags) % 2 == 0
refs = {}
for name, fname in zip(flags[0::2], flags[1::2]):
    refs[name] = fname

main['refs'] = refs

with open(out_filename, 'wt') as f:
    f.write(yaml.dump(main))
