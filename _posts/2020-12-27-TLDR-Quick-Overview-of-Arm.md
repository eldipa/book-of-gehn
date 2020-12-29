---
layout: post
title: "TL;DR Quick Overview of Arm"
---

Speed-reading of
[Whirlwind Tour of ARM Assembly](https://www.coranac.com/tonc/text/asm.htm).<!--more-->

# The Arm instruction set

Arm is a Reduced Instruction Set Computer (RISC) which have a small set
of instructions of fixed size in contrast with the Complex Instruction
Set Computer (CISC).

In Arm the instructions are of 32 bits and the Thumb version has 16 and
32 bits instructions.

ARMv3 to ARMv7 versions has 32 bits addresses, previous version has 26
bits and ARMv8 introduced the 64 bits addresses.

### Almost everything is conditional

Instructions can be executed conditionally. This avoids explicit jumps
which are slower and the overall code size is smaller.

Use this for small snippets and fallback to traditional branches/jumps
when the code is too large.

```nasm
; r2 = max(r0, r1), traditional impl with branches
    cmp     r0, r1
    blt     .Lbmax      ; go to Lbmax if r0 < r1
    mov     r2, r0      ; r0 is higher ==> r0 > r1
    b       .Lrest      ; finish
.Lbmax:
    mov     r2, r1      ; r1 is higher
.Lrest:
    ...                 ;  rest of code

; r2 = max(r0, r1), with conditionals moves
    cmp     r0, r1
    movge   r2, r0      ;  move if r0 >= r1 (r0 is higher)
    movlt   r2, r1      ;  move if r0 < r1  (r1 is higher)
    ...                 ;  rest of code
```

> Example took from
> [Whirlwind Tour of Arm Assembly](https://www.coranac.com/tonc/text/asm.htm)

Other instructions are also conditional. Even the set of the CPSR
flags is conditional: `sub` does not set the status flags while `subs`
it does.

### Immediate values and the second operand shift

Some instructions allow the second operand to be shifted/rotated in the
same instruction.

```nasm
    add r0, r1, r1          ;  r0 = r1 + r1
    add r0, r1, r1, lsl #4  ;  r0 = r1 + (r1 << 4)
    add r0, r1, r1, lsl r2  ;  r0 = r1 + (r1 << r2)
```

Five shift/rotation exist, both as part of an instruction like above
and as independent instructions as well.

> The immediate value for shifts is limited to 31.

Logical shift left `lsl`, logical shift right `lsr`, arithmetic shift
right `asr`, rotate right `ror` and rotate right with extend `rrx` (the
32 bits register is extended on the left with the *carry* bit: the LSB
is rotated to the carry bit and the carry bit is shifted to the right
into the MSB of the register)

```
          10000110
           \\\\\\\\
           ||||||| \
           vvvvvvv  \
          01000011   -> 0   (logical shift right)
          11000011   -> 0   (arithmetic shift right)

          10000110
           \\\\\\\\
           ||||||| \
           vvvvvvv  \
          01000011   |      (rotate shift right)
          ^---------/

   C=0    10000110
      \    \\\\\\\\
       \--\||||||| \
          vvvvvvvv  \
   C=0    01000011   |     (rotate right extended)
     ^---------------/
```

Having all these nice features in one instruction (shift, conditional,
flag set) come with a cost: less room for immediate values.

In Thumb-2 and ARMv6 and above exists `mov rd, #<imm16>` to set a 16
bits number in a register without the possibility of using any of those
fancy features. It is a plain move.

But that's the exception to the rule. Most of the instructions
including fancy moves only allow 8 bits immediate values.

Like

```nasm
    movs r0, #<imm8>, lsl #4    ;  r0 = imm8 << 4, update condition flags
```

Larger than 255 values in `#<imm8>` are possible because the instruction
has 12 bits to store them. Why not just `#<imm12>` then?

The 4 extra bits are used to rotate to the right the `#<imm8>` value by
*twice* the number encoded in those 4 bits.

In other words, the final value is `n8 ror (2*r4)`: the 8 bits encoded
number rotated by twice the 4 bits encoded.

This allows to set immediate values larger than 12 bits but loosing the
possibility to encode some numbers. If you try to set one of those you
will get a *invalid constant* error.

```nasm
    mov r2, 128000  ;   r2 = 0x1f400
    mov r2, 127999  ;   Invalid operand (KS_ERR_ASM_INVALIDOPERAND)
```

More instructions are needed to compute an arbitrary 32 bits number or a
load.

> Note: a 32 bit number can be set in two instructions: set the 16 lower
> bits with `mov rd, #<imm16>` and set the 16 upper bits with *move
> top*, `movt rd, #<imm16>`

```nasm
    mov r2, 0xccdd      ;   r2 = 0x0000ccdd
    movt r2, 0xaabb     ;   r2 = 0xaabbccdd
```


## Registers

`r0` to `r3` are *scratch* registers: they are not preserved cross calls
and it is caller's responsibility to preserve them if needed.

`r4` to `r11` are *variable* registers: they must be preserved cross
calls and it is callee's responsibility to preserve them if needed.

`r9` may play a different roll (platform dependent, known also as
*static base* register or `sb`) and `r11`
may play the roll of `fp` so both may not be free for arbitrary usage.

The `bl` instruction saves the next instruction (the *return address*)
in the *link* `lr` register (`r14`) and set the destination address
in the *program counter* `pc` register (`r15`).

For "long jumps" and inter-operability, the *intra-procedure-call*
registry `ip` (`r12`) is used.

`r13` is the *stack pointer* `sp`.

Take a look at the
[Procedure Call Standard for the Arm Architecture](https://developer.arm.com/documentation/ihi0042/latest/)


## Data instructions

The arithmetic and logical instructions fall in this category; they
manipulate only on registers, never on memory.

The destination and the first operand are registers while the second can
be a register, and immediate value or a register shifted by another
register or immediate value.

They can be conditionally executed and conditionally set the status
flags.

The
[ARM and Thumb-2 Instruction Set Quick Reference Card](https://documentation-service.arm.com/static/5ed66080ca06a95ce53f932d?token=)
is your friend!

There are no division instructions except on ARMv7-R and ARMv7-M and multiplication
operations are more special.

Because the registers are of 32 bits, the result of a multiplication
cannot fit there: we need 64 bits!

There are two sets of multiplications: the one that stores the result in
a 32 bits register (`mul rd, rm, rs`) and the one that stores it in two
registers (`umull rdlo, rdhi, rm rs`) -- the extra `l` means `long`.

## Memory instructions: load and store

Loads and stores are quite similar: they can operate (load/store)
on 32 bits words, half-words (`h`) and bytes (`b`), zero extended or
signed extended (`s`, `sh` and `sb` respectively).

> Note: `sb` and `sh` prefixes are not supported for stores.

### Indexing

In `ldr rd, [rn]` or `str rd, [rn]`, the `[ ]` denotes dereferencing
and the `rn` register is the *base register*.

```nasm
    ldr r0, [sp]  ; r0 = stack top
```

This is the *register indirect addressing*.

An offset can be added to the base register, useful to iterate over an
array like `ldr rd, [rn, rm]`, `ldr rd, [rn, #4]`
or even `ldr rd, [rn, rm, lsl #4]`.

```nasm
    ldr r0, [sp]                ; r0 = stack top
    ldr r0, [sp, #4]            ; r0 = elem below the top
    ldr r0, [sp, r3]            ; if r3 == 4, same above (sp + 4)
    ldr r0, [sp, r3, lsl #2]    ; if r3 == 2, same above (sp + (1 << 2))
```

This is known as *pre-index addressing*.

Note the use of squares in `ldr rd, [rn, rm, lsl #4]`, the instruction
`ldr rd, [rn], rm, lsl #4` is a pre-index addressing *with post
write-back*: the base address is updated with the final value *after*
the load completed.

```nasm
    ldr r0, [sp], #4     ; r0 = stack top, sp move 4 down (aka "pop")
    ldr r0, [sp], #4     ; r0 = next stack top, sp move 4 down (aka "pop")
```

A *pre write-back* variant exists: `ldr rd, [rn, rm, lsl #4]!`.

```nasm
    ldr r0, [sp, #4]!    ; r0 = sp move 4 down then load (top was skipped)
```

> Note: *pre write-back* makes more sense for stores (aka pushes)
> and *post write-back* for loads (aka pops)

```nasm
    ; swap r0, r1 using the stack, really slow!
    str r0, [sp, #-4]!    ; r0 = sp move 4 up then store (aka push)
    str r1, [sp, #-4]!    ; r1 = sp move 4 up then store (aka push)
    ldr r0, [sp], #4      ; r0 = stack top, sp move 4 down (aka "pop")
    ldr r1, [sp], #4      ; r1 = stack top, sp move 4 down (aka "pop")
```

*PC-relative addressing* allows to load a memory which address is an
offset of the program counter: `ldr rd, <label>`. This works only for
loads; useful to load numbers that cannot fit in an `imm8`.

> Not all the combinations of sizes and addressing are possible. Check
> the data sheet.

### Bulk load/store

Several registers can be loaded or stored with a single *load multiple*
(`ldm`) and *store multiple* (`stm`) instructions.

They have a base address, a *set* of registers and an *indexing affix*
which controls how to "iterate the array/memory".

Four indexing exists: increment of the base address after/before accessing
the memory (`ia`/`ib`) and decrement of the base address after/before
(`da`/`db`).

`ia` is the default.

In short:

```nasm
                            ;              r4, r5, r6, r7
    ldmia   r0, {r4-r7}     ;  *src++    :  0,  1,  2,  3
    ldmib   r0, {r4-r7}     ;  *++src    :  1,  2,  3,  4
    ldmda   r0, {r4-r7}     ;  *src--    : -3, -2, -1,  0
    ldmdb   r0, {r4-r7}     ;  *--src    : -4, -3, -2, -1
```

Note the it is a *set* of registers, **not a list** so the order
is not important. The registers are loaded/stored by their index from
`r0` to `r15`.

For loads the registers are loaded from memory into the registers
in the natural order: from `r0` to `r15`. For stores, the registers
are dump into memory in the reverse order.

```nasm
            <------ store direction    <------ stack grows
    stmdb sp!,  {r0,r1}    ; stack top -> [r0  r1]
    ldmia sp!,  {r2,r3}    ; r2 = r0; r3 = r1
        load direction ------>     stack shrinks ---->
```

The additional `!` symbol means update the base register *before* the
load or store but it doesn't change how the load/store works.

The data sheet says that `push` and `pop` have the canonical form of
`stmdb sp!, {regs}` and `ldmia sp!, {regs}` respectively.

> Note that `sp` points to the last value of the stack and `stmdb`
> decrements the base address (`sp`) before doing the store in a `push`
> while `ldmia` increments after the load in a `pop`.
>
> In both cases the `sp` is updated *before* (*pre write-back*) regardless
> of `db`/`ia`.
>
> Note also that the stack grows decrementing the addresses and shrinks
> incrementing the addresses.

### Alignment

The assembler can do it for you: `.align n` aligns the code or data to 2^n
bytes.

### Endianess

Since version 3, Arm is bi-endian. The instructions are in little
endian but the data access can be little or big endian controlled by the
`E` flag of CPSR.

## Conditionals and branches

Three branches: *branch* (`b`) for `if` and `while` constructs,
*branch with link* (`bl`) for function call and *branch with exchange*
(`bx`) for returning from a call or to switch between Arm and Thumb
modes.

The first two receive a label while the last one operates with a
register.

More branches exist including *branch with change to Jazelle* (`bxj`)
which can switch to a special mode that
[executes Java bytecode](https://en.wikipedia.org/wiki/Jazelle) if
supported.

Due instruction size constrains, labels cannot be in arbitrary
positions. The `b` and `bl` requires the destination addresses to be in
a range relative to `PC` of [-32MB;+32MB].

The range shrinks for other flavours of Arm to [-16MB;+16MB] and to
[-252,256].

The branches can, as other instructions, be conditional executed. So
`bne` stands for branch if not equals.

Two registers have the flags that controls the conditional execution:
the *Current Program Status Register*
(CPSR) and the *Saved Program Status Register* (SPSR), used during the
interrupt handling.

The flags are set by special instructions like *compare* (`cmp`) or by
data manipulation instructions if the affix `s` is added like in `adds`.

Not all the data manipulation instructions alter all the flags. For
example the *overflow* flag (`v`) is set by arithmetic operations and
not by bit operations.

### Branching and condition codes

Current Program Status Register (CPSR):

 - Z: is zero?
 - N: is negative? (is MSB set?)
 - C: is carry bit set? (in a 32 bit register with bits numbered from 0
   (LSB) to 31 (MSB), is the 32 bit set?)
 - V: was an arithmetic overflow? (like given a>0 & b>0 and then a+b < 0)
 - E: are we in big endian mode (E==1) or in little endian (E==0)?

## Symbols

Global labels are defined with `.global label` while local labels
are just `.label` (conventionally they begin with `L` to denote local
but it is optional)

`.code n` declares the type of code: Arm (`n` is 32) or Thumb (`n` is
16). Alternative there are `.arm` and `.thumb` directives that do the
same.

These affect all the code below until another directive change the
setting.

`.thumb_func` on the other side affects only to the next symbol and it
is required for *interworking* Thumb functions.

Alignment of code and data can be set by `.aling n` and `.baling m`
where the former aligns to `2^n` bytes and the latter to `m` bytes.

They apply to the next instruction/data, they are not global.

`.type funcname %function` declares a function.

## Definition of variables

`.byte`, `.hword` and `.word` define data, array of items of 1, 2 and 4
bytes each.

This is handy way to define *"variables"* in the code:

```nasm
    .align 2            ;  mantain the alignment, always!
one_word:
    .word 0x41424344
one_array_u16:
    .hword 1, 2, 3, 4
hello:
    .string "hello", "hello world!"   ;  array of NULL-terminated strings
```

## Sections

These are `.data` (read-write non-zero initialized data) and `.bss`
(read-write zero initialized data).

Other sections exist as well and they are denoted with `.section` like
`.section .rodata` for read-only data.

```nasm
    .data
    .align 2
magic:
    .word 42

    .bss
counter:
    .space 4
```

Code section is denoted by `.text`

# References

 - [Whirlwind Tour of ARM Assembly](https://www.coranac.com/tonc/text/asm.htm).
 - [ARM and Thumb-2 Instruction Set Quick Reference Card](https://documentation-service.arm.com/static/5ed66080ca06a95ce53f932d?token=)
 - [Procedure Call Standard for the Arm Architecture](https://developer.arm.com/documentation/ihi0042/latest/)

<!-- stuff -->

<script>
function fix_asm_syntax(ev) {
    // pip install selectq
    //   cond = (val('text()') == 'blt') | (val('text()') == 'b') | (val('text()').startswith('mov')) | ...
    //   div = sQ.select('div', attr('class').contains('language-nasm'))
    //   xpath = div.select('span', cond)

    // Make some instructions "keywords"
    var xpath = ".//div[contains(@class,'language-nasm')]//span[(((text() = 'blt') or (text() = 'b')) or starts-with(text(), 'mov')) or starts-with(text(), 'ldm') or starts-with(text(), 'stm') or starts-with(text(), 'ldr')]";
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
}

document.addEventListener('DOMContentLoaded', fix_asm_syntax);
</script>

