---
layout: post
title: "Linux Control Group - Organization"
tags: [linux, kernel, cgroup, HIDDEN]
artifacts:
 - cgroup-hierarchical-org.svg
 - cgroup-states.svg
---


### Mount point

To access the control interface of `cgroup` we need to have mounted
the (pseudo) file system.

```shell
$ mount | grep cgroup                               # byexample: +fail-fast
cgroup2 on /sys/fs/cgroup type cgroup2 (<...>)
```

{% call marginnotes() %}
There are some kernel parameters that enable/disable parts of `cgroup` and
there are some options for `mount` to tweak it too.

The defaults of your distro should be fine.
{% endcall %}

In my case it is mounted on `/sys/fs/cgroup`.

It is possible to have mounted the version 1 but it is
deprecated in flavor of the version 2 so if you are running an updated
system (Debian 11 or Fedora) you probably will not have troubles.


### Domains

A `cgroup` that operates with processes is called, by default, a *domain*.

These can be easily created just creating subfolders inside the mount
point.

```shell
$ cd /sys/fs/cgroup
$ mkdir -p testing

$ ls -1 testing/
<...>
cgroup.procs
<...>
cgroup.threads
cgroup.type
<...>
```

The file `cgroup.type` says which kind of `cgroup` we have (a domain in
this case)

```shell
$ cat testing/cgroup.type
domain
```
`cgroup.procs` lists the processes' ids that belongs to
the `cgroup` and, as you may guessed, `cgroup.threads` lists the
threads' ids of the processes in the `cgroup`.

No process is in my `testing/` `cgroup` so both listings are empty.

```shell
$ cat testing/cgroup.procs

$ cat testing/cgroup.threads
```

At the moment (kernel 5.17) there is no limit on how much nested a
`cgroup` can be: we can create as many (sub) `cgroups` as we may please.

```shell
$ mkdir -p testing/cg1
$ cat testing/cg1/cgroup.type
domain

$ mkdir -p testing/cg2
$ cat testing/cg2/cgroup.type
domain
```

### Domains Threaded and `threaded cgroups`

A main difference with `cgroup v1` is that in `v2` we distribute the
resources at the process level, with *process granularity*.

However there are some resources that still make sense to distribute them even
further, at the thread level.

In these cases we can turn one *normal* domain into a *domain threaded*.

{% call marginnotes() %}
**Summary:** a `domain` or `domain threaded` are `cgroups` that operate at process
level while `threaded cgroups` operates at thread level.
{% endcall %}

The domain threaded still operates at the process level but further
divisions are for *partitioning the threads* of the processes in
the domain threads.

These divisions are neither normal domains nor domains threaded,
these are *threaded cgroups*.

Let's create first a few normal domains:

```shell
$ mkdir -p testing/cg1/t1
$ cat testing/cg1/t1/cgroup.type
domain

$ mkdir -p testing/cg1/t2
$ cat testing/cg1/t2/cgroup.type
domain
```

Now we turn one of the domains into a *threaded cgroup* and that will
automatically turn *its parent* into a *domain threaded*:

```shell
$ # The parent cgroup, before
$ cat testing/cg1/cgroup.type
domain

$ echo "threaded" > testing/cg1/t1/cgroup.type
$ cat testing/cg1/t1/cgroup.type
threaded

$ # The parent cgroup, after
$ cat testing/cg1/cgroup.type
domain threaded
```

### Domain invalid

We made `testing/cg1/t1` into a `threaded` and that turned its parent
`testing/cg1` into a `domain threaded`.

What happen with the sibling of `testing/cg1/t1`, the `testing/cg1/t2`
cgroup?


```shell
$ # The parent cgroup
$ cat testing/cg1/cgroup.type
domain threaded

$ # The threaded cgroup
$ cat testing/cg1/t1/cgroup.type
threaded

$ # Its sibling
$ cat testing/cg1/t2/cgroup.type
domain invalid
```

`testing/cg1/t2` is in an invalid state because we said that any
subfolder of a `domain threaded` must be of the `threaded` kind.

By default `testing/cg1/t2` was `domain` so this is incompatible.

The same would happen if we create a new cgroup, because the default is
of type `domain`, the resulting will be invalid too.

```shell
$ # The parent cgroup
$ cat testing/cg1/cgroup.type
domain threaded

$ # Create a new cgroup
$ mkdir testing/cg1/t3

$ # The default type is always 'domain' so it makes
$ # it invalid here inside of the 'domain threaded'
$ cat testing/cg1/t3/cgroup.type
domain invalid
```

We can turn these invalid domains into `threaded` cgroups just writing
in their `cgroup.type` the value `threaded`.

```shell
$ echo 'threaded' > testing/cg1/t2/cgroup.type
$ cat testing/cg1/t2/cgroup.type
threaded
```

### Life time of a `domain threaded`

As we saw earlier, a `domain threaded` can be created by making one of its
(sub) `cgroups` into a `threaded cgroup`.

It is *not* possible to write `domain threaded` neither to change the
type of a `domain invalid` nor to change a `domain` into a `domain
threaded`.

```shell
$ echo 'domain threaded' > testing/cg1/t3/cgroup.type
bash: echo: write error: Invalid argument

$ echo 'domain threaded' > testing/cg2/cgroup.type
bash: echo: write error: Invalid argument

$ cat testing/cg1/t3/cgroup.type
domain invalid

$ cat testing/cg2/cgroup.type
domain
```

The `domain threaded` type is a kind of condition or state: we cannot
change it because it reflects the state of its (sub) `cgroups` (if they
are or not `threaded cgroups`)

### `cgroup` states

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
A summary of all the possible types that a `cgroup` can have and the
possible transitions from one type to another.

All the transitions requires a direct action from the user like `rmdir`
a folder to delete a `cgroup` or writing `"threaded"` in `cgroup.type`
to turn that `cgroup` into a `threaded cgroup`.

There are 2 exceptions: a `domain` goes to `domain invalid` or to
`domain threaded` based on the type of its parent and children.
The same with the reverse transitions.
{% endcall %}


### `cgroup` hierarchical organization

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
Each box represents a `cgroup` *type* and the arrows
represents which `cgroup` type can *contain* which (sub) `cgroup`.
For example one `domain threaded` can have one or more `threaded
cgroups`.

Root is a very special `cgroup` which can contain any other type of
`cgroup`.

The diagram follows the semantics of an UML diagram.
{% endcall %}

We can summarize all the above in the following:

 - A domain can be divided into more (sub) `domains` just creating more
   (sub) `cgroups` with `mkdir`.
 - A `cgroup` can be turned into a `threaded cgroup`;
   its parent `cgroup` is automatically turned into a `domain threaded`.
 - If a `domain threaded` is left without `threaded cgroups`,
   automatically changes to `domain`.
 - A `domain threaded` is divided into `threaded cgroups` and these can
   be further divided in more (sub) `threaded cgroups`.

The mount point or *root* is a special `cgroup` that works as a `domain` but also
as a `domain threaded` so it can have (sub) `cgroups` of `domain` type and
of `threaded` type as well.




<!--
Delete recursively every cgroup (folder) from the leaves to the
root.

$ cd /sys/fs/cgroup/                                              # byexample: +pass -skip
$ rmdir $(find /sys/fs/cgroup/testing/ -type d | sort -r)         # byexample: +pass -skip
-->
