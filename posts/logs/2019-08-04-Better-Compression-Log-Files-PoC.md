---
layout: post
title: Better Compression of Log Files (PoC)
tags: [scripting, string compression]
---

The logs present several patterns that are repeated again and again;
LZMA takes advantage of that and reaches very high compress ratios.

Doing a quick test, LZMA at the 6 level of compression, compressed
a 2.5 GB log into 147 MB very tight binary blog. A ratio of 94.069%,
not bad!

But could we get better results?
<!--more-->

Consider the following log:

```
2019-07-23T07:18:23.034218+00:00 host evaluator: info No evaluator for 4b7c9f29-f945-3641-e737-39c180263f85
2019-07-23T07:18:23.041248+00:00 host evaluator: info Submitted: 4b7c9f29-f945-3641-e737-39c180263f85
2019-07-23T07:18:23.041453+00:00 host evaluator: info Acknowledged: 4b7c9f29-f945-3641-e737-39c180263f85
2019-07-23T07:18:23.042580+00:00 host storage: info Processing 4b7c9f29-f945-3641-e737-39c180263f85
2019-07-23T07:18:23.119849+00:00 host exporter: info Sending message
2019-07-23T07:18:23.120344+00:00 host storage: info Finished processing 4b7c9f29-f945-3641-e737-39c180263f85 (0.07786840550879322s)
2019-07-23T07:18:23.132928+00:00 host exporter: error lib: Could not create socket: Too many open files
2019-07-23T07:18:23.133107+00:00 host exporter: error Exception caught: Errno::EMFILE:Too many open files - getaddrinfo
2019-07-23T07:18:23.133280+00:00 host exporter: error exporter.rb:110:in `connect'
2019-07-23T07:18:23.133427+00:00 host exporter: error exporter.rb:110:in `initialize_socket'
```

The date times have a *lot* of redundancy that a standard compressor may
not compress.

The substring ``2019-07-23T07:18:23`` (date and time) is repeated
several times and can be compressed but the *microseconds* part isn't.

So here is my plan:
 - split the log file in two streams: date times on the one hand and texts
on the other
 - *delta encode* the date times
 - compress separately both streams using LZMA

The proof of concept is in [zlog repository](https://github.com/eldipa/zlog).

The results? The new ratio is 96.715%, the new compressed file is 44.615%
smaller than the former *straight* LZMA compressed file.

Compression  |  Size (bytes)        |   Compression Ratio
   :---:     |  :---:               |   :---:
None         | 2586369892           |   0
LZMA         | 153390408            |   94.069%
*Split* LZMA | 60047300 + 24907828  |   96.715%


### Open questions

The compressed date times represent the 41.480% of the total. The current
implementation encodes the deltas in 8 bytes and compresses the stream
using LZMA which may not be the best tool for this.

8 bytes perhaps is too much: if there is a log line each hour we can
represent the delta in microseconds using only 32 bits.

We could also pack them instead of compress them using
[frames of reference](https://github.com/lemire/FrameOfReference).
With a little of extra code, this would open the opportunity to
do searches by time without decompressing the whole thing.

LZMA and others are very good compressing repeated substrings
that are *closer* each other.

This is perfect of strings that represent ids in the logs
that appear in consecutive lines like
``4b7c9f29-f945-3641-e737-39c180263f85``

But what about substrings that are repeated everywhere in
a *time independent*?

Think in ``host evaluator: info No evaluator for``. It is very
likely to be repeated several times but if its *frequency* is
too low, several *other* lines could appear between one repetition
and the other which may confuse and reduce the performance
of the compressor.

Clustering the lines should bring them closer but if the operation
is not invertible without meta data (like the
[Burrows-Wheeler transform](https://en.wikipedia.org/wiki/Burrows%E2%80%93Wheeler_transform))
it may not be worthy.

Also, a clustering will go against of the
natural clustering of the *time dependent* strings. Not good.
