---
layout: post
title: "Control Group - Hierarchical Organization"
tags: [linux, kernel, cgroup]
artifacts:
 - cgroup-hierarchical-org.svg
 - cgroup-states.svg
---

{% call margindiag('cgroup-states.svg', 'already-exists', indexonly=True) %}
```
Not of use.
```
{% endcall %}

Control group or `cgroup` is a mechanism to distribute and enforce limits
over the resources of the system.

It was introduced in Linux kernel around 2007 but its complexity leaded
to inconsistent behaviour and hard adoption.

Fast forwarding 9 years, in kernel 4.5 a rewrite of `cgroup` revamp the
idea, making it simpler and consistent.

This post focus in the organization of cgroups and it is the first
of a 3-posts series about `cgroup` in its new `v2` version.

In the next posts
we will see how the
[resources are distributed](/articles/2022/04/24/Linux-Control-Group-Resource-Distribution.html)
among the cgroups and
[which constraints](/articles/2022/04/27/Linux-Control-Group-No-Internal-Process-Constraint.html)
do we have.


<!--more-->

<!--
$ test -d /sys/fs/cgroup/test && echo "cgroup test/ already created!"     # byexample: +fail-fast
-->

## Overview of `cgroup` organization

{% call marginnotes() %}
**Notation:** I will write `cgroup` to denote the Control Group
implementation or hierarchy while I will write cgroup or cgroups to
refer about one or more groups in particular.
{% endcall %}

`cgroup` can be split into two components: the *core* which mandates how
the cgroups, processes and controllers are organized and the *resource
controllers* which do the real resource distribution and enforce limits.

In this post I'll focus on the core only.

In the `v1` version, the `cgroup` system supported multiple hierarchies of
cgroups and processes but this flexibility didn't pay off.

In v2, `cgroup` has a single hierarchy where all the cgroups, processes
and controllers live and that's what we are going to explore here.

Let's get into!

### Mount point

To access the control interface of `cgroup` we need to have mounted
the (pseudo) file system.

```shell
$ mount | grep cgroup                               # byexample: +fail-fast
cgroup2 on /sys/fs/cgroup type cgroup2 (<...>)
```

In my case it is mounted on `/sys/fs/cgroup`; in some other distros it
is mounted under `/sys/fs/cgroup/unified`: just check where the (pseudo)
`cgroup2` file system is mounted.


### Creating new cgroups

A hierarchy is divided into cgroups and those into more sub cgroups.

These can be easily created just creating subfolders inside the mount
point.

```shell
$ cd /sys/fs/cgroup
$ mkdir -p test

$ ls -1 test/
<...>
cgroup.procs
<...>
cgroup.threads
cgroup.type
<...>
```

`cgroup.procs` lists the processes' ids that belongs to
the `test/` cgroup and, as you may guessed, `cgroup.threads` lists the
threads' ids of the processes in the cgroup.

No process is in my `test/` cgroup so both files are empty.

```shell
$ cat test/cgroup.procs

$ cat test/cgroup.threads
```

At the moment (kernel 5.17) there is no limit on how much nested a
cgroup can be: we can create as many (sub) cgroups as we may please.

```shell
$ mkdir -p test/cg1
$ mkdir -p test/cg2
```

## `domain` cgroups

The file `cgroup.type` says which kind of cgroup we have:

```shell
$ cat test/cgroup.type
domain

$ cat test/cg1/cgroup.type
domain

$ cat test/cg2/cgroup.type
domain
```

A cgroup that operates with processes is called a *domain* and it is
the default type for each newly created cgroup.

{% call marginnotes() %}
The term *slice* is borrowed from `systemd`: `systemd` uses `cgroup` to
manage the resources of processes and names `.slice` the files to
configure the resource distribution.
{% endcall %}

It is our main way to organize processes into different domains to
assign them different amounts of a resource, different *slices* of the
cake.


## `domain threaded` and `threaded` cgroups

However there are some resources that still make sense to distribute them even
further, at the thread level.

