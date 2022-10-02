---
layout: post
title: "Diff Between Data Frames for Testing"
tags: [python, dataframe, pandas]
inline_default_language: python
---

Let's say that we want to compare two Pandas' dataframes for unit
testing.

One is the *expected* dataframe, crafted by us
and it will be the *source of truth* for the test.

The other is the *obtained* dataframe which is the result of the
experiment that we want to check.

Doing a naive comparison will not work: first we may want to *tolerate*
some minor differences due computation imprecision; and second, and most
important, we don't want to know *just* if the dataframes are different or
not

We want to know **where are the differences**.

Knowing exactly what is different makes the debugging much easier -- trying to
figure out which column in which row there is a different by hand is
**not fun**.<!--more-->

## Comparison row-by-row (the naive approach)

Pandas has a beautiful `assert_frame_equal`
[function for unit testing](https://pandas.pydata.org/docs/reference/api/pandas.testing.assert_frame_equal.html):
it compares the dataframes row by row and shows which column has some
differences and how many there are.

Considere the following dataframes:

```python
>>> import pandas as pd

>>> expected_df = pd.DataFrame({
...     'name':    ['alice',  'bob',   'alice', 'charlie'],
...     'subject': [ 'math', 'math', 'physics',    'math'],
...     'grade':   [      5,      4,         4,         5],
... })

>>> obtained_df = pd.DataFrame({
...     'name':    [  'alice',   'bob',  'alice', 'charlie'],
...     'subject': ['physics',  'math',   'math',    'math'],
...     'grade':   [        4,       4,        3,         2],
... })
```

Now let's use `assert_frame_equal`:

```python
>>> from pandas.testing import assert_frame_equal
>>> assert_frame_equal(
...     obtained_df,
...     expected_df,
...     check_exact=True,
...     check_like=True,
...     check_dtype=False
... )
Traceback (most recent call last):
<...>
AssertionError: DataFrame.iloc[:, 1] (column name="subject") are different
<...>
DataFrame.iloc[:, 1] (column name="subject") values are different (50.0 %)
[index]: [0, 1, 2, 3]
[left]:  [physics, math, math, math]
[right]: [math, math, physics, math]
```

So `assert_frame_equal` detected that half of the rows are different on
the `"subject"` column.

With a closer inspection on the `left` and `right` series we see that the
first and third values are different (`physics/math` and
`math/physics`).

Now if you see dataframes `obtained_df` and `expected_df` you will see
that it is more likely to interpret this **difference as an reorder of the
rows** and not as a real discrepancy (unless you are really wanting to
have a specific order).

## Make the comparison order-insensitive

`assert_frame_equal` alone is not enough as it is sensible to reorders.

{% call marginnotes() %}
The `reset_index` is required because `sort_values` preserves the
index: each row remember its original position. `assert_frame_equal`
checks by index so it will revert the sort.
{% endcall %}

Let's try to sort the rows before the check then:

```python
>>> sort_by = ["subject"]

>>> ob = obtained_df.sort_values(sort_by).reset_index(drop=True)
>>> ex = expected_df.sort_values(sort_by).reset_index(drop=True)

>>> assert_frame_equal(
...     ob,
...     ex,
...     check_exact=True,
...     check_like=True,
...     check_dtype=False
... )
Traceback<...>
AssertionError: DataFrame.iloc[:, 0] (column name="name") are different
<...>
DataFrame.iloc[:, 0] (column name="name") values are different (50.0 %)
[index]: [0, 1, 2, 3]
[left]:  [bob, alice, charlie, alice]
[right]: [alice, bob, charlie, alice]
```

Mmm... more noise... perhaps sorting by `"name"` **and** `"subject"`?

```python
>>> sort_by = ["name", "subject"]

>>> ob = obtained_df.sort_values(sort_by).reset_index(drop=True)
>>> ex = expected_df.sort_values(sort_by).reset_index(drop=True)

>>> assert_frame_equal(
...     ob,
...     ex,
...     check_exact=True,
...     check_like=True,
...     check_dtype=False
... )
Traceback<...>
AssertionError: DataFrame.iloc[:, 2] (column name="grade") are different
<...>
DataFrame.iloc[:, 2] (column name="grade") values are different (50.0 %)
[index]: [0, 1, 2, 3]
[left]:  [3, 4, 4, 2]
[right]: [5, 4, 4, 5]
```

Better, I guess.

Sorting solves the reorder problem but it is still **hard to interpret** the
results.

Even with this example of just 4 rows, there are too many rows!

More over, `assert_frame_equal` is not helpful when the dataframes has a
different size, it just says that and that it `:|`

```python
>>> ob.loc[len(ob.index)] = ["alice", "algebra", 3]

>>> assert_frame_equal(
...     ob,
...     ex,
...     check_exact=True,
...     check_like=True,
...     check_dtype=False
... )
<...>
AssertionError: DataFrame are different
<...>
DataFrame shape mismatch
[left]:  (5, 3)
[right]: (4, 3)
```

## Comparing group-by-group

Instead of comparing row by row we could group the rows under some key
and compare then each row **within each group**.

```python
>>> group_by = ["name", "subject"]

>>> obtained_g = obtained_df.groupby(group_by, dropna=False)
>>> expected_g = expected_df.groupby(group_by, dropna=False)
```

The intuition is that we will get fewer differences between groups
and possibly more meaningful.

Here we get which groups do we have in common:

```python
>>> obtained_group_names = {key for key, item in obtained_g}
>>> expected_group_names = {key for key, item in expected_g}

>>> common_group_names = obtained_group_names & expected_group_names
>>> sorted(common_group_names)
[('alice', 'math'), ('alice', 'physics'), ('bob', 'math'), ('charlie', 'math')]
```

Now for each group we compare them using `assert_frame_equal`:

```python
>>> name = ('alice', 'math')
>>> ob = pd.DataFrame(obtained_g.get_group(name).reset_index(drop=True))
>>> ex = pd.DataFrame(expected_g.get_group(name).reset_index(drop=True))

>>> assert_frame_equal(
...     ob,
...     ex,
...     check_exact=True,
...     check_like=True,
...     check_dtype=False
... )
Traceback<...>
AssertionError: DataFrame.iloc[:, 2] (column name="grade") are different
<...>
DataFrame.iloc[:, 2] (column name="grade") values are different (100.0 %)
[index]: [0]
[left]:  [3]
[right]: [5]
```

Now it is clear that Alice got a grade of 3 in her Math class but it was
expected to get a 5.

{% call marginnotes() %}
`pd.concat` will put the rows of one dataframe after the rows of the
other *preserving* their original indexes.

Sorting by index then will
make the first row of the expected appear after the first row of the
obtained, the second row of the expected appear after the second row of
the obtained and so on.
{% endcall %}

We could pretty print the group *interleaving the rows* of the obtained
and expected dataframes so we can compare them line by line:

```python
>>> ob["DF"] = "obtained"
>>> ex["DF"] = "expected"

>>> merged = pd.concat([ob, ex]).sort_index()
>>> merged
    name subject  grade        DF
0  alice    math      3  obtained
0  alice    math      5  expected
```

Much better!

## Putting all this together

The plan is:

 - group by some columns to compare smaller groups
 - sort the rows of each group to make the comparison
   order-insensitive.
 - call `assert_frame_equal` on each *common* group and add the
   differences found to the list of differences.
 - add to the list any *unexpected* and *missing* group
 - if the list is not empty, raise `AssertionError`

This is the code:

```python
>>> def assert_df_equal(obtained_df, expected_df, group_by=[], sort_by=[], check_exact=True, rtol=1e-5, atol=1e-8, to_string_kwargs={}):
...     diffs = []
...
...     # See the whole dataframe as the single group in case of
...     # the user don't wanting to group the rows
...     singleton_group = False
...     if not group_by:
...         group_by = lambda *args: singleton_group
...         singleton_group = True
...
...     obtained_g = obtained_df.groupby(group_by, dropna=False)
...     expected_g = expected_df.groupby(group_by, dropna=False)
...
...     obtained_group_names = {key for key, item in obtained_g}
...     expected_group_names = {key for key, item in expected_g}
...
...     common_group_names = obtained_group_names & expected_group_names
...     unexpected_group_names = obtained_group_names - expected_group_names
...     missing_group_names = expected_group_names - obtained_group_names
...
...     # Check if we have unexpected groups or missing groups.
...     # These are groups that cannot be compared with any other row
...     # in the opposite dataframes and therefore they are straight
...     # differences by definition
...     for name in sorted(unexpected_group_names):
...         ob = pd.DataFrame(obtained_g.get_group(name))
...         if sort_by:
...             ob.sort_values(sort_by, inplace=True)
...
...         ob["DF"] = "obtained"
...
...         msg = f"Unexpected (not expected) group {name!r}\n\n{ob.to_string(**to_string_kwargs)}"
...         diffs.append(msg)
...
...     for name in sorted(missing_group_names):
...         ex = pd.DataFrame(expected_g.get_group(name))
...         if sort_by:
...             ex.sort_values(sort_by, inplace=True)
...
...         ex["DF"] = "expected"
...
...         msg = f"Missing (not obtained) group {name!r}\n\n{ex.to_string(**to_string_kwargs)}"
...         diffs.append(msg)
...
...     # Compare group by group, sorting them if sort_by is given.
...     for name in sorted(common_group_names):
...         ob = pd.DataFrame(obtained_g.get_group(name))
...         ex = pd.DataFrame(expected_g.get_group(name))
...
...         if sort_by:
...             ob.sort_values(sort_by, inplace=True)
...             ex.sort_values(sort_by, inplace=True)
...
...         ob.reset_index(drop=True, inplace=True)
...         ex.reset_index(drop=True, inplace=True)
...
...         try:
...             assert_frame_equal(ob, ex, check_exact=check_exact, rtol=rtol, atol=atol, check_like=True, check_dtype=False)
...         except Exception as err:
...             ob["DF"] = "obtained"
...             ex["DF"] = "expected"
...
...             merged = pd.concat([ob, ex]).sort_index()
...
...             if singleton_group:
...                 msg = f"{err}"
...             else:
...                 msg = f"For group {name!r}: {err}"
...
...             msg = f"{msg}\n\n{merged.to_string(**to_string_kwargs)}"
...             diffs.append(msg)
...
...     if diffs:
...         msg = f"Found {len(diffs)} difference{'s' if len(diffs) > 1 else ''}.\nDetails follows:\n\n"
...         raise AssertionError(msg + "\n\n".join(diffs))
```


## Examples

Let's begin with the same dataframes as before:

```python
>>> expected_df = pd.DataFrame({
...     'name':    ['alice',  'bob',   'alice', 'charlie'],
...     'subject': [ 'math', 'math', 'physics',    'math'],
...     'grade':   [      5,      4,         4,         5],
... })

>>> obtained_df = pd.DataFrame({
...     'name':    [  'alice',   'bob',  'alice', 'charlie'],
...     'subject': ['physics',  'math',   'math',    'math'],
...     'grade':   [        4,       4,        3,         2],
... })
```

Calling `assert_df_equal` without any group by or sort by does not gives
you much. As before a straight call to `assert_frame_equal` says that
there is a difference on `"subject"` when we already know that it is
not.

```python
>>> assert_df_equal(obtained_df, expected_df)
<...>
AssertionError: Found 1 difference.
Details follows:
<...>
DataFrame.iloc[:, 1] (column name="subject") are different
<...>
DataFrame.iloc[:, 1] (column name="subject") values are different (50.0 %)
[index]: [0, 1, 2, 3]
[left]:  [physics, math, math, math]
[right]: [math, math, physics, math]
<...>
      name  subject  grade        DF
0    alice  physics      4  obtained
0    alice     math      5  expected
1      bob     math      4  obtained
1      bob     math      4  expected
2    alice     math      3  obtained
2    alice  physics      4  expected
3  charlie     math      2  obtained
3  charlie     math      5  expected
```

Sorting quickly makes the real difference visible:

```python
>>> assert_df_equal(obtained_df, expected_df, sort_by=['name', 'subject'])
<...>
AssertionError: Found 1 difference.
Details follows:
<...>
DataFrame.iloc[:, 2] (column name="grade") are different
<...>
DataFrame.iloc[:, 2] (column name="grade") values are different (50.0 %)
[index]: [0, 1, 2, 3]
[left]:  [3, 4, 4, 2]
[right]: [5, 4, 4, 5]
<...>
      name  subject  grade        DF
0    alice     math      3  obtained
0    alice     math      5  expected
1    alice  physics      4  obtained
1    alice  physics      4  expected
2      bob     math      4  obtained
2      bob     math      4  expected
3  charlie     math      2  obtained
3  charlie     math      5  expected
```

But the dataframes are too large and it is not easy to see exactly where
is the problem.

Moreover adding an extra row breaks the comparison.

```python
>>> obtained_df.loc[len(obtained_df.index)] = ["alice", "algebra", 3]
>>> assert_df_equal(obtained_df, expected_df, sort_by=['name', 'subject'])
<...>
AssertionError: Found 1 difference.
Details follows:
<...>
DataFrame are different
<...>
DataFrame shape mismatch
[left]:  (5, 3)
[right]: (4, 3)
<...>
```

`group_by` to rescue!

Partitioning the dataframes in smaller groups makes much easier the
debugging and much more robust against shape mismatches

```python
>>> assert_df_equal(obtained_df, expected_df, group_by=['name', 'subject'])
Traceback (most recent call last):
<...>
AssertionError: Found 3 differences.
Details follows:
<...>
Unexpected (not expected) group ('alice', 'algebra')
<...>
    name  subject  grade        DF
4  alice  algebra      3  obtained
<...>
For group ('alice', 'math'): DataFrame.iloc[:, 2] (column name="grade") are different
<...>
DataFrame.iloc[:, 2] (column name="grade") values are different (100.0 %)
[index]: [0]
[left]:  [3]
[right]: [5]
<...>
    name subject  grade        DF
0  alice    math      3  obtained
0  alice    math      5  expected
<...>
For group ('charlie', 'math'): DataFrame.iloc[:, 2] (column name="grade") are different
<...>
DataFrame.iloc[:, 2] (column name="grade") values are different (100.0 %)
[index]: [0]
[left]:  [2]
[right]: [5]
<...>
      name subject  grade        DF
0  charlie    math      2  obtained
0  charlie    math      5  expected
```

It looks complicated but now we know **exactly** where are the differences:

 - We have a *unexpected* row: `alice  algebra  3`
 - For `('alice', 'math')` the obtained grade was 3 but expected 5
 - For `('charlie', 'math')` the obtained grade was 2 but expected 5


