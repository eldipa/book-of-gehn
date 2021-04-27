---
layout: post
title: "Optimum Packaging of Chocolate"
---

A small business sells two types of chocolate packs: A and B.

The pack A has 300 grams of bittersweet chocolate, 500 grams of
chocolate with walnuts and 200 grams of white chocolate.

The pack B has 400 grams of bittersweet chocolate, 200 grams of
chocolate with walnuts and 400 grams of white chocolate.

The pack A has a price of 120$ while the pack B has a price of 90$.

Let's assume that this small business has for today 100 kilograms of
bittersweet chocolate, 120 kilograms of chocolate with walnuts and 100
kilograms of while chocolate.

How many packs of A and B type should be packed to maximize the profits?
<!--more-->

## Of variables and restrictions

First, we set up a solver that not only will say if a set of
restrictions are
satisfiable or not but it will also give us an instance (model) that
*maximizes* a given *objective function*.

```python
>>> from z3 import Reals, Optimize
>>> s = Optimize()
```

Let start defining be the following variables that represent how many packs
of each type we need to make:

```python
>>> a_cnt, b_cnt = Reals('a_cnt b_cnt')
```

Then, we have the variables that represent how much chocolate we *use* of
each flavor:

```python
>>> bittersweet, with_walnuts, white = Reals('bittersweet with_walnuts white')
```

So now we can relate the amount of A and B packs with the amount of
chocolate of each flavor:

```python
>>> s.add(
...     300 * a_cnt + 400 * b_cnt == bittersweet,
...     500 * a_cnt + 200 * b_cnt == with_walnuts,
...     200 * a_cnt + 400 * b_cnt == white
... )
```

But the amount of chocolate is limited:

```python
>>> s.add(
...     bittersweet <= 100*1000,
...     with_walnuts <= 120*1000,
...     white <= 100*1000
... )
```

And technically, the amount of packs has also a lower bound

```python
>>> s.add(
...     a_cnt >= 0,
...     b_cnt >= 0,
...     bittersweet >= 0,
...     with_walnuts >= 0,
...     white >= 0
... )
```

{% marginnote
'In Python `a <= b <= c` is a valid expression but in Z3 it is not
and you need to define two separated statements `a <= b` and `b <= c`.
' %}

## The objective

And finally, this is the *linear* function that we want to maximize:

```python
>>> objective = s.maximize(120 * a_cnt + 90 * b_cnt)
>>> s.check()
sat

>>> objective.value()
33000
```

So the optimal income will be 33000$ and the amount of packs and
chocolate is:

```python
>>> s.model()
[b_cnt = 100,
 a_cnt = 200,
 white = 80000,
 with_walnuts = 120000,
 bittersweet = 100000]
```

As expected the optimal solution is when we use most of the chocolate.

### Slack

The only one that had some *slack* was white chocolate. Having a limit
of 100 kilograms, the optimal solution required 80 kilograms with 20
kilograms without use.

We can let Z3 to calculate that for use redefining the inequalities by
introducing *slack variables* and making them equalities:

```python
>>> bittersweet_slack, with_walnuts_slack, white_slack = Reals('bittersweet_slack with_walnuts_slack white_slack')
>>> s.add(
...     bittersweet_slack >= 0,
...     with_walnuts_slack >= 0,
...     white_slack >= 0,
...     bittersweet + bittersweet_slack == 100*1000,
...     with_walnuts + with_walnuts_slack == 120*1000,
...     white + white_slack == 100*1000
... )

>>> s.check()
sat

>>> s.model()
[b_cnt = 100,
 a_cnt = 200,
 white_slack = 20000,
 with_walnuts_slack = 0,
 bittersweet_slack = 0,
 white = 80000,
 with_walnuts = 120000,
 bittersweet = 100000]
```

## Assumptions

{% marginnote
'Precise values; linear, proportional and additivity relations; and
variables in $$\mathbb{R}$$
' %}

When we say "the pack A has 300 grams of bittersweet chocolate" we are
incurring in a huge assumption: that the number 300 is a real and
*precise* thing.

In the real world is hard or even impossible to operate with precise
quantities. Think that the manufacturing process has some
inefficiencies, the balance/scale used to measure has not infinite
precision and things like that.

We also said without much thinking that inputs and
outputs are *proportional*: if the outcome of selling 1 pack A is 120$,
selling 10 packs we should earn 1200$.

We said that we wanted to maximize `120 * a_cnt + 90 * b_cnt`. Under the
hood we are also making the assumption that we can *sell* packs A and
packs B independently and then *add them* together.

This and the *proportional* assumptions are required for **linear**
programming.

A cleaver reader may noticed that I used Z3's `Reals` for creating the
variables `a_cnt` and `b_cnt`. It is obviously wrong because the amount
of packs is an **integer** and not a real number.

We've got an integer solution of `a_cnt = 200` and `b_cnt = 100` but
this was pure luck.

But the same objection can be done for the amount of chocolate: absurd
tiny amounts like 0.0001 grams of chocolate makes no sense.

We assumed that all the variables here have the *divisibility* property:
they can be modeled as real numbers -- that's why call it **real** linear
programming in opposition to the **integer** linear programming.

The former can be solved in polinomial time (Z3 uses the [Simplex
algorithm](https://en.wikipedia.org/wiki/Simplex_algorithm)) while the
latter is NP-complete.

