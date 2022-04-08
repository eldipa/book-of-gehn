#!/bin/bash

set -e
set -o pipefail

name=blog
run_in_docker() {
    local wd="/home/user/proj/book-of-gehn"
    local img=blog-env
    local user="1000:1000"
    sudo -E docker run                          \
        --device /dev/fuse                      \
        --cap-add SYS_ADMIN                     \
        --security-opt apparmor:unconfined      \
        --rm                                    \
        -u "$user"                              \
        -v "$wd":/mnt                           \
        -w /mnt                                 \
        -p '127.0.0.1:4000:4000'                \
        -h "$name"                              \
        --name "$name"                          \
        --add-host "$name:127.0.0.1"            \
        $EXTRA "$img" "$@"
}
