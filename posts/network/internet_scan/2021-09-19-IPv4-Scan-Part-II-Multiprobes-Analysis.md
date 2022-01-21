---
layout: post
title: "IPv4 Scan 2021 - Multiprobes Analysis"
tags: [pandas, julia, categorical, ordinal, parquet, statistics, seaborn]
inline_default_language: julia
---

To my surprise the
[dataset](https://www.kaggle.com/signalspikes/internet-port-scan-1)
preprocessed in my
[previous post](/articles/2021/09/10/IPv4-Scan-Dataset-Preprocessing.html)
**has** duplicated entries. These are scans
to the same host and port but with a different timestamp.

{% call marginfig('time_interval_hist.svg', indexonly=True) %}
Histogram of the interval between probes to the same host-port in seconds.
{% endcall %}

Questions like "which open port is more likely" will biased
because the same host-port may be counted more than once.

On the other hand, this opens *new questions*:

 - which is the reason to scan the same port more than once? If it is
*fixed* by the scanner we can deduce that ports scanned once *were scanned
more times* but the other probes failed and get an estimation of such.
 - is the same port opened due different reasons?
 - could we characterize the scanner based on the timestamps like
scanning patterns?

The second surprise was that even working with small samples (around
100MB),
[Pandas](https://pandas.pydata.org/)/[Dask](https://dask.org/)
has **serious performance problems**:

 - consumes much more memory (gigas)
 - CPU at 100% all the time
 - simple operations like `groupby` take forever.

Goodbye Pandas, hello [Julia](https://julialang.org/)?<!--more-->

## Julia's DataFrames

First we need to install a few packages:

```julia
julia> import Pkg

julia> Pkg.add("DataFrames")
julia> Pkg.add("Parquet")
julia> Pkg.add("CategoricalArrays")
julia> Pkg.add("StatsBase")
julia> Pkg.add("Statistics")
julia> Pkg.add("StatsPlots")
```

Then we load the dataframe:

```julia
julia> using Parquet, DataFrames, CategoricalArrays, StatsBase, Statistics, StatsPlots
julia> df = DataFrame(read_parquet("scans"))
```

### Categorical data

{% call marginnotes() %}
The `compress=true` is needed so the column will be of the smallest type
that can represent the categories, in our case, `UInt8`; otherwise
`CategoricalArrays.jl` uses `UInt32` by default.
 {% endcall %}

`Parquet.jl` does not load the categories (or Pandas's `to_parquet` is
not writing them). This consumes more RAM because the `reason` and `port`
columns are strings.

We can make them *categorical* back again with:

```julia
julia> df[!, :reason] = categorical(df[:, :reason], compress=true)
```

### Ordinal data

We do the same for `port` column but we additionally mark the categorical
as *ordered*.

```julia
julia> df[!, :port] = categorical(df[:, :port], compress=true, ordered=true)
```

As
[explained earlier](/articles/2021/09/10/IPv4-Scan-Dataset-Preprocessing.html),
the ports **don't** have a natural order however
I this as an opportunity to explore and document *how to work with ordinals*.

`CategoricalArrays.jl` orders lexicographically by default. To change
the order we need to do it later with `levels!`.

First we get ports labels (strings):

```julia
julia> s = levels(df.port)
```

Then we parse them as integers and sort them numerically:

```julia
julia> s = sort(parse.(UInt16, s))
```

We get back the ports labels as strings:

```julia
julia> s = string.(s)
```

Finally we rewrite the levels of the ordinal column:

```julia
julia> levels!(df.port, s)
```

Now the `port` column is an ordinal column and the order is implied by
the numerical interpretation of its labels.


<!--
using Parquet, DataFrames, CategoricalArrays, StatsBase, Statistics, StatsPlots
df = DataFrame(read_parquet("indexed"))
df[!, :reason] = categorical(df[:, :reason], compress=true)
df[!, :port] = categorical(df[:, :port], compress=true, ordered=true)
s = levels(df.port)
s = sort(parse.(UInt16, s))
s = string.(s)
levels!(df.port, s)


sudo apt-get install libreadline-gplv2-dev libncursesw5-dev libgdbm-compat-dev
sudo apt-get install libsqlite3-dev tk-dev libgdbm-dev libc6-dev libbz2-dev
sudo apt-get install libssl-dev liblzma-dev zlib1g-dev lzma lzma-dev libgdbm-dev

make clean
./configure --enable-shared --enable-optimizations
make
make test

ENV["PYTHON"] = "/home/user/env/bin/python"
ENV["PYTHONHOME"] = ""
Pkg.add("PyCall")
Pkg.build("PyCall")
<..restart..>

import Pkg; Pkg.add("PyPlot")

-->

## Is the same port opened due different reasons?


{% call marginnotes() %}
The `:foo` are symbols which in our case are the names of the columns. The
`∘` (`\circ` in Latex) is the *composite operator*: `length ∘ unique` is
equivalent to `length(unique(x))`.
The whole `:reason => length ∘ unique => :nunique` reads as: take the
`reason` column, count how many unique values are in each group and
store the result (one per group) in the column `nunique`.
 {% endcall %}

```julia
julia> g = groupby(df, [:ip, :port])
julia> df2 = combine(g,
                :reason => length ∘ unique => :nunique)

julia> countmap(df2.nunique)
Dict{Int64, Int64} with 1 entry:
  1 => 64787998
```

Nope, for each open port there is only one reason why it is open.

## Which is the reason to scan the same port more than once?

`masscan` supports a `--retries` flag. From the
[documentation](https://github.com/robertdavidgraham/masscan/blob/952755771ab8065c052cdf4b6d18041435b2d661/doc/masscan.8.markdown):

> *`--retries`: the number of retries to send, at 1 second intervals. Note
> that since this scanner is stateless, retries are sent regardless if
> replies have already been received.*

This means that `masscan` will send `N`{.mathjax} probes to each port, always,
within a second apart.

Let's check that.

## What is the distributions of probes per open port?

{% call marginnotes() %}
`nrow` is a special value that `DataFrame`'s `combine` will
interpret as *count the rows of each group*. The rest follows the usual
meaning: `nrow => :count` means store the count in a column named `count`.
 {% endcall %}

```julia
julia> g = groupby(df, [:ip, :port])
julia> df2 = combine(g, nrow => :count)

julia> countmap(df2.count)
Dict{Int64, Int64} with 5 entries:
  5 => 1
  4 => 27
  2 => 13038
  3 => 750
  1 => 64774182
```

Notice how most of ip-port tuples were scanned once.

So `masscan` didn't send `N`{.mathjax} probes to each port **or** it did it but the
some probes never were answered *(why?, who knows)*.

This could explain why some ports were scanned twice while others only
one.

## What is the distribution of intervals between probes for each port?

{% call marginnotes() %}
Sanity check: from the distribution of probes per port we know that we
have 13038 ports with 2 probes which will contribute with 13038 rows to
the difference dataframe;

750 ports with 3 probes which will contribute
with 750 * 2 rows to the result; 27 ports with 4 probes contributing
with 27 * 3 rows and finally 1 port with 5 probes contributing with 5 *
4 rows.

The expected total is 14623 which it is exactly the row count
of `df2`.
 {% endcall %}

```julia
julia> g = groupby(df, [:ip, :port])
julia> df2 = combine(g,
                :timestamp => diff ∘ sort => :interval)

julia> countmap(df2.interval)
Dict{Union{Missing, Int32}, Int64} with 30 entries:
  0  => 320
  1  => 2793
  2  => 585
  3  => 2625
  4  => 843
  5  => 159
  6  => 316
  7  => 1364
  8  => 512
  9  => 1435
  10 => 495
  11 => 149
  12 => 103
  13 => 52
  14 => 139
  15 => 1715
  16 => 828
  17 => 15
  18 => 6
  19 => 1
  23 => 2
  24 => 5
  25 => 3
  28 => 2
  29 => 1
  31 => 55
  32 => 92
  33 => 4
  34 => 3
  40 => 1
```

Certainly a histogram is better for this case:

{% call mainfig('time_interval_hist.svg') %}
Histogram of intervals between probes to the same host-port in seconds.

The median (5.0) and the mean (6.89) are labeled. The vertical axis is
in logarithmic scale.
{% endcall %}


This was more spread than I expected. Most of the intervals are in the
low range but there is non-negligible count for the 15 secs interval.

A quick statistics for the intervals:

```julia
julia> describe(df2, :mean, :std, :min, :q25, :median, :q75, :max, cols=:interval)
1×8 DataFrame
 Row │ variable  mean     std      min    q25      median   q75      max
     │ Symbol    Float64  Float64  Int32  Float64  Float64  Float64  Int32
─────┼─────────────────────────────────────────────────────────────────────
   1 │ interval   6.8051  5.75237      0      2.0      5.0     10.0  40
```

Or, statistic by statistic:

```julia
julia> mean(df2.interval)
6.805101552349039

julia> median(df2.interval)
5.0

julia> mode(df2.interval)
1

julia> std(df2.interval)
5.752370354791699

julia> quantile(df2.interval, [.25, .5, .75])
3-element Vector{Float64}:
  2.0
  5.0
 10.0

julia> iqr(df2.interval)
8.0
```

The median confirms our first analysis: the distribution is right skewed
*(the mean is on the right of the median)*.


### What about the zero interval?

We can filter which rows has such in two ways being the second one the
preferred and fastest:

```julia
julia> filter(dfrows -> dfrows.interval == 0, df2, view=true)
julia> filter(:interval => ==(0), df2, view=true)
```

Choosing one of the got IPs we can get the probes:

```julia
julia> filter(:ip => ==(22207380), df, view=true)
2×5 SubDataFrame
 Row │ timestamp   port   ttl     reason   ip
     │ Int32?      Cat…?  Int32?  Cat…?    Int64?
─────┼──────────────────────────────────────────────
   1 │ 1619740697  80         42  syn-ack  22207380
   2 │ 1619740697  80         42  syn-ack  22207380
```


`timestamp` as you see has 1-second resolution
([4 bytes](https://github.com/robertdavidgraham/masscan/blob/2895fa0acfe45983a3e9b2bbfadf25934c8d2c65/src/out-binary.c#L131)).

We could assume then that these two probes were done with 1-second
interval apart but due the low resolution of the clock we got the same
timestamp.

## Some thoughts

My initial idea was to use this walk-through to learn and practice
[Pandas](https://pandas.pydata.org/).
Having a dataset of a non-trivial size, I knew that this was
going to be a challenge.

But what a better opportunity to work with
[Dask](https://dask.org/) too!

I really tried to make it work but even processing a 10% of the dataset
made no difference: Pandas and Dask consumed so much memory that I
couldn't finish a single group-by + aggregation.

It is obvious that there are too many copies.

Doing a home-made custom aggregation function to sort this,
I successfully *bypassed* the memory problem but I ended up in
another one: *CPU 100% never-finishing* execution problem.

The custom aggregation function was written in Python, of course, but
calling Python code for each row is incredible slow.

And all of this for a reduced dataset!

I'm talking of processing a 10% dataset and it didn't finish after
running for a whole night.

After a week of trying and failing, it was clear that Pandas+Dask need
more love.

That's when I considered
[Julia](https://julialang.org/).

Julia code is compiled into machine code and because it deduces the types
(most of the times), it can pack the data in arrays with high-locality
and generates fast code ala C.

It is not magic and the libraries are designed to work in this way and
avoid any sort of temporal copies.

On the other hand Julia libraries are much more modest in capabilities
compared with Python's ones.

It is a non-trivial trade-of.

