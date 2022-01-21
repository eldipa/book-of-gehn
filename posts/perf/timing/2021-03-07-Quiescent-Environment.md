---
layout: post
title: "Quiescent Environment"
tags: [quiescent, performance]
inline_default_language: cpp
---

You are working in optimizing a piece of software to reduce
the CPU cycles that it takes.

To compare your improvements, it is reasonable to measure the elapsed
time before and after your change.

Unless you are using a simulator, it is impossible to run a program
*isolated* from the rest and your measurements will be noisy.

If you want to take precise measurements you need a *quiescent*
environment as much as possible.<!--more-->

## An incomplete cheatsheet

Isolate the machine:
 - use a bare metal machine or VMs if not possible. Try to
avoid container environments.
 - unplug the network cable or reduce by some mean the traffic (from
outside the machine)

At hardware level disable:
 - Hyperthreading (hardware multitenancy)
 - Intel Turbo Boost or Overclocking [How-to (maybe)](https://askubuntu.com/questions/619875/disabling-intel-turbo-boost-in-ubuntu)
 - Dynamic Voltage & Frequency Scaling [How-to (maybe)](https://askubuntu.com/questions/523640/how-i-can-disable-cpu-frequency-scaling-and-set-the-system-to-performance)

At the kernel level:
 - isolate one or more CPUs so you run your programs there without much
interruptions from other tasks. Two options: removing the CPUs from the
scheduler at boottime [(isolcpus)](https://www.kernel.org/doc/html/v4.19/admin-guide/kernel-parameters.html?highlight=isolcpu)
or assigning them to an isolated cgroup at runtime
[(cset)](https://manpages.ubuntu.com/manpages/bionic/man1/cset.1.html).
 - use a preconfigured
[tuned](https://manpages.debian.org/buster/tuned/tuned.8.en.html) setup.
[(repo)](https://github.com/redhat-performance/tuned/blob/master/profiles/realtime/tuned.conf);
[(guide)](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux_for_real_time/7/html/tuning_guide/chap-Realtime-Specific_Tuning).
 - disable the interruptions handling in those CPUs.
 - use thread's CPU affinity to assign the threads to each CPU (this is
mandatory if you disabled the scheduler with `isolcpus`). See
[taskset](https://man7.org/linux/man-pages/man1/taskset.1.html)
 - disable not needed kernel threads ? [may
be](https://www.kernel.org/doc/Documentation/kernel-per-CPU-kthreads.txt); and
other sources of noise. See [more](https://lwn.net/Articles/816298/)


At the user-space level:
 - disable all the services that you can
 - follow some part of the
[general](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux_for_real_time/7/html/tuning_guide/chap-general_system_tuning)
and
[advanced](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux_for_real_time/7/html/tuning_guide/chap-Realtime-Specific_Tuning)
tuning guides.

At the instrumentation level:
 - static low-overhead instrumentation if possible, dynamic if you can't
recompile.
 - prefer deterministic (like counting the elapsed time) over sampling, specially for
small-fast function targets; sometimes sampling is the only way however.
 - use a [high precision clock](/articles/2021/02/27/High-Precision-Timers.html).
 - perhaps a [causal profiler
(coz)](https://github.com/plasma-umass/coz). See
[post](https://easyperf.net/blog/2020/02/26/coz-vs-sampling-profilers)
and [video](https://www.youtube.com/watch?v=r-TLSBdHe1A).

At the binary level:
 - code alignment can be mostly controlled by the compiler, but it may
add delays due the increasing of the binary. See
[post](https://easyperf.net/blog/2018/01/25/Code_alignment_options_in_llvm).
 - if you cannot control it, randomize it: you will add noise but it
will be random noise and not *biased noise* which is much worst.
[Stabilizer (may be)](https://github.com/ccurtsinger/stabilizer)

The experiment:
 - automate the setup of the machine as much as possible
 - automate the experiment execution so it can be reproduced again in
the future.
 - run several executions and track the minimum value (if applies); if
possible, try to run several different benchmark programs that use your
target function.
 - use different test suites and benchmarks ([google's](https://github.com/google/benchmark)).

## Sources of noise in the environment

There are a lot.

Other processes running, the OS scheduler making your program to *yield*
the CPU, the OS interrupting to process a more urgent task (like
interruptions) and more.

Graphical interfaces, network traffic and disk usage add to the mix.

{% call fullfig('all-services-up-and-down.svg') %}
The elapsed time of `foo()` executed 1000 times and sorted
from the smallest value to the largest. The last 10 values were drop
(not shown); numbers are in nanoseconds. On the left the experiment
was done in a machine without any modification; on the right all the
services were turned off, the CPU were isolated and the IRQ where
disabled. Note not only how smaller values are obtained in the
right environment (less noisy) but also the dispersion of the numbers
is smaller: on the left the time goes from 0.765 to 0.8 ns (range of 0.035 ns)
while on the right the time goes from 0.7635 to 0.7665 ns (range of
0.003 ns). One order of magnitude.
{% endcall %}


But software is not the only source of noise.

The CPU may decide to *slowdown* to conserve energy/reduce the power
consumption. This is called [Dynamic Voltage & Frequency Scaling
(DVFS)](https://en.wikipedia.org/wiki/Dynamic_frequency_scaling)

On the other hand, the CPU may *speedup* and run faster if it see that
other CPUs are idle (basically the energy/power not used by the idle CPUs
is used by the busy CPU increasing the frequency). This is called
[Dynamic Overclocking](https://en.wikipedia.org/wiki/Overclocking)
or in Intel parlance, [Turbo Boost](https://en.wikipedia.org/wiki/Intel_Turbo_Boost)

## Multitenancy: illusion of power

Is you hardware fully dedicated to you and your programs?

In these days you need to take into account the virtualization:
how your OS interacts with the hypervisor
(if you are running in a VM like in AWS) and how many other VMs are
running in the same *bare metal*, competing for it.

And VMs are not the only ones that add overheads. If you are in
container like if you are using docker, you have the same issue.

This is called [multitenancy](https://en.wikipedia.org/wiki/Multitenancy).

A similar illusion of power can come from the hardware. Intel's
[Hyperthreading](https://en.wikipedia.org/wiki/Hyper-threading)
technology allows a CPU (a core) to run two threads
concurrently.

While having each thread it own set of registers in the CPU, the
hardware is *not* duplicated (you *don't* have two cores).

Instead, hardware units like the ALU is shared among the hyper threads.
While the OS may show a CPU with 2 hyperthreads as 2 different cores,
the performance is only 15%-30% compared to a non-hyperthreaded CPU.

This is another form of multitenancy, a hardware-based multitenancy if
you want.

## Noise of the measurement

If you use a dynamic instrumentation like [Valgrind](https://valgrind.org/),
the code will [slowdown](https://valgrind.org/info/about.html)
by a factor in range from 5 to 100.

A static instrumentation is faster but requires recompilation: you may
need to add code by hand or let the compiler to do it.

And it is not trivial. Consider the following code:

```cpp
void experiment() {
    setup();

    uint64_t begin = now();
    foo();
    uint64_t end = now();

    tear_down();
    printf("Elapsed %lu\n", end-begin);
}
```

'If `foo()` is *inlined*, the compiler / CPU may decide to execute
some instructions from `foo()` *before* taking the `begin` mark (or
*after* the `end` mark).

Even if `foo()` is not inline, code *before* the `begin` may be
executed *after* it (and the same for the `end` mark).

{% call marginnotes() %}
I wrote a few posts about this: a lock free queue [part
1](/articles/2020/03/22/Lock-Free-Queue-Part-I.html),
[part
2](/articles/2020/04/28/Lock-Free-Queue-Part-II.html).
 {% endcall %}

Welcome to the *out of order execution* world.

You could use barriers but these are **not** cheap.

## Precision of the measurement

Getting the time is not cost-free. Even the most [precise
clocks](/articles/2021/02/27/High-Precision-Timers.html) like
`clock_gettime` adds some delay.

If instrumenting the binary (statically or dynamically) is too invasive,
sampling is another option like [linux's perf](https://perf.wiki.kernel.org/index.php/Main_Page)
(see [more](http://www.brendangregg.com/perf.html).

You just ask what function is a program running a few times per second
and count how many times a particular function was seen.

More times a function was seen, more *expensive* should be because it
was found more times in the CPU.

But it is tricky. What if the function is *called* a lot of times? That
would increase the probability of find it in the CPU too and it is not
necessary related with its performance.

And if you want to see the performance of a very small-quick function,
how many times do you need to sample the CPU until find the function
there? Unlikely, short events are mostly invisible for sampling tools.

This is the trade-off between *deterministic* and *sampling* profilers.

## Unknown variables

This is perhaps the most subtle topic.

You have the first version of `foo()`, let's name it `foo_1()`. By some
mean you measure its performance in the most precise way and you
obtained `X`.

How do you know that `X` is real and not the product from an *unknown*
source of noise?

You don't and you can probably assume that `X` **is**, in some part,
contributed by unknown sources of noise.

Assuming *additive* noise you can approximate the real value `X`
measuring `foo_1()` several times and getting the minimum.

Now that you "know" the performance of `foo_1()` you want to improve it.

You have `foo_2()`, you measure it several times, get the minimum and
obtain the approximated value of `Y`.

If you find `X > Y` you may get happy: you improved `foo()`, **didn't
you?**

The fact that the improvement may **not** due your modification to
`foo()` but due the fact you did **any** modification.

Changing the code changes how the code is loaded in the memory.

A simple refactor moving two functions closer in the same file may
result in a better performance.

Consider the following two versions of the same `.c` file:

```cpp
// version A            // version B
void foo() {            void foo() {
   // code...              // code...
   bar()                   bar()
}                       }

void zaz() {            void bar() {
   // code...              // code...
}                       }

void bar() {            void zaz() {
   // code...              // code...
}                       }
```

Version B may be *faster* than A just because `bar()` was moved closer
to `foo()` and the code of `bar()` gets into the cache at the moment
that `foo()` does the call.


Code layout, [code alignment](https://easyperf.net/blog/2018/01/18/Code_alignment_issues),
data alignment, and who knows what else may change.

And trust me, [Producing Wrong Data Without Doing Anything Obviously Wrong!](https://users.cs.northwestern.edu/~robby/courses/322-2013-spring/mytkowicz-wrong-data.pdf)
is very common and almost unavoidable.

