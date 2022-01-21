---
layout: post
title: "IPv4 Scan 2021 - Hop-Distance Average and IP Distribution"
tags: [pandas, julia, categorical, ordinal, parquet, statistics, seaborn]
inline_default_language: julia
---

{% call marginfig('ttl_hist_log_scale.svg', indexonly=True) %}
Histogram of TTL observed: the peaks indicate the different operative systems and their relative position respect the expected positions estimate the mean distance between the hosts and the scanner in hop count.
{% endcall %}

In the [Multiprobes Analysis](/articles/2021/09/19/IPv4-Scan-Part-II-Multiprobes-Analysis.html),
we explored the statistics of the hosts and the communication to them.

This is a follow up to keep exploring the data:

 - which is the average distance between a host and the scanner in term
of hop count?
 - which OS are running?
 - how are the hosts distributed?
<!--more-->

## Setup

Following the
[terms defined in Hop-Stability post](/articles/2021/10/16/IPv4-Scan-Part-III-Hop-stability.html),
`masscan` sends multiple probes
to the same host at the same time: we call these *short bursts*.

`masscan` may also scan the same host multiple times, at different
moments: we call these *rounds of short bursts* or just *rounds*.

As we saw
[earlier](/articles/2021/10/16/IPv4-Scan-Part-III-Hop-stability.html),
for a given host the *time to live* (TTL) read
from every probe/packet remains constant within a short burst
and relatively constant between rounds.

```julia
julia> all_rounds_g = groupby(df, :ip)
```

The TTL changes between rounds only by 1 or 2; changes of 8 or greater
happen only in a very small fraction of the dataset, around 0.39998%.

For this reason we are going to work with the *mode*: the most common TTL
value per host.

```julia
julia> all_rounds = combine(all_rounds_g, :ttl => mode => :ttl)
```

## Histogram

Now we plot the histogram of `all_rounds`.

{% call mainfig('ttl_hist_log_scale.svg') %}
Histogram of TTL observed: the peaks indicate the different operative systems
and their relative position respect the expected positions estimate
the mean distance between the hosts and the scanner in hop count.
{% endcall %}

There are three really high peaks with `~10^6`{.mathjax} count
with one secondary peak at the left of each main peaks.

In the *x-axis* are marked the typical TTLs values that the operative systems
set by default. For some operative systems this may different depending
of the version of the OS and the protocol of the packet.

We cannot do anything about the version of the OS but we can ignore the
protocol because all the probes sent were TCP.

Notice however that the peaks are **left-shifted** from the expected default
TTLs.

This is because the packets received had travelled through the network and in
each hop the TTL is decremented by one.


## Peak estimation

First we compute the histogram. We cannot plug in `df[:, :ttl]`
directly because its type is `Vector{Union{Missing, Int32}}` and
`Histogram` does not work with `Missing` values, even if there are no
missing there.

```julia
julia> vec = convert(Vector{Int32}, df[:, :ttl])
julia> hist = fit(Histogram, vec, nbins=255)
```

Now we find where the local maxima ares. We use a window of 40, quite
large, to filter out the secondary peaks.

`strict=false` is crucial because while scanning, if the search window
gets slightly out of the range, no peak is detected. So peaks near the
ends, like the around 235, wouldn't be detected.

```julia
julia> argmaxima(hist.weights, 40, strict=false) .+ 4
3-element Vector{Int64}:
  49
 112
 239
```

## Hop-distance average

{% call marginnotes() %}
30, 32, 60, 64, 128, 200, 254 and 255 are the most common default TTLs;
the 64, 128 and 254 correspond roughly to Unix, Windows and Solaris/AIX.

