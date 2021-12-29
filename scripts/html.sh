#!/bin/bash
set -e
set -o pipefail

if [ "$#" != 2 ]; then
    echo "Invalid number of arguments: $#."
    echo "Usage: $0 <input file> <out file>"
    exit 1
fi


. scripts/x/run_in_docker.sh

# This is the way that we have to communicate to Panflute's filter
# which file must log
#export PANFLUTE_TRACE_FILENAME="dbg/$(basename -s .tex "$2").panflute-trace"

mkdir -p "$(dirname $2)"
pandoc \
    -f markdown-tex_math_dollars-tex_math_single_backslash-tex_math_double_backslash \
    -t html \
    -o "$2" \
    "$1"
