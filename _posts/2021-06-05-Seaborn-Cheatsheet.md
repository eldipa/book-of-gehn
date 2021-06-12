---
layout: post
title: "Seaborn Cheatsheet"
tags: seaborn matplotlib pandas plotting cheatsheet
---

Plotting data was always for me a weak point: it always took me a lot of
time to make the plots and graphs, reading the documentation, *googling*
how to do one particular tweak and things like that.

So I challenge myself: could I build a *cheatsheet* about plotting?

Yes, yes I could.

{% maincolumn 'assets/statistics/seaborn-cheatsheet/seaborn-cheatsheet-v1.svg'
'' %}

[Seaborn](https://seaborn.pydata.org/) is a very simple but powerful
plotting library on top of [matplotlib](https://matplotlib.org/) designed
for statistical analysis.

Quick links:
[PDF (no bg)](/assets/statistics/seaborn-cheatsheet/seaborn-cheatsheet-v1.pdf),
[PDF (bg)](/assets/statistics/seaborn-cheatsheet/seaborn-cheatsheet-bg-v1.pdf),
[SVG (no bg)](/assets/statistics/seaborn-cheatsheet/seaborn-cheatsheet-v1.svg),
[SVG (bg)](/assets/statistics/seaborn-cheatsheet/seaborn-cheatsheet-bg-v1.svg)
.<!--more-->

## Instructions

Each rectangle list the parameters that take the plot functions.
The bold labels inside, like **hist** and **violin**, are the names
of the plots.

The names are followed by a list of **data parameter**, also in bold.
These are used to tell the function from **where** take the data. Some
functions may take more parameters additionally, so they are in between
**square brakets**.

The rest of the parameters listed are optional. Sometimes the
cheatsheet shows the *type* of the parameter, sometimes the *range* and
in others just a few possible values.

From all of that you can write Python code like the following that plots
a histogram for the univariate `"age"` in the given Pandas data frame.
The extra `kde=True` plots a *kernel density estimation* on top.

```python
>>> import seaborn as sns
>>> sns.histplot(data=df, x="age", kde=True)
```

Nested rectangles means that the outer rectangle **includes** the parameters
listed in the inner rectangle but not the other way around.

The **dashed** rectangles means the **union of**: the parameters are
shared across.

For example `bar` and `point` accepts the parameters of `box` and `line`.

Some parameters are followed by a *comment in italics* for a quick
explanation of the parameters.

The cheatsheet has a lot of small plots as visual examples. Some of them
are **linked with a line** with a plot function (rectangle) and some of them are
**linked with a dashed line** to a particular setting.

For example in the cheatsheet there are 4 examples of `hist` showing the
different results based on `element='step'`, `multiple='stack'` and
`multiple='dodge'`.

The fourth example is linked to the rectangle for the `hist` function
(bivariate) and not linked to a particular setting.

The colors also have a meaning: plot functions of the same color belongs
to the same *Seaborn module*.

Seaborn has --broadly speaking-- 2 groups of functions:

 - the ones that work at the **axes level**.
 - the ones that creates their own figure and axes, the **figure level**
(or module level)

The former are the core of Seaborn. Call them on the same axes to do a
combination (an overlay) of different plots.

The latter are however simpler. They just call the axes level function
based on the `kind=` parameter.

The advantage of the figure level functions is that they can create a
**matrix of plots** with the `row=` and `col=` parameters.

The colors represent these: red for uni/bivariate distribution plots
(`displot`), blue for relationship plots (`relplot`) and green for
distribution within categories plots (`catplot`).

The violet group is for regressions and does not follow exactly the
pattern above.


