---
layout: post
title: "Nondeterministic Finite Automata"
---

java.lang.ClassNotFoundException: org.scilab.forge.jlatexmath.TeXFormula

## Building blocks

{% marginplantuml caption:'Representation of a literal `a` as a NFA.' %}
`
@startuml
hide empty description

[*] -> [*] : a

@enduml
`
{% endmarginplantuml %}


{% marginplantuml caption:'Representation of the disyuntion/union between two state machines `sm1` and `sm2`.' %}
`
@startuml
hide empty description

[*] --> sm1 : e
[*] --> sm2 : e
sm1 --> [*] : e
sm2 --> [*] : e

@enduml
`
{% endmarginplantuml %}

{% marginplantuml caption:'Representation of the concatenation of two state machines `sm1` and `sm2`.' %}
`
@startuml
hide empty description

[*] -> sm1 : e
sm1 -> sm2 : e
sm2 -> [*] : e

@enduml
`
{% endmarginplantuml %}

{% marginplantuml caption:'Representation of the repetetion of `sm1` three times.' %}
`
@startuml
hide empty description

state "sm1" as sm1a
state "sm1" as sm1b
state "sm1" as sm1c

[*]  -> sm1a : e
sm1a -> sm1b : e
sm1b -> sm1c : e
sm1c -> [*]  : e

@enduml
`
{% endmarginplantuml %}


{% marginplantuml caption:'Representation of the *optional* state machine `sm1`.' %}
`
@startuml
hide empty description

[*] -> sm1 : e
sm1 -> [*] : e

[*] -> [*] : e

@enduml
`
{% endmarginplantuml %}


{% marginplantuml caption:'Representation of the *optional* state machine `sm1`.' %}
`
@startuml
hide empty description

[*] -> sm1 : e
sm1 -> [*] : e

[*] -> [*] : e

@enduml
`
{% endmarginplantuml %}

{% marginplantuml caption:'Representation of the *klee* state machine `sm1` that accepts zero or more.' %}
`
@startuml
hide empty description

[*] -> sm1 : e
sm1 -> [*] : e

[*] -> [*] : e
sm1 --> sm1

@enduml
`
{% endmarginplantuml %}


{% marginplantuml caption:'Representation of the state `sm1` repeated up to 2 times.' %}
`
@startuml
hide empty description

state "sm1" as sm1a
state "sm1" as sm1b

[*]  -> sm1a : e
sm1a -> sm1b : e
sm1b -> [*]  : e

[*]  -> [*]
sm1a -> [*]

@enduml
`
{% endmarginplantuml %}

{% marginplantuml caption:'Representation of the repetetion between 2 and 4 times of `sm1`.' %}
`
@startuml
hide empty description

state "sm1" as sm1a
state "sm1" as sm1b
state "sm1" as sm1c
state "sm1" as sm1d

[*]  -> sm1a : e
sm1a -> sm1b : e
sm1b -> sm1c : e
sm1c -> sm1d : e
sm1d -> [*]  : e

sm1b -> [*]
sm1c -> [*]

@enduml
`
{% endmarginplantuml %}

