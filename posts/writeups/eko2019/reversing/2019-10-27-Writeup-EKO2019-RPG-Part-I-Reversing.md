---
layout: post
title: RPG - Part I (IDA writeup - EKO 2019)
tags: [eko, challenge, reversing, IDA]
artifacts:
 - mentalmodel.svg
---

``rpg`` is a buggy game where the player can attack to
and defend from attacks of monsters.

Let's see if we can know how it works.<!--more-->

It is a 64 bits ELF [binary]({{ asset('rpg') }}):

```shell
$ file rpg                      # byexample: +norm-ws
rpg: ELF 64-bit LSB executable, x86-64, version 1 (GNU/Linux),
statically linked, for GNU/Linux 2.6.32,
BuildID[sha1]=<...>, stripped
```

We expect some part of ``libc`` in the binary
and no symbol at all.

So our first task is to find what pieces of the binary
are of the game and which aren't like ``stdlib``.

## Strings as Starting Points

Let's see what strings we can find:

```shell
$ strings -a -16 rpg | head -14
Monster %s attack to %s with %d damage.
%s has stopped the attack.
%s is dead. GG WP.
Monster %s defends with %d of defense.
%s hit a critical to %s.
0) Create player
1) Update player name
2) Delete player
3) Player attack
4) Player defend
5) Get current time
User created, first delete it.
Enter player name:
User not created.
```

Running the program we can map those strings to a mental model
of what it does:


{% call marginnotes() %}
If the player was not created, the options 1 to 4 print ``User not created.``;
if the player was created selecting 0 again yields a
``User created, first delete it.`` {% endcall %}

{% call maindiag('mentalmodel.svg', 'plantuml') %}
```plantuml
hide empty description
skinparam backgroundColor transparent

state "0) Create player\n1) Update player name\n2) Delete player\n3) Player attack\n4) Player defend\n5) Get current time" as menu
state "Enter player name:" as askname
state "User created, first delete it." as usercreated
state "Monster %s defends with %d of defense." as monsterattack
state "Monster %s attack to %s with %d damage." as monsterdefend
state "<i>timestamp</i>" as tstmp

menu -> askname : 0 or 1
menu -> usercreated : 0 or 1

menu --> monsterattack : 3 or 4
menu --> monsterdefend : 3 or 4

menu -> tstmp : 5
```
{% endcall %}

Other strings shown up. Of course, I'm speculating the *conversion
specifier* like ``%s`` and ``%d``:

```
%s defends.
%s roar to %s.
Name: %s
Lives: %d
```

``ctrl+F12`` opens the *Strings window* listing all the strings that IDA found.
Pressing ``enter`` in one of the strings, IDA shows us the memory where it was
found.

