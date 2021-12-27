#!/bin/bash

set -e
set -o pipefail

if [ "$#" != 2 ]; then
    echo "Invalid number of arguments: $#."
    echo "Usage: $0 <input file> <out dir>"
    exit 1
fi

. scripts/x/run_in_docker.sh

optipng -o7 --strip all -quiet -out "$2" "$1"
