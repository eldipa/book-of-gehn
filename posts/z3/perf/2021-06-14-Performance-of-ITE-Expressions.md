---
layout: post
title: "Performance of ITE Expressions (incomplete)"
tags: [z3, smt, sat, solver, if ITE, bithack, performance]
inline_default_language: python
---

A *branch* is an expensive operation even in modern CPUs because the
computer will know which of the paths is taken only in the latest stages
of the CPU pipeline.

In the meantime, the CPU *stalls*.

Modern CPUs use branch prediction, speculative execution and instruction
reordering to minimize the impact of a branch.

They do a good job but still a *branch* is potentially expensive so they
are replaced by *branchless* variants.

{% call marginfig('min-check-elapsed-per-func-in-encrypt-experiment.svg', indexonly=True) %}
Minimum  `check-elapsed` time (y axis) per branch/branchless function (x axis).
{% endcall %}

`If-Then-Else` or ITE for short, are symbolic expression that denotes
a value chosen from two possible values based on a condition. These are
the *symbolic branch*.

Naturally we could rewrite a symbolic ITE with a symbolic *branchless*
expression.

The question is: which is better for a solver like Z3? Which makes the
SMT/SAT solver faster?

After two weeks working on this post **I still don't have an answer but at
least I know some unknowns.**<!--more-->

## Z3 `If-Then-Else`

In Z3 we use `z3.If` to build such symbolic expressions.

Take for example the following Python function `xtime`:

```python
>>> def xtime(a):
...     thenval = (((a << 1) ^ 0x1B) & 0xFF)
...     elseval = (a << 1)
...     condval = (a & 0x80)
...     return thenval if condval else elseval
```

Symbolically, we could rewrite it as follows:

```python
>>> from z3 import If, BitVec, simplify
>>> def xtime_branch(a):
...     thenval = (((a << 1) ^ 0x1B) & 0xFF)
...     elseval = (a << 1)
...     condval = (a & 0x80)
...     return If(condval != 0, thenval, elseval)
```

Remember that in Python, the `(thenval) if (condval) else (elseval)` is
**evaluated** at runtime but in Z3 we cannot evaluate anything.

So we need to model the fact that the output of `xtime` it may be
`thenval` or `elseval`, depending of the condition.

Let's see what is the result of `xtime_branch`

```python
>>> T = BitVec('T', 8)

>>> xtime_branch(T)
If(T & 128 != 0, (T << 1 ^ 27) & 255, T << 1)

>>> simplify(xtime_branch(T))
If(Extract(7, 7, T) == 0,
   Concat(Extract(6, 0, T), 0),
   Concat(Extract(6, 4, T),
          ~Extract(3, 2, T),
          Extract(1, 1, T),
          ~Extract(0, 0, T),
          1))
```

Before continuing, I would like to simplify `xtime_branch` a little:

 - the input are always an 8 bits, so the `x & 0xFF` mask is not needed
 - the `thenval` can reuse the `elseval`

```python
>>> def xtime_branch(a):
...     elseval = (a << 1)
...     thenval = (elseval ^ 0x1B)
...     condval = (a & 0x80)
...     return If(condval != 0, thenval, elseval)

>>> xtime_branch(T)
If(T & 128 != 0, T << 1 ^ 27, T << 1)

>>> simplify(xtime_branch(T))
If(Extract(7, 7, T) == 0,
   Concat(Extract(6, 0, T), 0),
   Concat(Extract(6, 4, T),
          ~Extract(3, 2, T),
          Extract(1, 1, T),
          ~Extract(0, 0, T),
          1))
```

As you see, this `xtime_branch` and the previous one yield the **same
result** after applying `z3.simplify`.

However I'm going to keep those simplifications explicit in
`xtime_branch` for further optimizations later.

## Branchless ITE

The `(a & 0x80) != 0` condition is equivalent to `(a >> 7) != 0`.

The key point to notice is that when `(a & 0x80) != 0` then `a >> 7 == 1`; when
`(a & 0x80) == 0` then `a >> 7 == 0`.

