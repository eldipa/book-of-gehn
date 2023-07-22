---
layout: post
title: "Blending Whisky with Z3"
tags: [z3, smt, sat, solver, linear optimization, blending]
inline_default_language: python
---

A whisky producer uses three kind of licor to make their whisky:
`A`{.mathjax},
`B`{.mathjax} and `C`{.mathjax}.

Three kind of whisky can be made using the licor
in the following proportions:

  Whisky | Sales Price | Recipe
 :-----: | :---------: | :---------
  `]E`   | `]680`      | No less than 60% of `]A`, no more than 20% of `]C`
  `]F`   | `]570`      | No less than 15% of `]A`, no more than 80% of `]C`
  `]G`   | `]450`      | No more than 50% of `]C`

The producer has the following stock and price list from its licor supplier:

  Licor | Stock    | Price
 :----: | :------: | :------:
  `]A`  | `]2000`  | `]700`
  `]B`  | `]2500`  | `]500`
  `]C`  | `]1200`  | `]400`

Note: the prices are in $ per liter and the stock are in liters.

The goal is to maximize the profit.<!--more-->

## Bad plan: non-linear system

Let's begin with the bounds of each licor:

```tex;mathjax

A_E  E + A_F  F + A_G  G = A <= 2000 \\
B_E  E + B_F  F + B_G  G = B <= 2500 \\
C_E  E + C_F  F + C_G  G = C <= 1200 \\

```

We introduced a new variable per combination of licor and whisky:
`A_E`{.mathjax}
stands for the ratio of licor `A`{.mathjax} used in the whisky `B`,
`B_F`{.mathjax} stands for the ratio of licor `B`{.mathjax} used in the whisky `F`{.mathjax} and so on.

These variables are in liters of licor per liter of whisky (or they are
unit-less if you prefer).

And we are fuck.

These three equations are not longer linear because we have the product
of two variable (`A_E  E`{.mathjax} for example).

We need to rethink our strategy.

## The blending

Think in `A_E`{.mathjax} *not as the ratio but as the amount of
liters itself* of licor `A`{.mathjax} used in `E`{.mathjax}.

This is a *blending* problem where some variables represent a part,
fraction or subcomponent of another.

```tex;mathjax

A_E + A_F + A_G = A <= 2000 \\
B_E + B_F + B_G = B <= 2500 \\
C_E + C_F + C_G = C <= 1200 \\

```

Now the system is linear again.

What about the restrictions of each recipe?

It would be wonderful to put something like this
that it is a literal translation of the problem into inequalities:

```tex;mathjax

0.6 <= A_E/E <= 1 \\
0 <= C_E/E <= 0.2 \\
--- \\
0.15 <= A_F/F <= 1 \\
0 <= C_F/F <= 0.8 \\
--- \\
0 <= C_G/G <= 0.5 \\

```

But again, that makes the system non-linear.

Instead we do the following:

```tex;mathjax

0.6  E <= A_E <= 1  E \\
0  E <= C_E <= 0.2  E \\
--- \\
0.15  F <= A_F <= 1  F \\
0  F <= C_F <= 0.8  F \\
--- \\
0  G <= C_G <= 0.5  G \\

```


We complete the recipe of each whisky with the remaining licor:

```tex;mathjax

A_E + B_E + C_E = E \\
A_F + B_F + C_F = F \\
A_G + B_G + C_G = G \\

```

So what did we do? We split each licor (input `I`{.mathjax}) into `N`{.mathjax} *blending*
variables (`I_o`{.mathjax}), one for each whisky type (output `O`{.mathjax}).

 - We ensured that the sum of the *blending* variables for the **same** licor
(input) summed up the total amount of **that** licor (`A_E + A_F + A_G = A`{.mathjax}) --
we did a *partition*.
 - We restricted each blending variable based on a proportion of each
amount of whisky (`0.6  E <= A_E <= 1  E`{.mathjax}) -- these are the *blending
rules*.
 - We ensured that the sum of the *blending* variable **across** all the
licor (input) for the **same** whisky (output) summed up the total amount of
**that** whisky.

   |          |         |         |
:-:| :------: | :-----: | :-----: | :-----:
   |  `]A_E`  | `]A_F`  | `]A_G`  |  →  `]A`
   |  `]B_E`  | `]B_F`  | `]B_G`  |  →  `]B`
   |  `]C_E`  | `]C_F`  | `]C_G`  |  →  `]C`
   |  ↓       | ↓       | ↓       |
   |  `]E`    | `]F`    | `]G`    |

## The goal

And finally, this is the goal to maximize:

```tex;mathjax

Z = max\{680 E + 570 F + 450 G - 700 A - 500 B - 400 C \}

```


## Find the optimum with Z3

Setup the engine, create the variables and ensure that them are
non-negative.

```python
>>> from z3 import Reals, Optimize
>>> s = Optimize()

>>> A, B, C, E, F, G = Reals('A B C E F G')
>>> A_E, A_F, A_G = Reals('A_E A_F A_G')
>>> B_E, B_F, B_G = Reals('B_E B_F B_G')
>>> C_E, C_F, C_G = Reals('C_E C_F C_G')

>>> s.add(*[x >= 0 for x in [A, B, C, E, F, G]])
>>> s.add(*[x >= 0 for x in [A_E, A_F, A_G]])
>>> s.add(*[x >= 0 for x in [B_E, B_F, B_G]])
>>> s.add(*[x >= 0 for x in [C_E, C_F, C_G]])
```

Limit the amount of supplies

```python
>>> s.add(
...     A <= 2000,
...     B <= 2500,
...     C <= 1200
... )
```

Split the licor for each whisky

```python
>>> s.add(
...     A_E + A_F + A_G == A,
...     B_E + B_F + B_G == B,
...     C_E + C_F + C_G == C
... )
```

Blending rules:

```python
>>> s.add(
...     # minimum amount of licor for whisky E
...     0.6 * E <= A_E,
...     0 <= C_E,
...     # maximum amount of licor for whisky E
...     A_E <= E,
...     C_E <= 0.2 * E,
...
...     # minimum amount of licor for whisky F
...     0.15 * F <= A_F,
...     0 <= C_F,
...     # maximum amount of licor for whisky F
...     A_F <= F,
...     C_F <= 0.8 * F,
...
...     # the same for whisky G
...     0 <= C_G,
...     C_G <= 0.5 * G
... )

>>> s.add(
...     A_E + B_E + C_E == E,
...     A_F + B_F + C_F == F,
...     A_G + B_G + C_G == G
... )
```

Profit!

```python
>>> costs = A * 700 + B * 500 + C * 400
>>> income = E * 680 + F * 570 + G * 450
>>> profit = s.maximize(income - costs)

>>> s.check()
sat

>>> profit.value()
3590000/9

>>> m = s.model()
>>> print("Licor:", "A =", m[A], "B =", m[B], "C =", m[C])
Licor: A = 2000 B = 2500 C = 1200

>>> # We use m[.] to retrieve simple variables
>>> print("Whisky:", "E =", m[E], "F =", m[F], "G =", m[G])
Whisky: E = 22900/9 F = 28400/9 G = 0

>>> # We use m.eval() to evaluate complex expressions in the model context
>>> print("Costs =", m.eval(costs), "Income =", m.eval(income), "Profit =", profit.value())
Costs = 3130000 Income = 31760000/9 Profit = 3590000/9
```
