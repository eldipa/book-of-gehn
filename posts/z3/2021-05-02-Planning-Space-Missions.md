---
layout: post
title: "Planning Space Missions with Z3"
tags: [z3, smt, sat, solver, integer linear optimization]
inline_default_language: python
---

A space company is planning the next 4 years. It has several projects,
each one with its own budget requirement per year, but the company has a
limited budget to invest.

Moreover, some projects *depends* on others to make them feasible and
some projects *cannot be done* if other projects due unbreakable restrictions.

 Project           | 1st | 2nd | 3rd | 4th | Depends  | Not    | Profit
 :---------------- | :-: | :-: | :-: | :-: | :------- | :----- | :-----:
 1 Cube-1 nano-sat | 1.1 | 2   |     |     |          |        | 12
 2 Cube-2 nano-sat |     | 2.5 | 2   |     |          |        | 12
 3 Infrared sat    |     |     | 1   | 4.1 | on 6     | with 4 | 18
 4 Colored img sat |     |     | 2   | 8   |          | with 3 | 15
 5 Mars probe      |     | 2   | 8   | 4.4 | on 1 & 2 |        | 12
 6 Microwave tech  | 4   | 2.3 | 2   |     |          |        | 1

Under an incredible amount of assumptions and good luck, what is the
best strategy to maximize the profit?<!--more-->

We can model if one project is make or not with a *boolean variable*
`P_i`{.mathjax}; we not longer are in the plane of *pure real linear
programming*.

The relation between the profit and them is simply:

```tex;mathjax

Z = max\{12 P_1 + 12 P_2 + 18 P_3 + 15 P_4 + 12 P_5 + 1 P_6 \}

```

