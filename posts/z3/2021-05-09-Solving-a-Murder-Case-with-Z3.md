---
layout: post
title: "Solving a Murder Case with Z3"
latex_macros: "R: '{\\\\tiny{\\\\_}}', s: '{_}'"
tags: [z3, smt, sat, solver, propositional logic, first order]
inline_default_language: python
---


Victor has been murdered!

There are strong evidences that point that Victor was murdered by
a single person. The investigation led to three suspects:
Art, Bob, and Carl.

But who is the murder?<!--more-->

{% call marginnotes() %}
I took this logic puzzle from a Stanford University course:
[Introduction to Logic](http://intrologic.stanford.edu/extras/whodunnit.html)
 {% endcall %}

Art says he did not do it. He says that Bob was the victim's friend but
that Carl hated the victim.

Bob says he was out of town the day of the murder, and besides he didn't
even know the guy.

Carl says he is innocent and he saw Art and Bob with the victim just
before the murder.


## Propositional logic

The proposition "Bob says he was out of town the day of the murder"
cannot be tested by pure logic.

It is a statement that is not related with any other statement said
including his own so it will not be in contradiction.

Unless we have a camera capturing Bob near the crime scene the day
of the murder with a validated date and time, we cannot contradict his
claim.

The propositions "Art says he did not do it" and "Carl says he is innocent"
have the same level of useless.

```tex;mathjax

\begin{aligned}
Art \R claims &= Bob \R friend \R of \R Victor ∧ ¬Carl \R friend \R of \R Victor  \\
Bob \R claims &= ¬Bob \R knows \R Victor                          \\
Carl \R claims &= Art \R saw \R with \R Victor ∧ Bob \R saw \R with \R Victor
\end{aligned}

```

The propositions of above seems to be disconnected. This is a limitation
of the *propositional logic*: we cannot connect "Bob was the victim's
friend" with "[Bob] didn't even know the guy".

Those are two separated propositions.

To connect them we need to use a *first order logic* or *predicated
logic*.

## First order logic

A first order logic has more expressive power to capture more subtle
connections.

We know that if a person `s`{.mathjax} is a friend of `v`{.mathjax},
then `s`{.mathjax} must know `v`{.mathjax} -- or at
least is a reasonable assumption of how human friendship works.

Then we can have the following two *predicates* (think in them as
functions or parametric propositions).

```tex;mathjax

is \R friend(s, v)     \\
knows(s, v)

```

These predicates are not true or false: only when we *fix* their inputs
we can ask about their truthfulness.

{% call marginnotes() %}
Formally I should add that `s`{.mathjax} belongs to the *domain* of
suspects `\{Art, Bob, Carl\}`{.mathjax} and `v`{.mathjax} belongs to the *domain*
of victims `\{Victor\}`{.mathjax}.

Without a domain, `s`{.mathjax} and `v`{.mathjax} are just letters and the proposition
makes no sense.
 {% endcall %}

However we can build propositions that are true or false on top
of that:

```tex;mathjax

∀ s, ∀ v \; is \R friend(s, v) ⟹  knows(s, v)

```


And that proposition is true for all the suspects and victims possible.

In particular, the following is also true:

```tex;mathjax

is \R friend(Bob, Victor) ⟹  knows(Bob, Victor)

```

That's the link, the connection between "Bob was the victim's
friend" with "[Bob] didn't even know the guy".

It is a mathematical way to say: "if Bob was the victim's friend, then
he knew the guy; if he didn't know the guy he could not be his friend".

The claim "[Carl] saw Art [...] with the victim just before the murder"
is tricky.

A person `s`{.mathjax} can be in a public place with `v`{.mathjax} and that does not implies
anything. Even if they are in the same room, `s`{.mathjax} may forget about
`v`{.mathjax} 5 minutes later.

For the sake of simplicity we will say that the following is true:

```tex;mathjax

∀ s, ∀ v \; be \R with(s, v) ⟹  knows(s, v)

```

Using the predicates we can rewrite the suspects' claims as follows:

```tex;mathjax

\begin{aligned}
Art \R claims &= is \R friend(Bob, Victor) ∧ ¬is \R friend(Carl, Victor)  \\
Bob \R claims &= ¬knows(Bob, Victor)                                \\
Carl \R claims &= be \R with(Art, Victor) ∧ be \R with(Bob, Victor)
\end{aligned}

```

## Z3

```python
>>> from z3 import (DeclareSort, Function, BoolSort, Bools, And, Not,
...                 Implies, ForAll, Solver, Consts, AtLeast)

>>> Suspects = DeclareSort('Suspects')
>>> Art, Bob, Carl, s = Consts("Art Bob Carl s", Suspects)

>>> Victims = DeclareSort('Victims')
>>> Victor, v = Consts("Victor v", Victims)
```

Notice how we explicitly declare the *domains* or *sorts* over we will
be operating: the domain of suspects and the domain of victims.

"Bob is a sort of Suspects; Victor is a sort of Victims". Weird.

The sort is used to define the *predicates* --aka functions:

```python
>>> is_friend = Function('is_friend', Suspects, Victims, BoolSort())
>>> knows = Function('knows', Suspects, Victims, BoolSort())
>>> be_with = Function('be_with', Suspects, Victims, BoolSort())
```

All those three functions receives a suspect and a victim as inputs and
return an element of sort boolean: true or false.

Note how those functions are either true or false, they are just
functions.

In contrast the following relationships are true and they are our first
two restrictions set:

```python
>>> solver = Solver()
>>> solver.add(
...     ForAll([s, v], Implies(is_friend(s, v), knows(s, v))),
...     ForAll([s, v], Implies(be_with(s, v), knows(s, v)))
... )

>>> solver.push()
```

And now the suspects' claims:

```python
>>> art_claims = And(is_friend(Bob, Victor), Not(is_friend(Carl, Victor)))
>>> bob_claims = Not(knows(Bob, Victor))
>>> carl_claims = And(be_with(Art, Victor), be_with(Bob, Victor))

>>> solver.assert_and_track(art_claims, 'art_claims')
>>> solver.assert_and_track(bob_claims, 'bob_claims')
>>> solver.assert_and_track(carl_claims, 'carl_claims')
```

Finally, we check if the claims are *consistent between* or if there are
any *contradiction*.

```python
>>> solver.check()
unsat
```

Nop! Someone is lying!

## Finding the murder

```python
>>> solver.unsat_core()
[art_claims, bob_claims]
```

Z3 can calculate the *unsat core* which it is a subset of the *tracked*
restrictions that lead to *unsatisfiable* result.

So Art's or Bob's claims is/are producing contradictions.

{% call marginnotes() %}
Z3 does not produce the *minimum unsat core* by default. We could force
it to have exactly which claim is false but in my setup I could not make
it work.

So we will have to do it by hand.
 {% endcall %}

By assumption, only one of the suspects is lying, the rest are telling
us the truth. But who is lying?

We restore the solver before anding the claims and this time we will require
not all but at least 2 claims to be true.
By assumption the third claim will be false.

```python
>>> solver.pop()
>>> solver.push()

>>> solver.add(AtLeast(art_claims, bob_claims, carl_claims, 2))
>>> solver.check()
sat
```

Now, what suspect is lying?

```python
>>> m = solver.model()
>>> m.eval(art_claims)
True
>>> m.eval(bob_claims)
False
>>> m.eval(carl_claims)
True
```

So Bob is lying!

To rule out any other possible solution we will roll back the solver
again and in this time we use the claims as *assumptions*.

For the `check()` method an assumption is a restriction like any other but
it is not added to the solver (like when you call `add()`).

This is handy way to test different claims combinations without rolling
back the entire solver over and over.

```python
>>> solver.pop()
>>> solver.push()

>>> solver.check(art_claims, bob_claims)
unsat
>>> solver.check(bob_claims, carl_claims)
unsat
>>> solver.check(art_claims, carl_claims)
sat
```

Indeed, only when Bob's claims are **not** considered we see a
consistent scenario.

Bob was the killer.