In these cases we can turn one *normal* `domain` into a `domain threaded`.

{% call marginnotes() %}
**Summary:** a `domain` or `domain threaded` are `cgroups` that operate at process
level while `threaded cgroups` operates at thread level.
{% endcall %}

The domain threaded still operates at the process level but further
divisions are for *partitioning the threads* of the processes in
the domain.

These divisions are neither normal `domain` nor `domain threaded`,
these are `threaded` cgroups.

Let's create first a few normal `domain`s:

```shell
$ mkdir -p test/cg1/t1
$ cat test/cg1/t1/cgroup.type
domain

$ mkdir -p test/cg1/t2
$ cat test/cg1/t2/cgroup.type
domain
```

Now we turn one of the domains into a `threaded` cgroup and that will
automatically turn *its parent* into a `domain threaded`:

```shell
$ # The parent cgroup, before
$ cat test/cg1/cgroup.type
domain

$ echo "threaded" > test/cg1/t1/cgroup.type
$ cat test/cg1/t1/cgroup.type
threaded

$ # The parent cgroup, after
$ cat test/cg1/cgroup.type
domain threaded
```

While we can still use `test/cg1/` to control the resources of the processes
that belong to the group, we can now use `test/cg1/t1/` and
`test/cg1/t2/` to distribute the resources differently among the
*threads* of the processes.

Of course this is possible only if the resource controller supports such
distribution, if it is meaningful.

A resource controller that can distribute the resource among threads is
a *thread controller*. A resource controller that operates only at the
process level is a *domain controller*.

A main difference with `cgroup v1` is that in `v2` all the threads of
a process belong to the *same* domain and hence they are subject to the
control of a domain controller.

We can distribute the resources even further creating `threaded`
partitions but all of them are inside the *same* `domain threaded` group.

In `v1` the threads of a process
could live in a different, totally unrelated part of the hierarchy
which made the implementation of the controllers much complex.



## `domain invalid`

We made `test/cg1/t1/` into a `threaded` and that turned its parent
`test/cg1/` into a `domain threaded`.

What happen with the sibling of `test/cg1/t1/`, the `test/cg1/t2/`
cgroup?


```shell
$ # The parent cgroup
$ cat test/cg1/cgroup.type
domain threaded

$ # The threaded cgroup
$ cat test/cg1/t1/cgroup.type
threaded

$ # Its sibling
$ cat test/cg1/t2/cgroup.type
domain invalid
```

`test/cg1/t2/` is in an invalid state because we said that any
subfolder of a `domain threaded` must be of the `threaded` kind.

By default `test/cg1/t2/` was `domain` so this is incompatible.

The same would happen if we create a new cgroup, because the default is
of type `domain`, the resulting will be invalid too.

```shell
$ # The parent cgroup
$ cat test/cg1/cgroup.type
domain threaded

$ # Create a new cgroup
$ mkdir test/cg1/t3

$ # The default type is always 'domain' so it makes
$ # it invalid here inside of the 'domain threaded'
$ cat test/cg1/t3/cgroup.type
domain invalid
```

We can turn these invalid domains into `threaded` cgroups just writing
in their `cgroup.type` the value `threaded`.

```shell
$ echo 'threaded' > test/cg1/t2/cgroup.type
$ cat test/cg1/t2/cgroup.type
threaded
```

## Life time of a `domain threaded`

As we saw earlier, a `domain threaded` can be created by making one of its
(sub) cgroups a `threaded` cgroup.

It is *not* possible to write `domain threaded` neither to change the
type of a `domain invalid` nor to change a `domain` into a `domain
threaded`.

```shell
$ echo 'domain threaded' > test/cg1/t3/cgroup.type
bash: echo: write error: Invalid argument

$ echo 'domain threaded' > test/cg2/cgroup.type
bash: echo: write error: Invalid argument

$ cat test/cg1/t3/cgroup.type
domain invalid

$ cat test/cg2/cgroup.type
domain
```