{% call mainfig('string_address.png') %}
Read-only [.rodata](https://en.wikipedia.org/wiki/Data_segment)
section where the strings of the game are stored: the
ones that we found with ``strings``, the ones that we saw running the program
and some others that we did not spot like ``"date +%s"``
{% endcall %}

## Guessing Functions from their Arguments

From there we can go to the locations of the binary that have a reference
to each string selecting the label (``aMonsterSAttack``) and pressing ``x``.

{% call mainfig('monster_attack_loc.png') %}
Hint: the ``mov     eax, 0`` before the call; the calling
convention says that the *variadic* function (like ``printf``) will
receive 0 floating point arguments.
{% endcall %}

The de facto
[calling convention](https://en.wikipedia.org/wiki/X86_calling_conventions)
in Linux 64 bits says that the first six
parameters are passed to the callee in registers ``rdi``, ``rsi``,
``rdx``, ``rcx``, ``r8``, ``r9`` (``xmm0``, ``xmm1``, ``xmm2``, ``xmm3``,
``xmm4``, ``xmm5``, ``xmm6`` and ``xmm7`` for floating point arguments).

With this we could assume that the next call after referencing
``aMonsterSAttack`` is a ``printf``-like function.


This is what we got:

{% call mainfig('monster_attack_loc_labeled.png') %}
Press ``n`` on top of a label we can change the name; press ``:``
we can add a comment on that line.
{% endcall %}

{% call marginfig('second_indirection.png') %}
To get the pointer to the players name the code does a *second* indirection:
possibly we are dealing with an attribute of a ``struct``.
{% endcall %}


``printf``-like function call with four arguments: the format string, the
name of the monster, name of the player and the damage.

What about the code that *reads* the player's name?

{{ mainfig('enter_player_name_loc.png') }}

Three calls happen after the print of the message. One of them should be
a ``read`` like function:

 - ``sub_4117C0``: unlikely, it only receives one parameter (``cs:off_6CC840``)
 - ``sub_400D16``: more likely, it receives a buffer and a size (``100h``)
 - ``sub_425850``: unlikely, it receives the buffer but not the size because
the size previously set in ``esi`` is
[not preserved](https://wiki.osdev.org/System_V_ABI)
between calls so it could
be garbage. Besides, ``sub_425850`` is not call when the user needs to select an
option in the main menu so it is unlikely that it is a ``read`` like.

{% call marginnotes() %}
If you said, *ey!*, may be there is a buffer overflow there. No.
Double click in ``sbuf`` to go to the *Stack view* and right click on ``sbuf``
and select ``Convert to Array``: based on IDA analysis there are at least
264 bytes (greater than ``100h`` o 256). {% endcall %}

Ok, if the second call (``sub_400D16``) is ``fgets?``,
the third should be a ``strdup?`` call.

Why?

The name is stored in the stack so the only way to make it to
survive is copying it to the heap or other global place. ``strdup`` will do
the trick.

{% call mainfig('enter_player_name_loc_labeled.png') %}
The last instruction marks that *the user was created* in a global variable.

``cs:is_user_created`` is tested against 0 in several
places to check if the user was created or not.
{% endcall %}

## Keep Guessing

The entire block configures the hypothetical ``player_struct`` setting
the name of the player at the offset 8 (like we saw before) and the
lives of the player at the offset 0:

```asm
mov     byte ptr [rax], 10h
mov     rax, [rbp+player_struct] ; player's lives (= 16)
```

{% call marginfig('delete_player_free.png') %}
No, there are not memory leaks here. The *delete player* function is a good boy.
{% endcall %}

If this is correct, ``mov     cs:player_struct, rax`` saves the *pointer*
to the struct globally, struct allocated at the begin of the block.

{{ mainfig('enter_player_name_loc_struct_labeled.png') }}

The key note here is that *we don't know*. We can just guess.

But guessing is good, and the guess in one side may give use the context to
understand other pieces of code.

## Magic Numbers

The begin of the game gives us more clues

{% call mainfig('game_start_loc.png') %}
``time`` and ``sys_alarm`` are wrappers of *syscalls*. In Linux a syscall
call is made setting the *syscall number* in the ``eax`` register and calling
``syscall`` instruction. IDA detects those quite well.
<br />
Full of shifts, multiplications and *magic numbers* like
``834E0B5Fh`` and ``41C64E6Dh``? That looks like a *congruent* PRNG.
That is how I found ``srand``.
{% endcall %}


I bet this is something like ``srand(time(NULL) >> 8)``.

{{ marginfig('rand_loc.png') }}

We found ``srand``, and we found the *global state* of the PRNG at ``6CC100h``,
now we can find who *updates* that global state: the guy will probably be
the ``rand`` function.

## Nice Findings

{{ marginfig('get_time_loc.png') }}

The *get time* function is quite short: it is just a call to the ``date`` program
and no command injection is possible.

However this gives us two pieces of information:

 - we know the time of the remote machine: we can break things
like ``srand(time())``.
 - we know the position of the ``system`` function (``0x411070``) and a
``call`` to it (``0x401258``).


The *player attack* code has a preamble of several operations but after that,
there is a interesting section.

{{ marginfig('player_attack_loc.png') }}

It choose a monster name and if it is ``NULL``, jumps to a block that copy
the player's name into the heap and *stores* it in the array that initially
has the names of the *monsters*.

Then it is passed as the first argument of a indirect call. Initially the only
function that should be called is ``monster_attack`` but we may point to somewhere.

Interesting things:

 - ``monster_attack`` does not free its argument so we may have a **memory leak**
which content is controlled by us.
 - ``monster_attack`` does free the ``player_struct`` but it doesn't set
``is_user_created`` to 0 so we may have a **double free** if we call
``delete_player`` later.
 - unfortunately ``monster_attack`` may return 0 which makes ``player_attack``
to call ``exit()``; only under a specific path ``monster_attack`` returns 1.

Something similar happen in ``monster_defense`` and ``roar`` functions with
the exception that ``roar`` returns always 0.

## Next Steps

We found a **memory leak** and a **double free** but we don't have
a real crash. We just reviewed the code.

We need to keep exploring this, here are some ideas for a future post:

 - [Valgrind](http://valgrind.org/): we could see if there are more
memory corruptions. Play with [AFL](http://lcamtuf.coredump.cx/afl/) perhaps?
 - [Angr](https://angr.io/): trigger the leaking ``strdup`` is not trivial,
we may use a symbolic execution for that.
 - Heap attack: after all, we need to know how the heap management works and
plan the attack.
