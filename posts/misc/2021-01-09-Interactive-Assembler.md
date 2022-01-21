---
layout: post
title: "iasm: Interactive Assembler"
tags: [ARM, reversing, iasm]
---

I crossed with a series of [Arm challenges](https://github.com/azeria-labs/ARM-challenges)
by causality and I decided to give it a shoot.

But I have **0** knowledge about Arm so the disassembly of the binaries
were too strange for me.

I stepped back to plan it better: my idea was to use GDB to debug small snippets of Arm
code, learn about it before jumping into the challenges.

I setup a [QEMU virtual machine](/articles/2020/12/15/Qemulating-Rasbian-ARM.html)
running Rasbian in an Arm CPU.

With a GCC and GDB running there I started but the compile-load-debug
cycle was too inflexible.

I could not use it to *explore*.

If I wanted to see the effect of a particular instruction I needed to write
it in assembly, compile it and debug it.

And the time between the "what does X?" and the "X does this" was too
large, reducing the *momentum* that you have when you explore something
new.

Too tedious.

So I decided to shorten the cycle writing an
[*interactive* assembler](https://github.com/bad-address/iasm).<!--more-->

## First try: GDB as the engine

GDB can manipulate the memory of the debuggee process. In particular we
could write binary code, jump to it and execute it. Perfect.

But GDB doesn't have a compiler for assembly.

Or has it?

### Keystone engine

No, but one can be implemented easily with
[keystone-engine](https://www.keystone-engine.org/).

Keystone takes assembly code and compiles it. Having Python bindings
we could put this into a GDB plugin and *presto!*

## Second try: Unicorn engine

GDB requires a full operative
system (Rasbian) running in a full emulated QEMU machine.

Can we make it lighter? -- Yes we can.

### Unicorn engine

[unicorn-engine](https://www.unicorn-engine.org/) it is a CPU emulator
based on QEMU.

The trick is that Unicorn only emulates the CPU and memory and nothing
else: no devices, disks or network cards.

Without anything to manage, Unicorn does not need an operative system
making it a solution much lighter.

And better, the Python bindings for Unicorn gives us access to the CPU
registers and memory so we can get rid of GDB.

## iasm: keystone + unicorn + python

I soon realized that while learning Arm by writing code is the best way
to do it,
writing *everything* in assembly is hard.

Simple tasks like initialize the registers or print a chunk
of stack involves several instructions.

In Python `r0 = 1111127999`. In Arm:

```nasm
100:0>     ldr r0, .Lval
100:0>
100:0> .Lval:
100:0>     .word 1111127999
```

So, [`iasm`](https://github.com/bad-address/iasm) has an escape mode.
Basically I call `eval`/`exec`
emulating with Python variables like `r0` and `M` registers
and memory.

And that's `iasm` an keystone assembler connected with a unicorn
emulator and some python code to glue them.


## Features

### Python Prompt Toolkit

[python-prompt-toolkit](https://python-prompt-toolkit.readthedocs.io/en/latest/)
or PPT for short, is a library to build CLI applications.

It has syntax highlighting as you write (using [pygments](https://pygments.org/)),
autocompletion and command line history.

An enhanced replacement for Python's `input` for sure.

### Memory

Unicorn has `mem_read` and `mem_write` to change the memory of the
process but like any other process, the memory pages need to be mapped
before with `mem_map` and released with `mem_unmap`.

```python
mu.mem_map(0x1000, 0x2000)
mu.mem_write(0x1100, 0x1200, b"A" * 0x100)
mu.mem_read(0x1100, 0x1200)
mu.mem_unmap(0x1000, 0x2000)
```

`iasm` has a more pythonic syntax accessible from the Python shell:

```python
100:0> ;! M[0x1000:0x2000] = 0  # map and initialize
Mapping memory region [0x1000-0x1fff] (sz 0x1000)

100:0> ;! M[0x1050:0x1055] = 0x41       # write like 'memset'
100:0> ;! M[0x1055:0x105a] = b'B' * 5   # write like 'memcpy'

100:0> ;! M[0x1050:0x105a]     # read
[AAAAABBBBB]

100:0> ;! M    # list mapped pages
[0x1000-0x1fff] (sz 0x1000)
[0x1000000-0x11fffff] (sz 0x200000)

100:0> ;! del M[0x1000:0x2000]    # unmap
```

### Allocate stack

To allocate the stack and setup the (Arm) registers just run:

```python
100:0> ;! M[0x1000:0x2000] = 0
Mapping memory region [0x1000-0x1fff] (sz 0x1000)

100:0> ;! fp = sp = 0x2000
```

Now, play with it and practice your (Arm) assembly:

```nasm
100:0> mov r0, #4
100:0> mov r1, #8
100:0> push {r0, r1}
```

And check the stack (was `r0` pushed before `r1` or not? Check it!)

```python
100:0> ;! M[sp:]   # from sp to the end of the mapped page
[\x04\x00\x00\x00\x08\x00\x00\x00]
```

### Initialization script

Write in a file all the initialization like the stack allocation and
load it from the command line with `-i`.

```shell
$ echo ';! r0 = r1 = r2 = 8' > init

$ iasm -a arm -m arm -i init
Mapping memory region [0x1000000-0x11fffff] (sz 0x200000)
------  -  ------  -  ------  -  ------  -----
    r0  8  r1      8  r2      8  r3      0
<...>
```

### Inline documentation

Following the tradition of Python, `iasm` includes documentation for the
assembly instructions.

After the mnemonic type `?` and enter to show it:

```nasm
100:0> mul ?
<...>
```

Basically what I did was to convert to text the manual of reference of
the ISA (typically it is a PDF file) and then parse the text.

I only focused in the documentation of the instructions, the rest is up
to the user to search the complete story in the official documentation
(only Arm for now)

### Globs registers

`iasm` allows to select which registers to show using *globs*,
Unix like pattern expressions defined by
[fnmatch](https://docs.python.org/3/library/fnmatch.html).

```shell
$ iasm -a arm -m arm -r 'r[0-9]'
Mapping memory region [0x1000000-0x11fffff] (sz 0x200000)
--  -  -----  -  --  -  --  -
r0  0  r1     0  r2  0  r3  0
r4  0  r5     0  r6  0  r7  0
r8  0  r9/sb  0
--  -  -----  -  --  -  --  -
<...>
```

So the expression `r[0-9]` selects all the Arm registers from `r0` to
`r15`.

### Compressed hex values

32 bit numbers are too large to display (and 64 bit address are
worse!).

Instead, `iasm` shows them as *compressed* hexadecimal numbers.

They are like hexadecimals but the number is split into 4-digits groups
divided by a `:`.

The leading zeros of each group are omitted and if the group is full of
zeros only a single `0` is put and if the group is on the left (more
significant digits), the whole group is omitted.

Here are some examples:

```
0x00000000             0
0x000000ab            ab
0x00ab00cd         ab:cd
0x00ab0000          ab:0
```
