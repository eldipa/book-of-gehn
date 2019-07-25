---
layout: post
title: "From a Regex to a Nondeterministic Finite Automata"
---

Before building complex state machine we need to learn the basics blocks.

When the solution to a problem can be seen as set of states with
transitions from ones to others, modeling them as a nondeterministic
finite automatas makes clear how the solution works and allows to spot
deficiencies.

A regular expression is an example of this. As an introductory step
let's review how to turn a regex into a NFA.
<!--more-->

## From a regular expression to a NFA

Before getting deep in this, let's define a very simple problem: we
want to validate if a particular string follows or not a given structure.

Let's assume that this structure can be writing using a
*regular language*{% sidenote '**??**' %}

A *regular expresion* or *regex* is a handy way to write this in a concise
way. Keep in mind that most of the regex engines are more powerful than
a NFA so not all the features that such engines provide can be translated
to a NFA.{% sidenote '**??**' %}

But a NFA is powerful enough to solve a lot of problems so it worth it.

## Labeled transitions

First, we say that the NFA can *move* from one state to another
if there is a *transition* between the states and it is labeled
with the same *character* that was read.

We represent this with a simple arrow connecting the two states
labeled with the particular character.

{% maincolumnplantuml %}
`
@startuml
hide empty description

[*] -> [*] : a

@enduml
`
{% endmaincolumnplantuml %}

A NFA allows the use of *epsilon* transitions or $$\epsilon$$-transitions
for short.

A NFA moves from one state to another through a $$\epsilon$$-transition
*without* reading any character: it represents the empty string match.

{% maincolumnplantuml caption:'We are going to drop the label in some cases for clarity in the following diagrams.' %}
`
@startuml
hide empty description

[*] -> [*] : <math>\epsilon</math>

@enduml
`
{% endmaincolumnplantuml %}

## Optional match

We this two simple definitions we can build an *optional match* represented
in regex syntax as ``a?``

{% maincolumnplantuml %}
`
@startuml
hide empty description

[*] -> [*] : <math>\epsilon</math>
[*] -> [*] : a

@enduml
`
{% endmaincolumnplantuml %}

The optional part can be as complex as we want like another NFA, no necessary must
be a simple *literal*.

{% maincolumnplantuml caption:'We represent any arbitrary complex construction as state machine ($$sm_1$$) defined elsewhere. We plug it using $$\epsilon$$-transitions and we make it *optional* using a third $$\epsilon$$-transition to *bypass* $$sm_1$$.' %}
`
@startuml
hide empty description

state "<math>sm_1</math>" as sm1

[*] -> sm1 : <math>\epsilon</math>
sm1 -> [*] : <math>\epsilon</math>

@enduml
`
{% endmaincolumnplantuml %}

## Concatenation and repetition of NFAs

{% marginplantuml caption:'Concatenation of two state machines $$sm_1$$ and $$sm_2$$ (``ab`` in regex syntax).' %}
`
@startuml
hide empty description

state "<math>sm_1</math>" as sm1
state "<math>sm_2</math>" as sm2

[*] -> sm1 : <math>\epsilon</math>
sm1 -> sm2 : <math>\epsilon</math>
sm2 -> [*] : <math>\epsilon</math>

@enduml
`
{% endmarginplantuml %}



Two or more NFAs can be concatenated to match a *sequence* of submatches
being linked one to the other using $$\epsilon$$-transitions.

In regex notation this corresponds to ``ab`` (``a`` followed by ``b``)

As a extension, a NFA can be *link to a clone of itself*{% sidenote 'This
is made obvious in the diagrams:
$$sm_1$$ cannot link to itself. Underwood we will have three $$sm_1$$ identical objects.' %}
to match a sequence of *repeated* submatches. In regex syntax, ``a{n}``.

{% marginplantuml caption:'Repetition of $$sm_1$$ three times  (``a{3}`` in regex syntax).' %}
`
@startuml
hide empty description

state "<math>sm_1</math>" as sm1a
state "<math>sm_1</math>" as sm1b
state "<math>sm_1</math>" as sm1c

[*]  -> sm1a : <math>\epsilon</math>
sm1a -> sm1b : <math>\epsilon</math>
sm1b -> sm1c : <math>\epsilon</math>
sm1c -> [*]  : <math>\epsilon</math>

@enduml
`
{% endmarginplantuml %}

We say that the link is to a clone because technically a link to itself would
end up in an *unbounded* loop and what we want instead is a *sequence* of
a *fixed size*.

When the NFA links to itself, the loop matches an *unbounded* repetition,
a *zero or more* or *klee* construction, the famous ``a*``:

{% maincolumnplantuml caption:'*Klee* construction of $$sm_1$$ that accepts zero or more items. Notice the difference between this (link to itself) and the fixed repetition above (link to a clone).' %}
`
@startuml
hide empty description

state "<math>sm_1</math>" as sm1

[*] -> [*]

[*] -> sm1 : <math>\epsilon</math>
sm1 -> [*] : <math>\epsilon</math>
sm1 -l-> sm1

@enduml
`
{% endmaincolumnplantuml %}


The repetition can have different finite lower and higher bounds to form
a *range* with a minimum and a maximum of repetitions ``a{,2}`` ``a{2,4}``
or with the higher limit unbounded ``a{2,}`` ``a+``.


{% maincolumnplantuml caption:'Repeated at least 2 times, up to 4 times: is the combination of a fixed ``a{2}`` followed by an *up to* ``a{,2}``.' %}
`
@startuml
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

@enduml
`
{% endmaincolumnplantuml %}


## Union

Finally, the ``a|b`` regex:

{% maincolumnplantuml caption:'Disjunction/union of two state machines $$sm_1$$ and $$sm_2$$.' %}
`
@startuml
hide empty description

state "<math>sm_1</math>" as sm1
state "<math>sm_2</math>" as sm2

[*] -> sm1 : <math>\epsilon</math>
[*] -> sm2 : <math>\epsilon</math>
sm1 -> [*] : <math>\epsilon</math>
sm2 -> [*] : <math>\epsilon</math>

@enduml
`
{% endmaincolumnplantuml %}

## Further readings

Compilers: Principles, Techniques, & Tools, Aho, Lam, Sethi and Ullman, Second edition, Chapter 3.
