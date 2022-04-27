---
layout: post
title: "Control Group - No Internal Process Constraint"
tags: [linux, kernel, cgroup]
artifacts:
 - starting.svg
 - testing_with_proc_in_cg1.svg
 - testing_with_proc_in_cg1_simple.svg
 - testing_with_proc_in_cg1_and_cg2.svg
 - testing_with_proc_in_cg1_and_cg2_alt.svg
 - restart.svg
 - proc-move-in-no-internal-process.svg
 - enable-controller-in-no-internal-process.svg
---


<!--
$ test -d /sys/fs/cgroup/test && echo "cgroup test/ already created!"     # byexample: +fail-fast
-->

{% call marginnotes() %}
Previous posts: [hierarchical organization](/articles/2022/04/23/Linux-Control-Group-Hierarchical-Organization.html)
<br />
and [resources distribution](/articles/2022/04/24/Linux-Control-Group-Resource-Distribution.html)
{% endcall %}

In the previous post we saw that we cannot enable a controller or add a
process to a cgroup freely. That would make the implementation of
each controller harder.

In `v2` the hierarchy is subject to the *no internal process*
constraint which ensures that a controller will have all the processes
in leaves of its domain tree.

This is the last of a 3-post series about `cgroup` and certainly, this
*no internal process* constraint was the hardest to understand.
<!--more-->

Let's create the following `cgroup` hierarchy to play with. Notice how we enable the
resource controller `+cpu` on
`test/`'s and `test/cg1/`'s subtrees but not on `test/cg2/`'s.

{% call marginnotes() %}
```shell
$ cd /sys/fs/cgroup
$ mkdir -p test/cg1/cg1_1
$ mkdir -p test/cg1/cg1_2
$ mkdir -p test/cg2/cg2_1
$ mkdir -p test/cg2/cg2_2

$ echo '+cpu' > test/cgroup.subtree_control
$ echo '+cpu' > test/cg1/cgroup.subtree_control
```
{% endcall %}

{% call maindiag('starting.svg', 'dot') %}
```dot
digraph CG  {
    bgcolor="transparent";

    // Controllers
    node [shape=none] {
        "cpu" [label="cpu ≤ max", group=lvl0];
        "cpu_cg1" [label="cpu ≤ max", group=lvl1];
        "cpu_cg2" [label="cpu ≤ max", group=lvl1];
        "cpu_cg1_1" [label="cpu ≤ max", group=lvl9];
        "cpu_cg1_2" [label="cpu ≤ max", group=lvl9];
    }

    // Domains
    node [shape=box, color="#000000", style=solid] {
        "test" [label="test/", group=lvl0];
        "cg1" [label="cg1/", group=lvl1];
        "cg2" [label="cg2/", group=lvl1];
        "cg1_1" [label="cg1_1/", group=lvl2];
        "cg1_2" [label="cg1_2/", group=lvl2];
        "cg2_1" [label="cg2_1/", group=lvl2];
        "cg2_2" [label="cg2_2/", group=lvl2];
    }

    // Processes
    node [shape=circle,  color="#880000", style=bold, width=0.5, fixedsize=true] {
    }

    // Failed processes
    node [shape=circle,  color="#880000", style="dashed,bold", width=0.5, fixedsize=true] {
    }

    // Cgroups at top
    {rank=min; cpu cpu_cg1}
    {rank=same; test cg1 cg1_1 cpu_cg1_1}

    {rank=same; cpu_cg2  cg1_2 cpu_cg1_2}
    {rank=same; cg2 cg2_1}
    {rank=max; cg2_2}

    cpu -> test [style=dashed, arrowtail=dot, dir=back, color="#620099"];
    cpu_cg1 -> cg1 [style=dashed, arrowtail=dot, dir=back, color="#620099"];
    cpu_cg2 -> cg2 [style=dashed, arrowtail=dot, dir=back, color="#620099"];

    test -> cg1;
    test -> cg2;

    cg1 -> cg1_1;
    cg1 -> cg1_2;

    cg1_1 -> cpu_cg1_1  [style=dashed, arrowhead=dot, color="#620099"];
    cg1_2 -> cpu_cg1_2 [style=dashed, arrowhead=dot, color="#620099"];

    cg2 -> cg2_1;
    cg2 -> cg2_2;

    cg1 -> cg2 [style=invis];
    cg1_1 -> cg1_2 [style=invis];
    cg1_2 -> cg2_1 [style=invis];
    cg2_1 -> cg2_2 [style=invis];
}
```
{% endcall %}

