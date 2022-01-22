---
layout: post
title: "Congruence Closure with Z3"
tags: [z3m smt, sat, solver, equivalence, congruence, equivalence, set]
inline_default_language: python
---

Assume that you know that `a = b`{.mathjax}, `b = c`{.mathjax} and `d = e`{.mathjax}. What can you
tell me about the claim `a = c`{.mathjax} ? Is it true or false?<!--more-->

## Equivalence class

The `=`{.mathjax} denotes an *equivalence* between two elements: `a = b`{.mathjax} means
that `a`{.mathjax} is equivalent to `b`{.mathjax} (not necessary that they are *the same*
element or *equals* however).

So, because we know `a = b`{.mathjax} and `b = c`{.mathjax} we conclude
that `a = c`{.mathjax} and
therefore the claim is true.

You see, in general `a = X`{.mathjax} is true iff `X`{.mathjax} is
`a`{.mathjax}, `b`{.mathjax}, or `c`{.mathjax}.

`a`{.mathjax}, `b`{.mathjax} y `c`{.mathjax} are equivalent between themselves:
they form an *equivalence class*.

The initial set `T: \{a, b, c, d, e\}`{.mathjax} has two equivalence classes:
`C_1: \{a, b, c\}`{.mathjax} and `C_2: \{d, e\}`{.mathjax}

## Set operations

We say that the set `E`{.mathjax} of equivalence *rules* induced a *partition*
over `T`{.mathjax} yielding, in this case, the two equivalence classes of above.

And the point of all of this is...?

Pick any claim `X = Y`{.mathjax}, it will be true if and only if both elements
are part of the same equivalence class.

And checking *membership* can be implemented easily and efficiently. No
matter how many elements `T`{.mathjax} has, once you built the equivalence
classes (sets), checking a claim `X = Y`{.mathjax} requires two membership
tests.

Moreover, seen `C_1`{.mathjax} and `C_2`{.mathjax} as sets, adding a new equivalence rule the
has elements of both sets like `c = d`{.mathjax} *merges*
`C_1`{.mathjax} and `C_2`{.mathjax} into a
single set: `C`{.mathjax} is the *union* of `C_1`{.mathjax} and
`C_2`{.mathjax}.

## Congruence rule

Let's ask ourselves if the claim `f(a) = f(c)`{.mathjax} is true or not where
`f`{.mathjax} is an arbitrary function.

There is *rule* that says if `X`{.mathjax} and `Y`{.mathjax} belongs to the same equivalence
class then `f(X)`{.mathjax} and `f(Y)`{.mathjax} must both belong to the same equivalence class
(but not necessary to the same class of `X`{.mathjax} and `Y`{.mathjax}).

Intuitively, if `X = Y`{.mathjax} then `f(X)`{.mathjax} can be replaced by
`f(Y)`{.mathjax}.

In general, if `X_1, Y_1 \in C_1`{.mathjax},  `X_2, Y_2 \in C_2`{.mathjax}, and so on up
to  `X_n, Y_n \in C_n`{.mathjax}, then `f(X_1, X_2, ..., X_n)`{.mathjax} **must** be
equivalent to `f(Y_1, Y_2, ..., Y_n)`{.mathjax}.

The equivalence class and the congruence rule form a *congruence
closure*.


## Playing with Z3

```python
>>> from z3 import DeclareSort, Function, Consts, solve

>>> T = DeclareSort('T')
>>> a, b, c, d, e = Consts('a b c d e', T)

>>> f = Function('f', T, T)
>>> g = Function('g', T, T, T)

>>> E = [a == b, b == c, d == e]

>>> solve(E + [a != c])  # a != c is a contradiction of a == c
no solution

>>> solve(E + [a != d])  # they are in different equivalence classes, so ok
[c = T!val!0,
 e = T!val!1,
 d = T!val!1,
 a = T!val!0,
 b = T!val!0]

>>> solve(E + [f(a) != f(c)]) # another contradiction
no solution

>>> solve(E + [g(a, f(d)) != g(c, f(e))]) # more interesting example...
no solution

>>> # And if we force that the last equivalence, we will get a single
>>> # equivalence class with the elements valued to 'T!val!0'
>>> solve(E + [g(a, f(d)) == g(c, f(e))])
[e = T!val!0,
 d = T!val!0,
 c = T!val!0,
 a = T!val!0,
 b = T!val!0]
```