The only way to get a `domain threaded` is to have a (sub) cgroup of
`threaded` type.

The same restriction works on the way back: to make
a `domain threaded` back to a `domain` you must delete the (sub) `threaded` cgroups
(changing them to `domain` does not work).

```shell
$ # this doen't work
$ echo 'domain' > test/cg1/t1/cgroup.type
<...>write error: Invalid argument

$ rmdir test/cg1/t1
$ rmdir test/cg1/t2

$ # back to "normal" domain
$ cat test/cg1/cgroup.type
domain

$ # not longer domain invalid
$ cat test/cg1/t3/cgroup.type
domain
```

## cgroup's type transitions

{% call maindiag('cgroup-states.svg', 'plantuml') %}
```plantuml
hide empty description
hide members
hide circle
skinparam backgroundColor transparent

state "_" as X {
    state "domain" as D
    state "domain invalid" as DI
    state "domain threaded" as DT
    state "threaded" as T
}


[*] -right-> D : call mkdir
D --> DI
D -up-> DT
DT -down-> D : when no child is\nthreaded
D -> T
DI --> D : when parent\nnot longer is\ndomain threaded
DI --> T

X -left-> [*] : call rmdir
```
A summary of all the possible types that a cgroup can have and the
possible transitions from one type to another.

All the transitions requires a direct action from the user like `rmdir`
a folder to delete a cgroup or writing `"threaded"` in `cgroup.type`
to turn that `cgroup` into a `threaded` cgroup.

There are 2 exceptions: a `domain` goes to `domain invalid` or to
`domain threaded` based on the type of its parent and children.
The same with the reverse transitions.
{% endcall %}


## `cgroup` hierarchical organization

{% call margindiag('cgroup-hierarchical-org.svg', 'plantuml') %}
```plantuml
hide empty description
hide members
hide circle
skinparam backgroundColor transparent

domain "1" *-- "0..*" domain

domain "1" *-- "0..*" "domain threaded"

"domain threaded" "1" *-- "1..*" "threaded"

root *- "0..*" domain
root *- "0..*" "domain threaded"
root *- "0..*" threaded
```
<br />
Each box represents a cgroup *type* and the arrows
represents which cgroup type can *contain* which (sub) `cgroup`.
For example one `domain threaded` can have one or more `threaded`
cgroups.

*Root* is a very special cgroup which can contain any other type of
cgroup: `domain`, `domain threaded` and `threaded`.

The diagram follows the semantics of an UML diagram.
{% endcall %}

We can summarize all the above in the following:

 - A domain can be divided into more (sub) `domains` just creating more
   (sub) cgroups with `mkdir`.
 - A cgroup can be turned into a `threaded` cgroup;
   its parent cgroup is automatically turned into a `domain threaded`.
 - If a `domain threaded` is left without `threaded` cgroups,
   automatically changes to `domain`.
 - A `domain threaded` is divided into `threaded` cgroups and these can
   be further divided in more (sub) `threaded` cgroups.

The mount point or *root* is a special cgroup that works as a `domain` but also
as a `domain threaded` so it can have (sub) cgroups of `domain` type and
of `threaded` type as well.

## Further reading

We mentioned `mount` but nothing else. `cgroup v2` has a few options for
the `mount` call but I didn't covered them.

The kernel also has a few parameters to disable certain controllers but
I totally skipped them :)

In general, the default setting of your distro should be fine.


## Next stuff

We shown how the `cgroup` hierarchy is organized. In the next post
we will see how the
[resources are distributed](/articles/2022/04/24/Linux-Control-Group-Resource-Distribution.html)
among the cgroups and
[which constraints](/articles/2022/04/27/Linux-Control-Group-No-Internal-Process-Constraint.html)
do we have.



<!--
Delete recursively every cgroup (folder) from the leaves to the
root.

$ cd /sys/fs/cgroup/                                              # byexample: +pass -skip
$ rmdir $(find /sys/fs/cgroup/test/ -type d | sort -r)         # byexample: +pass -skip
-->