Let's create a long running process and let's move it to one cgroup. In
fact, let's try *different cgroups* and see what happen:

```shell
$ sleep 1000 &
[<job-id-proc1>] <pid-proc1>

$ echo <pid-proc1> > test/cgroup.procs            # byexample: +paste
$ echo <pid-proc1> > cgroup.procs         # byexample: +paste

$ echo <pid-proc1> > test/cg1/cgroup.procs        # byexample: +paste
$ echo <pid-proc1> > cgroup.procs         # byexample: +paste

$ echo <pid-proc1> > test/cg1/cg1_1/cgroup.procs        # byexample: +paste
$ echo <pid-proc1> > cgroup.procs               # byexample: +paste

$ echo <pid-proc1> > test/cg2/cg2_1/cgroup.procs        # byexample: +paste
$ echo <pid-proc1> > cgroup.procs               # byexample: +paste
```

The process could be moved to `test/`, `test/cg1/`, `test/cg1/cg1_1/`
and `test/cg2/cg2_1/` without problems.

But you may wonder, what is the need of `echo <pid-proc1> >
../cgroup.procs1`? Why after moving the process to a cgroup I had to
move it to the *root before move it again* to another cgroup?

The hierarchy is *empty* so the resource controller is not acting on any
process yet. Once a process is added to one of the cgroups the *"no
internal process" constraint* enters in action.

Let me show you.

## Adding a process under the *"no internal process" constraint*

I will move the `sleep` process to `test/cg1/` and then move
it again to `test/cg1/cg1_1/` as before *but* without moving it to the root in
between.


```shell
$ echo <pid-proc1> > test/cg1/cgroup.procs        # byexample: +paste

$ echo <pid-proc1> > test/cg1/cg1_1/cgroup.procs        # byexample: +paste
<...>write error: Operation not supported
```

Okay, it seems that we cannot move our process after all!

Is because we cannot move it **from** where it is or because we cannot move
it **to** where we want?

We could move it outside so it is likely that the problem is that we
cannot move it **to** `test/cg1/cg1_1/`.

Let's try with another process:


{% call margindiag('testing_with_proc_in_cg1.svg', 'dot') %}
```dot
digraph CG  {
    bgcolor="transparent";

    // Controllers
    node [shape=none] {
        "cpu" [label="cpu ≤ max", group=lvl0];
        "cpu_cg1" [label="cpu ≤ max", group=lvl1];
        "cpu_cg1_1" [label="cpu ≤ max", group=lvl9];
        "cpu_cg1_2" [label="cpu ≤ max", group=lvl9];
    }

    // Domains
    node [shape=box, color="#000000", style=solid] {
        "test" [label="test/", group=lvl0];
        "cg1" [label="cg1/", group=lvl1];
        "cg1_1" [label="cg1_1/", group=lvl2];
        "cg1_2" [label="cg1_2/", group=lvl2];
    }

    // Processes
    node [shape=circle,  color="#880000", style=bold, width=0.5, fixedsize=true] {
        "p1" [label="p1", group=lvl1];
        "p2" [label="p2", group=lvl1];
    }

    // Failed processes
    node [shape=circle,  color="#880000", style="dashed,bold", width=0.5, fixedsize=true] {
    }

    // Error messages
    node [shape=underline,  color="#880000", style="dashed,bold", fixedsize=false] {
        "NotSupp1" [label="NotSup", group=lvl2];
        "NotSupp2" [label="NotSup", group=lvl2];
        "Busy1" [label="Busy", group=lvl0];
    }

    // Cgroups at top
    {rank=min; cpu cpu_cg1}
    {rank=same; test cg1 cg1_1 cpu_cg1_1}

    {rank=same; p1 p2 NotSupp1}
    {rank=same; cg1_2 cpu_cg1_2}
    {rank=max; NotSupp2}

    cpu -> test [style=dashed, arrowtail=dot, dir=back, color="#620099"];
    cpu_cg1 -> cg1 [style=dashed, arrowtail=dot, dir=back, color="#620099"];

    test -> cg1;

    test -> Busy1  [style=dashed, arrowhead=none, color="#880000"];

    cg1 -> cg1_1;
    cg1 -> cg1_2;

    cg1 -> p1;
    cg1 -> p2;

    cg1_1 -> cpu_cg1_1  [style=dashed, arrowhead=dot, color="#620099"];
    cg1_2 -> cpu_cg1_2 [style=dashed, arrowhead=dot, color="#620099"];

    cg1_1 -> NotSupp1  [style=dashed, arrowhead=none, color="#880000"];
    cg1_2 -> NotSupp2  [style=dashed, arrowhead=none, color="#880000"];

    NotSupp1 -> cg1_2 [style=invis];
}
```
Diagram that shows the errors got when tried to add process 2 (`p2`) to
different cgroups. Only to `test/cg1/` succeeded.
{% endcall %}