Reference: [Subin&apos;s Default TTLs](https://subinsb.com/default-device-ttl-values/)
 {% endcall %}

Comparing these with the expected default TTLs we can know by how much
the histogram was left-shifted:

```julia
julia> [64, 128, 254] - [49, 112, 239]
3-element Vector{Int64}:
 15
 16
 15
```

So the scanner is at 15 - 16 hops of distance, on average, from any
other host in the network.

{% call mainfig('ttl_hist_log_scale_shifted.svg') %}
Histogram of TTL observed but with the values shifted to the right
to compensate the fact that the TTLs are decremented during their travel
through the network.
{% endcall %}

## IP distribution

We can get an idea of how the hosts scanned are distributed in the IP
space.

Sorted by IP address, we can compute the first order difference (aka
`df[i+1, :ip] - df[i, :ip]`: hosts in the same subnetwork will have very
small differences.

This **crude model** is not free of misinterpretations: two hosts
at the end and at the begin of two large subnets, like `1.255.255.254`
and `2.0.0.1` and you will get a difference of 2 but clearly they are at
two different subnets.

```julia
julia> sort!(df, [:ip])
julia> unique!(df, [:ip])

julia> df_diff = DataFrame(diff = diff(df[:, :ip]))

julia> describe(df_diff)
1×7 DataFrame
 Row │ variable  mean     min    median   max       nmissing  eltype
     │ Symbol    Float64  Int64  Float64  Int64     Int64     DataType
─────┼─────────────────────────────────────────────────────────────────
   1 │ diff       86.893      1      2.0  50359752         0  Int64
```

The median tells us that half of the hosts' IPs differ by 1 or 2 at
most. **They are far from being uniformely distributed**.

The mean of `86.893` tells us that despite being highly non-uniform,
clusters are quite separated each other, generating larger differences in the
IP (so the mean moves towards the right).

## Rough estimation for cluster density

We can integrate the difference back to the dataframe as follows:

```julia
julia> df[!, :diff] = insert!(diff(df[:, :ip]), 1, 0)
```

Arbitrarily, I chose 0 as the difference for the first IP, that's why
I did a `insert!(..., 1, 0)`. Reasonable, I guess.

If we define that the maximum difference per cluster to 8, we can count
how many clusters do we have:

```julia
julia> df_cluster_leaders = filter(:diff => >(8), df)
10822514×6 DataFrame
```

Once again we need to take into account the first cluster that it is
counted above because its first host has a difference of 0 so obviously
it is not part of the `df_cluster_leaders`.

```julia
julia> cluster_leaders  = insert!(df_cluster_leaders[:, :ip], 1, df[1, :ip])
```

{% call marginnotes() %}
Do not laugh. This is my first time coding a function in Julia, trying
to do some closure-thing.
 {% endcall %}

We can tag then each host of `df` with the first IP of its cluster,
its leader.

```julia
julia> ix = [1]
julia> next_ix = [2]

julia> function assign_leader(val)
           if val >= cluster_leaders[next_ix[1]]
                 ix[1] = next_ix[1]
                 next_ix[1] += 1
           end
           return cluster_leaders[ix[1]]
       end

julia> df[!, :leader] = assign_leader.(df[:, :ip])
```

Now we can group by leader and count how many rows do we have. Remember
that we filtered out duplicated IPs so counting the rows effectively is
the same that counting how many hosts we have in each cluster.

```julia
julia> clusters_g = groupby(df, [:leader])
GroupedDataFrame with 10822515 groups based on key: leader
```

From there, we can estimate the clusters' density:

```julia
julia> clusters_size = combine(clusters_g, nrow)

julia> describe(clusters_size[:, :count])
Summary Stats:
Length:         10822515
Missing Count:  0
Mean:           3.978428
Minimum:        1.000000
1st Quartile:   1.000000
Median:         1.000000
3rd Quartile:   2.000000
Maximum:        212730.000000
Type:           Int64
```

Keep in mind that we defined arbitrary the cluster as hosts that do not
differ by more than 8 IPs.

The maximum is also, at least, suspicious. Again, the model used is
probably too simplistic.

## Further research

Indeed, the estimation of the clusters' density is too *coarse* and the
numbers are hard to interpret and make compatible with the estimation of
the IP distribution.

Augmenting the dataset with the geolocalization of each host may
help.

Using the TTLs to group the hosts is also possible: even hosts running
different OS (and therefore with different default TTLs), the scanner
should observe their TTLs decremented by the same factor if the hosts are
in the same *physical* network.

Combining this with routing information it would be also helpful.

