---
layout: post
title: "High Precision Timers (userspace)"
tags: timers clocks performance
---

You want to measure the time that it takes `foo()` to run so
you do the following:

```cpp
void experiment() {
    uint64_t begin = now();
    foo();
    uint64_t end = now();

    printf("Elapsed: %lu\n", end - begin);
}
```

The question is, what `now()` function you would use?<!--more-->


{% marginnote
'You could read a CPU register that implements the clock in hardware.
Beware, however, that the read may not be cheap and the clock
may not have the precision that you need.
<br />
Also, the register may be per CPU: to make it work you need to
ensure that `experiment()` does not migrate to another CPU.
<br />
See [libpfm4](https://github.com/wcohen/libpfm4).
' %}

There are some options available:

 - `time()` from `time.h`
 - `gettimeofday()` from `sys/time.h`
 - `getrusage()` from `sys/time.h` and `sys/resource.h`
 - `clock_gettime()` from `time.h`

However not all of them are as suitable for the task as they may seem.

## Test escenario

The idea is to call a particular clock several times in a tight loop.

```cpp
const size_t rounds = atoi(argv[1]);
struct timespec * const times1 = malloc(sizeof(*times1) * rounds);

for (int i = 0; i < rounds; ++i) {
    clock_gettime(CLOCK_MONOTONIC, &times1[i]);
}
print_nsec_resolution(rounds, "mono", times1);
```

{% marginnote
'If the clock jumps *backwards*, this function will print a *huge*
number and not a negative value.
' %}

The `print_*` functions will print the measurements normalized: no
matter the clock's resolution, the printed value will be in nanoseconds
and to get comparable results the values are respect the first
measurement.

In other words:

```cpp
uint64_t ref = times1[0].tv_sec * 1000000000; // seconds as nanoseconds
ref += times1[0].tv_nsec; // plus the nanoseconds

for (int i = 0; i < rounds; ++i) {
    uint64_t tmp = times1[i].tv_sec * 1000000000;
    tmp += times1[i].tv_nsec;

    printf("%s %lu\n", category, tmp-ref);
}
```

The full code can be found
[here](/assets/timing-assets/clocks.c).

## Evaluation

Compiled and executed with 10000 rounds each clock, it generated 70000
lines.

{% marginnote
'The use of `dtype={"clock type": "category"}` is important. Pandas
will load these strings and it will create a category for each distinct
label which internally is represented as an integer.
<br />
This reduces by two orders of magnitud the memory usage
(`d.memory_usage(True, True)` to compare them).
[Pandas
reference](https://pandas.pydata.org/pandas-docs/stable/user_guide/scale.html)
' %}

Each line is prefixed with a string that labels the clock type.

The output can be loaded with `pandas` as follows:

```python
>>> import pandas as pd
>>> d = pd.read_csv(
...         fname,
...         sep=' ',
...         header=None,
...         names=['clock type', 'tval'],
...         dtype={'clock type': 'category'})
```

It makes sense to analyze not the time returned by each call but the
difference between two consecutive calls. This highlights how much
stable is the clock and how much delay adds the call.

```python
>>> for c in d['clock type'].cat.categories:
...     selected_rows = d['clock type'] == c
...     differences = d[selected_rows]['tval'].diff()
...     d.loc[selected_rows, 'tval'] = differences
```

The full code can be found
[here](/assets/timing-assets/analyze.py).

Let's review what we've got.

### `time()`

`time()` has a resolution of a second, so it is a *no-go* to measure things
of the order of the microsecond or less.

But for completeness I tested `time()` anyways and what I found
it was a surprise:

```
Clock type: time
         tval
count  9999.0
mean      0.0
std       0.0
min       0.0
25%       0.0
50%       0.0
75%       0.0
max       0.0
```

If I run `time()` in tight `for` loop, it returns always the same value,
no matter how many times the loop iterates.

I thought that it was a bug but nope, when I run it with `gdb` it works as
expected.

Weird.


### `gettimeofday()`

{% marginnote
'This can be explained due its implementation: instead of doing a
syscall, a call to `gettimeofday()` calls a snippet of code in user
space.
<br />
See more about [vsyscall and vDSO here](https://0xax.gitbooks.io/linux-insides/content/SysCall/linux-syscall-3.html)
' %}

`gettimeofday()` shown the best performance: the worst time measured
between two consecutive calls is just 2 microseconds, which it is twice
the minimum resolution of the function.


Fast but it is also super imprecise.

More than 75% of the differences between two consecutive measurements
are zero which means that `gettimeofday()` returns a cached value and it
is updated very infrequently.

```
clock type: tofd
              tval
count  9999.000000
mean     27.102710
std     166.646544
min       0.000000
25%       0.000000
50%       0.000000
75%       0.000000
max    2000.000000
```

In addition to its intrinsic imprecision, `gettimeofday()` is **not
guaranteed to be monotonically increasing**. So you can see *jumps* to
the future or event to the past.

This is because `gettimeofday()` is in sync with external sources of
time like NTP. The user may even change it running `date`.

Fast but not useful to measure differences of time.

### `getrusage()`

Something similar happens with `getrusage()`: it is slightly slower than
`gettimeofday()` but it is still super fast (7 microseconds) but returns
cached values (at least half of the times).

```
Clock type: ruse
              tval
count  9999.000000
mean    524.152415
std     656.260508
min       0.000000
25%       0.000000
50%       0.000000
75%    1000.000000
max    7000.000000
```

### `clock_gettime()`

{% marginnote
'See also the [PEP 418](https://www.python.org/dev/peps/pep-0418/#time-monotonic).
' %}

The manpage describes four kind of clocks that may work:

 - `CLOCK_MONOTONIC`: monotonic time but it may be affected by
incremental changes done by `adjtime` or NTP.
 - `CLOCK_MONOTONIC_RAW`: like `CLOCK_MONOTONIC` but it is not affected by
`adjtime` or NTP. Uses hardware-specific.
 - `CLOCK_PROCESS_CPUTIME_ID`: per process clock that measures the
CPU time for the process (among all the threads).
 - `CLOCK_THREAD_CPUTIME_ID`: per thread clock that measures the
CPU time for that particular thread.

`clock_gettime()` is the only that returned values that make sense
and `CLOCK_MONOTONIC` is the winner.

It has the smallest elapsed time (80 nanoseconds) and it has a
dispersion of the values of few nanoseconds.

This can be seen in the percentiles 80, 84, 85, 86 nanoseconds.

`CLOCK_PROCESS_CPUTIME_ID` and `CLOCK_THREAD_CPUTIME_ID` are in the
second place.

```
         MONOTONIC    MONOTONIC_RAW   PROCESS_CPUTIME    THREAD_CPUTIME
              tval             tval              tval              tval
count  9999.000000      9999.000000       9999.000000       9999.000000
mean    102.900290       773.215422        387.565257        379.232923
std     295.741321       200.428225        216.037233        210.391130
min      80.000000       709.000000        366.000000        358.000000
25%      84.000000       719.000000        374.000000        367.000000
50%      85.000000       723.000000        377.000000        370.000000
75%      86.000000       728.000000        401.000000        391.000000
max    8019.000000     13532.000000      17392.000000      17572.000000
```

In all the cases the clocks are quite stable and the outliers are
probably due noise in the system.

## Conclusions

`clock_gettime()` with `CLOCK_MONOTONIC` is the winner, at least in my
4.19 kernel, with a minimum delta of 80 to 86 nanoseconds.

In second place `clock_gettime()` with `CLOCK_PROCESS_CPUTIME_ID` or
`CLOCK_THREAD_CPUTIME_ID`. Good performance, roughly 4 or 5 times slower
than `CLOCK_MONOTONIC`.

`clock_gettime()` with `CLOCK_MONOTONIC_RAW` is not bad but it is at
least 8 times slower than `CLOCK_MONOTONIC`.

The rest of the clocks are **not** useful.




