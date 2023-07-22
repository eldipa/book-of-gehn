---
layout: post
title: "TL;DR Screen Optimizations Results for Terminal Emulator Pyte"
tags: [python, pyte, byexample, optimization, performance, tldr, tl;dr]
inline_default_language: python
---

This post describes to some level of detail all the performance boosts
and speedups due the
[optimizations contributed](https://github.com/byexamples/pyte/tree/Screen-Optimizations)
to [pyte](https://github.com/selectel/pyte) and
[summarized here](/articles/2022/07/15/Sparse-Aware-Optimizations-for-Terminal-Emulator-Pyte.html)

For large geometries (240x800, 2400x8000), `Screen.display` runs orders
of magnitud faster and consumes between 1.10 and 50.0 times less memory.

For smaller geometries the minimum improvement was of 2 times faster.

`Stream.feed` is now between 1.10 and 7.30 times faster and if
`Screen` is tuned, the speedup is between 1.14 and 12.0.

For memory usage, `Stream.feed` is between 1.10 and 17.0 times lighter
and up to 44.0 times lighter if `Screen` is tuned.

`Screen.reset` is between 1.10 and 1.50 slower but several cases improve
if the `Screen` is tuned (but not all).

However there are a few regressions, most of them small but some
up to 4 times.

At the moment of writing this post, the PR is still pending to review.
<!--more-->

# What is this PR about?

Optimization. My goal was to make `pyte` faster and lighter specially
for large geometries (think in a screen of 240x800 or 2400x8000 size).

# Context (background)

While `pyte` implements a sparse buffer, most of its algorithms
are not aware and they don't take advantage of that making the terminal
emulation really slow and consuming a lot of memory.

# Contributions

 - Upgrade `pyperf`
 - Extended the benchmark tests to test `Screen.display`,
`Screen.resize` and `Screen.reset` under different geometries (24x80,
240x800, 2400x8000, 24x8000, 2400x80). With these the benchmark takes
much more time (sorry!) but it gives a deeper view of how `pyte` works.
 - Fixed a bug in the benchmarks that used `Stream` instead of
`ByteStream`. The use of the former led to an incorrect interpretation
of the new lines; the use of `ByteStream` fixed that and it is aligned
with the `test_input_output.py` tests.
 - Optimize `Screen.display` to work (approx) linearly with the input
and not with the size of the screen (quadratic). Improved by a lot
both for runtime and memory (specially for large geometries).
 - Implement `Screen.compressed_display` that works similar to
`Screen.display` but it allows to *"strip"* empty space from the left or
right and *"filter"* empty lines on top and bottom of the screen
reducing time and memory.
 - Optimize `Screen.draw` with caching of attributes and methods (the
same optimizations already present in `Stream._parser_fsm`).
 - Refactor out `Char`'s foreground, bold, blink (...) into a separated
`namedtuple` `CharStyle`. When possible, reuse the same style for
multiple characters reducing the memory usage at the expense of an
additional lookup (instead of `char.fg` you have `char.style.fg`).
 - Make `Char` a mutable object allowing changes in the `data` and
`width` fields to be in-place instead of creating a new `Char` object.
 - Sparse-aware algorithms for `Screen.index` and `Screen.reverse_index`
that improved indirectly `Screen.draw` and `Stream.feed`.
 - Sparse-aware algorithms for `Screen.resize`
 - Sparse-aware algorithms for `Screen.tabstop`
 - Sparse-aware algorithms for `ScreenHistory.prev_page` and
`ScreenHistory.next_page`.
 - Sparse-aware algorithms for `Screen.insert_characters`,
`Screen.delete_characters`, `Screen.insert_lines` and
`Screen.delete_characters` that improved the performance of *"terminal
aware"* programs.
 - Statistics about `Screen`'s buffer and lines to have insight about
the sparsity and usage of these elements. (The API is not not standard
like `DebugScreen`).
 - Make the public attribute `Screen.buffer` return a `BufferView`.
Retrieve of lines from it yield `LineView` instead of `Line` objects.
This adds an overhead on user code but allows a separation between the
public part and the internals. Iterate over `LineView` still yields
`Char` objects as usual (to much high penalty otherwise).
 - Make the public `Screen.history`'s `top` and `bottom` queues return
`LineView` and not `Line` objects
 - Make the private attribute `Screen._buffer` a `dict` and not a
`defaultdict`. This prevent adding entries unintentionally that would
make the buffer less sparse and therefore slow.
 - If the current cursor attributes (style) matches the default
attributes of the screen, do not write explicit spaces on erase methods
(`Screen.erase_characters`, `Screen.erase_in_line` and
`Screen.erase_in_display`)
 - When `disable_display_graphic` is `True` prevent
`Screen.select_graphic_rendition` to change the cursor attributes
(style). If the cursor attrs don't change, we can optimize the erase
methods. The flag is `False` by default.
but just remove the chars from the buffer. This makes speedup other
algorithms and maintain high the sparsity (and consume less memory).
 - When `track_dirty_lines` is `False` use a `NullSet` for `Screen.dirty`
attribute to not consume any
memory and discard any element, disabling effectively the dirty
functionality. This saves time and memory for large geometries.
The flag is `True` by default.
 - Make `Screen.margin` always a `Margin` object so we can avoid
checking if it is `None` or not.

## Compatibility changes

The following are changes in the API that may break user code. A special
care was taken to avoid this situation.

 - `Char` is not longer a `namedtuple` so things like `_replace` are
gone. If necessary we could reimplement the API of `namedtuple` but I
don't think users will use.
 - `Char` is mutable but the user must not relay on this: changes to
character will have undefined behaviour. The user must use always the
API provided by `Screen`.
 - `Char` not longer has attributes for `fg`, `bg`, `bold`. Instead, it has a
single read-only `CharStyle`. The `Char` class implements  `fg`, `bg`, `bold`
as *properties* to do the lookup to the style behind the scene. User
code should not break then.
 - `Screen.buffer` now is a property that returns a `BufferView` with a
similar API to a dictionary. It yields `LineView` objects instead of
`Line` objects. These in turn yield `Char` objects (not views). User can
still iterate over the lines and chars as if the buffer were a dense
array and not a sparse array as it is really.
Like any view, these are valid until the next modification of the
screen. This change may break user code if it uses `buffer` in another
way.
 - The queues `top` and `bottom` of `ScreenHistory.history` contain
`LineView` and not `Line` objects. This may break user code.
 - `Screen.margin` is always a `Margin` object: the `None` value is not
longer supported.


# Results

## High level results

For large geometries (240x800, 2400x8000), `Screen.display` runs orders
of magnitud faster and consumes between 1.10 and 50.0 times less memory.

For smaller geometries the minimum improvement was of 2 times faster.

`Stream.feed` is now between 1.10 and 7.30 times faster and if
`Screen` is tuned, the speedup is between 1.14 and 12.0.

However there is a regression for the `mc.input` test of up to 4 times
slower.

For memory usage, `Stream.feed` is between 1.10 and 17.0 times lighter
and up to 44.0 times lighter if `Screen` is tuned.

Screen.reset is between 1.10 and 1.50 slower but several cases improve
if the `Screen` is tuned (but not all).


## TL;DR - Numbers overview

The following is a overview of the numbers got. To make this post
as short as possible, the some results were omitted
(rows omitted are marked with `:::`).

Full benchmark results are listed below; people is encouraged to do
their own benchmarks for cross validation.

 - [0.8.1 - runtime]({{ asset('screen-optimizations-benchmark-results/0.8.1.json') }})
 - [0.8.1 - tracemalloc]({{ asset('screen-optimizations-benchmark-results/0.8.1.tracemalloc.json') }})
 - [optimized (default) - runtime]({{ asset('screen-optimizations-benchmark-results/0.8.1+screen-optimizations+default-conf.json') }})
 - [optimized (default) - tracemalloc]({{ asset('screen-optimizations-benchmark-results/0.8.1+screen-optimizations+default-conf.tracemalloc.json') }})
 - [optimized (tuned) - runtime]({{ asset('screen-optimizations-benchmark-results/0.8.1+screen-optimizations+custom-conf.json') }})
 - [optimized (tuned) - tracemalloc]({{ asset('screen-optimizations-benchmark-results/0.8.1+screen-optimizations+custom-conf.tracemalloc.json') }})

### `Screen.display`

`Screen.display` was optimized to generate large chunks of spaces
very quickly.

For large geometries, this has an huge impact on the performance:

```
+----------------------------------------------------------+----------+-----------------------------------------+
| Benchmark                                                | 0.8.1    | 0.8.1+screen-optimizations+default-conf |
+==========================================================+==========+=========================================+
| [screen_display 2400x8000] mc.input->Screen              | 6.69 sec | 9.95 us: 672459.98x faster              |
| [screen_display 2400x8000] mc.input->HistoryScreen       | 6.60 sec | 10.3 us: 638209.07x faster              |
| [screen_display 2400x8000] vi.input->HistoryScreen       | 6.80 sec | 132 us: 51648.56x faster                |
| [screen_display 2400x8000] vi.input->Screen              | 6.60 sec | 130 us: 50691.68x faster                |
    :::                 ::::                                    ::::         :::
| [screen_display 240x800] ls.input->HistoryScreen         | 70.1 ms  | 248 us: 283.21x faster                  |
| [screen_display 240x800] ls.input->Screen                | 69.1 ms  | 244 us: 282.76x faster                  |
| [screen_display 240x800] top.input->Screen               | 68.2 ms  | 249 us: 273.98x faster                  |
| [screen_display 240x800] top.input->HistoryScreen        | 67.3 ms  | 257 us: 261.64x faster                  |
    :::                 ::::                                    ::::         :::
| [screen_display 24x80] find-etc.input->HistoryScreen     | 670 us   | 101 us: 6.63x faster                    |
| [screen_display 24x80] find-etc.input->Screen            | 640 us   | 97.9 us: 6.54x faster                   |
| [screen_display 24x80] vi.input->HistoryScreen           | 606 us   | 115 us: 5.27x faster                    |
| [screen_display 24x80] vi.input->Screen                  | 584 us   | 117 us: 5.00x faster                    |
| [screen_display 24x80] cat-gpl3.input->Screen            | 605 us   | 189 us: 3.21x faster                    |
| [screen_display 24x80] cat-gpl3.input->HistoryScreen     | 605 us   | 195 us: 3.11x faster                    |
| [screen_display 24x80] ls.input->HistoryScreen           | 609 us   | 221 us: 2.75x faster                    |
| [screen_display 24x80] ls.input->Screen                  | 585 us   | 221 us: 2.65x faster                    |
| [screen_display 24x80] top.input->Screen                 | 567 us   | 244 us: 2.33x faster                    |
| [screen_display 24x80] top.input->HistoryScreen          | 580 us   | 251 us: 2.32x faster                    |
| [screen_display 24x80] htop.input->HistoryScreen         | 564 us   | 269 us: 2.10x faster                    |
| [screen_display 24x80] htop.input->Screen                | 559 us   | 273 us: 2.05x faster                    |
```

`Screen.display` takes advantage of the sparsity of the screen and therefore
it was indirectly beneficed by the optimizations done across `Screen`
to avoid filling it with *false entries*.

`Screen.display` it was also optimized on memory (`tracemalloc`) avoiding
then append of each space character separately when they could be
appended in a single chunk.

```
+--------------------------------------------------------------+-------------------+-----------------------------------------------------+
| Benchmark                                                    | 0.8.1.tracemalloc | 0.8.1+screen-optimizations+default-conf.tracemalloc |
+==============================================================+===================+=====================================================+
| [screen_display 2400x8000] ls.input->HistoryScreen           | 19.7 MB           | 408.1 kB: 49.43x faster                             |
| [screen_display 2400x8000] mc.input->HistoryScreen           | 19.7 MB           | 411.4 kB: 49.04x faster                             |
| [screen_display 2400x8000] mc.input->Screen                  | 19.7 MB           | 411.4 kB: 49.04x faster                             |
| [screen_display 2400x8000] ls.input->Screen                  | 19.7 MB           | 411.5 kB: 49.03x faster                             |
| [screen_display 2400x8000] vi.input->HistoryScreen           | 18.5 MB           | 404.7 kB: 46.84x faster                             |
| [screen_display 2400x8000] top.input->HistoryScreen          | 18.5 MB           | 408.3 kB: 46.43x faster                             |
| [screen_display 2400x8000] vi.input->Screen                  | 18.5 MB           | 408.5 kB: 46.40x faster                             |
| [screen_display 2400x8000] top.input->Screen                 | 18.5 MB           | 411.5 kB: 46.07x faster                             |
| [screen_display 2400x8000] htop.input->Screen                | 18.5 MB           | 1102.6 kB: 17.19x faster                            |
| [screen_display 2400x8000] htop.input->HistoryScreen         | 18.5 MB           | 1103.2 kB: 17.18x faster                            |
| [screen_display 2400x8000] cat-gpl3.input->HistoryScreen     | 19.5 MB           | 5392.6 kB: 3.70x faster                             |
| [screen_display 2400x8000] cat-gpl3.input->Screen            | 19.5 MB           | 5392.0 kB: 3.70x faster                             |
| [screen_display 240x800] mc.input->Screen                    | 513.2 kB          | 403.5 kB: 1.27x faster                              |
| [screen_display 240x800] ls.input->Screen                    | 517.0 kB          | 411.5 kB: 1.26x faster                              |
| [screen_display 240x800] ls.input->HistoryScreen             | 511.7 kB          | 408.1 kB: 1.25x faster                              |
| [screen_display 240x800] mc.input->HistoryScreen             | 510.4 kB          | 411.4 kB: 1.24x faster                              |
| [screen_display 2400x8000] find-etc.input->HistoryScreen     | 18.7 MB           | 16.6 MB: 1.12x faster                               |
| [screen_display 2400x8000] find-etc.input->Screen            | 18.7 MB           | 16.6 MB: 1.12x faster                               |
```

The only two regressions are:

```
| [screen_display 240x800] htop.input->HistoryScreen           | 408.7 kB          | 487.3 kB: 1.19x slower                              |
| [screen_display 240x800] htop.input->Screen                  | 405.8 kB          | 486.2 kB: 1.20x slower                              |
```

Not sure why this happen.


### `Stream.feed`

`stream.feed` was not modified but its runtime depends on `Screen`'s
performance.

For terminal programs that just write into then terminal, like
`cat-gpl3` and `find-etc`, `stream.feed` merely sends then input
to `Screen.draw` for rendering.

The method `Screen.draw` was optimized to avoid the modification
of the cursor internally and update it only at the exit. This saved a
few lookups.

While not been frequently called, `Screen.index` was the next bottleneck
for `Screen.draw`: it moves all the lines of the screen that it means
that all the entries of the buffer are rewritten.

`Screen.index` and `Screen.reverse_index` were optimized to take advantage
of the sparsity and to avoid adding false entries.

This resulted on a speedup across the tests:


```
+----------------------------------------------------------+----------+-----------------------------------------+
| Benchmark                                                | 0.8.1    | 0.8.1+screen-optimizations+default-conf |
+==========================================================+==========+=========================================+
| [stream_feed 2400x8000] vi.input->HistoryScreen          | 49.4 ms  | 6.70 ms: 7.38x faster                   |
| [stream_feed 2400x8000] top.input->HistoryScreen         | 7.35 ms  | 1.31 ms: 5.62x faster                   |
| [stream_feed 2400x8000] find-etc.input->HistoryScreen    | 2.92 sec | 543 ms: 5.38x faster                    |
| [stream_feed 240x800] ls.input->HistoryScreen            | 9.29 ms  | 1.75 ms: 5.31x faster                   |
| [stream_feed 24x80] top.input->HistoryScreen             | 6.61 ms  | 1.25 ms: 5.30x faster                   |
| [stream_feed 240x800] top.input->HistoryScreen           | 6.57 ms  | 1.24 ms: 5.29x faster                   |
| [stream_feed 240x800] cat-gpl3.input->HistoryScreen      | 215 ms   | 43.3 ms: 4.97x faster                   |
| [stream_feed 24x80] ls.input->HistoryScreen              | 6.26 ms  | 1.34 ms: 4.68x faster                   |
| [stream_feed 24x80] cat-gpl3.input->HistoryScreen        | 140 ms   | 31.9 ms: 4.38x faster                   |
| [stream_feed 240x800] find-etc.input->HistoryScreen      | 532 ms   | 123 ms: 4.32x faster                    |
| [stream_feed 2400x8000] vi.input->Screen                 | 13.7 ms  | 3.53 ms: 3.88x faster                   |
| [stream_feed 24x80] find-etc.input->HistoryScreen        | 294 ms   | 81.1 ms: 3.62x faster                   |
| [stream_feed 2400x8000] htop.input->HistoryScreen        | 122 ms   | 34.4 ms: 3.54x faster                   |
    :::                 ::::                                    ::::         :::
| [stream_feed 240x800] vi.input->Screen                   | 5.39 ms  | 2.67 ms: 2.02x faster                   |
| [stream_feed 24x80] mc.input->HistoryScreen              | 44.3 ms  | 24.4 ms: 1.82x faster                   |
| [stream_feed 2400x8000] htop.input->Screen               | 38.1 ms  | 21.4 ms: 1.78x faster                   |
| [stream_feed 240x800] htop.input->Screen                 | 23.2 ms  | 13.2 ms: 1.76x faster                   |
| [stream_feed 240x800] find-etc.input->Screen             | 134 ms   | 77.0 ms: 1.74x faster                   |
| [stream_feed 24x80] vi.input->Screen                     | 4.45 ms  | 2.57 ms: 1.73x faster                   |
| [stream_feed 24x80] htop.input->Screen                   | 20.8 ms  | 12.2 ms: 1.71x faster                   |
| [stream_feed 2400x8000] cat-gpl3.input->HistoryScreen    | 262 ms   | 157 ms: 1.67x faster                    |
| [stream_feed 240x800] mc.input->HistoryScreen            | 63.7 ms  | 43.8 ms: 1.45x faster                   |
| [stream_feed 2400x8000] ls.input->Screen                 | 7.77 ms  | 5.61 ms: 1.38x faster                   |
| [stream_feed 24x80] mc.input->Screen                     | 17.6 ms  | 13.1 ms: 1.34x faster                   |
| [stream_feed 2400x8000] find-etc.input->Screen           | 616 ms   | 501 ms: 1.23x faster                    |
| [stream_feed 2400x8000] cat-gpl3.input->Screen           | 170 ms   | 143 ms: 1.19x faster                    |
| [stream_feed 2400x8000] mc.input->HistoryScreen          | 259 ms   | 285 ms: 1.10x slower                    |
| [stream_feed 240x800] mc.input->Screen                   | 23.3 ms  | 32.3 ms: 1.39x slower                   |
| [stream_feed 2400x8000] mc.input->Screen                 | 71.2 ms  | 281 ms: 3.94x slower                    |
```

The `mc.input` however took much more time.


When `track_dirty_lines` is `False` and `disable_display_graphic` is `True`,
the overall performance increases even further.

```
+----------------------------------------------------------+----------+----------------------------------------+
| Benchmark                                                | 0.8.1    | 0.8.1+screen-optimizations+custom-conf |
+==========================================================+==========+========================================+
| [stream_feed 2400x8000] mc.input->HistoryScreen          | 259 ms   | 21.2 ms: 12.19x faster                 |
| [stream_feed 2400x8000] vi.input->HistoryScreen          | 49.4 ms  | 5.52 ms: 8.95x faster                  |
| [stream_feed 2400x8000] mc.input->Screen                 | 71.2 ms  | 10.8 ms: 6.60x faster                  |
| [stream_feed 2400x8000] find-etc.input->HistoryScreen    | 2.92 sec | 464 ms: 6.29x faster                   |
| [stream_feed 2400x8000] top.input->HistoryScreen         | 7.35 ms  | 1.27 ms: 5.80x faster                  |
| [stream_feed 2400x8000] htop.input->HistoryScreen        | 122 ms   | 22.3 ms: 5.45x faster                  |
| [stream_feed 2400x8000] vi.input->Screen                 | 13.7 ms  | 2.52 ms: 5.43x faster                  |
| [stream_feed 24x80] top.input->HistoryScreen             | 6.61 ms  | 1.23 ms: 5.38x faster                  |
| [stream_feed 240x800] ls.input->HistoryScreen            | 9.29 ms  | 1.73 ms: 5.37x faster                  |
| [stream_feed 240x800] cat-gpl3.input->HistoryScreen      | 215 ms   | 42.0 ms: 5.12x faster                  |
    :::                 ::::                                    ::::         :::
| [stream_feed 24x80] cat-gpl3.input->Screen               | 46.3 ms  | 17.2 ms: 2.69x faster                  |
| [stream_feed 240x800] top.input->Screen                  | 2.39 ms  | 913 us: 2.61x faster                   |
| [stream_feed 24x80] top.input->Screen                    | 2.36 ms  | 914 us: 2.58x faster                   |
| [stream_feed 2400x8000] ls.input->HistoryScreen          | 13.4 ms  | 5.39 ms: 2.50x faster                  |
| [stream_feed 24x80] htop.input->HistoryScreen            | 55.3 ms  | 22.6 ms: 2.44x faster                  |
    :::                 ::::                                    ::::         :::
| [stream_feed 240x800] vi.input->Screen                   | 5.39 ms  | 2.57 ms: 2.10x faster                  |
| [stream_feed 24x80] mc.input->HistoryScreen              | 44.3 ms  | 21.3 ms: 2.08x faster                  |
| [stream_feed 2400x8000] cat-gpl3.input->HistoryScreen    | 262 ms   | 132 ms: 1.99x faster                   |
| [stream_feed 240x800] find-etc.input->Screen             | 134 ms   | 76.3 ms: 1.76x faster                  |
| [stream_feed 24x80] vi.input->Screen                     | 4.45 ms  | 2.54 ms: 1.75x faster                  |
| [stream_feed 24x80] mc.input->Screen                     | 17.6 ms  | 10.6 ms: 1.66x faster                  |
| [stream_feed 2400x8000] ls.input->Screen                 | 7.77 ms  | 4.85 ms: 1.60x faster                  |
| [stream_feed 2400x8000] find-etc.input->Screen           | 616 ms   | 422 ms: 1.46x faster                   |
| [stream_feed 2400x8000] cat-gpl3.input->Screen           | 170 ms   | 118 ms: 1.44x faster                   |
```


On memory there is an improvement too:

```
+--------------------------------------------------------------+-------------------+-----------------------------------------------------+
| Benchmark                                                    | 0.8.1.tracemalloc | 0.8.1+screen-optimizations+default-conf.tracemalloc |
+==============================================================+===================+=====================================================+
| [stream_feed 2400x8000] vi.input->HistoryScreen              | 11.7 MB           | 686.8 kB: 17.45x faster                             |
| [stream_feed 2400x8000] vi.input->Screen                     | 4742.1 kB         | 538.0 kB: 8.81x faster                              |
| [stream_feed 2400x8000] htop.input->HistoryScreen            | 14.5 MB           | 3552.1 kB: 4.18x faster                             |
| [stream_feed 240x800] vi.input->HistoryScreen                | 2679.0 kB         | 686.8 kB: 3.90x faster                              |
| [stream_feed 2400x8000] top.input->HistoryScreen             | 2120.7 kB         | 611.8 kB: 3.47x faster                              |
| [stream_feed 2400x8000] htop.input->Screen                   | 11.5 MB           | 3408.2 kB: 3.45x faster                             |
| [stream_feed 2400x8000] top.input->Screen                    | 2155.1 kB         | 680.2 kB: 3.17x faster                              |
| [stream_feed 240x800] htop.input->HistoryScreen              | 2189.7 kB         | 1005.8 kB: 2.18x faster                             |
| [stream_feed 240x800] vi.input->Screen                       | 1107.7 kB         | 536.1 kB: 2.07x faster                              |
| [stream_feed 240x800] htop.input->Screen                     | 1782.7 kB         | 990.6 kB: 1.80x faster                              |
            :::                 ::::                                    ::::         :::
| [stream_feed 240x800] find-etc.input->HistoryScreen          | 2233.5 kB         | 1502.4 kB: 1.49x faster                             |
| [stream_feed 24x80] ls.input->HistoryScreen                  | 1554.3 kB         | 1086.0 kB: 1.43x faster                             |
| [stream_feed 24x80] cat-gpl3.input->HistoryScreen            | 1354.0 kB         | 960.1 kB: 1.41x faster                              |
| [stream_feed 24x80] top.input->Screen                        | 948.2 kB          | 680.2 kB: 1.39x faster                              |
| [stream_feed 24x80] vi.input->HistoryScreen                  | 954.7 kB          | 686.8 kB: 1.39x faster                              |
| [stream_feed 24x80] find-etc.input->HistoryScreen            | 1017.6 kB         | 774.9 kB: 1.31x faster                              |
| [stream_feed 240x800] top.input->HistoryScreen               | 763.6 kB          | 653.6 kB: 1.17x faster                              |
| [stream_feed 24x80] mc.input->HistoryScreen                  | 485.0 kB          | 417.6 kB: 1.16x faster                              |
| [stream_feed 24x80] htop.input->Screen                       | 936.1 kB          | 814.3 kB: 1.15x faster                              |
| [stream_feed 24x80] mc.input->Screen                         | 722.3 kB          | 651.6 kB: 1.11x faster                              |
```


The following are the tests that show regression on memory usage.

```
| [stream_feed 240x800] mc.input->Screen                       | 1842.2 kB         | 2577.4 kB: 1.40x slower                             |
| [stream_feed 240x800] mc.input->HistoryScreen                | 1793.2 kB         | 2548.1 kB: 1.42x slower                             |
| [stream_feed 2400x8000] mc.input->HistoryScreen              | 13.6 MB           | 22.3 MB: 1.64x slower                               |
| [stream_feed 2400x8000] ls.input->HistoryScreen              | 8422.1 kB         | 13.7 MB: 1.67x slower                               |
| [stream_feed 2400x8000] mc.input->Screen                     | 12.2 MB           | 22.3 MB: 1.82x slower                               |
```


When `track_dirty_lines` is `False` and `disable_display_graphic` is `True`, this is even better:

```
+--------------------------------------------------------------+-------------------+----------------------------------------------------+
| Benchmark                                                    | 0.8.1.tracemalloc | 0.8.1+screen-optimizations+custom-conf.tracemalloc |
+==============================================================+===================+====================================================+
| [stream_feed 2400x8000] mc.input->HistoryScreen              | 13.6 MB           | 414.1 kB: 33.60x faster                            |
| [stream_feed 2400x8000] mc.input->Screen                     | 12.2 MB           | 447.6 kB: 27.98x faster                            |
| [stream_feed 2400x8000] htop.input->Screen                   | 11.5 MB           | 600.5 kB: 19.59x faster                            |
| [stream_feed 2400x8000] vi.input->HistoryScreen              | 11.7 MB           | 665.4 kB: 18.01x faster                            |
| [stream_feed 2400x8000] htop.input->HistoryScreen            | 14.5 MB           | 1009.0 kB: 14.73x faster                           |
| [stream_feed 2400x8000] vi.input->Screen                     | 4742.1 kB         | 522.4 kB: 9.08x faster                             |
| [stream_feed 240x800] mc.input->HistoryScreen                | 1793.2 kB         | 417.4 kB: 4.30x faster                             |
| [stream_feed 240x800] mc.input->Screen                       | 1842.2 kB         | 447.6 kB: 4.12x faster                             |
| [stream_feed 240x800] vi.input->HistoryScreen                | 2679.0 kB         | 652.6 kB: 4.11x faster                             |
| [stream_feed 2400x8000] top.input->HistoryScreen             | 2120.7 kB         | 653.6 kB: 3.24x faster                             |
| [stream_feed 2400x8000] top.input->Screen                    | 2155.1 kB         | 680.6 kB: 3.17x faster                             |
| [stream_feed 240x800] htop.input->Screen                     | 1782.7 kB         | 600.5 kB: 2.97x faster                             |
| [stream_feed 240x800] htop.input->HistoryScreen              | 2189.7 kB         | 785.0 kB: 2.79x faster                             |
| [stream_feed 240x800] vi.input->Screen                       | 1107.7 kB         | 522.4 kB: 2.12x faster                             |
| [stream_feed 2400x8000] cat-gpl3.input->HistoryScreen        | 20.3 MB           | 11.8 MB: 1.72x faster                              |
            :::                 ::::                                    ::::         :::
| [stream_feed 24x80] find-etc.input->HistoryScreen            | 1017.6 kB         | 774.8 kB: 1.31x faster                             |
| [stream_feed 240x800] top.input->HistoryScreen               | 763.6 kB          | 653.6 kB: 1.17x faster                             |
| [stream_feed 24x80] mc.input->HistoryScreen                  | 485.0 kB          | 422.0 kB: 1.15x faster                             |
```

However, we still have some regressions:

```
| [stream_feed 24x80] htop.input->HistoryScreen                | 863.7 kB          | 1009.0 kB: 1.17x slower                            |
| [stream_feed 2400x8000] ls.input->HistoryScreen              | 8422.1 kB         | 13.7 MB: 1.67x slower                              |
```

### `Screen.reset`

For `Screen.reset` we have a regressions, some minor, some not-so-much
minor:

```
+----------------------------------------------------------+----------+-----------------------------------------+
| Benchmark                                                | 0.8.1    | 0.8.1+screen-optimizations+default-conf |
+==========================================================+==========+=========================================+
| [screen_reset 2400x8000] ls.input->HistoryScreen         | 65.4 us  | 68.9 us: 1.05x slower                   |
| [screen_reset 2400x8000] mc.input->Screen                | 51.9 us  | 54.8 us: 1.06x slower                   |
| [screen_reset 2400x8000] top.input->HistoryScreen        | 65.6 us  | 69.5 us: 1.06x slower                   |
    :::                 ::::                                    ::::         :::
| [screen_reset 24x80] cat-gpl3.input->HistoryScreen       | 13.2 us  | 15.4 us: 1.17x slower                   |
| [screen_reset 24x80] vi.input->HistoryScreen             | 13.0 us  | 15.3 us: 1.18x slower                   |
| [screen_reset 240x800] htop.input->Screen                | 4.87 us  | 5.78 us: 1.19x slower                   |
| [screen_reset 24x80] mc.input->HistoryScreen             | 13.1 us  | 15.7 us: 1.19x slower                   |
| [screen_reset 240x800] mc.input->Screen                  | 4.81 us  | 5.75 us: 1.20x slower                   |
| [screen_reset 24x80] ls.input->HistoryScreen             | 13.0 us  | 15.5 us: 1.20x slower                   |
| [screen_reset 24x80] find-etc.input->HistoryScreen       | 13.0 us  | 15.6 us: 1.20x slower                   |
| [screen_reset 24x80] htop.input->HistoryScreen           | 12.9 us  | 15.5 us: 1.21x slower                   |
| [screen_reset 240x800] find-etc.input->Screen            | 4.86 us  | 5.87 us: 1.21x slower                   |
| [screen_reset 240x800] htop.input->HistoryScreen         | 15.6 us  | 18.9 us: 1.21x slower                   |
| [screen_reset 240x800] vi.input->Screen                  | 4.83 us  | 5.87 us: 1.22x slower                   |
| [screen_reset 240x800] top.input->Screen                 | 4.72 us  | 5.77 us: 1.22x slower                   |
    :::                 ::::                                    ::::         :::
| [screen_reset 240x800] ls.input->Screen                  | 4.79 us  | 5.86 us: 1.22x slower                   |
| [screen_reset 240x800] cat-gpl3.input->Screen            | 4.79 us  | 5.89 us: 1.23x slower                   |
| [screen_reset 24x80] vi.input->Screen                    | 2.05 us  | 3.05 us: 1.49x slower                   |
| [screen_reset 24x80] mc.input->Screen                    | 2.04 us  | 3.05 us: 1.49x slower                   |
| [screen_reset 24x80] ls.input->Screen                    | 2.01 us  | 3.01 us: 1.50x slower                   |
| [screen_reset 24x80] htop.input->Screen                  | 2.02 us  | 3.06 us: 1.51x slower                   |
| [screen_reset 24x80] cat-gpl3.input->Screen              | 2.03 us  | 3.07 us: 1.52x slower                   |
| [screen_reset 24x80] top.input->Screen                   | 2.03 us  | 3.11 us: 1.53x slower                   |
| [screen_reset 24x80] find-etc.input->Screen              | 2.00 us  | 3.06 us: 1.53x slower                   |
```

However when
`track_dirty_lines` is `False` and `disable_display_graphic` is `True`,
the things improves (but we still have regressions):

```
+----------------------------------------------------------+----------+----------------------------------------+
| Benchmark                                                | 0.8.1    | 0.8.1+screen-optimizations+custom-conf |
+==========================================================+==========+========================================+
| [screen_reset 2400x8000] find-etc.input->Screen          | 51.3 us  | 15.2 us: 3.38x faster                  |
| [screen_reset 2400x8000] mc.input->Screen                | 51.9 us  | 15.5 us: 3.35x faster                  |
| [screen_reset 2400x8000] vi.input->Screen                | 52.8 us  | 15.9 us: 3.32x faster                  |
    :::                 ::::                                    ::::         :::
| [screen_reset 2400x8000] cat-gpl3.input->HistoryScreen   | 66.5 us  | 29.9 us: 2.22x faster                  |
| [screen_reset 2400x8000] htop.input->HistoryScreen       | 64.6 us  | 29.4 us: 2.20x faster                  |
| [screen_reset 240x800] htop.input->Screen                | 4.87 us  | 4.58 us: 1.06x faster                  |
| [screen_reset 240x800] find-etc.input->Screen            | 4.86 us  | 4.62 us: 1.05x faster                  |
| [screen_reset 240x800] cat-gpl3.input->HistoryScreen     | 16.0 us  | 17.0 us: 1.06x slower                  |
| [screen_reset 240x800] mc.input->HistoryScreen           | 16.0 us  | 17.1 us: 1.07x slower                  |
| [screen_reset 240x800] find-etc.input->HistoryScreen     | 16.1 us  | 17.3 us: 1.07x slower                  |
| [screen_reset 240x800] top.input->HistoryScreen          | 15.9 us  | 17.1 us: 1.08x slower                  |
| [screen_reset 240x800] htop.input->HistoryScreen         | 15.6 us  | 17.5 us: 1.12x slower                  |
    :::                 ::::                                    ::::         :::
| [screen_reset 24x80] htop.input->HistoryScreen           | 12.9 us  | 15.3 us: 1.19x slower                  |
| [screen_reset 24x80] htop.input->Screen                  | 2.02 us  | 2.89 us: 1.43x slower                  |
| [screen_reset 24x80] top.input->Screen                   | 2.03 us  | 2.92 us: 1.44x slower                  |
| [screen_reset 24x80] mc.input->Screen                    | 2.04 us  | 2.94 us: 1.44x slower                  |
| [screen_reset 24x80] ls.input->Screen                    | 2.01 us  | 2.90 us: 1.44x slower                  |
| [screen_reset 24x80] vi.input->Screen                    | 2.05 us  | 2.96 us: 1.44x slower                  |
| [screen_reset 24x80] find-etc.input->Screen              | 2.00 us  | 2.90 us: 1.45x slower                  |
| [screen_reset 24x80] cat-gpl3.input->Screen              | 2.03 us  | 2.96 us: 1.46x slower                  |
```