```shell
$ sleep 1000 &
[<job-id-proc2>] <pid-proc2>

$ echo <pid-proc2> > test/cg1/cg1_1/cgroup.procs        # byexample: +paste
<...>write error: Operation not supported

$ echo <pid-proc2> > test/cg1/cg1_2/cgroup.procs        # byexample: +paste
<...>write error: Operation not supported

$ echo <pid-proc2> > test/cgroup.procs                  # byexample: +paste
<...>write error: Device or resource busy

$ echo <pid-proc2> > test/cg1/cgroup.procs              # byexample: +paste
```

Interesting!

Once we put the first process in `test/cg1/` we *locked* the `test/cg1/`
*subtree* and all its *ancestors*: no process can be added to them
except exclusively to `test/cg1/` itself (well, *root* is an exception to
this).

### Sibling hierarchy

Adding a process to a hierarchy enforces us to add the rest of the
processes in the same cgroup or in different *sibling* hierarchy.


{% call maindiag('testing_with_proc_in_cg1_and_cg2.svg', 'dot') %}
```dot
digraph CG  {
    bgcolor="transparent";

    // Controllers
    node [shape=none] {
        "cpu" [label="cpu ≤ max", group=lvl0];
        "cpu_cg1" [label="cpu ≤ max", group=lvl1];
        "cpu_cg2" [label="cpu ≤ max", group=lvl1];
        "cpu_cg1_1" [label="cpu ≤ max", group=lvl9];
        "cpu_cg1_2" [label="cpu ≤ max", group=lvl9];
    }

    // Domains
    node [shape=box, color="#000000", style=solid] {
        "test" [label="test/", group=lvl0];
        "cg1" [label="cg1/", group=lvl1];
        "cg2" [label="cg2/", group=lvl1];
        "cg1_1" [label="cg1_1/", group=lvl2];
        "cg1_2" [label="cg1_2/", group=lvl2];
        "cg2_1" [label="cg2_1/", group=lvl2];
        "cg2_2" [label="cg2_2/", group=lvl2];
    }

    // Processes
    node [shape=circle,  color="#880000", style=bold, width=0.5, fixedsize=true] {
        "p1" [label="p1", group=lvl1];
        "p2" [label="p2", group=lvl1];
        "p3" [label="p3", group=lvl1];
    }

    // Failed processes
    node [shape=circle,  color="#880000", style="dashed,bold", width=0.5, fixedsize=true] {
    }

    // Error messages
    node [shape=underline,  color="#880000", style="dashed,bold", fixedsize=false] {
    }

    // Cgroups at top
    {rank=min; cpu cpu_cg1}
    {rank=same; test cg1 cg1_1 cpu_cg1_1}

    {rank=same; p1 p2}
    {rank=same; cg1_2 cpu_cg1_2}
    {rank=same; cg2 cg2_1}
    {rank=same; cpu_cg2}
    {rank=max; cg2_2}

    cpu -> test [style=dashed, arrowtail=dot, dir=back, color="#620099"];
    cpu_cg1 -> cg1 [style=dashed, arrowtail=dot, dir=back, color="#620099"];
    cpu_cg2 -> cg2 [style=dashed, arrowtail=dot, dir=back, color="#620099"];

    test -> cg1;
    test -> cg2;

    cg1 -> cg1_1;
    cg1 -> cg1_2;

    cg1 -> p1;
    cg1 -> p2;

    cg1_1 -> cpu_cg1_1  [style=dashed, arrowhead=dot, color="#620099"];
    cg1_2 -> cpu_cg1_2 [style=dashed, arrowhead=dot, color="#620099"];

    cg1_1 -> cg1_2 [style=invis];
    cg1_2 -> cg2_1 [style=invis];

    cg2 -> cg2_1;
    cg2 -> cg2_2;

    cg2 -> p3;

    p1 -> cpu_cg2 [style=invis];
    p2 -> cpu_cg2 [style=invis];

    cg1_1 -> cg1_2 [style=invis];
    cg1_2 -> cg2_1 [style=invis];
    cg2_1 -> cg2_2 [style=invis];
}
```
Add a third process to `test/cg2/`, no problem arise from.
```shell
$ sleep 1000 &
[<job-id-proc3>] <pid-proc3>

$ echo <pid-proc3> > test/cg2/cgroup.procs        # byexample: +paste
```
{% endcall %}

