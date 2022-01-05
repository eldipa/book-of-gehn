FROM debian:bullseye-20210621

RUN apt-get -y update                           \
 && DEBIAN_FRONTEND=noninteractive apt-get --no-install-recommends -y install \
            apt-utils                           \
            bash                                \
            build-essential                     \
            clang-format                        \
            fuse3                               \
            ghostscript                         \
            git                                 \
            graphviz                            \
            less                                \
            libfuse3-dev                        \
            optipng                             \
            pandoc                              \
            pkg-config                          \
            preview-latex-style                 \
            procps                              \
            python3                             \
            python3-pip                         \
            python3-setuptools                  \
            python3-venv                        \
            sudo                                \
            vim                                 \
            wget                                \
 && apt-get clean                               \
 && rm -rf /var/lib/apt/lists/                  \
 && groupadd admin                              \
 &&  echo '%admin  ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/admin       \
 &&  chmod 0400 /etc/sudoers.d/admin                                    \
 &&  useradd -s /bin/bash -u 1000 -M -g 1000 user                       \
 &&  usermod -aG sudo user                                              \
 &&  usermod -aG admin user                                             \
 &&  mkdir -p /home/user                                                \
 &&  chown -R user /home/user                                           \
 && git clone git://github.com/gittup/tup.git   \
 && cd tup                                      \
 && chmod u+x ./bootstrap.sh                    \
 && CFLAGS="-g" ./build.sh                      \
 && mv build/tup /usr/bin/                      \
 && chmod a+x /usr/bin/tup                      \
 && cd ..                                       \
 && rm -R tup/

RUN apt-get -y update                           \
 && DEBIAN_FRONTEND=noninteractive apt-get --no-install-recommends -y install \
            npm                                 \
 && apt-get clean                               \
 && rm -rf /var/lib/apt/lists/

RUN pip3 install                                \
            j2cli                               \
            dot2tex                             \
            panflute==2.1.3                     \
            pygments                            \
            python-frontmatter                  \
            fonttools[woff]                     \
            feedgen                             \
 && npm install -g sass                         \
 && npm install -g clean-css-cli                \
 && npm install -g uglify-js                    \
 && wget https://github.com/jgm/pandoc/releases/download/2.16.2/pandoc-2.16.2-1-amd64.deb \
 && sha256sum pandoc-2.16.2-1-amd64.deb | grep -q '^2001d93463c003f8fee6c36b1bfeccd551ab6e35370b24f74f457e3f6dffb8b7 ' \
 && dpkg -i pandoc-2.16.2-1-amd64.deb  \
 && rm -f pandoc-2.16.2-1-amd64.deb

