---
layout: post
title: "From a Regex to a Nondeterministic Finite Automata"
tags: [regex, automata, state machine, NFA, string]
artifacts:
 - label.svg
 - epsilon.svg
 - sm_optional.svg
 - optional.svg
 - concat.svg
 - repeated.svg
 - klee.svg
 - range.svg
 - union.svg
---

Before building complex state machine we need to learn the basics blocks.

When the solution to a problem can be seen as set of states with
transitions from ones to others, modeling them as a nondeterministic
finite automatas makes clear how the solution works and allows to spot
deficiencies.

A regular expression is an example of this. As an introductory step
let's review how to turn a regex into a NFA.

Take at look of the [source code in Github](https://github.com/eldipa/nfa).
<!--more-->

## From a regular expression to a NFA

Before getting deep in this, let's define a very simple problem: we
want to validate if a particular string follows or not a given structure.

Let's assume that this structure can be writing using a
*regular language*.

A *regular expresion* or *regex* is a handy way to write this in a concise
way. Keep in mind that most of the regex engines are more powerful than
a NFA so not all the features that such engines provide can be translated
to a NFA.

But a NFA is powerful enough to solve a lot of problems so it worth it.

## Labeled transitions

First, we say that the NFA can *move* from one state to another
if there is a *transition* between the states and it is labeled
with the same *character* that was read.

We represent this with a simple arrow connecting the two states
labeled with the particular character.

{% call maindiag('label.svg', 'plantuml') %}
```plantuml
hide empty description

[*] -> [*] : a
```
{% endcall %}

A NFA allows the use of *epsilon* transitions or `\epsilon`{.mathjax}-transitions
for short.

A NFA moves from one state to another through a `\epsilon`{.mathjax}-transition
*without* reading any character: it represents the empty string match.

{% call maindiag('epsilon.svg', 'plantuml') %}
```plantuml
hide empty description

[*] -> [*] : <math>\epsilon</math>
```
We are going to drop the label in some cases for clarity
in the following diagrams.
{% endcall %}

## Optional match

We this two simple definitions we can build an *optional match* represented
in regex syntax as ``a?``

{% call maindiag('optional.svg', 'plantuml') %}
```plantuml
hide empty description

[*] -> [*] : <math>\epsilon</math>
[*] -> [*] : a
```
{% endcall %}

The optional part can be as complex as we want like another NFA, no necessary must
be a simple *literal*.

{% call maindiag('sm_optional.svg', 'plantuml') %}
```plantuml
hide empty description

state "<math>sm_1</math>" as sm1

[*] -> sm1 : <math>\epsilon</math>
sm1 -> [*] : <math>\epsilon</math>
```
We represent any arbitrary complex construction as state
machine (`sm_1`{.mathjax}) defined elsewhere.
We plug it using `\epsilon`{.mathjax}-transitions and we make it
*optional* using a third `\epsilon`{.mathjax}-transition
to *bypass* `sm_1`{.mathjax}.
{% endcall %}

## Concatenation and repetition of NFAs

{% call margindiag('concat.svg', 'plantuml') %}
```plantuml
hide empty description

state "<math>sm_1</math>" as sm1
state "<math>sm_2</math>" as sm2

[*] -> sm1 : <math>\epsilon</math>
sm1 -> sm2 : <math>\epsilon</math>
sm2 -> [*] : <math>\epsilon</math>
```
Concatenation of two state machines `sm_1`{.mathjax} and
`sm_2`{.mathjax} (``ab`` in regex syntax).
{% endcall %}



Two or more NFAs can be concatenated to match a *sequence* of submatches
being linked one to the other using `\epsilon`{.mathjax}-transitions.

In regex notation this corresponds to ``ab`` (``a`` followed by ``b``)

{% call marginnotes() %}
This
is made obvious in the diagrams:
`sm_1`{.mathjax} cannot link to itself.
Underwood we will have three `sm_1`{.mathjax} identical objects.
{% endcall %}

As a extension, a NFA can be *link to a clone of itself*
to match a sequence of *repeated* submatches. In regex syntax, ``a{n}``.

{% call margindiag('repeated.svg', 'plantuml') %}
```plantuml
hide empty description

state "<math>sm_1</math>" as sm1a
state "<math>sm_1</math>" as sm1b
state "<math>sm_1</math>" as sm1c

[*]  -> sm1a : <math>\epsilon</math>
sm1a -> sm1b : <math>\epsilon</math>
sm1b -> sm1c : <math>\epsilon</math>
sm1c -> [*]  : <math>\epsilon</math>
```
Repetition of `sm_1`{.mathjax} three times  (``a{3}`` in regex syntax).
{% endcall %}

We say that the link is to a clone because technically a link to itself would
end up in an *unbounded* loop and what we want instead is a *sequence* of
a *fixed size*.

When the NFA links to itself, the loop matches an *unbounded* repetition,
a *zero or more* or *klee* construction, the famous ``a*``:

{% call maindiag('klee.svg', 'plantuml') %}
```plantuml
hide empty description

state "<math>sm_1</math>" as sm1

[*] -> [*]

[*] -> sm1 : <math>\epsilon</math>
sm1 -> [*] : <math>\epsilon</math>
sm1 -l-> sm1
```
*Klee* construction of `sm_1`{.mathjax} that accepts zero or more items.
Notice the difference between this (link to itself) and the
fixed repetition above (link to a clone).
{% endcall %}


The repetition can have different finite lower and higher bounds to form
a *range* with a minimum and a maximum of repetitions ``a{,2}`` ``a{2,4}``
or with the higher limit unbounded ``a{2,}`` ``a+``.


{% call maindiag('range.svg', 'plantuml') %}
```plantuml
hide empty description

state "<math>sm_1</math>" as sm1a
state "<math>sm_1</math>" as sm1b
state "<math>sm_1</math>" as sm1c
state "<math>sm_1</math>" as sm1d

[*]  -> sm1a : <math>\epsilon</math>
sm1a -> sm1b : <math>\epsilon</math>
sm1b -> sm1c : <math>\epsilon</math>
sm1c -> sm1d : <math>\epsilon</math>
sm1d -> [*]  : <math>\epsilon</math>

sm1b -> [*]
sm1c -> [*]
```
Repeated at least 2 times, up to 4 times: is the combination of a
fixed ``a{2}`` followed by an *up to* ``a{,2}``.
{% endcall %}


## Union

Finally, the ``a|b`` regex. As you may guessed, we stick two or
more state machines using `\epsilon`{.mathjax}-transitions.

{% call maindiag('union.svg', 'plantuml') %}
```plantuml
hide empty description

state "<math>sm_1</math>" as sm1
state "<math>sm_2</math>" as sm2

[*] --> sm1
[*] --> sm2 : <math>\epsilon</math>
sm1 --> [*]
sm2 --> [*] : <math>\epsilon</math>
```
Disjunction/union of two state machines `sm_1`{.mathjax} and `sm_2`{.mathjax}.
{% endcall %}

## Further readings

Aho, Lam, Sethi and Ullman. *Compilers: Principles, Techniques, & Tools*, Second edition, Chapter 3.

You can find a NFA implementation in Python [here in Github](https://github.com/eldipa/nfa).
