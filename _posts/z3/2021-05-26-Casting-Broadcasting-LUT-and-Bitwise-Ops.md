---
layout: post
title: "Casting, broadcasting, LUT and bitwise ops"
---

Z3 has a few basic symbolic operation over bit vectors.

But some others are missing (or at least I couldn't find them).

*Cast* bit vectors to change the vector width, like when you want to
*upcast* or *promote* a `uint8_t` to `uint16_t`, is one of them.

Arbitrary *bitwise operations* is another one. Z3 provides the basic
`And`, `Or` and `Xor` but arbitrary functions needs to be defined and
applied by hand.

And about function definitions, Z3 does not have a simple way to *define
a function from a lookup table (LUT) or truth table*.

> *A much tricker that I thought!*

This post is a kind-of sequel of
[Verifying some Bithacks post](/book-of-gehn/articles/2021/05/17/Verifying-Some-Bithacks.html)
and prequel of some future posts.<!--more-->

## Casting

Z3 does not provide a mechanism to change the size of a bit vector (or
at least I didn't find one).

The following is a quite simple `cast` function *ala C* -- however it is
**far** from
[being](https://en.cppreference.com/w/c/language/conversion)
a fully C/C++ compliance
[*cast*](https://en.cppreference.com/w/c/language/cast)
including its UBs.

```python
>>> from z3 import BitVecVal, Concat, Extract, simplify

>>> def cast(bv, type):
...     if type[0] not in ('i', 'u'):
...         raise ValueError(f"Not supported cast type '{type}'")
...
...     signed = type[0] == 'i'
...     new_sz = int(type[1:])
...
...     sz = bv.size()
...     if sz < new_sz:
...         if signed:
...             sign_bit = Extract(sz-1, sz-1, bv)
...             high = Concat(*[sign_bit] * (new_sz - sz))
...         else:
...             # zero extended
...             high = BitVecVal(0, (new_sz - sz))
...
...         return Concat(high, bv)
...
...     else:
...         # downcast
...         return Extract(new_sz-1, 0, bv)
```

Casting to a larger bit vector may be done zero-extended (for unsigned)
or sign-extended (for signed):

```python
>>> i4 = BitVecVal(0b1011, 4)
>>> i4
11

>>> simplify(cast(i4, 'u8'))
11
>>> simplify(cast(i4, 'i8'))
251

>>> bin(251)
'0b11111011'
```

When the target size is smaller, it is a down-cast and the higher bits
are lost:

```python
>>> simplify(cast(i4, 'u2'))
3

>>> simplify(cast(i4, 'i2'))
3
```

Not other casting are implemented:

```python
>>> simplify(cast(i4, 'foo'))
<...>
ValueError: Not supported cast type 'foo'
```

## Broadcasting

For the signed upper-cast, the `cast` function does a *broadcasting*: it
takes the most significant bit, the sign bit, and extends it to fulfill
the wider bit vector.

The sign bit is repeated N times -- it is *broadcasted*:

```python
...    sign_bit = Extract(sz-1, sz-1, bv)
...    high = Concat(*[sign_bit] * (new_sz - sz))
```

## Bitwise operation

Another handy algorithm consists in applying a function bit by bit:

```python
>>> def bitwise(fun, *bvs):
...     if not bvs:
...         raise ValueError("No bit vector was provided")
...
...     sz = bvs[0].size()
...     if any(bv.size() != sz for bv in bvs):
...         raise TypeError(f"Bit vector size mismatch, not all are {sz} bits.")
...
...     index = range(sz-1, -1, -1) # from MSB to LSB
...     applied = [fun(*[Extract(i, i, bv) for bv in bvs]) for i in index]
...     return Concat(*applied)
```

`bitwise` can operate over *symbolic functions*:

```python
>>> from z3 import Function, BitVecSort

>>> BSort = BitVecSort(1)
>>> zor = Function('zor', BSort, BSort, BSort)

>>> simplify(bitwise(zor, BitVecVal(0b1011, 4), BitVecVal(0b0010, 4)))
Concat(zor(1, 0), zor(0, 0), zor(1, 1), zor(1, 0))
```

But it can operate over *concrete (Python) functions*.

## Concrete function definition

If the function is known, we will have to add a constrain per
input/output pair to *constrain* the symbolic function.

Something like:

```python
... solver.add([
...     zor(0, 0) == 1,
...     zor(1, 0) == 1,
...     zor(0, 1) == 0,
...     zor(1, 1) == 1,
... ])
```

But that requires an exponential amount of constrains, $$2^{arity}$$ to
be precise.

A more compact representation would be a *lookup table (LUT)* or *truth
table*.

```
zor LUT:
    0 0 -> 1
    1 0 -> 1
    0 1 -> 0
    1 1 -> 1
```

From there we can build a *product of sums* or a *sums of products*
using a [Karnaugh map](https://en.wikipedia.org/wiki/Karnaugh_map): a
graphical representation of the truth table from where we can derive a
**single** boolean expression made of a minimum amount of `Or` and
`And` instructions that represents it.

Karnaugh maps relays in humans' ability to detect patterns but the
maps gets too complicated for 5 and more inputs so they are not
practical for large functions.

{% marginnote
'However, this problem is NP-complete in general.
' %}

The non-human counterpart is the [Quine-McCluskey algorithm](
https://en.wikipedia.org/wiki/Quine%E2%80%93McCluskey_algorithm)
which can handle much more inputs.


{% marginnote
'Z3 [could do it too](https://github.com/Z3Prover/z3/issues/4822)
but the solution is perhaps more hand-crafted.
' %}

And [SymPy](https://www.sympy.org/en/index.html) has a nice
implementation.

From the LUT we need to specify which combination of inputs yields `True`
and the rest of the combinations will be assumed as `False`.

```
zor LUT:
    0 0 -> 1    -->   0 0
    1 0 -> 1    -->   1 0
    0 1 -> 0    x
    1 1 -> 1    -->   1 1
```

These are called *minterms*:

```python
>>> zor_minterms = [
...     [0, 0],
...     [1, 0],
...     [1, 1]
... ]
```

{% marginnote
'With support for *don&apos;t cares*: combination of inputs for which
don&apos;t care the output.
' %}

SymPy can build a simplified boolean expression in terms of *product of
sums* (`or` subterms joined with `and`s) and *sum of products* (`and`
subterms joined with `or`s)

```python
>>> from sympy.logic import POSform     # byexample: +timeout=10
>>> from sympy import symbols           # byexample: +timeout=10

>>> POSform(symbols('x y'), zor_minterms)
x | ~y
```

There is no elegant way to map SymPy expressions to Z3 expressions
but we can do **a hack** with `eval`:

```python
>>> import sympy
>>> def truth_table_to_fun(minterms, dontcares=None, form='POS', arity=None):
...     assert form in ('POS', 'SOP')
...     arity = arity or len(minterms[0]) # num of args of our function
...
...     # create on the fly a SymPy variable per argument
...     varnames = ['A%i' % i for i in range(arity)]
...     s = sympy.symbols(' '.join(varnames))
...
...     # simplify as a Product of Sums or as a Sum of Products and get
...     # an expression as a string
...     fun = (sympy.POSform if form == 'POS' else sympy.SOPform)
...     expr = str(fun(s, minterms, dontcares))
...
...     # make the SymPy expression suitable as a Python function definition
...     expr = f'lambda {",".join(varnames)}: ({expr})'
...     # evaluate the expression and return the Python function
...     return eval(expr, None, {})
```

With `truth_table_to_fun` we can build a *Python function* that it will
take *Z3 bit vectors* and it will return a *bit vector expression* that
encodes the *minterms* specified.

```python
>>> from z3 import BitVecs
>>> zor = truth_table_to_fun(zor_minterms)

>>> A, B = BitVecs('A B', 1)
>>> zor(A, B)
A | ~B

>>> expr = simplify(bitwise(zor, BitVecVal(0b1001, 4), BitVecVal(0b0010, 4)))
>>> bin(expr.as_long())
'0b1101'
```

> *Quick and dirty. Don't blame me.*

## Further things

Quite a lot.

Some
[bithacks](https://graphics.stanford.edu/~seander/bithacks.html) could
be used to simplify Z3 expressions and speedup the model solving.

When [verifying the rank
bit](/book-of-gehn/articles/2021/05/17/Verifying-Some-Bithacks.html) I
tested different approaches and only the *branchless* implementation
gave me a result in a reasonable time.

Testing the performance is something to explore. Soon.
