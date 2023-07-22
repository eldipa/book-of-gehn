---
layout: post
title: "XXX"
tags: [DRAFT]
---
Import the usual stuff and load the dataset

```python
>>> import pandas as pd
>>> import numpy as np
>>> import seaborn as sns
>>> import matplotlib.pyplot as plt

>>> dataset = pd.read_parquet('results.parquet')
>>> dataset['prog'] = dataset['prog'].astype('category')
```

The measurements are always noisy, even in a
[quiescent environment]().

So we want to keep the smallest 10 measurement for a given experiment
(a given program executed with a given `rounds` parameter).

```python
>>> elapsed = dataset.groupby(['prog', 'rounds'])['elapsed']
>>> elapsed_smallest = elapsed.nsmallest(10)
```

`elapsed_smallest` is however a `pd.Series`, not a `pd.DataFrame` so we
need to convert it back:

```python
>>> df = pd.DataFrame(elapsed_smallest)
```

The resulting `df` has a *multi level* index, inherited from the
`groupby` above.

```python
>>> df
                      elapsed
prog rounds
c O0 1000000    4053    14357
                1911    14359
                2268    14359
...                       ...
java 1000000000 776   4748214
                1532  4748673
                2582  4748796
                4115  4748796
                3422  4749163
<...>
[210 rows x 1 columns]
```

We want those indexes back again into the dataframe as columns. The
first `reset_index` does that and the second removes any other remaining
index.

```python
>>> df = df.reset_index(['prog', 'rounds'])
>>> df = df.reset_index(drop=True)

>>> df
     prog      rounds  elapsed
0    c O0     1000000    14357
1    c O0     1000000    14359
2    c O0     1000000    14359
..    ...         ...      ...
207  java  1000000000  4748796
208  java  1000000000  4748796
209  java  1000000000  4749163

[210 rows x 3 columns]
```

The minimum of the `elapsed` column is going to be our best estimation
for the truly elapsed time.

We could get this value earlier without requiring to getting the
`nsmallest` but I wanted to calculate the standard deviation too of the
smallest elapsed times, slightly larger than our estimation.

```python
>>> df = df.groupby(['prog', 'rounds'])['elapsed'].agg([np.min, np.std])
>>> df = df.reset_index()

>>> df
    prog      rounds     amin         std
0   c O0     1000000    14357    2.626785
1   c O0     5000000    63045    5.952590
<...>
5   c O0   500000000  3079427  745.824741
6   c O0  1000000000  6548346  338.559776
7   c O3     1000000     4323    1.229273
8   c O3     5000000    21734    3.267687
<...>
12  c O3   500000000  2186285  242.826779
13  c O3  1000000000  4551512  301.988226
14  java     1000000    15737   34.937404
15  java     5000000    65740   55.986209
<...>
19  java   500000000  2332344  578.046221
20  java  1000000000  4746684  710.562969
```

Let's take a look at what we've got:

```python
>>> ax = sns.lineplot(data=df, x=df.rounds, y=df.amin, hue=df.prog)
>>> ax.set(xscale='log', yscale='log')
```

As expected, C has a predictable linear performance, proportional to the
amount of rounds executed being the binary compiled with `-O3` much
faster than the one not optimized at all.

Java, on the other hand shows a peculiar line. It starts slightly above
the `-O0` line but around `x=5e6` it starts to outperform it and gets
quite close to the `-O3` line at the end.

This is the **just in time compiler** in action.

The program runs a very tight loop that it is executed millions of
times. The JVM decides that the code would benefit if it is compiled
to native code and optimized, like `-O3` is.

There is a trade-off here. In one hand Java code is slower but it is
ready to be executed, in the other hand, compiled code is faster
but the program must pay a delay for the compilation takes place.

{% call marginnotes() %}
Why? Imagine a concrete class `FooConcrete` that implements the interface
`Fooable`.

If the function `void bar(Fooable f)` is called repeatably with the same
specific class `FooConcrete` as argument, the JVM will compile it to
native code.

But it cannot ruled out the Java code of `void bar(Fooable f)`
because it is possible that the program calls `bar` with another class
that implements the `Fooable` interface and that will behave totally
different and would require a totally different native code.
{% endcall %}

And don't forget about the memory: the JVM will have to
keep both the Java and the compiled versions of the loop.

These constrains impose serious limitations to the JIT and in general,
it cannot outperform C (if it is coded and optimized *correctly* of
course!)



https://matplotlib.org/stable/gallery/subplots_axes_and_figures/zoom_inset_axes.html
