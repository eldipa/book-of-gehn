#!/bin/sh
set -e
if [ ! -f "$1" ]; then
    echo "Input file '$1' does not exit. Abort."
    exit 1
fi

sed 's$@import url(https://fonts.googleapis.com/css2?family=\([^)]*\));$@import url(/css/\1.min.css);$g' $1 > $2