### How does the resource controller affect?

There is one last piece to our puzzle.

We *can* add a process to a subtree of an occupied cgroup if there are **no** resource controller
enabled on the subtree.

Take this case where we can add a processes to `test/cg2/` subtree but not to
`test/cg1/` subtree. In both cases `test/cg2/` and `test/cg1/` are already occupied but
`test/cg1/` delegated the `+cpu` to its subtree and that's what block us to add
any process there.


{% call maindiag('testing_with_proc_in_cg1_and_cg2_alt.svg', 'dot') %}
```dot
digraph CG  {
    bgcolor="transparent";

    // Controllers
    node [shape=none] {
        "cpu" [label="cpu ≤ max", group=lvl0];
        "cpu_cg1" [label="cpu ≤ max", group=lvl1];
        "cpu_cg2" [label="cpu ≤ max", group=lvl1];
        "cpu_cg1_1" [label="cpu ≤ max", group=lvl9];
        "cpu_cg1_2" [label="cpu ≤ max", group=lvl9];
    }

    // Domains
    node [shape=box, color="#000000", style=solid] {
        "test" [label="test/", group=lvl0];
        "cg1" [label="cg1/", group=lvl1];
        "cg2" [label="cg2/", group=lvl1];
        "cg1_1" [label="cg1_1/", group=lvl2];
        "cg1_2" [label="cg1_2/", group=lvl2];
        "cg2_1" [label="cg2_1/", group=lvl2];
        "cg2_2" [label="cg2_2/", group=lvl2];
    }

    // Processes
    node [shape=circle,  color="#880000", style=bold, width=0.5, fixedsize=true] {
        "p1" [label="p1", group=lvl1];
        "p2" [label="p2", group=lvl1];
        "p3" [label="p3", group=lvl1];
        "p4" [label="p4", group=lvl1];
    }

    // Failed processes
    node [shape=circle,  color="#880000", style="dashed,bold", width=0.5, fixedsize=true] {
    }

    // Error messages
    node [shape=underline,  color="#880000", style="dashed,bold", fixedsize=false] {
        "NotSupp1" [label="NotSup"];
    }

    // Cgroups at top
    {rank=min; cpu cpu_cg1}
    {rank=same; test cg1 cg1_1 cpu_cg1_1}

    {rank=same; p1 p2}
    {rank=same; cg1_2 cpu_cg1_2}
    {rank=same; cg2 cg2_1}
    {rank=same; cpu_cg2}
    {rank=max; p4}

    cpu -> test [style=dashed, arrowtail=dot, dir=back, color="#620099"];
    cpu_cg1 -> cg1 [style=dashed, arrowtail=dot, dir=back, color="#620099"];
    cpu_cg2 -> cg2 [style=dashed, arrowtail=dot, dir=back, color="#620099"];

    test -> cg1;
    test -> cg2;

    cg1 -> cg1_1;
    cg1 -> cg1_2;

    cg1 -> p1;
    cg1 -> p2;

    cg1_1 -> cpu_cg1_1  [style=dashed, arrowhead=dot, color="#620099"];
    cg1_2 -> cpu_cg1_2 [style=dashed, arrowhead=dot, color="#620099"];

    cg1_1 -> cg1_2 [style=invis];
    cg1_2 -> NotSupp1  [style=dashed, arrowhead=none, color="#880000"];
    NotSupp1 -> cg2_1 [style=invis];

    cg2 -> cg2_1;
    cg2 -> cg2_2;

    cg2 -> p3;

    p1 -> cpu_cg2 [style=invis];
    p2 -> cpu_cg2 [style=invis];

    cg1_1 -> cg1_2 [style=invis];
    cg1_2 -> cg2_1 [style=invis];
    cg2_1 -> cg2_2 [style=invis];

    cg2_2 -> p4;
}
```
Add a fourth process to `test/cg1/cg1_2`, fail and then add it
to `test/cg2/cg2_2`. The only difference that would explain why we failed
in the first cgroup is because `+cpu` controller is enabled on the
cgroup while in `test/cg2/cg2_2` is not.

