---
layout: post
title: "Hanoi File System"
tags: [kernel, file system, fuse]
inline_default_language: cpp
---

Yeup, why not implement the classic
[Tower of Hanoi](https://en.wikipedia.org/wiki/Tower_of_Hanoi) using
folders as the towers and files as the discs?

Using [FUSE](https://github.com/libfuse/libfuse) we can implement
a *file system* that can enforce the rules of the puzzle.

 - each file would have a *size* that represent the disc's size
 - one can move a file from one folder to another if the file is
   the smallest of the files of both folders

Sounds fun?<!--more-->

## Code overview

Three FUSE hooks are required for this:

 - `getattr` to define which entries are files and which are folders
 - `readdir` to list which entries are in which folder.
 - `rename` to enforce the rules of Tower of Hanoi.

These plus some extra bits are implemented in
[hanoifs.c](https://github.com/eldipa/hanoifs/blob/master/hanoifs.c).

Behind scenes, the logic of the game is handled by
[hanoi.c](https://github.com/eldipa/hanoifs/blob/master/hanoi.c).

To keep the code simple, each tower (peg) is represented by a bit stack:
a bit vector with a LIFO discipline, coded at
[bitstack.c](https://github.com/eldipa/hanoifs/blob/master/bitstack.c).


## Hanoi FS

Once compiled, you can mount the puzzle running `hanoifs`

```shell
$ ./hanoifs mnt/
```

Within the mounted file system the folders represent the
*towers* of Hanoi

```shell
$ ls -lah mnt/
total 4.0K
drwxr-xr-x 5 root root    0 Jan  1  1970 .
drwxr-xr-x <...> ..
drwxr-xr-x 2 root root    0 Jan  1  1970 A
drwxr-xr-x 2 root root    0 Jan  1  1970 B
drwxr-xr-x 2 root root    0 Jan  1  1970 C
```

Inside each folder there are the files that represent the *discs*
of the game.

Initially all the files (discs) are in the first folder (tower).

```shell
$ ls -lah mnt/A
mnt/A:
total 0
drwxr-xr-x 2 root root 0 Jan  1  1970 .
drwxr-xr-x 5 root root 0 Jan  1  1970 ..
-r--r--r-- 1 root root 1 Jan  1  1970 0
-r--r--r-- 1 root root 2 Jan  1  1970 1
-r--r--r-- 1 root root 4 Jan  1  1970 2
```

The traditional `mv` is used to move the discs. Under the hood any
program that issue the `rename` syscall will be allowed.

```shell
$ mv mnt/A/0 mnt/C
```

Not all the movements are possible however;
the movements are restricted following the rules of the puzzle.

You cannot move a disc that is not in the top of its tower (it is not
the smallest file); you cannot move a disc to a tower on top
of a disc smaller either.

```shell
$ mv mnt/A/2 mnt/B
mv: cannot move 'mnt/A/2' to 'mnt/B/2': Permission denied

$ mv mnt/A/1 mnt/C
mv: cannot move 'mnt/A/1' to 'mnt/C/1': Permission denied
```

## Puzzle solution

<!--
$ mv mnt/C/0 mnt/A/0
-->

The goal of the Hanoi Towers is to move all the discs to the latest
tower (the latest folder, `C` in our case).

Here is the complete solution:

```shell
$ mv mnt/A/0 mnt/C
$ mv mnt/A/1 mnt/B
$ mv mnt/C/0 mnt/B
$ mv mnt/A/2 mnt/C
$ mv mnt/B/0 mnt/A
$ mv mnt/B/1 mnt/C
$ mv mnt/A/0 mnt/C
```

Once completed, a special file will appear at the root:

```shell
$ ls mnt/           # byexample: +norm-ws
 A   B   C  'you win'
```


<!--
$ fusermount -u mnt     # byexample: -skip +pass
-->
