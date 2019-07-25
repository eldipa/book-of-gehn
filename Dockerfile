FROM jekyll/jekyll:3.6

COPY _docker/*.jar ./

RUN    apk update       \
    && apk add          \
        bash            \
        graphviz        \
        openjdk8-jre    \
        ttf-dejavu      \
    && mkdir -p /usr/bin/                       \
    && mkdir -p /usr/local/share/java/          \
    && mv *.jar /usr/local/share/java/

WORKDIR /srv/jekyll/
CMD jekyll serve --watch --drafts --host 0.0.0.0