```shell
$ sleep 1000 &
[<job-id-proc4>] <pid-proc4>

$ echo <pid-proc4> > test/cg1/cg1_2/cgroup.procs        # byexample: +paste
<...>write error: Operation not supported

$ echo <pid-proc4> > test/cg2/cg2_2/cgroup.procs        # byexample: +paste
```
{% endcall %}

### Flow diagram for adding a process

{% call maindiag('proc-move-in-no-internal-process.svg', 'plantuml') %}
```plantuml
!pragma useVerticalIf on
skinparam backgroundColor transparent
start

if (is root?) then (yes)
  :add the process to root;
elseif (is a non-root parent occupied?) then (yes)
  :fail with "Operation not supported";
  end
elseif (is subtree occupied?) then (yes)
  :fail with "Device or resource busy";
  end
else (no)
  :add the process to the cgroup;
endif
stop
```
Diagram of the flow for adding a process to a cgroup and the possible
outcomes that summarizes all the talked so far.

This is a sketch and by no means it is a fully specification.
{% endcall %}


## Enabling a resource control under the *"no internal process" constraint*

Let's shuffle the things resetting the resource controller and
repositioning the processes as follows:

{% call margindiag('restart.svg', 'dot') %}
```dot
digraph CG  {
    bgcolor="transparent";

    // Controllers
    node [shape=none] {
        "cpu" [label="", group=lvl0];
    }

    // Domains
    node [shape=box, color="#000000", style=solid] {
        "test" [label="test/", group=lvl0];
        "cg1" [label="cg1/", group=lvl1];
        "cg2" [label="cg2/", group=lvl1];
        "cg3" [label="cg3/", group=lvl1];
        "cg1_1" [label="cg1_1/", group=lvl2];
        "cg2_1" [label="cg2_1/", group=lvl2];
        "cg3_1" [label="cg3_1/", group=lvl2];
    }

    // Processes
    node [shape=circle,  color="#880000", style=bold, width=0.5, fixedsize=true] {
        "p1" [label="p1", group=lvl1];
        "p2" [label="p2", group=lvl1];
        "p3" [label="p3", group=lvl1];
        "p4" [label="p4", group=lvl1];
    }

    // Failed processes
    node [shape=circle,  color="#880000", style="dashed,bold", width=0.5, fixedsize=true] {
    }

    // Error messages
    node [shape=underline,  color="#880000", style="dashed,bold", fixedsize=false] {
    }

    // Cgroups at top
    {rank=min; cpu }
    {rank=same; test cg1 cg1_1 }
    {rank=same; cg2 cg2_1 }
    {rank=same; cg3 cg3_1}
    {rank=max; p4}

    cpu -> test [style=dashed, arrowtail=dot, dir=back, color="#620099"];

    test -> cg1;
    test -> cg2;
    test -> cg3;

    cg1 -> cg1_1;
    cg1 -> p1;

    p1 -> cg2 [style=invis];
    //cg1_1 -> cg1_2 [style=invis];

    cg1_1 -> p2;

    cg2 -> cg2_1;
    cg2_1 -> p3;

    cg2 -> cg3 [style=invis];
    p3 -> cg3_1 [style=invis];
    //cg1_1 -> cg1_2 [style=invis];

    cg3 -> cg3_1;
    cg3 -> p4;
}
```
State of the hierarchy after the reset and repositioning.
{% endcall %}

