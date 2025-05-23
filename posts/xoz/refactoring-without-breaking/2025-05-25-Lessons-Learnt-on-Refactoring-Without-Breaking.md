---
layout: post
title: "Lessons Learnt on Refactoring Without Breaking"
tags: [xoz, cpp, refactor]
inline_default_language: cpp
---

In [xoz](https://github.com/eldipa/xoz), every single piece of content data is associated with a *descriptor*.
The content data may fit in the
descriptor structure so it is placed somewhere else in the `xoz` file.

This content is referenced by the descriptor by a object called
`Segment` that knows how to recover the descriptor's content.

I eventually realized that a single segment would not be enough:
if the descriptor would like to have multiple contents *parts*, the descriptor
should own multiple segments as well.

*"I should replace `Segment segm;` by `Segment segm[];` and that's all -
a simple refactor - how hard could be?"*

Hell...

 - the branch ended with 69 commits, [squashed in a single commit](https://github.com/eldipa/xoz/commit/5521498b16a2bd24440a865c88f25c141be4271c)
 - it was 1 month of work
 - 41 files were changed
 - with 3014 insertions and 1479 deletions in total

It was hard, not because it was difficult the change but because
it was really hard to not break 300 tests with a single change.

This post is a summary of a few good lessons learnt.


## The price of breaking backward compatibility

Let me show exactly how was the situation before the refactor.

The descriptor is stored *in disk* as as follows:

```cpp
struct descriptor_t {
    uint16_t {
        uint own_content : 1;   // mask: 0x8000
        uint lo_isize    : 5;   // mask: 0x7c00
        uint has_id      : 1;   // mask: 0x0200
        uint type        : 9;   // mask: 0x01ff
    };

    /* present if own_content == 1 */
    uint16_t {
        uint large    : 1;      // mask: 0x8000
        uint lo_csize : 15;     // mask: 0x7fff
    };

    /* present if own_content == 1 and large == 1 */
    uint16_t hi_csize;

    /* present if own_content == 1 */
    struct segment_t segm;
};
```

It is obvious that if I wanted to change the single `segm` by an array,
I needed to store *in disk* how many elements segments the array has,
how many *"parts"* the content has: a `content_part_cnt` counter.

The problem is that `xoz` has almost 500 tests and most of them check
directly or indirectly how **exactly** a descriptor is written to disk.

Adding a new field will break a lot of them if not all.

Even if some tests don't check what is written, they compute
a **checksum** of the structure. Adding `content_part_cnt` will make
the checksum differ and again, more tests would be broken.

By that time `xoz` was not released to the public so changing the file
format in such non-backward compatible way was fine...
**except for me!**

## Lesson 1: minimize the changes

The `own_content` signals if the descriptor has or not
a segment. With multiple content parts (multiple segments), that bit
would signal if there is at least one segment.

This means that one segment is always implicit if `own_content` is set.
A `content_part_cnt` does not have to count how many parts are but how many
are plus the one implicit. A `content_part_cnt` valued to zero would mean that
there is one content part.

*So what?*

`xoz` uses the same checksum that the IP protocol uses: it is not very
robust but it can be computed easily and in particular, adding 2-bytes
zeros does not change the checksum.

So for all my tests that have a single segment, `content_part_cnt`
will be zero and for such tests, the checksum will not change.

I cannot avoid fixing the tests that check *exactly* what is written
to disk but I can prevent breaking the ones that check
the checksum.

This is how the structure looks like now:

```cpp
struct descriptor_t {
    uint16_t {
        uint own_content : 1;   // mask: 0x8000
        uint lo_isize    : 5;   // mask: 0x7c00
        uint has_id      : 1;   // mask: 0x0200
        uint type        : 9;   // mask: 0x01ff
    };

    /* present if own_content == 1 */
    uint16_t content_part_cnt;

    /* present if own_content == 1 */
    struct content_part_t cdata_entries[1 + content_part_cnt];
};
```

Another detail:
the `large`, `lo_csize` and `hi_csize` fields define the size of the
content part so now they are bundled together with its segment `segm`.
The `content_part_t` has the same layout as before to not break more
tests.

```cpp
struct content_part_t {
    uint16_t {
        uint large    : 1;      // mask: 0x8000
        uint lo_csize : 15;     // mask: 0x7fff
    };

    /* present if large == 1 */
    uint16_t hi_csize;

    struct segment_t segm;
};
```

## Lesson 2: if you break too much, stop and step back

Once I resolved the disk format it was time to do the refactor of the
structures in memory and run the tests.

But when I tried to do a much larger change in the code base, *hell*,
too many broken tests! Much more that I anticipated.

I faced this situation several times and the lesson that I learnt was
*"if you break too much, stop and step back"*.

No, it was not a bug, it was a **symptom** that the refactor
was **too disruptive** to be done in a single changeset.

Starting to do multiple sub-fixes + sub-refactors, all at once, while having
the tests broken was a **no-go**. Doing it so it's like going for a
driving, blind.

Step back and try something smaller..., even if you are going to throw it away later.

## Lesson 3: do incomplete throw-away refactors, keep all tests passing

Step back and try something smaller..., small incomplete refactors
*even* if you are going to *throw it away later*.

For example, I *only* modified the read-from-disk and write-to-disk functions
and maintain all the rest of the code from using the first segment loaded.

That allowed me to test the read/write of the new `content_part_cnt` and
fix the tests being 99% sure that if a test was broken it was because
I added 2 zero bytes (`content_part_cnt`) and nothing else.

I was sure that part of the code that I did it was temporal and not part
of the real refactor but doing these intermedian changes allowed me to
*keep the tests passing all the time* (after a reasonable amount of
fixing).

But I eventually I got stuck.

## Lesson 4: if decoupling is hard, isolate first (with spies)

In `xoz`, the `Descriptor` objects are managed by `DescriptorSet` sets.

These *sets* are an unorder collections of descriptors, not just in memory
but also in disk. There is an *intimate relationship* between those two
in order to operate efficiently. In fact,
`DescriptorSet` **is** a `friend` class of `Descriptor`.

And this **is** a problem.

Changing the internals of `Descriptor` made the logic in `DescriptorSet`
to change in unexpected ways.

{% call marginnotes() %}
But why? Because of life.

And because `DescriptorSet` was developed much earlier. Back then
the `Descriptor` class didn't offer any public API to manage the content
segment but also because using the internals, `DescriptorSet` could do
things hard to get done otherwise.

Time passed, and `Descriptor` acquired a simplified, high-level API
for managing its content. Great for any subclass of it but too limited
for `DescriptorSet`.
{% endcall %}

And to make it worse, `DescriptorSet` used its own self-managed content segment
(to store the descriptors in the set)
**bypassing the public interface** of `Descriptor` to interact with
the content.

The following is a oversimplification of the code:

```cpp
class Descriptor {
private:
  friend class DescriptorSet;

  // old, single-part content logic (but still the one working by now)
  uint32_t csize;
  Segment segm;

  // new, multi-part content logic (loaded from disk, but not in use)
  std::vector<content_part_t> cparts;
};

class DescriptorSet : public Descriptor {
private:
  uint32_t own_csize;
  Segment own_managed_segm;

  void update() {
    // attention! DescriptorSet is overriding Descriptor's (old) internal state!
    this->segm = own_managed_segm;
    this->csize = own_csize;
  }
};
```

Before trying to do any change, I needed to isolate what
`DescriptorSet` knew of `Descriptor`.
You may think, *"ok, just add a bunch of public `set()` and `get()` methods
to `Descriptor` and make `DescriptorSet` to use them instead of
accessing the internals*.

But no, adding just `set()` and `get()` would lead to a bad design. And
worse, those public methods would be callable from *anybody*, not just
`DescriptorSet`.

My approach was to use **spies**: classes that *are* `friend` of
`Descriptor` and implement a small subset of the functionality needed
by `DescriptorSet` making `DescriptorSet` a friend **not longer**.

```cpp
class Descriptor {
private:
  friend class DSpy; // DescriptorSet is not longer a friend

  // old, single-part content logic (but still the one working by now)
  uint32_t csize;
  Segment segm;

  // new, multi-part content logic (loaded from disk, but not in use)
  std::vector<content_part_t> cparts;
};

class DSpy {
private:
  Descriptor& dsc;

public:
  void update_segm(const Segment& segm, const uint32_t csize) const {
    // internals access, to the old logic
    dsc.segm = segm;
    dsc.csize = csize;
  }
};

class DescriptorSet : public Descriptor {
private:
  uint32_t own_csize;
  Segment own_managed_segm;

  void update() {
    // Not longer accessing anything private
    DSpy(*this).update_segm(own_managed_segm, own_csize);
  }
};
```

It may not seem like much, I'm still exposing the internals **but**:

 - I have **mapped** exactly **which** internals I'm leaking: they are in the `DSpy`
   methods, a much **smaller** place too look.
   For comparison, `DSpy` has 3 methods of 1 line each and
   `DescriptorSet` has ~40 methods with a total of more than 1000 lines
   of code.
 - The use of spies allows me to be **selective** to which internals I want
   to leak: I have a small `DSpy` class for `DescriptorSet` and another,
   larger `DSpyForTesting` for testing but nobody is a direct friend
   of `Descriptor` so nobody has access to the entire internals.

## Lesson 5: chop-chop, one small bite at time

With the spies in place, I took each of their methods, one by one, and
started to figure out how to remove it, doing the necessary changes
in `DescriptorSet` and fixing the tests, if required.

I started with a `DSpy` with ~8 non-trivial methods and today
I reduced it to just 2, one-liners. Each method removed, each
simplification lead to a smaller, much easier to understand, interaction
between `Descriptor` and `DescriptorSet`.

Only then I took the leap to remplace any use of the old single-part
implementation by the new one. The real refactor.

The result?

 - the branch ended with 69 commits, [squashed in a single commit](https://github.com/eldipa/xoz/commit/5521498b16a2bd24440a865c88f25c141be4271c)
 - it was 1 month of work
 - 41 files were changed
 - with 3014 insertions and 1479 deletions in total

## Summary

 - Try to break as little as possible.
 - If you break too much, stop and step back
 - Incomplete throw-away code is ok, keep your tests passing, don't get blind.
 - Decouple, and if it is hard, isolate first.
 - Split your refactor into the smallest chunks possible and go one by
   one.


