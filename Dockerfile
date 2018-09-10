FROM debian:stretch

ENV BUNDLE_SILENCE_ROOT_WARNING=1

COPY Gemfile .

RUN    buildeps=' \
            make        \
            ruby-dev    \
            gcc         \
            build-essential     \
            zlib1g-dev  \
       ' \
    && apt-get update \
    && apt-get install -y --no-install-recommends ruby $buildeps \
    && mkdir -p /usr/local/etc \
    && { \
                echo 'install: --no-document';   \
                echo 'update: --no-document';    \
       } >> /usr/local/etc/gemrc                 \
    && gem install bundler                   \
    && bundle install                        \
    && apt-get purge -y $buildeps            \
    && apt-get purge -y --auto-remove        \
    && apt-get clean                         \
    && rm -rf /var/lib/apt/lists/*


WORKDIR /srv/jekyll/
CMD bundle exec jekyll serve --incremental --drafts --host 0.0.0.0

