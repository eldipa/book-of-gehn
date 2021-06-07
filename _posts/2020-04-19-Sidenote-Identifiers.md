---
layout: post
title: "Sidenote: Identifiers"
tags: identifier
---

What would be a nice identifier for the people in, let's say, a database?

{% maincolumn 'assets/2020-04-19-Sidenote-Identifiers/email.png'
'' 'max-width: 70%;' 'in-index-only' %}

<!--more-->

We need identifiers to operate the tables, make joins, and all kind
of crazy data processing.

What would be a good one?

{% marginfigure 'name-img' 'assets/2020-04-19-Sidenote-Identifiers/name.png'
'' 'max-width: 70%;' %}

Their names and addresses? Quite old fashion. Collisions are possible
and can be very frequent. <br />
Building an id based on the attributes of the person is not good
in any case: it is a matter of time that the person change
in some way (like change her address) to make the id *schema* inconsistent.

{% marginfigure 'ssn-img' 'assets/2020-04-19-Sidenote-Identifiers/ssn.png'
'' 'max-width: 70%;' %}

Their government-level id, like the Social Security Number? Better but no,
different countries have different
identifier systems like [INSEE](https://en.wikipedia.org/wiki/INSEE_code)
in France. If you plan to use the software world-wide this
will not work. <br />
And you are still depending on
[humans](https://www.ssa.gov/history/ssn/misused.html) to ensure uniqueness.

Their email? Everyone has an email, right? Yea... well. It is more
nation agnostic but [still...](https://gist.github.com/adamloving/4401361)

{% maincolumn 'assets/2020-04-19-Sidenote-Identifiers/email.png'
'' 'max-width: 70%;' %}

Their DNA? That's unique right?

*Keep it simple. Use a plain number.*

Just:

 - do not allow a human to set the id, make the id unique by software.
 - do not associate any meaning to it, it is just a number.
 - be careful, assigning numbers incrementally will allow and attacker
to guess what will be the next id. This may or may not be a problem.
 - do not reuse any id, **never**.
 - make sure that the space of possible numbers is large enough.

{% maincolumn 'assets/2020-04-19-Sidenote-Identifiers/sheep.png'
'' 'max-width: 70%;' %}
