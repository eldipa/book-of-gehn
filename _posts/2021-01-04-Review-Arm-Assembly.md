---
layout: post
title: "Review Arm Assembly"
---

There is no other way to learn something that playing with it.

Take assembly code, read it and predice what will do. Then test it.

Those mistakes, those mismatches between what you think and what it
really is, those *surprises* are what move us forward into learning. Deeper.

In this post I will dig into Arm, assisted with an
[interactive assembler](https://github.com/bad-address/iasm).<!--more-->

## GCC generated Arm assembly

We will see the assembly of the following C code compiled as:

```shell
pi@raspberrypi:~$ gcc -S -O0 -o asm1.asm asm1.c
```

`raspberrypi` is a QEMU virtual machine for Arm running a Raspbian
Stretch. The setup is explained in my previous post
[QEMUlating a Rasbian (ARM)](/book-of-gehn/articles/2020/12/15/Qemulating-Rasbian-ARM.html).

The code is quite simple:

```cpp
int rand() {
  return 0x42;
}

int sum(int a, int b) {
  return a+b;
}

int main() {
  int r = rand();
  if (r == 0)
    return 0;
  else if (r > 0x4041)
    return sum(r, 0x4041);
  else
    return -1;
}
```

Let's dig into the assembly. I will use an
[interactive assembler](https://github.com/bad-address/iasm).

## The `rand` function

```nasm
        .align  2
        .global rand
        .arch armv6
        .syntax unified
        .arm
        .fpu vfp
        .type   rand, %function
rand:
        ; link register save eliminated.
        str     fp, [sp, #-4]!
        add     fp, sp, #0
        mov     r3, #66
        mov     r0, r3
        add     sp, fp, #0
        ldr     fp, [sp], #4
        bx      lr
        .size   rand, .-rand
```

First, the code is aligned and the symbol is marked as "global".
`.arm` says that the code is Arm (aka `.code 32`).

### Prologue

The function begins saving the *frame pointer* `fp` in the stack.

The `str fp, [sp, #-4]!` is a *pre-index* addressing store: the `fp`
is saved 4 bytes "up" in the stack (the stack grows towards lower
addresses).

And the store is in *pre write-back* store (`!`): the `sp` is
updated (decremented by 4) *before* performing the store.

The `sp` points always to the latest *valid* value in the stack. That's
why `sp` is decremented before performing the store.

The `add fp, sp, #0` is an alternative to `mov fp, sp`.

At the begin of the call:

```nasm
------  -  ------  ----  ------  ---------  ------  ---------
    r0  0  r1      0     r2      0          r3      0
    r4  0  r5      0     r6      0          r7      0
    r8  0  r9/sb   0     r10     0          r11/fp  bbbb:bbbb
r12/ip  0  r13/sp  2000  r14/lr  aaaa:aaaa  r15/pc  100:0
------  -  ------  ----  ------  ---------  ------  ---------
```

After the `fp` and `sp` update:

```nasm
------  -  ------  ----  ------  ---------  ------  -----
    r0  0  r1      0     r2      0          r3      0
    r4  0  r5      0     r6      0          r7      0
    r8  0  r9/sb   0     r10     0          r11/fp  1ffc
r12/ip  0  r13/sp  1ffc  r14/lr  aaaa:aaaa  r15/pc  100:4
------  -  ------  ----  ------  ---------  ------  -----
```


{% marginnote
'[iasm](https://github.com/bad-address/iasm), the interactive assembler,
allows to explore the memory with the `M` object. `M[sp:]` means show
the memory from the address stored in `sp` to the last address mapped
page.
<br />
In other words: show the stack.
' %}

And the state of the stack is:

```python
100:4> ;! M[sp:]
[\xbb\xbb\xbb\xbb]
       (fp)

100:4> ;! M[fp:]
[\xbb\xbb\xbb\xbb]
       (fp)
```

`sp` points always to the latest value of the stack; `fp` points to the
previous `fp` value (`0xbbbbbbbb` in this case).

### Body

The assembler didn't optimize the code: it stored in `r3` the immediate
value of `#66` (0x42) to then copy it to `r0` (the register used for
returning values). `mov r0, #66` would be shorter.

### Epilogue

Then the `sp` is restored to the current `fp` and the `fp` is restored
to the previous `fp` value with `ldr fp, [sp], #4`

This load is a *pre-index* addressing with *post write-back*. That's it,
the `fp` is loaded with the valued pointed by `sp` and then `sp` is
added 4 bytes (aka pop).

The compiler however should optimize this because the stack is not used
at all so saving and restoring `fp` has no value.

What the compiled did, it didn't save the *link* register `lr`.

The register holds the address to where return from a call. Because
`rand` doesn't call anything, `lr` from the caller is preserved so it is
not needed to save it in the stack.

`bx lr` returns to the caller.

## The `sum` function

```nasm
sum:
        str     fp, [sp, #-4]!
        add     fp, sp, #0
        sub     sp, sp, #12
        str     r0, [fp, #-8]
        str     r1, [fp, #-12]
        ldr     r2, [fp, #-8]
        ldr     r3, [fp, #-12]
        add     r3, r2, r3
        mov     r0, r3
        add     sp, fp, #0
        ldr     fp, [sp], #4
        bx      lr
        .size   sum, .-sum
```

### Prologue

In this case the function allocates 12 bytes to hold local variables
(`sub sp, sp, #12`).

The second argument `r1` is stored in the top of the stack; the first
argument `r0` is stored below. Arguments are pushed from left (`r0`) to
right (`r1`).

The call convention says that the arguments are passed via registers (up
to 4 args). They are set by the caller and, if needed, the callee needs
to preserve them in the stack.

No really needed here because `sum` does not call other function but
still the compiler follows the cookbook.

The function allocated 12 byte to hold 3 variables of 32 bits. We stored
2, the arguments, but the third element is never set.

The registers at the begin of the call were:

```nasm
------  ---------  ------  ---------  ------  ---------  ------  ---------
    r0  cccc:cccc  r1      dddd:dddd  r2      0          r3      0
    r4  0          r5      0          r6      0          r7      0
    r8  0          r9/sb   0          r10     0          r11/fp  bbbb:bbbb
r12/ip  0          r13/sp  2000       r14/lr  aaaa:aaaa  r15/pc  100:0
------  ---------  ------  ---------  ------  ---------  ------  ---------
```

And after the stores, the stack has:

```python
100:10> ;! M[sp:]
[\xdd\xdd\xdd\xdd\xcc\xcc\xcc\xcc\x00\x00\x00\x00\xbb\xbb\xbb\xbb]
       (r1)            (r0)            (??)            (fp)

100:10> ;! M[fp:]
[\xbb\xbb\xbb\xbb]
       (fp)
```

I presume that the unused space (??) is for the `lr` register.

## The `main` function

```nasm
main:
        push    {fp, lr}
        add     fp, sp, #4
        sub     sp, sp, #8
        bl      rand
        str     r0, [fp, #-8]
        ldr     r3, [fp, #-8]
        cmp     r3, #0
        bne     .L6
        mov     r3, #0
        b       .L7
.L6:
        ldr     r3, [fp, #-8]
        ldr     r2, .L9
        cmp     r3, r2
        ble     .L8
        ldr     r1, .L9
        ldr     r0, [fp, #-8]
        bl      sum
        mov     r3, r0
        b       .L7
.L8:
        mvn     r3, #0
.L7:
        mov     r0, r3
        sub     sp, fp, #4
        pop     {fp, pc}
.L10:
        .align  2
```

### Prologue

The function saves `fp` and `lr` with a single `push {fp,lr}`.

The `{r,r}` notation is a *set*, not a *list*: registers are pushed in
the *inverse* order of the registers (`r0` to `r15`)
regardless of how the `push` is written.

In our case `fp` is `r11` and `lr` is `r14` so that is the natural order,
then the inverse order applies: `r14` is pushed first, `r11` later.

In short: `r14` will be at the bottom of the stack (higher addresses)
while `r11` will be at the top (lower addresses).

The `fp` is then updated to the base of the stack for the current
function call. The stack frame begins *after* storing the previous `fp`
so the current `fp` points to the saved `lr`.

The `fp` update is done with `add fp, sp, #4` (by this moment the `sp`
is off by 4 due the push of `lr`).

The registers at the begin of the call were:

```nasm
------  ---------  ------  ---------  ------  ---------  ------  ---------
    r0  cccc:cccc  r1      dddd:dddd  r2      0          r3      0
    r4  0          r5      0          r6      0          r7      0
    r8  0          r9/sb   0          r10     0          r11/fp  bbbb:bbbb
r12/ip  0          r13/sp  2000       r14/lr  aaaa:aaaa  r15/pc  100:0
------  ---------  ------  ---------  ------  ---------  ------  ---------
```

And after the `push` and `add`, the registers were:

```nasm
------  ---------  ------  ---------  ------  ---------  ------  -----
    r0  cccc:cccc  r1      dddd:dddd  r2      0          r3      0
    r4  0          r5      0          r6      0          r7      0
    r8  0          r9/sb   0          r10     0          r11/fp  1ffc
r12/ip  0          r13/sp  1ff8       r14/lr  aaaa:aaaa  r15/pc  100:4
------  ---------  ------  ---------  ------  ---------  ------  -----
```

And the stack:

```python
100:4> ;! M[sp:]
[\xbb\xbb\xbb\xbb\xaa\xaa\xaa\xaa]
       (fp)            (lr)

100:4> ;! M[fp:]
[\xaa\xaa\xaa\xaa]
       (lr)
```

This is **not** compatible with what we saw in `rand` and `sum`: the
`fp` points to the saved `fp` in these functions but points to `lr` in
`main`.

Also, in `sum` we believed that 4 unused bytes were reserved to store
`lr` but here we see that the space is reserved later with
`sub sp, sp, #8` and does not include space for `lr`.

### Comparisons

The call to `rand` (parameterless) is done with `bl`, branch and link.

The return value is in `r0` and for some reason it is pushed and popped
back from the stack into `r3`.

`M[fp - 8]` is used as the placeholder for this and for subsequent
references to the returned value of `rand`.

Two comparisons are made for the `if-else if` statement:

```nasm
        ldr     r3, [fp, #-8]
        cmp     r3, #0
    ...
        ldr     r3, [fp, #-8]
        ldr     r2, .L9
        cmp     r3, r2
```

The first compares `r3` (`rand` returned value) with a immediate value
of `0` (`cmp r3, #0`).

The second compares two registers, `r3` and `r2`, where `r2` is also a
fixed value but it is to large to fit in the `cmp` instruction as an
immediate value.

In this case the value is loaded in the `r2` register from the code
segment (label `.L9`).

```nasm
.L9:
        .word   16449
```

### Function call

A function call is done with *branch with link* `bl`.

Arguments are passed via `r0` to `r3` registers from left to right.
More than 4 arguments require the stack.

```nasm
        ; call to sum(r, 0x4041)
        ldr     r1, .L9         ; second arg
        ldr     r0, [fp, #-8]   ; first arg
        bl      sum
```

The `bl` saves the next instruction (the *return address*) in the *link*
`lr` register (`r14`) and set the destination address in the *program
counter* `pc` register (`r15`).

`bx lr` (*branch and exchange*) is used to return to the caller.


## Arm directives

Two more fragments remains that are not part of any function.

These are [directives for the
GNU Assembler](https://sourceware.org/binutils/docs-2.27/as/ARM-Directives.html),
see also
[this](https://ftp.gnu.org/old-gnu/Manuals/gas-2.9.1/html_chapter/as_7.html):

```nasm
        .arch armv6
        .eabi_attribute 28, 1
        .eabi_attribute 20, 1
        .eabi_attribute 21, 1
        .eabi_attribute 23, 3
        .eabi_attribute 24, 1
        .eabi_attribute 25, 1
        .eabi_attribute 26, 2
        .eabi_attribute 30, 6
        .eabi_attribute 34, 1
        .eabi_attribute 18, 4
        .file   "asm1.c"
        .text
```

```nasm
        .ident  "GCC: (Raspbian 8.3.0-6+rpi1) 8.3.0"
        .section        .note.GNU-stack,"",%progbits
```

## Final thoughts

I have being reading [documentation](https://developer.arm.com/documentation/ihi0042/latest/)
and [write ups](https://www.coranac.com/tonc/text/asm.htm) about Arm
during the last weeks.

When I
[started](/book-of-gehn/articles/2020/12/27/TLDR-Quick-Overview-of-Arm.html)
 my idea was to use a [QEMU virtual machine for
testing](/book-of-gehn/articles/2020/12/15/Qemulating-Rasbian-ARM.html):
code a little of assembly, compile it, debugging it with GDB and seeing
the effects.

It turns out to be tedious very quickly.

I relayed then more in the documentation and the [instruction set
reference](https://documentation-service.arm.com/static/5ed66080ca06a95ce53f932d?token=)
but when I review real code (like the one in this post) some things made
no sense.

Obviously there were errors in my interpretation of the code.

That's why I coded an [interactive assembler](https://github.com/bad-address/iasm)
to have a quick feedback of what each instruction does without requiring
a compile-upload-debug cycle.

It really help me to "smooth out certain rough edges" and understand
better the code specially when the indexing flavors and how the things
are pushed and popped from the stack.


<!-- stuff -->

<script>
function fix_asm_syntax(ev) {
    // pip install selectq
    //   cond = (val('text()') == 'blt') | (val('text()') == 'b') | (val('text()').startswith('mov')) | ...
    //   div = sQ.select('div', attr('class').contains('language-nasm'))
    //   xpath = div.select('span', cond)

    // Make some instructions "keywords"
    var xpath = ".//div[contains(@class,'language-nasm')]//span[(((text() = 'blt') or (text() = 'b')) or starts-with(text(), 'mov')) or starts-with(text(), 'ldm') or starts-with(text(), 'stm') or starts-with(text(), 'ldr') or starts-with(text(), 'bx') or starts-with(text(), 'bl') or starts-with(text(), 'bne') or starts-with(text(), 'mvn')]";
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
