#!/bin/bash

set -e
set -o pipefail

docker build                                \
    -t blog-env                             \
    -f docker/md.Dockerfile          \
    docker/