With this *single bit boolean* we can get rid of the `If` doing a **branchless**
[bithack](https://graphics.stanford.edu/~seander/bithacks.html#IntegerMinOrMax)

```python
>>> def xtime_branchless(a):
...     elseval = (a << 1)
...     thenval = (elseval ^ 0x1B)
...     condval = (a >> 7) # it can be 0 or 1
...     return elseval ^ ((thenval ^ elseval) & -(condval))

>>> xtime_branchless(T)
T << 1 ^ (T << 1 ^ 27 ^ T << 1) & -(T >> 7)

>>> simplify(xtime_branchless(T))
Concat(Extract(6, 4, T),
       Extract(3, 2, T) ^ Extract(4, 3, 255*(T >> 7)),
       Extract(1, 1, T),
       Extract(0, 0, T) ^
       Extract(1, 1, 3*Extract(1, 0, T >> 7)),
       Extract(0, 0, T >> 7))
```

We don't longer have an ITE expression!

But there is a catch...

## Bit broadcasting

The catch is that we have some multiplications:

 - `255*(T >> 7)`
 - `3*Extract(1, 0, T >> 7)`

These come from `-(condval)`.

When `condval` is 0, then `-(condval)` is 0, represented as eight `0` bits,
the `((thenval ^ elseval) & -(condval))` goes to 0 and the expression
reduces to the left part of the main xor: `elseval`.

When `condval` is 1, then `-(condval)` is 1, represented as eight `1`
bits because in Z3 (and it a lot of other languages), the negative
numbers are in 2-complement representation.

This `1` bits mask *allows* the right side to be xor'd with the left
side `elseval ^ thenval ^ elseval` that reduces to `thenval`.

This why the **branchless** bithack works and more over, from *where*
those multiplications come: from the 2-complement.

`z3.simplify` was **not** smart enough to *broadcasting* the least
significant bit of `a >> 7`.

We could do it better *broadcasting* the most significant bit
of `a` and build the *condition mask* directly:

```python
>>> from z3 import Extract, Concat
>>> def xtime_broadcasted(a):
...     elseval = (a << 1)
...     thenval = (elseval ^ 0x1B)
...     msb = Extract(7, 7, a)
...     condmask = Concat(*([msb] * 8)) # broadcast a single bit to 8 bits
...     return elseval ^ ((thenval ^ elseval) & condmask)

>>> xtime_broadcasted(T)
T << 1 ^
(T << 1 ^ 27 ^ T << 1) &
Concat(Concat(Concat(Concat(Concat(Concat(Concat(Extract(7,
                                        7,
                                        T),
                                        Extract(7, 7, T)),
                                        Extract(7, 7, T)),
                                   Extract(7, 7, T)),
                            Extract(7, 7, T)),
                     Extract(7, 7, T)),
              Extract(7, 7, T)),
       Extract(7, 7, T))

>>> simplify(xtime_broadcasted(T))
Concat(Extract(6, 4, T),
       Extract(3, 3, T) ^ Extract(7, 7, T),
       Extract(2, 2, T) ^ Extract(7, 7, T),
       Extract(1, 1, T),
       Extract(0, 0, T) ^ Extract(7, 7, T),
       Extract(7, 7, T))
```

Ugly but once simplified with `z3.simplify`, `xtime_broadcasted` seems to
be quite simple: only bit picking and xor.

## One last hack

`xtime_broadcasted` can be simplified further *canceling* the `elseval`
from `thenval ^ elseval` because `thenval == elseval & 0x1B`

So `elseval ^ ((thenval ^ elseval) & condmask)` reduces to
`elseval ^ (0x1B & condmask)`:

```python
>>> def xtime_cancelled(a):
...     elseval = (a << 1)
...     msb = Extract(7, 7, a)
...     condmask = Concat(*([msb] * 8)) # broadcast a single bit to 8 bits
...     return elseval ^ (0x1B & condmask)

>>> xtime_cancelled(T)
T << 1 ^
27 &
Concat(Concat(Concat(Concat(Concat(Concat(Concat(Extract(7,
                                        7,
                                        T),
                                        Extract(7, 7, T)),
                                        Extract(7, 7, T)),
                                   Extract(7, 7, T)),
                            Extract(7, 7, T)),
                     Extract(7, 7, T)),
              Extract(7, 7, T)),
       Extract(7, 7, T))

>>> simplify(xtime_cancelled(T))
Concat(Extract(6, 4, T),
       Extract(3, 3, T) ^ Extract(7, 7, T),
       Extract(2, 2, T) ^ Extract(7, 7, T),
       Extract(1, 1, T),
       Extract(0, 0, T) ^ Extract(7, 7, T),
       Extract(7, 7, T))
```

Note how `z3.simplify` was **smart** enough to do the *cancellation*
automatically by itself: once simplified by Z3, `xtime_broadcasted` and
`xtime_cancelled` are the same.

## Correctness of `xtime*`

Let's verify that we didn't screw up.

The search space is only `2^8`{.mathjax} so we can prove if the
`xtime_X` works comparing it with the original `xtime` **for all the
possible inputs**.

```python
>>> from z3 import Solver, And, Or, BitVec
>>> a = BitVec('a', 8)
>>> solver = Solver()

>>> full_search = [And(a == i, xtime_branch(a) == xtime(i)) for i in range(256)]
>>> solver.check(Or(*full_search))
sat

>>> full_search = [And(a == i, xtime_branchless(a) == xtime(i)) for i in range(256)]
>>> solver.check(Or(*full_search))
sat

>>> full_search = [And(a == i, xtime_cancelled(a) == xtime(i)) for i in range(256)]
>>> solver.check(Or(*full_search))
sat

>>> full_search = [And(a == i, xtime_broadcasted(a) == xtime(i)) for i in range(256)]
>>> solver.check(Or(*full_search))
sat
```

Everything is in order.


## Experiments setup

The 4 functions were tested in [4 different
experiments]({{ asset('performance-ite-expr.py') }})
 or scenarios:

 - `null_experiment`: an 8-bit vector and a simple bitmask operation on it
**without** using `xtime*`. Intended to see the performance of Z3 in a
trivial case.
 - `single_bitvec_experiment`: a call to `xtime*` on an 8-bit vector
and the verification of the results testing 256 possible values.
 - `mix_two_bitvec_experiment`: call `xtime*` twice on two 8-bit vectors,
perform a few bitmask operations on them and verify the correctness doing
a full search of the 65536 possible values.
 - `encrypt_rounds_experiment`: call `xtime*` several times doing
several bitmask and shift operations on 32 8-bit vectors. This
represents a simplified version of a single round of the AES cipher.

For each experiment, each `xtime*` function was tested using the
simplified and not-simplified variants.

Each experiment consisted in create and setup a new `z3.Solver` with its
*own* `z3.Context` and [measure the time]({{ asset('perf-results.pq') }})
that it took checking the model:
the `check-elapsed` time.

Because Z3 is **not** deterministic, we ran each experiment at least 20
times with a maximum of 100 times and collected not only the
`check-elapsed` time but also the [statistics of the
solver]({{ asset('z3-stats-results.pq') }}) provided by
Z3 with `solver.statistics()`.

The `null_experiment` actually does **not** use the `xtime*` function and
it is used to have an idea of how small the  `check-elapsed` time can
be.

## Experiments results

The first thing that we can see is how each `xtime*` performed in each
experiment.

{% call fullfig('mean-check-elapsed-per-func-experiment.svg') %}
Mean  `check-elapsed` time (y axis) per `xtime*` function (x axis).
Each subplot corresponds to a different experiment.
{% endcall %}

A few remarks:

 - The `null_experiment` shows a quite stable plot regardless of the
`xtime*` used as expected.
 - For `single_bitvec_experiment` and `mix_two_bitvec_experiment` there
is little difference if `xtime*` was simplified or not but it **really
made a difference** for the `encrypt_rounds_experiment`.
 - The ITE expression of `xtime_branch` performed better than the others
in `single_bitvec_experiment` but it was as twice as slow in
`mix_two_bitvec_experiment`. *Why?*
 - The `encrypt_rounds_experiment` shows some weird results: a
simplified `xtime_branchless` is incredibly slow while the
non-simplified version is incredibly fast, even faster than the rest.
 - Moreover, in `encrypt_rounds_experiment` the simplified `xtime_broadcasted`
and `xtime_cancelled` have different performance but as we shown before,
they are the same!

This last item makes me thing, are we seeing an outlier affecting the
mean?

We can rule that out measuring the *minimum* instead of the *mean*.

{% call mainfig('min-check-elapsed-per-func-in-encrypt-experiment.svg') %}
Minimum  `check-elapsed` time (y axis) per `xtime*` function (x axis).
Each subplot corresponds to a different experiment. Note how the plot
has the same shape than before.
{% endcall %}

Nope, same thing.

Could be this discrepancy be just by luck? We need a measure independent
from the time and Z3 tracks several statistics for that.

It's unclear what they mean however.

Exploring a little it seems that there is a relationship between `'added
eqs'` and the elapsed time.

{% call mainfig('rel-check-elapsed-and-added-eqs.svg') %}
Relation and linear regression between the time that `check()` took and
the amount of `added eqs`. They follow almost a perfect linear
relationship.
{% endcall %}

Let's see how many `eqs` were `added` in the
`encrypt_rounds_experiment`:

{% call mainfig('mean-added-eqs-per-func-in-encrypt-experiment.svg') %}
Mean `added eqs` (y axis) per `xtime*` function (x axis).
Each subplot corresponds to a different experiment. Note how the plot
has the same shape than before showing a strong relationship between
`added eqs` and the `check-elapsed` time.
{% endcall %}

Same shape that before: for some reason Z3 added more eqs in
`xtime_broadcasted` than in `xtime_cancelled`
(both simplified) even if both are the same Z3 expressions.

So the discrepancy is not due the noise: Z3 indeed saw these two as
different things.

### Code and results

 - [Experiments (Python code)]({{ asset('performance-ite-expr.py') }})
 - [Plotting (Python code)]({{ asset('plot.py') }})
 - [Runtime results (Pandas DataFrame in Parquet format)]({{ asset('perf-results.pq') }})
 - [Z3 stats (Pandas DataFrame in Parquet format)]({{ asset('z3-stats-results.pq') }})


## Conclusions

None.

I'm still missing a lot of pieces of this puzzle.