Send all the processes to root temporally so they don't interfere:
```shell
$ echo <pid-proc1> > cgroup.procs        # byexample: +paste
$ echo <pid-proc2> > cgroup.procs        # byexample: +paste
$ echo <pid-proc3> > cgroup.procs        # byexample: +paste
$ echo <pid-proc4> > cgroup.procs        # byexample: +paste
```

Disable the controller and delete/create some nested cgroups:

```shell
$ echo '-cpu' > test/cg1/cgroup.subtree_control
$ echo '-cpu' > test/cgroup.subtree_control

$ rmdir test/cg1/cg1_2 test/cg2/cg2_2
$ mkdir test/cg3 test/cg3/cg3_1
```

Put back the processes into the cgroups:
```shell
$ echo <pid-proc1> > test/cg1/cgroup.procs              # byexample: +paste
$ echo <pid-proc2> > test/cg1/cg1_1/cgroup.procs        # byexample: +paste
$ echo <pid-proc3> > test/cg2/cg2_1/cgroup.procs        # byexample: +paste
$ echo <pid-proc4> > test/cg3/cgroup.procs              # byexample: +paste
```

Let's play with it and see to what extend we can enable the `+cpu`
controller along the hierarchy:

```shell
$ echo '+cpu' > test/cgroup.subtree_control

$ echo '+cpu' > test/cg1/cgroup.subtree_control
<...>write error: Device or resource busy
```

We could enable `+cpu` on `test/`'s children but we had some trouble
going further.

We couldn't enable on `test/cg1/`'s children because `test/cg1/` and one
of its children are not empty.

And because a cgroup can enable the control in its subtree only if its
parent enabled it for it, `test/cg1/cg1_1/` will fail because its parent
does not have the control of `+cpu`:

```shell
$ echo '+cpu' > test/cg1/cg1_1/cgroup.subtree_control
<...>write error: No such file or directory
```

In contrast with `test/cg1/` we didn't have trouble enabling on `test/cg2/`'s and
`test/cg3/`'s children because in the first case `test/cg2/` is empty and
in the second case is the child `test/cg3/cg3_1/` which it is empty.

```shell
$ echo '+cpu' > test/cg2/cgroup.subtree_control

$ echo '+cpu' > test/cg3/cgroup.subtree_control
```

```shell
$ echo '+cpu' > test/cg2/cg2_1/cgroup.subtree_control

$ echo '+cpu' > test/cg3/cg3_1/cgroup.subtree_control
<...>write error: Operation not supported
```

### Flow diagram for enabling a controller in a subtree


{% call maindiag('enable-controller-in-no-internal-process.svg', 'plantuml') %}
```plantuml
!pragma useVerticalIf on
skinparam backgroundColor transparent
start

if (is controller available on cgroup?) then (no)
  :fail with "write error";
  end
elseif (is subtree and cgroup occupied?) then (yes)
  :fail with "Device or resource busy";
  end
elseif (is a non-root parent occupied?) then (yes)
  :fail with "Operation not supported";
  end
endif
:enable the controller on the cgroup's subtree;
stop
```
Diagram of the flow for enabling a controller on a subtree and the possible
outcomes that summarizes all the talked so far.

This is a sketch and by no means it is a fully specification.
{% endcall %}

## *No internal process* constraint, from a controller's perspective

Consider the scenario seen earlier:

