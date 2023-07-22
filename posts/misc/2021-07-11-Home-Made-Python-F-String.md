---
layout: post
title: "Home Made Python F-String"
tags: [Python]
inline_default_language: python
---

Python 3.6 introduced the so called *f-strings*: literal strings that
support formatting from the variable in the local context.

Before 3.6 you would to do something like this:

```python
>>> x = 11
>>> y = 22
>>> "x={x} y={y}".format(x=x, y=y)
'x=11 y=22'
```

But with the f-strings we can remove the bureaucratic call to `format`:

```python
>>> f"x={x} y={y}"
'x=11 y=22'
```

A few days ago
[Yurichev](https://yurichev.com/news/20210707_py_problem/) posted: could
we achieve a similar feature but without using the f-strings?.

Challenge accepted.<!--more-->

The trick is to realize that even if we don't pass a variable explicitly
to a function, the function still have access it through the Python's
stack.

So we can write something like this:

```python
>>> import inspect
>>> def level2():
...     stack = inspect.stack()
...     level2_var = 2
...     return {c.function: c.frame.f_locals for c in stack}

>>> def level1():
...     level1_var = 1
...     return level2()

>>> level1()
{'<module>': {<...>
              'level1': <function level1 at <...>>,
              'level2': <function level2 at <...>>,
              'x': 11,
              'y': 22},
 'level1': {'level1_var': 1},
 'level2': {'level2_var': 2,
            'stack': [<...>]}}
```

From `level2` we can access `level1`'s variables and even further.

The other part of the challenge consist in to parse strings like
`"x={x} x^2={x**2}"`. I played a lot with Python's `string.Formatter`
when I implemented [xview](https://github.com/bad-address/xview),
a `hexdump`-like utility for [iasm](https://github.com/bad-address/iasm)
an interactive assembler.

In particular, the `get_field` method of `string.Formatter` gets called
each time the parser finds a `"{x}"`.

The idea is to *eval* `x` in the context of the caller's frame: this
will not only resolve variables like `x` but also expressions like
`x**2`.

Combining all together:


```python
>>> from string import Formatter
>>> class LocalsFormatter(Formatter):
...     def __init__(self, caller_ix=1):
...         super().__init__()
...         self._caller_ix = caller_ix
...
...     def vformat(self, fmt, args, kargs):
...         stack = inspect.stack()
...         args, kargs = self._augment_eval_context(stack, args, kargs)
...         return super().vformat(fmt, args, kargs)
...
...     def format(self, fmt, *args, **kargs):
...         stack = inspect.stack()
...         args, kargs = self._augment_eval_context(stack, args, kargs)
...         return super().vformat(fmt, args, kargs)
...
...     def _augment_eval_context(self, stack, args, kargs):
...         caller = stack[self._caller_ix]
...         frame = caller.frame
...         ctx = dict(frame.f_locals) # ensure a copy
...         ctx.update(kargs)
...         return args, ctx
...
...     def get_field(self, field_name, args, kargs):
...         val = eval(field_name, None, kargs)
...         return val, field_name
```

`caller_ix` is the index of the frame in the stack that we want to use
as the context for the evaluation.

`caller_ix == 1` means use the caller of `format()` or `vformat()`;
`caller_ix == 2` means use the caller of the caller of
`format()`/`vformat()`

`string.Formatter` implements `format` calling `vformat` but that would
introduces another frame in the stack *shifting* the caller index.

To simplify I redefined `format` and `vformat` to get the stack from
*their point of view* and only then call other methods.

### Examples

Let's see how it works:

```python
>>> def printf(fmt):
...     f = LocalsFormatter(caller_ix=2)
...     print(f.format(fmt))

>>> x=123
>>> y=456
>>> printf("{x+y}")
579
```

This also includes calling methods and functions:

```python
>>> l=[1,2,3]
>>> printf("{l} {l.__len__()} {len(l)}")
[1, 2, 3] 3 3
```

Closures should work too:

```python
>>> def outter():
...     outter_y = 1
...     def inner():
...         nonlocal outter_y
...         printf("{outter_y}")
...     inner()

>>> outter()
1
```

I thought that I could cache the result of an expression and reuse it
if it was used in the format string more than once.

But then I realize that would not work in some edge-cases:

Considere the following edge-case using a closure and notice
how `inc()` is called three times.

```python
>>> def counter(start):
...     start -= 1
...     def inc():
...         nonlocal start
...         start += 1
...         return start
...     return inc

>>> inc = counter(0)
>>> printf("{inc()}, {inc()}, {inc()}")
0, 1, 2
```

`LocalsFormatter` can also use the user-provided variables
that will take precedence:

```python
>>> def printf(fmt, *args, **kargs):
...     f = LocalsFormatter(caller_ix=2)
...     print(f.vformat(fmt, args, kargs))

>>> x = 42
>>> y = 33
>>> printf("x={x} y={y}", x=27)
x=27 y=33
```


If a variable cannot be found, an error will be shown

```python
>>> def inner():
...     printf("{outter_y}")

>>> def outter():
...     outter_y = 1
...     inner()

>>> outter()
<...>
NameError: name 'outter_y' is not defined
```

