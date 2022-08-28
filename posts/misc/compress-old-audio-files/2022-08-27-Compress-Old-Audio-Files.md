---
layout: post
title: "Compress Old Audio Files"
tags: [misc, ffmpeg]
inline_default_language: shell
---

We the pass of the years one keeps storing files, music in my case.

A few thousands.

But technology improved in this sense and new encoders exist that can
compress (loosely) the same audio with the same quality but at a much
smaller bit rate, and therefore, resulting in much smaller files.

Quick and dirty script follows!<!--more-->

## Encoders & containers

The current documentation of [FFmpeg](https://ffmpeg.org/) gives a ranking of the encoders
available, from best (left) to not so good (right):

```
libopus > libvorbis >= libfdk_aac > libmp3lame >= eac3/ac3 > aac > libtwolame > vorbis > mp2 > wmav2/wmav1
```

So the idea is to re-encode an arbitrary audio file to `libopus`:


```shell
ffmpeg -i $fn -acodec libopus $name
```

For the output file `ffmpeg` can save the audio into a container.
Different container files exists (`.m4a`, `.mp4`, `.ogg`, `.flv`) but
today's internet stream platforms use `.webm`.

{% call marginnotes() %}
You could write directly `.opus`, the raw encoded audio, without a
container and get even smaller files.
{% endcall %}

I'll go with that.

## Bit rates

One of the things of better encoders is that we can use a lower bit rate
without losing quality, as long as we are in the expected numbers for
which the encoder was designed.

For `libopus` we need  bit rates of 32kbps or larger.

Doing a quick, totally subjective test, ~50k is the smallest bit rate
that maintains the same quality of my files (which range between 96k and
128k MP3).

```shell
ffmpeg -i $fn -acodec libopus -b:a 50k $name.webm
```

Final tweak, I have some videos which I only care their audio. We can
instruct `ffmpeg` to get those with the "no video" option (`-nv`).

## Scripting

The [`compress_audio.sh`]({{ asset('compress_audio.sh') }})  script follows:

```shell
#!/bin/bash

set -euo pipefail
shopt -s nocaseglob

if [ "$#" != "1" ]; then
    echo "Usage $0 <target dir>"
    exit 1
fi

cd "$1"
echo  "Processing $(pwd)..."

IFS=$'\n'
for fn in $(ls *.mp3 *.ogg *.wav *.wma *.m4a *.avi *.opus); do
    name=$(basename -- "$fn")
    ext="${name##*.}"
    name="${name%.*}"

    # Take the input (-i) file, ignore any video stream (-vn)
    # and change its audio codec (-acodec) tto the codec libopus
    # and change its audio bitrate (-b:a) to 50k
    # and save it under the same name but with .webm extension
    ffmpeg -i "$fn" -vn -acodec libopus  -b:a 50k "$name.webm"

    rm "$fn"
done
```

The script processes the files inside a folder. Any error and the
processing will stop and fail so the input file will not be deleted
(`rm "$fn"`).

The script does *not* work recursively, instead I use `find`.

```shell
find . -type d -exec compress_audio.sh {} \;
```

This is on purpose: if `compress_audio.sh` fails, that folder is skipped
(no file is further processed or removed) but the whole recursive scan
keeps on (`find` will not stop on an error).

## Results

The ~3k audio files with a total size of ~20GB was processed in ~2hs
with a final total size of ~7GB, a ~65% reduction. Not bad.

That only counted for audio files. Extracting the audio from videos and
deleting the videos additionally saved a few hundred of megabytes more.