But we have restriction on the budget per year. Let's say 6 and let's
assume that the unspent budget of one year `B_j`{.mathjax} can be used the next one
(and let's assume that the unspent budget is not part of the profit).

```tex;mathjax

1.1 P_1 + 4   P_6 +     B_1                         = 6         \\
2   P_1 + 2.5 P_2 + 2   P_5 + 2.3 P_6 +   B_2       = 6 + B_1   \\
2   P_2 + 1   P_3 + 2   P_4 + 8   P_5 + 2 P_6 + B_3 = 6 + B_2   \\
4.1 P_3 + 8   P_4 + 4.4 P_5 +     B_4               = 6 + B_3

```

This is *mixed linear programming*: mixing integers (booleans) and real
arithmetics.

The interesting part is how to model the restrictions between the
projects using only integers/booleans.

## Boolean theory as integer linear inequalities

The company could choose to do project 3 or project 4 but not both.

Becase all the variables `P_i`{.mathjax} can be 0 or 1, this is modeled as:

```tex;mathjax

P_3 + P_4 <= 1

```

In general, *zero or one* restriction among `X_i`{.mathjax} is modeled as

```tex;mathjax

\sum_{\forall i} X_i <= 1

```

We can tweak this to make an *one and only one* restriction
(`\sum_{\forall i} X_i = 1`{.mathjax}), a *at least N* restriction
(`\sum_{\forall i} X_i >= N`{.mathjax}),
a *no more than N* restriction (`\sum_{\forall i} X_i <= N`{.mathjax}) and more.

In particular, the *at least 1* is equivalent to do the boolean *or*
operation: ` X_1 ∨ X_2 ∨ \dots ∨ X_n = Y `{.mathjax}


What about the dependency restrictions? Project 3 depends on 6 and
project 5 depends on 1 and 2.

```tex;mathjax

P_3 <= P_6          \\
2 P_5 <= P_1 + P_2  \\

```

In general, a boolean variable `Y`{.mathjax} depends on `N`{.mathjax} boolean variables
`X_i`{.mathjax}, then

```tex;mathjax

N Y <= \sum_{\forall i} X_i

```

As before, we can tweak this to make a *depends on at least M*
restriction (`M Y <= \sum_{\forall i} X_i`{.mathjax} with `M < N`{.mathjax}).

A `Y`{.mathjax} depends on `X_i`{.mathjax} is weaker than `X_i ⟹  Y`{.mathjax} (in the
former case, `Y`{.mathjax} may be false even of all the dependencies are
satisfied).

An implication can be modeled as:

```tex;mathjax

N Y <= \sum_{\forall i} X_i <= (N-1) + Y

```

This last one can be seen as if **all** the dependencies are set,
`Y`{.mathjax}
is set. In boolean terminology, this is an *and*:
` X_1 ∧ X_2 ∧ \dots ∧ X_n = Y `{.mathjax}


## Z3 time!

```python
>>> from z3 import Bools, Reals, Optimize
>>> s = Optimize()

>>> P = Bools('P0 P1 P2 P3 P4 P5 P6') # P[0] will not be used
>>> B = Reals('B0 B1 B2 B3 B4') # B[0] will not be used

>>> profit = s.maximize(12 * P[1] + 12 * P[2] + 18 * P[3] + 15 * P[4] + 12 * P[5] + 1 * P[6])
```

Variables `P[0]` and `B[0]` are not used, they were created just to make
the `P[i]` notation to match with the inequalities of above.

However, I'm not going to let Z3 pick random values for them so I'm
going to pin them:

```python
>>> s.add(
...     P[0] == False,
...     B[0] == 0
... )
```

The following is a 1-to-1 translation of the inequalities for the budget
restrictions:

```python
>>> s.add(
...     1.1 * P[1] + 4   * P[6] +       B[1] == 6,
...     2   * P[1] + 2.5 * P[2] + 2   * P[5] + 2.3 * P[6] +     B[2] == 6 + B[1],
...     2   * P[2] + 1   * P[3] + 2   * P[4] + 8   * P[5] + 2 * P[6] + B[3] == 6 + B[2],
...     4.1 * P[3] + 8   * P[4] + 4.4 * P[5] +       B[4] == 6 + B[3]
... )
```

Now, I want to set the dependency and conflict restrictions in two
different ways: using inequalities as described above and using Z3 high
level abstraction to work with `Bools` and its support for *boolean
theories*.

Because of this I'm going to preserve a copy of the current
object `s` to restore it later.

```python
>>> s.push()
```

> Note: technically `push()` and `pop()` also change what solver can be
> used; a safer alternative could be use `Optimize`'s deep copy.
> However, currently in Z3 version `4.8.10` it is not supported (a bug
> perhaps?)

## Integer linear programming

```python
>>> from z3 import IntSort

>>> to_int = lambda b: IntSort().cast(b)
>>> s.add(
...     # conflict rule: or P3 or P4 but not both
...     to_int(P[3]) + to_int(P[4]) <= 1,
...     # dependency rule: P3 depends on P6
...     to_int(P[3]) <= to_int(P[6]),
...     # dependency rule: P5 depends on P1 and P2
...     2 * P[5] <= to_int(P[1]) + to_int(P[2])
... )
```

As you see, `Bools` cannot be added up or compared by inequality
directly (how would you interpret `True + True`?). Instead we *cast them*
to integers.

In the other inequalities we didn't have to because things like
`2 * P[5]` already makes an integer expression; multiplying by 0 or 1
does not work however.

> Note: currently in Z3 version `4.8.10` has a `ToInt` function but it
> does not work with `Bools` (`BoolRef` objects).

```python
>>> s.check()
sat

>>> profit.value()
55

>>> m = s.model()
>>> print("Projects:\n", *[f"- {P[i]} = {m[P[i]]}\n" for i in range(1, 7)])
Projects:
 - P1 = True
 - P2 = True
 - P3 = True
 - P4 = False
 - P5 = True
 - P6 = True
```

Now let's see how we can rewrite the inequalities for dependency and
conflict restrictions.

## Boolean theory

First we restore the solver to the point before adding those
inequalities:

```python
>>> s.pop()
```

Now we use *boolean expressions* that may make more sense:

```python
>>> from z3 import And, If
>>> s.add(
...     # conflict rule: P3 and P4 cannot happen
...     And(P[3], P[4]) == False,
...     # If the dependency P6 is not met, P3 must be False,
...     # otherwise whatever P3 is fine
...     If(P[6] == False, P[3] == False, P[3]),
...     # If the dependencies P1 and P2 are not met, P5 must be False,
...     # otherwise whatever P5 is fine
...     If(And(P[1], P[2]) == False, P[5] == False, P[5])
... )

>>> s.check()
sat

>>> profit.value()
55
>>> m = s.model()
>>> print("Projects:\n", *[f"- {P[i]} = {m[P[i]]}\n" for i in range(1, 7)])
Projects:
 - P1 = True
 - P2 = True
 - P3 = True
 - P4 = False
 - P5 = True
 - P6 = True
```

Z3 has a bunch of boolean expressions/functions that can replace the
traditional inequalities: `If`, `AtMost`, `AtLeast`, `Implies`, `And`,
`Or` and `Not`.


