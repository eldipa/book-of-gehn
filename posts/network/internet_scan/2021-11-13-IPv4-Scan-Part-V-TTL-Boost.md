---
layout: post
title: "IPv4 Scan 2021 - TTL Boost (or reset)"
tags: [pandas, julia, statistics, seaborn]
inline_default_language: julia
---

In [the post about Hop-Stability](/articles/2021/10/16/IPv4-Scan-Part-III-Hop-stability.html)
we analyzed the TTL of the responses from all the scanned hosts.

In particular we used the TTL range: the difference between
the smallest and the greatest TTL seen per host.

{% call marginfig('multirounds_ttl_range_unbiased__hist.svg', indexonly=True) %}
Histogram of TTL range between rounds of scans to the same host showing how much stable the routes are.
{% endcall %}

With a range of 0 or very close we claimed that the route to the host was
stable; with range larger than 7 we said the contrary.

The analysis shown that only 0.39998% of 43056567 unique hosts had
unstable routes.

However the analysis was only using a few statistics, when we plot the
*histogram of TTL ranges* we see much more **mysteries to solve**.<!--more-->


## TTL range histogram (how much stable is a route in a longer period? - revised)

We can plot `multirounds_range` in a histogram. Recap that `multirounds_range`
is the range of TTLs, that means `rounds_ttl[:,:max] - rounds_ttl[:,:min]`; a quick
histogram was shown before as `hist_biased`.

{% call mainfig('multirounds_ttl_range_unbiased__hist.svg') %}
Histogram of TTL range between rounds of scans to the same host showing how much stable the routes are.

The dataset does not include hosts scanned only once.
The vertical axis is in logarithmic scale.
{% endcall %}

The histogram may be misleading at first but remember that the vertical
axis is in *logarithmic scale*.

That means that the main peak at 0 is almost 3 orders of magnitude
larger than the three secondary peaks on the right.

This is compatible with the analysis made previously: the routes are
highly stable and only a small fraction (0.39998%) are unstable with
a large variance (represented by the right side of the histogram).

But the histogram shows some interesting features.

### Peaks

Now we find where the local maxima are. We use a window of 40 to filter
any peak that it is not high enough.

`strict=false` is crucial because `argmaxima` ignores any peak that it
is too close on the edges (for which a full window cannot be computed).
Without this, the peak at 0 would be lost.

```julia
julia> hist = fit(Histogram, convert(Vector{Int32}, multirounds_range[:, :range]), nbins=255)

julia> argmaxima(hist.weights, 40, strict=false) .- 1
4-element Vector{Int64}:
   0
  63
 127
 191
```

`argmaxima` returns the indexes where the peaks were found in
the `bins` vector created.

Julia's vectors are 1-based indexed but those indexes also represent the
TTL range values where the peak were found **except** that they are
shifted by 1.

In short, a peak at index `n` means a peak for the TTL range of `n-1`.

That's why we do a `.- 1`.

Back to the numbers, *what the hell do those peaks mean?*

## Analysis of the 3 secondary peaks

{{ marginfig('multirounds_ttl_range_unbiased__hist.svg') }}

Let's ignore the peak at 0 (those are the stable routes). Why do we have
3 secondary peaks?

Focus on the peak at TTL range of 191 (the right most).

That means that we have a host that in
some moment had a TTL of `m`{.mathjax} and later it had a TTL of
`M`{.mathjax}.

Then, the range for
that host is `M-m = 191`{.mathjax}.

That happen for several hosts, probably each having a **different** `M`{.mathjax} and
`m`{.mathjax} but all ended up having the **same** range of 191.

Let's assume that one of those hosts is a Windows with a default TTL of
128.

{% call marginnotes() %}
The *15* comes from our estimation of the *average distance in hop counts*
made in the [Hop-Distance and Clusters post](/articles/2021/11/13/IPv4-Scan-Part-IV-Hop-Distance-and-Clusters.html)
{% endcall %}

We know that the scanner will receive the packets from it with an
expected TTL of `128-15=113`{.mathjax}. This of course will depend of how far is
the host but it is expected to be at a distance of 15 hops.

So, we have two scenarios for this Windows host:

```
m=113,  M=304       (ttl=128, hops=15)
m=-78,  M=113
```

And none of those makes sense...

### Revising the assumptions

To have a difference of 191, or we need `M=304`{.mathjax} or we need `m=-78`{.mathjax} which it
is impossible: TTL must be between 0 and 255!

Let's review the assumptions so far:

 - the host is a Windows with a default TTL of 128
 - the are 15 hops between the host and the scanner
 - the hops between the host and the scanner always decrement the TTL by 1


We could explain those numbers assuming that the hosts that contributed
to form the peak at 191 are not Windows, or their default TTL are not
128.

A TTL of 64, with a distance of 15 hops, yields

```
m=49,    M=240       (ttl=64, hops=15)
m=-142,  M=49
```

We could also explain the peak if the hops between the hosts  and the
scanner is larger than 15.

For example, Windows hosts at a 64 hops yields:

```
m=63,    M=254       (ttl=128, hops=64)
m=-128,  M=63
```

So, the only way to explain the peak at 191 without falling
in the cases `M=304`{.mathjax} or `m=-78`{.mathjax} is that the peak
at 191 is formed by non-Windows hosts *and/or* really far Windows hosts.

But if that it is true, it is also true that are **more hosts that can
contribute** to the first two secondary peaks at 63 and 127.

In other words, it is more likely to have a random host to fall in one
of those two peaks (63 and 127); it is more **unlikely** to fall
in the third one because --and this is also another assumption--
it is more **unlikely** to pick a non-Windows host and/or a far Windows host.

Perhaps it is a wild idea but the fact that the peak at 191
is the **same height and shape** that the peaks at 63 and 127
is just weird.

We would be expecting the third peak at 191 to be **smaller** (less hosts
matching the conditions). Right?

What if we drop our third assumption: the hops decrement the TTL
by 1?

Could be possible that some hops instead of decrementing the TTL,
increment it, like a TTL boost?

*Perhaps.*

## TTL boost

Let's assume that in some cases the packets coming from a host pass
through a hop that does not decrement the TTL but **resets it** to 255.

Some kind of TTL boost.

Let's see what would we see if a reset or a boost happen. What would be
the observed range by us?

```python
>>> default_ttls = [64, 128, 255]
>>> expected_hops = 15

>>> for ttl in default_ttls:
...    print(f"Default TTL={ttl} => m={ttl-expected_hops}, M={255-expected_hops} => Range=M-m={255-ttl}")
Default TTL=64 => m=49, M=240 => Range=M-m=191
Default TTL=128 => m=113, M=240 => Range=M-m=127
Default TTL=255 => m=240, M=240 => Range=M-m=0
```

That's interesting! We would get peaks at 127 and 191 as we saw earlier.

## Further research

The histogram shows more features that could be explained with the
*boost* theory but it is required to have a more precise model about the
internet.

Saying that there are 15 hops between any two machines is a too
simplistic model.

Also, what have in common these hosts that gained a boost in their TTLs?
May be there is a geographic reason. Again, we need a richer model to
explore this.
