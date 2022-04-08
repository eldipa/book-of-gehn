#!/bin/bash

set -e
set -o pipefail

sudo docker build                           \
    -t blog-env                             \
    -f docker/md.Dockerfile          \
    docker/
