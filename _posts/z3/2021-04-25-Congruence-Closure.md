---
layout: post
title: "Congruence Closure with Z3"
---

Assume that you know that $$a = b$$, $$b = c$$ and $$d = e$$. What can you
tell me about the claim $$a = c$$ ? Is it true or false?<!--more-->

## Equivalence class

The $$=$$ denotes an *equivalence* between two elements: $$a = b$$ means
that $$a$$ is equivalent to $$b$$ (not necessary that they are *the same*
element or *equals* however).

So, because we know $$a = b$$ and $$b = c$$ we conclude that $$a = c$$ and
therefore the claim is true.

You see, in general $$a = X$$ is true iff $$X$$ is $$a$$, $$b$$, or
$$c$$.

$$a$$, $$b$$ y $$c$$ are equivalent between themselves:
they form an *equivalence class*.

The initial set $$T: \{a, b, c, d, e\}$$ has two equivalence classes:
$$C_1: \{a, b, c\}$$ and $$C_2: \{d, e\}$$

## Set operations

We say that the set $$E$$ of equivalence *rules* induced a *partition*
over $$T$$ yielding, in this case, the two equivalence classes of above.

And the point of all of this is...?

Pick any claim $$X = Y$$, it will be true if and only if both elements
are part of the same equivalence class.

And checking *membership* can be implemented easily and efficiently. No
matter how many elements $$T$$ has, once you built the equivalence
classes (sets), checking a claim $$X = Y$$ requires two membership
tests.

Moreover, seen $$C_1$$ and $$C_2$$ as sets, adding a new equivalence rule the
has elements of both sets like $$c = d$$ *merges* $$C_1$$ and $$C_2$$ into a
single set: $$C$$ is the *union* of $$C_1$$ and $$C_2$$.

## Congruence rule

Let's ask ourselves if the claim $$f(a) = f(c)$$ is true or not where
$$f$$ is an arbitrary function.

There is *rule* that says if $$X$$ and $$Y$$ belongs to the same equivalence
class then $$f(X)$$ and $$f(Y)$$ must both belong to the same equivalence class
(but not necessary to the same class of $$X$$ and $$Y$$).

Intuitively, if $$X = Y$$ then $$f(X)$$ can be replaced by $$f(Y)$$.

In general, if $$X_1, Y_1 \in C_1$$,  $$X_2, Y_2 \in C_2$$, and so on up
to  $$X_n, Y_n \in C_n$$, then $$f(X_1, X_2, ..., X_n)$$ **must** be
equivalent to $$f(Y_1, Y_2, ..., Y_n)$$.

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
