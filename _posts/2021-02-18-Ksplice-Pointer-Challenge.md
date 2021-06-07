---
layout: post
title: "Ksplice-Pointer-Challenge"
tags: pointer memory
---

What does the following code?

```cpp
#include <stdio.h>
int main() {
  int x[5];
  printf("%p\n", x);
  printf("%p\n", x+1);
  printf("%p\n", &x);
  printf("%p\n", &x+1);
  return 0;
}
```

<!--more-->

This problem was
[posted](https://blogs.oracle.com/linux/the-ksplice-pointer-challenge-v2) in 2011.

Apparently t born in the context of the developing of
[ksplice](https://en.wikipedia.org/wiki/Ksplice), a project made by the
students of the MIT to patch the Linux kernel in runtime without
needing to boot.

The challenge is just about printing 4 things.

Despite being so simple in comparison with what
[ksplice](https://en.wikipedia.org/wiki/Ksplice) does, the challenge may
had a few surprises for you.

## The analysis

We reserve 5 `int`s in the stack:

```cpp
?: #include <stdio.h>
?: int x[5];
```

{% marginnote
'
The examples that are you seeing are **executed by real** in a machine
and **compared by real** with expected values below the example.
<br />
Because I cannot hardcode an address (because they are not
deterministic) I&apos;m going to **capture** the address with the
`<array-addr>` tag and use it later for comparison.
<br />
The magic behind this is [byexample](https://byexamples.github.io/).
' %}

We then print the address of the array:

```cpp
?: printf("%p\n", x);
<array-addr>
```

The address of the array is the address of the first element.
In a more verbose but perhaps more explicit notation:

{% marginnote
'
[byexample](https://byexamples.github.io/) will **paste** the
previously captured text replacing the `<array-addr>` in the snippet.
<br >
Remember this is the number printed by the previous `printf`. Because
it *is* an integer the compiler will warn us due the comparison of a
pointer (left side) and a number (right side).
<br >
The `(int*)` cast is to tell the compiler "it is okay to compare".
<br />
' %}
```cpp
?: (&x[0] == (int*) <array-addr>)        // byexample: +paste
(bool) true
```

Array increments (and decrements) are in terms of the size of the
element.

In our case, the array element is `int`:

```cpp
?: printf("%p\n", x+1);
<array-plus-1-addr>

?: (<array-addr> + sizeof(int) == <array-plus-1-addr>)     // byexample: +paste
(bool) true
```

So that means also that `x+1` is the same than `&x[1]`.

```cpp
?: (&x[1] == (int*) <array-plus-1-addr>)     // byexample: +paste
(bool) true
```

The *philosofical* question begins with `&x`: what is the address
of the address of an array?

Well the fact it is the address itself, a kind of self-referencing
notation:

```cpp
?: printf("%p\n", &x);
<ampersand-array-addr>

?: (<array-addr> == <ampersand-array-addr>)      // byexample: +paste
(bool) true
```

Now the `&x+1` requires understand the [operator
precedence](https://en.cppreference.com/w/c/language/operator_precedence).

The *address-of* operator has **more precedence** than the
*addition* operator so we should interprete the expression as `(&x)+1`.

```cpp
?: (&x+1 == (&x)+1)      // byexample: +paste
(bool) true
```

*This is when the thing gets weird.*

An address is not just a number, it **carries** information of the type:
`x` is an `int[5]` array so `&x` points to an `int[5]` array.

{% marginnote
'
My initial thought was `(&x)` is an address so `+1` adds 1 to the
address. I was so wrong.
' %}

It is a *pointer* so the addition is in terms of the size of the element
pointer to: not `sizeof(int)` but `sizeof(int[5])`!.

```cpp
?: printf("%p\n", &x+1);
<ampersand-array-plus-1-addr>

?: (<ampersand-array-addr> + sizeof(int[5]) == <ampersand-array-plus-1-addr>)      // byexample: +paste
(bool) true
```

For completeness, `&(x+1)` is the address of the second element's
*address*. An address of an address makes no sense:

```cpp
?: printf("%p\n", &(x+1));
<...>cannot take the address of an rvalue of type 'int *'<...>
```

## Final score

```cpp
#include <stdio.h>
int main() {
  int x[5];
  printf("%p\n", x);        // Good
  printf("%p\n", x+1);      // Good
  printf("%p\n", &x);       // Good
  printf("%p\n", &x+1);     // EPIC FAIL
  return 0;
}
```

Honestly, `&x+1` took me by surprise.

## Bonus track

[cdecl](https://linux.die.net/man/1/cdecl), a tool to
compose and decode C/C++ type declarations.

<!--
$ hash cdecl 2>/dev/null && echo "installed"
<cdecl-installed>

-->

```shell
$ cdecl declare 'signal as function (arg1,arg2) returning pointer to function returning void'   # byexample:  +if=cdecl-installed
void (*signal(arg1, arg2))()

$ cdecl explain 'char *(*fptab[])()'   # byexample:  +if=cdecl-installed
declare fptab as array of pointer to function returning pointer to char
```
