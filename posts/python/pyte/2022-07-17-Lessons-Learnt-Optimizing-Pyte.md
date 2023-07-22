---
layout: post
title: "Lessons Learnt Optimizing Pyte"
tags: [python, pyte, terminal, optimization, performance]
inline_default_language: python
---

Few thoughts about Python code optimization and benchmarking
for
[pyte](https://github.com/selectel/pyte) and
[summarized here](/articles/2022/07/15/Sparse-Aware-Optimizations-for-Terminal-Emulator-Pyte.html).<!--more-->

## Optimize Python code is **not** like optimize C code

The *mental model* for optimize of Python code is not the same for
optimize C/C++/Rust code.

{% call marginnotes() %}
Actually any modern compiler will do this for
you and if possible, it will replace the bit hacks by much faster
specific instructions for you micro.
{% endcall %}

In low level languages a conditional can be replaced with as faster
combination of bit hacks.

A classic example is
[find the minimum two values](https://graphics.stanford.edu/~seander/bithacks.html#IntegerMinOrMax):


```cpp
int x = 1, y = 2;

int minimum = (x < y) ? x : y;   // slow, branch version

int minimum = y ^ ((x ^ y) & -(x < y)); // fast, branchless version
```

Doing this in Python is insanely slow:

```python
: %%timeit x, y = 1, 2
: x if x < y else y

20.3 ns ± 0.917 ns per loop (mean ± std. dev. of 7 runs, 100,000,000
loops each)

: %%timeit x, y = 1, 2
: y ^ ((x ^ y) & -(x < y))

81.4 ns ± 4 ns per loop (mean ± std. dev. of 7 runs, 10,000,000 loops
each)

: %%timeit x, y = 1, 2
: min(x, y)

70.5 ns ± 0.88 ns per loop (mean ± std. dev. of 7 runs, 10,000,000 loops
each)
```


{% call marginnotes() %}
A *just in time* compiler may change this but for now, CPython does
not implements it. [PyPy](https://www.pypy.org/)
may yield different results.
{% endcall %}

The bit hack is insanely slow when compared with the branch
version: it is because the bit hack involves many more Python
instructions that need to be interpreted by the VM.

The call to `min` is not much faster either. While this requires less code and
the function it is implemented in C, the call to a function is expensive
and (for CPython 3.9), the function is not inline'd.

Also complex code may not be too slow if they are coded entirely in C.

For example, Rust developer could think that a simple `x = y + 2` is way
faster than a lookup on a hash-based dictionary/map. It is obvious that
the addition can be done in a single instruction and the lookup will
take much more.

But in Python the things are not so clear:

```python
: %%timeit x, y = 1, 2
: x = y + 2

16.1 ns ± 0.321 ns per loop (mean ± std. dev. of 7 runs, 100,000,000
loops each)

: %%timeit d = {1: 2}
: x = d[1]

19.3 ns ± 0.584 ns per loop (mean ± std. dev. of 7 runs, 10,000,000
loops each
```


## Loops

Doing a loop in Python is okay but doing it in C is much faster:


```python
: %%timeit d = {x: x for x in range(10000)}; keys = list(d)
: for k in keys:
:    d.get(k)

292 µs ± 6.35 µs per loop (mean ± std. dev. of 7 runs, 1,000 loops each)

: %%timeit d = {x: x for x in range(10000)}; keys = list(d)
: list(map(d.get, keys))

179 µs ± 5 µs per loop (mean ± std. dev. of 7 runs, 10,000 loops each)
```

## Attribute/methods lookups

In C, `foo.bar.baz` is typically resolved by the compiler as an offset
from the base address of `foo` at compile time. Not big deal.

But due the dynamic nature of Python, `foo.bar.baz` not only needs to be
resolved at runtime but every single time because the objects may change
and point to another.

When a lookup is done in a loop, prefetching the attribute or method before
the loop saves precious time.

```python
: %%timeit d = {x: x for x in range(10000)}; keys = list(d)
: for k in keys:
:    d.get(k)

301 µs ± 6.56 µs per loop (mean ± std. dev. of 7 runs, 1,000 loops each)

: %%timeit d = {x: x for x in range(10000)}; keys = list(d); get = d.get
: for k in keys:
:    get(k)

286 µs ± 10.8 µs per loop (mean ± std. dev. of 7 runs, 1,000 loops each)
```

It may not seem like much but in the example above I prefetched a single
method; in complex loops prefetching more things will speed it up.

## Remove asserts

Assertions are great for check invariants of the code: things that
**must** be guaranteed to make any sense of the programs.

{% call marginnotes() %}
Well, this is true for C/C++ but not strictly true for Python. An
`assert` in Python raises an `AssertionError` that can be captured like
any other exception.

You may think that nobody would want to capture an `AssertionError` but,
sorry to say, this exception inherits from `Exception` and it is quite
common to capture those.
{% endcall %}

If an invariants ends up to be false, an assert on that will fail
leading the program to its termination.

It is like a self-destruction mechanism.

An indeed if something really bad happen to the program's state, not
further action may be safe to execute. It is better to die as quickly as
possible and avoid doing more damage.

An `assert` requires *at least* a check; complex invariants will require
complex asserts and this leads to spend more time on that..

In C and similar the asserts can be removed with a compilation flag:
you can have them
enabled during testing but disabled on production.

```cpp
void foo(() {
    assert(expensive());
    ...
}
```

When disabled, neither the `assert` nor the `expensive()` function are called.

Python with the `-O` flag has something similar:
the asserts are not executed **but** the asserts' arguments do.

```python
def foo():
    assert expensive()
```

The `expensive()` is executed with or without `-O` --
a pointless optimization IMHO.

An easy win for optimization is just to **remove** the asserts.


## Ensure your benchmark suite is valid

When doing a benchmark the first thing to validate is not if it ran
faster or slower. The first thing to validate is that the output of your
benchmark makes sense.

In `pyte` a benchmark test consists in a input file that it is passed
through `pyte.Stream` that turns it into actions on the `pyte.Screen`.

It is important then that this processing makes sense before using it
for benchmarking.

Guess what...

I found that the test suite was incorrectly implemented. The input files
are *binary* files and `pyte.Stream` opens them as *text* files (UTF8).

This mismatch made the *return line* `\r` to be missed from the stream.

This is not how real code would use `pyte` so the benchmark suite was
invalid.

The fix was to use `pyte.ByteStream` but I had to pay the price to run
all the tests again (hours lost).

## Have a parallel project for benchmark

Trying different things may make you repo a little messy. For running
benchmark it is better to have a second repo and use the first as
upstream.

```shell
$ ls proj/pyte                            # main project
$ git clone proj/pyte proj/benchmark_pyte     # second project
```

Then, only what it is committed and update on `benchmark_pyte` will be
used for the benchmark.

## Plan the benchmark execution

When a full benchmark execution takes **hours**, you need to know *what*
and *when* you really need to run and run only that.

Save your time.




