---
title: "Behind `memcpy`/`memmove`: overlap, words and alignment"
layout: post
tags: [memory, memcpy, copy, bytes, xoz]
inline_default_language: cpp
---


{{ marginfig('00_no_overlap_setup.svg', width='auto') }}
How do `memcpy`/`memmove` work?

I ended asking that question a few days ago while I was implementing the
copy between sections of a file for the `xoz` library.

`memcpy` and `memmove` deal with memory, not with files, but I imagined that I could
borrow some ideas anyways.

And I did.<!--more-->

`memcpy` copyies bytes from a `src` buffer into another that does not
overlap (both buffers are in differen parts of the memory)
`memmove` does the same thing, copying from `src` to `dst` but handling
carefuly the situation of overlap.

Under the hood, both functions are implemented in the same way. But why
the stdlib has 2 separated functions then?

When doing the *"copy"* between overlapping buffers, you will end up being
overriding part of the `src` content.
{% call marginnotes() %}
Well, quantum information cannot be copied without destroying the
original one. It is called *teleportation*.

I guess the physics are more sci-fi inclined for picking terms.
It is obvious to me that the Universe is just calling `memmove`.
{% endcall %}
Imagine wanting to *copy* `src` and got `src` corrupted, the copies
does not work like that!
It makes sense to name the function
`memmove` because it feels that the content is moved from `src` to `dst`
(so you don't care what was left in `src`) and leave `memcpy` for when
it is a truly copy.

For the rest of the post I will refer to `memcpy` for simplicity
in the wording, even if we are going to see how to handle overlapping buffers
like `memmove` does.

## Copy one byte at time - bytecopy

Let's start with the most obvious algorithm: *copy one byte at time*.

{{ marginfig('01_no_overlap_1_byte_copy_alternative_shot.svg', width='auto') }}
```cpp
void naivecopy(char* dst, char* src, size_t sz) {
    while (sz) {
        *dst = *src;
        ++dst;
        ++src;
        --sz;
    }
}
```

When we copy between two *non-overlaping* areas, eveything goes smooth
but when they do overlap, this doesn't work.

{{ mainfig('02_overlap_1_byte_copy_incorrect_alt.svg', width='auto') }}

The problem is that when we do the write we are overriding data we
didn't copyied yet.

So we just need start copying from the overlapping
bytes before they are overriden.

There are 2 cases:

 - when the overlap is at the begin of `src` we copy *forwards* as in `naivecopy`
 - when the overlap is at the end of `src` we copy *backwards*

{{ mainfig('02_overlap_1_byte_copy_fwd_bwd_correct.svg', width='auto') }}

Let's call these `bytecopy_fwd` and `bytecopy_bwd` respectively and
`bytecopy` the main algorithm that call one or the other depending of
the overlap.


## Copy multiple bytes at time - wordcopy and blockcopy

{% call marginnotes() %}
The term *"word"* is misleading: a 64 bits architecture may support operands
larger than its word size, like `uint128_t`. So don't take this term
to strictly.

AVX instructions can these days work with 512 bits but its usefulness
for copying seems not be clear according
[this post](https://stackoverflow.com/questions/66923045/why-glibc-memcpy-not-choose-avx512-version).
While it can copy data faster, it may degrade the performance of the system due
how they are implemented
([other post](https://stackoverflow.com/questions/56852812/simd-instructions-lowering-cpu-frequency)).

At the end of the day is a per-architecture analysis: just pick
the largest and fastest word size.
{% endcall %}


Instead of copying byte by byte we can do it *word by word*.
Modern computers can operate with `uint32_t`, `uint64_t`, or even `uint128_t`
in a single instruction so a `memcpy` implementation using them
can go 4, 8 or even 16 times faster.

{% call marginnotes() %}
To be precise, the glibc uses `vm_copy` that maps the pages of `dst` to
the pages of `src` on *copy-on-write*. So `vm_copy` defers the copy
until a page fault.<br />
When copying large buffers with infrequent writes, this lazy copy
avoids the costs of a real copy.

Reference: [developer apple docs](https://web.archive.org/web/20240901173225/https://developer.apple.com/library/archive/documentation/Performance/Conceptual/ManagingMemory/Articles/MemoryAlloc.html)
{% endcall %}

And if supported by the architecture, we could use even larger chunks
or *blocks*.
[glibc](https://github.com/bminor/glibc/blob/751a5502bea1d13551c62c47bb9bd25bff870cda/sysdeps/mach/pagecopy.h#L26-L32)
for example has `PAGE_COPY_FWD_MAYBE` that copyies
entire pages: few kilobytes in a single operation!

We may call these algorithm `wordcopy` and `blockcopy` respectively.

{{ mainfig('03_no_overlap_n_byte_copy_correct.svg', width='auto') }}

{% call marginnotes() %}
If we are talking of `uint64_t` or similar word sizes, all the
implementations that I saw don't try smaller word sizes and fallback
immediately to `bytecopy`.

However, some implementations,
like [glibc's memcpy](https://github.com/lattera/glibc/blob/895ef79e04a953cac1493863bcae29ad85657ee1/string/memcpy.c#L26-L58),
copy by page sizes (a few kilobytes), then copy by word and finally
copy the last bytes by one byte at time.<br />
And it makes sense, from copy a few kilobytes per operation to copy
one byte at time, there is room to do a much efficient copy in between.
{% endcall %}

When dealing with input sizes not multiple of the word/block size, we
need to copy by smaller sizes towards the end and copying byte by byte
in the last steps.

{{ mainfig('03_no_overlap_n_byte_copy_no_multiple_size_correct.svg', width='auto')}}

### Overlapping areas

To deal with overlapping areas we have the same fordward/backward
algorithms than before but copying word by word so let's call them
`wordcopy_fwd` and `wordcopy_bwd` respectively.

**But...**


{% call marginnotes() %}
In most architectures reading/writing words are only possible from/to
addresses aligned to the word size.
So the pathological example should never happen.

However, as mentioned before, relax the term *"word"*. In `xoz` for
example, the copy between parts of a files does not require any
alignment so I faced this **very** overlapped case.
{% endcall %}

When the source and destination areas are **very** overlapped,
it may be possible that the read of a word overlap with its write (left diagram),
The solution is to copy into a local variable in between (right diagram).

{{ mainfig('04_overlap_n_byte_copy_incorrect_and_with_temp_buffer.svg', width='auto') }}

## Alignment

In general, copying words/blocks requires that both the source and the
destination are aligned to the word/block size.

### Eventually `src` and `dst` get aligned

If we are lucky, we could have `src` and `dst` addresses misaligned but
by the same amount. This is the same to say that both addresses share the same `]N` lower bits
where `]N` is the `]\log_2\left(word size\right)` or

```cpp
src & (-wordsize) == dst & (-wordsize)
```

If that is the case we can call `bytecopy` until both gets aligned and
then go full speed with copying by words/blocks.

{{ mainfig('05_misaligned_n_byte_copy_correct.svg', width='auto') }}

### Only `dst` gets eventually aligned

As before we start with by calling `bytecopy` until `dst` is aligned
but not necessary `src` is.

Consider the following:

{{ mainfig('05_src_misaligned_but_dst_aligned_setup.svg', width='auto') }}

Take the `src` address and compute:

{% call marginnotes() %}
In this example, `src` is at address 3 so with `wordsize` of 4 bytes
`sh1` is 3 and `sh2` is 1.
{% endcall %}

```cpp
int sh1 = src % wordsize;
int sh2 = wordsize - sh1;
```

`sh1` and `sh2` are how many bytes we should shift a word to make it
aligned either towards lower addresses or higher addresses.

Now the trick: for writing 1 word into `dst`, we read 2 words
from `src`, *combine* (or *merge*) them and write that into `dst`.

{% call marginnotes() %}
This is valid only for *big endian* architectures. For *little endian*,
invert the shift directions.

Reference: [glibc's MERGE](https://github.com/bminor/glibc/blob/e64a1e81aadf6c401174ac9471ced0f0125c2912/sysdeps/generic/memcopy.h#L66-L71)
{% endcall %}

The *combine* (also called *merge*) of two words takes the left word (lower
addr) and shifts it by `sh1` to the left; takes the right word (higher addr)
and shifts it by `sh2` to the right and finally bitwise `or` them and write
the result into `dst`.

{{ mainfig('06_merge_all.svg', width='auto') }}

Note how the word-aligned read  {{ inlinefig('06_bcde.svg', width='auto', vertical_align='bottom') }}
is right shifted 1 byte making
room for the single byte from the previous word
{{ inlinefig('06_a.svg', width='auto', vertical_align='bottom') }}
and in combination,
 {{ inlinefig('06_abcd.svg', width='auto', vertical_align='bottom') }}
is formed and written.

The remaining byte {{ inlinefig('06_e.svg', width='auto', vertical_align='bottom') }}
is not thrown away but used to build the next word to write.


The first loop iteration is slighly special because we cannot read a full
word (we cannot read behind the initial `src` pointer).

{{ mainfig('05_src_misaligned_but_dst_aligned_merge_p1.svg', width='auto') }}

For the rest of the loop iterations we don't need any padding and work
with entire words.

{{ mainfig('05_src_misaligned_but_dst_aligned_merge_p2.svg', width='auto') }}


The shifts and `or` operations are not free so this `memcpy`
implementation is slower than the one with the inputs aligned
but still much faster that a `bytecopy`.

The key insight is that while we are reading 2 words per write, we can
hold in a local variable a word to used in the next iteration. So we are
*not* reading the whole `src` buffer twice.

{% call marginnotes() %}
Here are the
[glibc's implementations](https://github.com/lattera/glibc/blob/895ef79e04a953cac1493863bcae29ad85657ee1/string/wordcopy.c#L340).
{% endcall %}

Let's call this algorithm `wordcopy_dst_aligned` and like before it has
two flavours `wordcopy_dst_aligned_fwd` and `wordcopy_dst_aligned_bwd`
for handling overlap.

## My take aways

I didn't know the *combine* / *merge* trick or the possibility to lazy
copy entire pages.

Taking the seemingly simple `memcpy` and `memmove` functions and seeing
their implementations shown me that even a plain copy can hide some
interesting tricks.

*What are your take aways?*