{% call maindiag('testing_with_proc_in_cg1_simple.svg', 'dot') %}
```dot
digraph CG  {
    bgcolor="transparent";

    // Controllers
    node [shape=none] {
        "cpu" [label="cpu ≤ X", group=lvl0];
        "cpu_cg1" [label="cpu ≤ Y", group=lvl1];
        "cpu_cg1_1" [label="cpu ≤ Z", group=lvl2];
    }

    // Domains
    node [shape=box, color="#000000", style=solid] {
        "test" [label="test/", group=lvl0];
        "cg1" [label="cg1/", group=lvl1];
        "cg1_1" [label="cg1_1/", group=lvl2];
    }

    // Processes
    node [shape=circle,  color="#880000", style=bold, width=0.5, fixedsize=true] {
        "p1" [label="p1", group=lvl1];
        "p2" [label="p2", group=lvl1];
    }

    // Failed processes
    node [shape=circle,  color="#880000", style="dashed,bold", width=0.5, fixedsize=true] {
    }

    // Error messages
    node [shape=underline,  color="#880000", style="dashed,bold", fixedsize=false] {
    }

    // Cgroups at top
    {rank=min; cpu cpu_cg1, cpu_cg1_1}
    {rank=same; test cg1 cg1_1}

    {rank=max; p1 p2 }

    cpu -> test [style=dashed, arrowtail=dot, dir=back, color="#620099"];
    cpu_cg1 -> cg1 [style=dashed, arrowtail=dot, dir=back, color="#620099"];

    test -> cg1;

    cg1 -> cg1_1;

    cg1 -> p1;
    cg1 -> p2;

    cg1_1 -> cpu_cg1_1  [style=dashed, arrowhead=dot, color="#620099"];
}
```
{% endcall %}

Let's see it from the `+cpu` controller's perspective.

You are at `test/cg1/` with some processes there. The cgroup
has the controller's files to control/distribute the
resources (`cpu.max` in this case).

It is easy to see how `cpu.max` can be interpreted: just control the CPU
usage among `p1` and `p2`.

But what would you if a process is added to `test/cg1/cg1_1/`. The
problem is not that you have another process, the problem is that
`test/cg1/cg1_1/` also has its own control file.

How would you interpret that control file in `test/cg1/cg1_1/`
and at the same time the file in `test/cg1/` and distribute
the CPU among the processes of both cgroups?

It is not easy.

In `v1` this situation added a lot of complexity to the controllers and
eventually added inconsistencies between them about how to treat these
cases.

In `v2` these cases are just forbidden: you cannot have processes in one
cgroup and in its subtree *and at the same time* have a control file in
the cgroup and another in the subtree.

From the controller's perspective, in term of the location of its control file,
all the processes are at the *leaves of its domain*. Even if the processes
are in different sub cgroups, these sub cgroups *will not distribute
the resource further* (they don't have a control file to do it!).

## Final comments

We grasped how `cgroup` works, how it is
[organized](/articles/2022/04/23/Linux-Control-Group-Hierarchical-Organization.html)
and how the resources are
[distributed](/articles/2022/04/24/Linux-Control-Group-Resource-Distribution.html).

But I left a lot of things outside: how `cgroup` security works, which
controllers are how they work, how `cgroup` works inside a container and
probably a few bits more.

Happy research!


<!--
Remove any constraint on cpu
Move our shell(s) to the root
$ echo $$ > /sys/fs/cgroup/cgroup.procs                     # byexample: +pass -skip

Kill any subprocess
$ kill -9 $(jobs -p) && wait                                # byexample: -skip +pass
$ sleep 5                                                   # byexample: -skip +pass +timeout=8

$ echo '-cpu' > /sys/fs/cgroup/test/cg1/cg1_1/cgroup.subtree_control           # byexample: -skip +pass
$ echo '-cpu' > /sys/fs/cgroup/test/cg1/cg1_2/cgroup.subtree_control           # byexample: -skip +pass
$ echo '-cpu' > /sys/fs/cgroup/test/cg2/cg2_1/cgroup.subtree_control           # byexample: -skip +pass
$ echo '-cpu' > /sys/fs/cgroup/test/cg2/cg2_2/cgroup.subtree_control           # byexample: -skip +pass
$ echo '-cpu' > /sys/fs/cgroup/test/cg1/cgroup.subtree_control           # byexample: -skip +pass
$ echo '-cpu' > /sys/fs/cgroup/test/cg2/cgroup.subtree_control           # byexample: -skip +pass
$ echo '-cpu' > /sys/fs/cgroup/test/cgroup.subtree_control           # byexample: -skip +pass

Delete recursively every cgroup (folder) from the leaves to the
root. All of them should be empty by now
$ cd /sys/fs/cgroup/                                        # byexample: +pass -skip
$ rmdir $(find /sys/fs/cgroup/test/ -type d | sort -r)   # byexample: +pass -skip
-->
