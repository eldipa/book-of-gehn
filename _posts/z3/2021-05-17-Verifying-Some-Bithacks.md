---
layout: post
title: "Verifying some bithacks"
tags: z3 smt sat solver bitvec verify bithacks
---

We are going to verify some of the [bit twiddling
hacks](https://graphics.stanford.edu/~seander/bithacks.html) made and
collected by Sean Eron Anderson and other authors.

This is *the* classical scenario to put on test your Z3 skills.<!--more-->

The plan is to pick 4 *bithacks* and verify them with Z3. Who knows, we
may find a bug.

## Detect if two integers have opposite signs

This is a simple
[bithack](https://graphics.stanford.edu/~seander/bithacks.html#DetectOppositeSigns)
suggested by Manfred Weis.

```cpp
int x, y;               // input values to compare signs

bool f = ((x ^ y) < 0); // true iff x and y have opposite signs
```

It has an immediate translation to Z3 using `BitVecs`:

```python
>>> from z3 import BitVecs, Solver, If, And, Or

>>> x, y = BitVecs('x y', 32)
>>> f = (x ^ y) < 0
```

To verify this we will set an *assumption* that contradicts the expected
(and correct) value: if we find it satisfiable it means that the model
found by Z3 is a *counterexample* and then a bug.

An unsatisfiable means that the code is correct.

In this case the assumption is simple:

 - we say that `f` is true (the inputs have *opposite* signs) **and**
the inputs have the *same* signs;
 - *and* we say that `f` is false **and** the inputs have the *opposite*
signs.

```python
>>> same_sign = Or(And(x >= 0, y >= 0), And(x < 0, y < 0))

>>> s = Solver()
>>> s.add(If(same_sign, False, True) != f)

>>> s.check()
unsat
```

Verified.


## Conditionally negate a value without branching

The following
[bithack](https://graphics.stanford.edu/~seander/bithacks.html#ConditionalNegate)
suggested by Avraham Plotnitzky.

```cpp
bool fDontNegate;  // Flag indicating we should not negate v.
int v;             // Input value to negate if fDontNegate is false.
int r;             // result = fDontNegate ? v : -v;

r = (fDontNegate ^ (fDontNegate - 1)) * v;
```

Its translation to Z3 is *almost* immediate:

```python
>>> from z3 import BitVecs, Solver, If, Or

>>> fDontNegate, = BitVecs('fDontNegate', 32)
>>> v, = BitVecs('v', 32)
>>> f = (fDontNegate ^ (fDontNegate - 1)) * v
```

The C code uses a `bool` for the `fDontNegate` variable but in Z3 we use
a `BitVec` of the same width than the input.

Z3 does not know how to *upcast* a `bool` to a `BitVec` and mixing
variables of *different sort* leads to error.

Instead we just see the boolean as an `BitVec`.

The C99 and C++11 specifications say that a boolean can be seen as a `0`
(`false`) or as a `1` (`true`).

```python
>>> s = Solver()
>>> s.add(Or(fDontNegate == 0, fDontNegate == 1))   # force a boolean value
```

Now, we assume the contradiction.

```python
>>> s.add(If(fDontNegate == 1, v, -v) != f)

>>> s.check()
unsat
```

And nope, no counterexample was found: the bithack is correct.

## Merge bits from two values according to a mask

This
[bithack](https://graphics.stanford.edu/~seander/bithacks.html#MaskedMerge)
was suggested by Ron Jeffery.

```cpp
unsigned int a;    // value to merge in non-masked bits
unsigned int b;    // value to merge in masked bits
unsigned int mask; // 1 where bits from b should be selected; 0 where from a.
unsigned int r;    // result of (a & ~mask) | (b & mask) goes here

r = a ^ ((a ^ b) & mask);
```

The verification steps are the same, nothing new around here.

```python
>>> from z3 import BitVecs, Solver, If, And, Or, Bools

>>> a, b, mask = BitVecs('a b mask', 32)
>>> r = a ^ ((a ^ b) & mask)

>>> s = Solver()
>>> s.add(((a & ~mask) | (b & mask)) != r)

>>> s.check()
unsat
```

## Select the bit position (from the most-significant bit) with the given count (rank)

*This is a long one.*

This
[bithack](https://graphics.stanford.edu/~seander/bithacks.html#SelectPosFromMSBRank)
was suggested by Juha Järvi and it is much more complex than the others
bithacks.

Given an `uint64_t` number `v` and a rank `r` (a number
between 1 and 64), the bithack returns the *position* `s` of the bit that it
is the `r`th `1` bit counting from the left.

The following 64-bit code selects the position of the `r`th `1` bit
when counting from the left.

The C code is quite large so we are going to go to the Z3 code directly,
step by step.

The bithack uses `a`, `b`, `c`, `d` and `t` as intermediate and temporal
values. These are not *variables* of the model so we don't need to
create a `BitVec` for them.

On the other hand, `v` and `r` are. In the C code `r` is 32 bits
integer and `v` is 64 bits but in the following setup both will have
the same width of 64 bits.

This is required because Z3 does not know how to *upper cast* or
*promote* a 32 bits integer to 64 bits.

It is easier to use 64 bits and *constraint* its range.

```python
>>> from z3 import BitVecs, Solver, If, And, Or, Bools, ULT, Not
>>> solver = Solver()
>>> v, r = BitVecs('v r', 64)

>>> solver.add(1 <= r, r <= 64) # rank valid range [1-64]

>>> UL3 = 0x5555555555555555
>>> UL5 = 0x3333333333333333
>>> UL11 = 0xf0f0f0f0f0f0f0f
>>> UL101 = 0xff00ff00ff00ff
```

This is the first setup. Notice how `a`, `b` and others are just
*expressions* and not Z3's variables.

```python
>>> a = v - ((v >> 1) & UL3)
>>> b = (a & UL5) + ((a >> 2) & UL5)
>>> c = (b + (b >> 4)) & UL11
>>> d = (c + (c >> 8)) & UL101

>>> t = (d >> 32) + (d >> 48)
>>> s = 64
```

In C `r` is a *variable*: a piece of memory which value can change.

But in Z3 we want to preserve the variables and **don't change them**.
Their should be *constants*.

Instead we will use
a simple Python variable `q` to hold the intermediate expressions.

In C we have:

```cpp
r -= (t & ((t - r) >> 8))   // note the -= modifier
```

But in Python we introduce `q` instead

```python
>>> q  = r - (t & ((t - r) >> 8))   # changed from -= to a plain =
```

Now `q` is a Z3 expression and we can replace it by another like in C we
replace one value by other for the *same* variable.

The rest are just a copy-and-paste from the bithack.

```python
>>> s -= ((t - r) & 256) >> 3
>>> t  = (d >> (s - 16)) & 0xff

>>> s -= ((t - q) & 256) >> 4
>>> q -= (t & ((t - q) >> 8))
>>> t  = (c >> (s - 8)) & 0xf

>>> s -= ((t - q) & 256) >> 5
>>> q -= (t & ((t - q) >> 8))
>>> t  = (b >> (s - 4)) & 0x7

>>> s -= ((t - q) & 256) >> 6
>>> q -= (t & ((t - q) >> 8))
>>> t  = (a >> (s - 2)) & 0x3

>>> s -= ((t - q) & 256) >> 7
>>> q -= (t & ((t - q) >> 8))
>>> t  = (v >> (s - 1)) & 0x1

>>> s -= ((t - q) & 256) >> 8
>>> s = 65 - s
```

### Verification - when `s != 64`

Now, the funny part. How to verify this?

First a sanity check:  `s` must always to be between 1 and 64 -- it is
the position of a bit in a 64 bits width number after all.

```python
>>> solver.check(Or(s <= 0, 64 < s)) # check out of range for selected bit
unsat
```

Ok, let's see what `s` value we have for some values of `v` and `r`.

```python
# The 60th bit is the first 1 counting from the left (rank 1)
>>> solver.check(v == 0b00010001, r == 1)
sat
>>> solver.model().eval(s)
60

# The 64th bit is the second 1 counting from the left (rank 2)
>>> solver.check(v == 0b00010001, r == 2)
sat
>>> solver.model().eval(s)
64
```

Verifying that `s` is correct for *every* possible value of `r` and `v`
**by enumerating each possible case is not feasible**.

It's just too expensive, in time, memory and brain power.

So the plan is build a set of constraints that lead to a
contradiction against `s`: if it is satisfiable, the model (solution)
found will be a counterexample and we'll know that `s` is wrong.

Assume that we fix `s` and `r` to `s = 60` and `r = 2`. What we know
about `v`?

We know that `v` has one `1` bit set at position 60 (reading from left), which
it is the *rank bit* and on the left of it it has one and only one `1` bit
more.

`v` could be one of these to name a few:

```
MSB  rank bit  LSB
   \     V    /
    ::10010000      (the :: means a bunch of zero
    ::01010000       to fill the 64 bits bit vector)
    ::00110011
 /------|
one and only one
    1 bit
```

From the picture we can think, what value `v` is the *lowest* of all the
possible `v` values that satisfy `s = 60` and `r = 2`?

A number is lower than other than another if it has fewer `1` bits and
those are in the right side (lesser significant bits).

We cannot reduce the count of `1` bits on the left side of the rank bit:
we are forced to have `r - 1` bits otherwise we would violate the `r =
2` condition. But we have no restriction on the right side.

The *minimum* `v` value has all zeros on the right and it has all the `1`
bits *"pushed"* to the left of the rank bit as possible.

In short:

```
     rank bit
         V
    ::00110000 ← the minimum
    ::10010000
    ::01010000
    ::00110011
 /------|
a single 1
```

Given `s` and `r` we can write the `minimum` value in two steps:

 - build the `1` bits sequence including the rank bit
 - shift the sequence to the left filling the right bits with 0s

```python
>>> minimum = ((1 << r) - 1) << (64 - s)
```

The next question is, what are the *greatest* `v` of all the possible
`v` that satisfy `s` and `r`?

The *maximum* `v` value has all the `r - 1` `1` bits on the left (most
significant bits) and the bits on the right of the rank bits are all `1`.

It is basically the same reasoning for the minimum but in the opposite
direction.

In short:

```
     rank bit
         V
    ::00110000 ← the minimum
    ::10010000
    ::01010000
    ::00110011
   1::00011111 ← the maximum
 /------|
a single 1
```

The maximum has two parts.

 - the high part which are the `r - 1` bits pushed to the left

```python
>>> highpart = ((1 << (r-1)) - 1) << (64 - (r-1))
```

 - and the lower part which it is the rank bit and all the bits on its
right being `1`

```python
>>> lowerpart = (1 << (64 - s + 1)) - 1
```

Trivially, the maximum is:

```python
>>> maximum = highpart | lowerpart
```

Now, let's try to find a counterexample: a number `v` that does **not**
satisfy the minimum/maximum range for *some valid* `r` and `s`.

The `BitVecs` are **signed** integers and they use **signed** comparisons.
In our definition of `minimum` and `maximum` we though them as
**unsigned** so we need to use Z3's `ULT` functions (unsigned less
than).

```python
>>> not_in_range = Or(ULT(v, minimum), ULT(maximum, v))

>>> solver.check(s != 64, not_in_range) # byexample: +timeout=120 +skip
unsat
```

The extra assumption `s != 64` is because while 64 is a valid position,
it is *also* used as an error.

A trivial error settings which *violates* the minimum/maximum range
could be:

```python
>>> solver.check(s == 64, r == 2, v == 1, not_in_range)
sat
```

### Verification - when `s == 64` (first try)

Because `s = 64` means that the rank bit is the LSB, we know that we
must have `r - 1` bits in the rest of the bit vector.

In particular we must have exactly `r` `1` bits in `v` -- no more, no
less.

So we have two scenarios:

 - when we have `v` with its LSB set to `1` *and* with exactly `r` `1` bits
in total
 - when `v` has less than `r` `1` bits and therefore it is an expected error
case

For the bit-count we can use a [naive
bithack](https://graphics.stanford.edu/~seander/bithacks.html#CountBitsSetNaive)

```python
>>> def bit_count(v):
...     count = 0
...     for i in range(64):
...         count += v & 1
...         v >>= 1 # we can override v here 'cause it won't affect the outer v
...     return count

>>> good_cases = And(bit_count(v) == r, (v & 1) == 1)
>>> bad_cases = bit_count(v) < r
```

Finally we check the negation of it. Sadly the check takes **too much
time** and I don't know the result

```python
>>> solver.check(s == 64, And(Not(good_cases), Not(bad_cases)))     # byexample: +skip
"i don't know bro"
```

### Verification - when `s == 64` (second try)

The naive approach iterates 64 times, perhaps we could use the
[Kernighan's way](https://graphics.stanford.edu/~seander/bithacks.html#CountBitsSetKernighan).

In C, it goes through as many iterations as `1` bits are in `v`.

```cpp
unsigned int v; // count the number of bits set in v
unsigned int c; // c accumulates the total bits set in v
for (c = 0; v; c++) {
  v &= v - 1; // clear the least significant bit set
}
```

However in Z3 we must go through all the 64 iterations because in the
Kernighan's code, the loops ends when the variable `v` is zero.

In C, you are *evaluating* the code in each instruction; in Z3 you are
*defining* code but **no evaluation is taking place**.

This makes an iteration dependent of the previous one: when *checking*
(evaluation) the model yields `v = 0` for some iteration, *then* the
rest of the iteration should be no-ops.

So we *must* express this in Z3, we must stablish the relation between
one iteration and the next one for all the 64 iterations:

```python
>>> from z3 import BitVecVal
>>> def bit_count(v):
...     c = BitVecVal(0, 64)
...     for i in range(64):
...         # Create a "new generation" expression for 'c'
...         # based if v != 0 or not
...         c = If(v != 0, c + 1, c)
...
...         # Only the last instruction can "update" 'v'
...         v = If(v != 0, v & (v - 1), v)
...
...     return c
```

In the code above I introduced an auxiliary `c` variable. This is
because the C variable `c = 0` will be interpreted by Z3's `If` as a
boolean (`false`) which cannot be promoted later to a `BitVec`.

To enforce the correct type, we use a `BitVecVal` value initialized to
0.

```python
>>> good_cases = And(bit_count(v) == r, (v & 1) == 1)
>>> bad_cases = bit_count(v) < r

>>> solver.check(s == 64, And(Not(good_cases), Not(bad_cases)))     # byexample: +skip
"i don't know bro"
```

Unfortunately, it didn't work either.

### Verification - when `s == 64` (third try - the good one)

In both cases, the naive and the Kernighan's way of counting bits
created 64 restrictions.

In particular they are *nested* or *entangled* restrictions: one
restriction depends on a previous one.

Moreover, we use arithmetic addition (`+`). When we perform a bit
operation like *and* (`&`), each output bit is calculated based on its
two input bits and *independently* from the rest.

But when we add two bit vectors, the *carry bit* is propagated from the
LSB to the MSB making the output bit **dependant** of the input bits on
its right (LSBs).

The arithmetic addition *entangles* the bits.

Long story short: it will be slow.

*The key is to operate in parallel.*

And this
[bithack](https://graphics.stanford.edu/~seander/bithacks.html#CountBitsSetParallel)
suggested by Andrew Shapira, improved later by Charlie Gordon and Don
Clugston, Eric Cole, Al Williams and Sean Eron Anderson will do the
trick.

```python
>>> def bit_count(v):
...     UL3 = 0x5555555555555555
...     UL15 = 0x3333333333333333
...     UL255a = 0xf0f0f0f0f0f0f0f
...     UL255b = 0x101010101010101
...     S = (8 - 1) * 8
...     v = v - ((v >> 1) & UL3)            # temp
...     v = (v & UL15) + ((v >> 2) & UL15)  # temp
...     v = (v + (v >> 4)) & UL255a         # temp
...     c = (v * UL255b) >> S               # count
...     return c

>>> z = bit_count(v)    # compute this once
>>> good_cases = And(z == r, (v & 1) == 1)
>>> bad_cases = z < r

>>> solver.check(s == 64, And(Not(good_cases), Not(bad_cases))) # byexample: +timeout=600
unsat
```

*Victory!*

## The hidden bug

The link in the index to the last bithack is broken.

Not very exciting bug though.

## Final thoughts

Verification is hard.

Thinking in a way to build a set of restrictions and assumptions that
could lead to a contradiction **without** leading to an exponential
search is not trivial.

Working with shifts, masks and binary operations is not a problem but
when we do arithmetics the bits not longer are independent.

Arithmetic operations *entangle* the bits.

`for`-loops are also another way to entangle the bits when the loop
condition depends on the value of a Z3 variable.

`for`-loops like those forces us to model **all** the iterations.

With respect to Z3, `BitVec` works pretty well but it lacks of a way to
*promote* or *upcast* to wider `BitVecs`. This needs to be done by hand.

And don't forget that `BitVec` is a **signed integer** so `<` are signed
by default.
