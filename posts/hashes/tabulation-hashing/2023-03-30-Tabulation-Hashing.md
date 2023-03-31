---
layout: post
title: "Tabulation Hashing Implementation and Analysis"
tags: [hash, hashing, perf, performance, cython]
inline_default_language: python
---

There are a lot of hash algorithms for different use cases but
*tabulation hashing* caught my attention years ago for its incredible simplicity and
nice independence properties.

Fast and simple.

I will explore a `cython`
[implementation](https://github.com/eldipa/tabulation-hashing)
and see how fast really is.<!--more-->

## What is a tabulation hashing?

The idea is to take keys of `k`{.mathjax} bits and convert them into
hashes of `h`{.mathjax} bits.

We split the key into chunks of `c`{.mathjax} bits and we construct a
table of *random numbers* of `h`{.mathjax} bits each.

This table will have one row per chunk and each row will be
`2^c`{.mathjax} numbers long.

The tabulation hashing is completed defined then by these parameters:

 - key of `k`{.mathjax} bits
 - hash of `h`{.mathjax} bits
 - chunk of `c`{.mathjax} bits

While in theory we can choose any value, the size of a chunk (`c`{.mathjax})
should be small as the rows grows exponentially (`2^c`{.mathjax}) and we
want *small tables to keep them in the cache*.

And how a key is actually hashed? The following diagrams should explain
it:

{% call	mainfig('tabulationhashing.svg') %}
Hash a key in 3 simple steps:

1.- Take the key, split it into `k/c`{.mathjax} chunks.

2.- Use each to *index* each row of the table
obtaining then `k/c`{.mathjax} random numbers of `h`{.mathjax} bits.

3.- Finally xor' them and the result will be the hash of the key.
{% endcall %}


## `cython` implementation

While we have 3 free parameters, I will restrict these:

 - keys of 32 or 64 bits
 - hashes of 32 or 64 bits
 - chunk of 8 bits

We could code a specific implementation for each key/hash bit size
but `cython` thankfully supports a kind of C++ templates called
*fused types*

So, here are the definitions:

```cython
from libc.stdint cimport uint32_t, uint64_t

ctypedef fused key_dtype:
    uint32_t
    uint64_t

ctypedef fused hash_dtype:
    uint32_t
    uint64_t
```

Now let's write a *single* generic hash function:


```cython
@cython.boundscheck(False)
@cython.wraparound(False)
@cython.infer_types(True)
cdef inline hash_dtype c_hash_x(key_dtype k, hash_dtype[::1] table) nogil:
    cdef:
        hash_dtype h = 0, h0, h1, h2, h3, h4, h5, h6, h7
        key_dtype k0, k1, k2, k3, k4, k5, k6, k7

    k0 = k & 0x000000ff
    k1 = (k >> 8) & 0x000000ff
    k2 = (k >> 16) & 0x000000ff
    k3 = (k >> 24) & 0x000000ff

    h0 = table[k0]
    h1 = table[k1 + 256]
    h2 = table[k2 + 256 * 2]
    h3 = table[k3 + 256 * 3]

    h = h0 ^ h1 ^ h2 ^ h3

    if key_dtype is uint64_t:
        k4 = (k >> 32) & 0x000000ff
        k5 = (k >> 40) & 0x000000ff
        k6 = (k >> 48) & 0x000000ff
        k7 = (k >> 56) & 0x000000ff

        h4 = table[k4 + 256 * 4]
        h5 = table[k5 + 256 * 5]
        h6 = table[k6 + 256 * 6]
        h7 = table[k7 + 256 * 7]

        h ^= h4 ^ h5 ^ h6 ^ h7

    return h
```

Few notes of the implementation:

 - `cython` will replace `key_dtype` and `hash_dtype` by the specific
types (`uint32_t`{.c} and `uint64_t`{.cpp}) doing a cross product of types. In
this case `cython` will generate 4 functions in total.
 - the conditional `if key_dtype is uint64_t` is resolved by `cython`
in compile time so it is a handy way to write conditional code without
the C preprocessor.
 - `hash_dtype[::1] table` tells to `cython` that we expect a **memory
view**, in particular an unidimensional contiguous array (faster access).
 - with `@cython.boundscheck(False)` and `@cython.wraparound(False)` we will
be playing with the table as a plain C array (faster access): no out of bound exceptions
or fancy Pythonic indexing.
 - the entire `c_hash_x` function does not use any Python object:
everything is C data. In such case we can release the GIL during its
execution with `nogil` (concurrent friendly)

`c_hash_x` is a `cdef` function which means it can be called only from
within C code.

To make it accessible from Python we code:

```cython
def hash_x(key_dtype k, hash_dtype[::1] table):
    return c_hash_x(k, table)
```

C functions are `static` by default so the C compiler should optimize
the call. In fact, I marked `c_hash_x` as `inline` to hint the compiler.

## Hash a vector of keys

The tabulation hashing shines when we hash a vector of keys as much of
the table rows will be in the cache.

The `cython` code is:

```cython
@cython.boundscheck(False)
@cython.wraparound(False)
@cython.infer_types(True)
@cython.cdivision(True)
def hash_vec_full(key_dtype[::1] kvec, hash_dtype[::1] table, hash_dtype[::1] out):
    cdef:
        hash_dtype hi, h
        key_dtype k, xi

        uint32_t vec_size = kvec.shape[0]
        uint32_t row, shift, rebase
        uint32_t nrows

    with nogil:
        for i in range(0, vec_size):
            k = kvec[i]

            h = c_hash_x[key_dtype, hash_dtype](k, table)
            out[i] = h
```

A few notes:

 - as before we require the arrays to be contiguous
 - a Python function cannot be marked as `nogil` but we can mark as
subpart of it with a context manager
 - the `c_hash_x[key_dtype, hash_dtype]` tells `cython` to call the
*specialized* `c_hash_x` function for those types.

## Runtime performance

I'll analyse the [1.0.1
version](https://github.com/eldipa/tabulation-hashing/releases/tag/1.0.1)
of the tabulation hashing implementation.

For comparison I will use a simple linear hashing:

```
h = (a * k + b)     (mod N)
```

Where `a` and `b` are random numbers of `h`{.mathjax} bits and `N` is `2^h`{.mathjax}

The beauty of this function is that is really simple and fast because we can use `numpy` to write a vectorized
version to hash several keys in one shot.

{% call	mainfig('cmp_runtime_32-32_and_64-64_full_lin.svg') %}
Comparison of elapsed time (in nanoseconds) of tabulation hashing and linear hashing
for a 32-32 `k`{.mathjax}-`h`{.mathjax} bits on the left and 64-64
bits on the right.

The experiment run 1000 times for each setting and the plot shows the
*minimum* elapsed time for each.

The error (dispersion) of the metric is
too tiny to be visible but a more detailed analysis of the noise in the
measurement is provided bellow.

Here the `order` means datasets of `2^{order}`{.mathjax} random numbers
to hash.
{% endcall %}

Linear hashing performs better than tabulation hashing, probably because
`numpy` is well optimized for computing a multiplication and a addition
in a vectorized fashion.

In contrast my `cython` implementation does not take any advantage of
such instructions.

Nevertheless tabulation hashing shows a consistent performance across
the different datasets.

Note also that the performance of the linear hashing gets worst on
larger datasets. The *why* is an open question.

For reference here is the [code for plotting and raw dataset]({{ asset('') }}).

## Noise measurement evaluation

{% call	fullfig('cmp_runtime_noise_full_lin.svg') %}
Dispersion of the elapsed time measured in each experiment (in
nanoseconds).
On top is tabulation hashing, on bottom is linear hashing.
{% endcall %}

Here we can see how the elapsed times of linear hashing are
left-shifted meaning that it ran faster than tabulation hashing.

But the dispersion density is much interesting!

For tabulation hashing we have very high peaks which means smaller
dispersion of the measurements.

Tabulation hashing in mostly affected by cache misses as it is primary
a set of memory lookups.

Linear hashing may use the ALU more intensively. Would this explain the
dispersion?

I'm not sure: I disabled
[hyperthreading/SMT and isolated the CPUs](/articles/2021/03/07/Quiescent-Environment.html)
for the experiment so nobody should had interfered with the ALU.

## Conclusions and further research

Tabulation hashing is slower than linear hashing but close.

The comparison however is not taking into account that a linear hashing
has less math properties than the tabulation hashing.

For example the latter is 3-way independence which some applications
requires and a linear hashing would not be applicable.

My `cython` [implementation](https://github.com/eldipa/tabulation-hashing)
does not make any of vectorized memory access
nor parallelism so it is not exploiting the full capabilities of a
modern CPU.

Something that I may explore in the future.

