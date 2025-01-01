---
layout: post
title: "Greenwald-Khanna e-approximated q-quantile - a review"
tags: [stats, quantile, rank, sublinear]
inline_default_language: mathjax
---

{% call marginfig('01_setup.svg') %}
Sorted observations stored in an array.
Assuming 1-based index, the observation at rank `r`
**is** at the index `r`.
{% endcall %}

Given `n` observations, finding which value is at rank `r`
is trivially easy: if we store and sort the observations,
the rank `r` will be at index `r`.

But when `n` gets really large, it is unfeasible to store or sort *all* the observations.

Greenwald and Khanna
 developed a data structure that solves
this but with a trade off: we can
answer which value is at rank `r` within *certain error*.

{% call marginnotes() %}
For the entire post I will talk about ranks. To deal with quantiles
it is just a matter of computing its equivalent rank `r \leftarrow q n`.
{% endcall %}

It is called an `q`-quantile `\epsilon`-approximation *summary*.

I coded it, it didn't work and after a week on this I realized
that the original work of Greenwald an Khanna may have a few
*imprecisions*.

This post describes how I rethinked the data structure from scratch,
where I found the mentioned imprecisions and how I got a working
implementation.

TL;DR -> [python implementation in cryptonita](https://github.com/cryptonitas/cryptonita/blob/93688906dbaf781618d86e17e0a156dfe806fbc5/cryptonita/stats/distribution_summary.py)
<!--more-->
Paper -> [Greenwald and Khanna (GK01)]({{ asset('quantiles-GK-algorithm.pdf') }})

## Square one: what is wrong with using a sorted array?

The cost is *not* bad: sorting is `O(n \textrm{log}(n))` and answering is
`O(1)`. If we query multiple times, the cost of
the sort will be amortized.

But this assumes that `n` is fixed and we have *all* the observations
at the moment of sorting.

What would happen if we want to add new observations on the fly?

You see, to keep the array sorted we find the insertion point
of the new observation with a binary search `O(\textrm{log}(n))`
and once we know where to insert, we need to *move* all
the next elements of the array to make room. And this is `O(n)`.

{% call mainfig('02_insert_bad_linear_time.svg') %}
{% endcall %}

And *that* displacement is bad.

## Implicit (computed) ranks

An array is a dead road; long live to a linked list!

The downside is that we lose the `O(1)` for querying a rank
but we avoid having to move the elements to make room for a new one.

Or kind of.

If we explicitly track the rank of each element we still have an `O(n)`
insert because we
would have to update *all* the next elements' ranks.

{% call mainfig('03_insert_bad_explicit_ranks.svg') %}
Example of inserting the value `12`, at rank `3`. The rank
of *all* the observations on its right must be updated
increasing their ranks by `1`.
{% endcall %}


Instead, we store *tuples* of the form `t_i = (v_i, g_i)`:

{% call marginfig('04_computed_rank_with_g.svg') %}
For example, `g_1 + g_2 + g_3 = 1 + 1 + 1 = 3` gives the rank of the third observation `20`.
{% endcall %}

 - `v_i`: the value of observation.
 - `g_i`: the *gap* between that element's rank and the previous' rank.

Every time we want to know the rank of any tuple `t_i`
we compute `\sum_{j \le i} g_j`.


Now let's review what happen when we insert the observation `12`.
The observations previous to it should not change but we know that
`20` cannot be at rank `3` anymore but at least *one more*, making
*room* for the new incoming `12`.

{% call mainfig('04_insert_ok_g.svg') %}
{% endcall %}

In other words, adding a new observation *shifts by 1* the rank of all
the observations on the right. But there is no need to update anything:
setting `g = 1` for `12` is enough, no need to do any `O(n)` stuff.

{% call marginnotes() %}
We are going to improve this even further at the end of the post.
{% endcall %}

The insertions are now just `O(log(n))`.

## Don't keep all, remove some tuples

To handle very large `n` we cannot keep
all the observations in memory: we *need* to remove some while
still preserving the rank of the others within some error.

For example, the tuple `t_{i+1}` with value `12` is at rank `3`.
If we remove the previous tuple `t_i`, the value `12` *must*
still be at rank `3`.

This is easy to achieve: we just need to increase `g_{i+1}` by
`g_i`.

{% call mainfig('05_delete_and_g_update.svg') %}
{% endcall %}

Here are a few more examples:

{% call mainfig('05_delete_and_g_update_2_and_3.svg') %}
You can corroborate that the observation `21` remains at rank `5`
in all the cases.
{% endcall %}

Removing tuples trades off space by accuracy.

If we ask for the rank `2`, we *lost* the precise answer
but we can return an *approximated* one:
if we answer with rank `1` (value `4`), we missed just be `1` rank.

{% call mainfig('06_query_and_error.svg') %}
Ask for the observation at rank `2` but we answer with the observation
at rank `1` effectively making a mistake of `1` rank.
{% endcall %}

In general we answer with the closest tuple so the maximum error
is at the middle point and it is half the count of tuples removed
in between the tuples.

{% call mainfig('08_computed_error.svg') %}
In this example, `\lceil \frac{4 - 1}{2} \rceil = 2`
{% endcall %}

Luckily, we already are tracking how many tuples we removed:
it is just the `g_i` value of the right-most tuple minus 1.

{% call mainfig('07_gap.svg') %}
Why the `- 1`? Because each `g_i` starts at `1` and increases
by the same amount of removed tuples.
{% endcall %}

So we can put a upper bound on the error for answering for a rank `r`
that falls in the gap: `\lceil \frac{g_i - 1}{2} \rceil`


## Minimum and maximum ranks

Let's back to how we handle an insert. What would happen if we want to
insert the value `16`?

{% call mainfig('09_insert_but_where.svg') %}
We don't know what rank the value `16` should have but we know that it
is between ranks `2` and `6`.
{% endcall %}

{% call marginfig('09_insert_but_where_cheating.svg') %}
In fact, if we didn't delete any tuple, the precise rank for `16` should had been `4`
which it is between `2` and `5`.
{% endcall %}

The value `16` is between `4` and `21` so the rank of `4` should not change
but the value `21` cannot longer be at rank `5` but at rank `6`
to make room for the new observation.

Therefore the value `16` is at rank between `2` and `5` (inclusive)

Those ranks are the respective *minimum* and *maximum* ranks for `16`.

```tex;mathjax
\begin{align*}
    \textrm{rmin}_i &= \textrm{rank}_{i-1} + 1                    \\
    \textrm{rmax}_i & = \textrm{rank}_{i+1}
\end{align*}
```

{% call mainfig('10_insert_rmin_rmax.svg') %}
{% endcall %}

But our tuples don't have explicit ranks but relative offsets.

From `\textrm{rmin}_{i}` we solve `g_{i}`:

{% call marginnotes() %}
I'm using here `\textrm{rmax}_{i+1}` to be the rank *before* updating
the `g_{i+1}` of the tuple `t_{i+1}`.
In the example, `\textrm{rmax}_{i+1}` would be `5` not `6`.

In the practice this detail doesn't matter because the algorithm
would never be working with ranks directly.
{% endcall %}

```tex;mathjax
\begin{align*}
\textrm{rank}_{i} &= \textrm{rank}_{i-1} + 1      \\
\textrm{rank}_{i} - \textrm{rank}_{i-1} &= 1      \\
                                  g_{i} &= 1

\end{align*}
```


Let's define a new offset, `\Delta_{i} = \textrm{rmax}_{i} - \textrm{rmin}_{i}`
which can be rewritten as:


```tex;mathjax
\begin{align*}
\textrm{rmax}_{i} & = \textrm{rank}_{i+1}               \\
                  &= \textrm{rank}_{i-1} + g_{i+1}      \\
\textrm{rmax}_{i} - \textrm{rmin}_{i} &= \textrm{rank}_{i-1} + g_{i+1} - \textrm{rmin}_{i}          \\
\textrm{rmax}_{i} - \textrm{rmin}_{i} &= \textrm{rank}_{i-1} + g_{i+1} - \textrm{rank}_{i-1} - 1    \\
                                      &= g_{i+1} - 1       \\
                           \Delta_{i} &= g_{i+1} - 1
\end{align*}
```

Our tuples now we have 3 values:

- `v_i`: the observed value
- `g_i`: the *gap* between the predecessor `\textrm{rmin}_{i-1}` to the
    current tuple's `\textrm{rmin}_i`.
- `\Delta_i`: the difference between  `\textrm{rmax}_i` and `\textrm{rmin}_i`.

## Insert, revised

But the above is incomplete. Let's see an insert in between
two observations that don't have a single rank but a range.

{% call mainfig('11_setup_range.svg') %}
{% endcall %}

The value `4` may be at rank `1` or `2`. We know for sure that the value
`16` is after `4` so it cannot have a rank of `1` but it *could* have a
rank of `2` or anything above.

The `\textrm{rmin}` of `4` defines the `\textrm{rmin}` of `16`.

For the value `21` we do the same analysis: it may be at ranks `5` and
`6` so the value `16` cannot be at rank `6` but it *could* be at rank `5`
and above.

In summary:

```tex;mathjax
\begin{align*}
    \textrm{rmin}_i &= \textrm{rmin}_{i-1} + 1                    \\
    \textrm{rmax}_i & = \textrm{rmax}_{i+1} - 1
\end{align*}
```

From the first equation we get `g_i = 1` for the inserted tuple `t_i`
as we got before.

`\Delta_i` is slightly different:

{% call marginnotes() %}
I'm using here `\textrm{rmax}_{i+1}` to be the rank *before* updating
the `g_{i+1}` of the tuple `t_{i+1}`.
{% endcall %}

```tex;mathjax
\begin{align*}
       \Delta_i & = \textrm{rmax}_i - \textrm{rmin}_i                                       \\
                & = \textrm{rmax}_{i+1} - \textrm{rmin}_{i-1} - 1                           \\
                & = \textrm{rmin}_{i+1} + \Delta_{i+1} - \textrm{rmin}_{i-1} - 1            \\
                & = \textrm{rmin}_{i-1} + g_{i+1} + \Delta_{i+1} - \textrm{rmin}_{i-1} - 1  \\
       \Delta_i & = g_{i+1} + \Delta_{i+1} - 1
\end{align*}
```

{% call mainfig('12_insert_range.svg') %}
{% endcall %}

## Removed tuples count, revised

We saw that `g_i - 1` counts for the tuples removed immediately before
the tuple `t_i` but this is not enough.

Visually we want to count the removed tuples from `\textrm{rmin}_{i-1}`
to `\textrm{rmax}_{i}`.

{% call mainfig('13_gap_range.svg') %}
{% endcall %}


```tex;mathjax
\begin{align*}
    & = \textrm{rmax}_{i} - \textrm{rmin}_{i-1} - 1             \\
    & = \Delta_i + \textrm{rmin}_{i} - \textrm{rmin}_{i-1} - 1  \\
    & = \Delta_i + g_i - 1
\end{align*}
```

With this, the upper bound error for answering for a rank `r`
that falls in the gap becomes `\lceil \frac{\Delta_i + g_i - 1}{2} \rceil`

{% call mainfig('14_computed_error_range.svg') %}
{% endcall %}

## Answer, revised

To answer for a rank `r`, we search any tuple whose ranks are fully
contained in the range `(r - \lfloor \epsilon n \rfloor , r + \lfloor \epsilon n \rfloor)`.

This is because we cannot answer with a tuple `t_i` if *any* of *its*
possible ranks are outside of the range. Answering with such tuple will
imply that we are potentially answering with a value with a truly rank
beyond the tolerance `\lfloor \epsilon n \rfloor`, hence having a
relative error larger than `\epsilon`.

{% call mainfig('15_query_range.svg') %}
{% endcall %}

The answering requires a `O(s)` search where `s` is the count of tuples
in the summary, much smaller than the total number of observations `n`.

## Invariant of the summary: we can always guarantee to answer any rank

It's easy to see that if the maximum gap between 2 consecutive tuples
is `\Delta_i + g_i - 1` (twice the maximum error), and if we keep this
below `2 \lfloor \epsilon n \rfloor`, we can always find the rank
with an error of up to `\epsilon n` (just divide both expressions by 2).

Not a proof but here we go with an intuition:

 - you are looking for a rank `r` with maximum error of `\lfloor \epsilon n \rfloor`
 - a tuple/rank is found iif the tuple's rank range fully falls inside
   the `2 \lfloor \epsilon n \rfloor` window.
 - not finding such tuple/rank means that the *almost* correct tuple
   has a rank range larger than `2 \lfloor \epsilon n \rfloor`.
 - in other words, `\Delta_i \gt 2 \lfloor \epsilon n \rfloor`
 - but `\Delta_i` is a value that never changes (it is fixed when the
   tuple is inserted) and its value is `g_{i+1} + \Delta_{i+1} - 1`
 - but `g_{i+1} + \Delta_{i+1} - 1` is also the maximum gap between
   the tuples `t_i` and `t_{i+1}` (it is twice the maximum error)
 - and for hypothesis
   `\Delta_{i+1} + g_{i+1} - 1 \lt 2 \lfloor \epsilon n \rfloor`
   which conflicts with the above and leads to a contradiction
 - so we should be able to find always a tuple for the query of rank `r`
   with a maximum error of `\lfloor \epsilon n \rfloor`

In short, the summary **always** maintains the invariant:

```tex;mathjax
\Delta_i + g_i - 1 \le 2 \lfloor \epsilon n \rfloor
```

This imposes a restriction when we can remove or not a tuple:
a tuple can be removed if by doing so we are not creating a gap
that violates the invariant.

In other words, the tuple `t_i` can be removed iff:

```tex;mathjax
g_i + \Delta_i + g_{i+1} + \Delta_{i+1} - 1 \le 2 \lfloor \epsilon n \rfloor
```

## Amortization via deferring inserts

So far we have `O(\textrm{log} s)` inserts. However,
it is possible to defer the inserts, holding them in a temporal
buffer and insert all them together later.

Once the buffer is full, we sort it in `O(b \textrm{log} b)` and
do a *merge* between it and the summary in
`O(s+b)`.

We traded `b` inserts of `O(\textrm{log} s)`
by one `O(b \textrm{log} b) + O(s+b)`.

Moreover, during the merge we can check if the tuple
can be removed without violating the invariant.

## Wrapping all together

The *summary* data structure has 3 operations:

 - insert
 - merge
 - query

On each *insert*, store the observation in a buffer. Once the buffer
reaches to the size of the current summary or to some predefined
limit, merge it and create a new summary.

The *merge* operation is as follows:

- sort the observations in the buffer
- iterate over the buffer and the summary at the same time from the
  largest to the smallest values; compare both tips and take the
  largest

  - if the value comes from the buffer (new observation), create
    the tuple `t_i = (v_i, g_i=1, \Delta_i=g_{i+1} + \Delta_{i+1})`
  - otherwise, the value comes from the summary, use its tuple
  - insert the tuple `t_i` in the new summary only if otherwise
    would create a gap too large that would violate the invariant.
    The only exception is the last (smallest) value (the minimum)
    that must be inserted in the summary (so the summary always
    contains the extremes values).

For *query*, we can offer answers for quantiles or ranks.

To answer for the rank `r` we scan the summary, summing the `g_j`
values along the way to compute:

```tex;mathjax
\begin{align*}
\textrm{rmin}_i &\leftarrow  \sum_{j \le i} g_j \\
\textrm{rmax}_i &\leftarrow  \textrm{rmin}_i + \Delta_i
\end{align*}
```

We stop once we find a tuple `t_i` that satisfies both inequalities:

```tex;mathjax
\begin{align*}
\textrm{rmin}_i &\ge r - \lfloor \epsilon n \rfloor      \\
\textrm{rmax}_i &\le r + \lfloor \epsilon n \rfloor
\end{align*}
```

To answer for the quantile `q`, we compute the equivalent
rank `r \leftarrow q n` and proceed as above.


## So, which are the discrepancies with Greenwald-Khanna's work?

### Typo in the invariant

Considere the *corollary 1* (GK01):

```tex;mathjax
\textrm{max}(g_i + \Delta_i) \le 2 \epsilon n \quad \forall i
```

The incorrect part is `g_i + \Delta_i`.

For any new tuple, its `g_i` is `1` and it is easy to find
a valid *small* `n` such `2 \epsilon n` is *smaller* than 1
and because `\Delta_i` is never negative,
the corollary *does not hold*.

I think that the expression should had been:

```tex;mathjax
\textrm{max}(g_i + \Delta_i - 1) \le 2 \epsilon n \quad \forall i
```

The left side is always positive but it can be zero so it does not
enter in conflict with the right side. This is just a slightly weaker
version of the invariant mentioned in the blog post.

And of course, it may no be an error at all ans just I'm not
interpreting the paper correctly.

### Compress and bands

The authors also implemented a separated routine called `COMPRESS` that removes
unneeded tuples which requires the categorization of all the `\Delta_i` into *bands*.

While they use the concept of *bands* to prove the properties of the algorithm,
IMO, these are not needed for running it.

### Initial `\Delta_i`

In the first sections of the paper, the authors define for a new tuple
`t_i`, its `\Delta_i` as `\Delta_i = \lfloor 2 \epsilon n \rfloor`.

This is a loose value but the authors used it to prove properties of the
algorithm.

In the next sections of the paper, they use `\Delta_i = g_{i+1} + \Delta_{i+1}` as in
the blog post.

### Minimum is not preserved

I didn't explain this but in the
[python implementation](https://github.com/cryptonitas/cryptonita/blob/93688906dbaf781618d86e17e0a156dfe806fbc5/cryptonita/stats/distribution_summary.py)
I added some
extra condition to delete or not a tuple: if the tuple is at one extreme
(its value `v` is either the maximum or the minimum), do not delete it.

This was the intention of the GK01 authors too but their implementation
(or better said, its pseudo code) does not prevent the minimum to be
removed.


## Conclusions

It was hard. You have no idea.

Once I realized that the paper had some inconsistencies, it took me a
week to fully understand and write down --from the scratch-- the algorithm
and summary data structure.

But that was the easy part. It took me like a month to write this
blog post and I truly have deep respect for Greenwald and Khanna.

Writing this blog post taught me how hard is to explain something
and even harder to it write without mistakes.
I had to redo more than one diagram, fixing indices or adding a missing `- 1`
and, of course, I'm quite sure there is room for improvements.

This is also a reminder why publishing the full implementation, not just
pseudo code, is so important. It is written in a formal language and
it can be executed and put in test easy.

For example, checking the incorrect invariant
`\textrm{max}(g_i + \Delta_i - 1) \le 2 \epsilon n \quad \forall i` it
would be trivial: just add an assert in the code.

The code is never immune to errors, but it is a bit closer to the truth.

## Future work

 - Combine multiples summaries (see [Chapter-GK]({{ asset('quantiles-chapter-overview-multiple-algorithms-GK-combine-2-Summaries.pdf') }}):
   One may observe values produced from different places, summarized
   locally and then, somehow, combine these *local summaries* into a
   single one.
 - Non-uniform error: GK's *summary* answers with a fixed relative error
   across the entire range of ranks. In some applications one may want
   to have certain quantiles with less errors than others.
 - Read about related problems (see [Quantiles over Data Streams: Experimental Comparisons, New Analyses, and Further Improvements]({{ asset('quantile-estimation-for-very-large-infinite-data-stream--random-deterministic-probabilidad-linear.pdf') }})

