---
layout: post
title: "Fresh Python Defaults"
tags: [Python]
inline_default_language: python
---

When defining a Python function you can define the default value
of its parameters.

The defaults are evaluated *once* and bound to the function's signature.

That means that *mutable* defaults are a bad idea: if you modify them in
a call, the modification will persist cross calls because for Python
its is the same object.

```python
>>> def foo(a, b='x', c=[]):
...     b += '!'
...     c += [2]
...     print(f"a={a} b={b} c={c}")

>>> foo(1)  # uses the default list
a=1 b=x! c=[2]

>>> foo(1)  # uses the *same* default list
a=1 b=x! c=[2, 2]

>>> foo(1, 'z', [3]) # uses another list
a=1 b=z! c=[3, 2]

>>> foo(1)  # uses the *same* default list, again
a=1 b=x! c=[2, 2, 2]
```

A mutable default can be used as the function's private state
as an alternative to functional-traditional *closures* and
object-oriented classes.

But in general a mutable default is most likely to be a bug.

Could Python have a way to prevent such thing? Or better, could Python
have a way to *restart* or *refresh* the mutable defaults in each
call?

This question raised up in the `python-list`{.none}. Let's see how far we get.<!--more-->


## Signatures

The beauty of most dynamic languages is the ability to reason about
themselves.

```python
>>> import inspect
>>> inspect.signature(foo)
<Signature (a, b='x', c=[2, 2, 2])>
```

`inspect.signature` does not retrieve the *"static"* signature of `foo`
but its *current-alive* signature. That's why we get `c=[2, 2, 2]`
instead of `c=[]`.

While `Signature` is an immutable object, `Signature` parameters' defaults
aren't:

```python
>>> sig = inspect.signature(foo)
>>> sig.parameters['c'].default.clear() # clear c's default list

>>> foo(1)  # uses the same but "refreshed" default list
a=1 b=x! c=[2]

>>> sig.parameters['c'].default.clear() # clear for the next call
```

This is an interesting way to refresh default objects but `clear()`
is not universal: it works for `list`, `dict` and `set` but not for
user-defined objects.

Still, `inspect.signature` gives the name of the parameters that have
a default and it is a good starting point.

```python
>>> params = sig.parameters
>>> params_with_defaults = {
...     name: param for name, param in params.items()
...     if param.default is not param.empty
... }
```

## Mutability

No all the default objects need to be refreshed: immutable ones are
perfectly safe as their value, by definition, cannot change.

```python
>>> const_types = frozenset((
...     type(frozenset()),
...     type(tuple()),
...     type(None),
...     type(""),       # str
...     type(b""),      # bytes
...     type(1),        # int
...     type(1j),       # complex
...     type(0.1),      # float
...     type(True),     # bool
...     type(range(1)), # range
...     ))

>>> params_to_refresh = {
...     name: param for name, param in params_with_defaults.items()
...     if type(param.default) not in const_types
... }
```

`const_types` is not an exhaustive set, only the most common types are
there.

In fact we don't need to store the `param` objects as they are stored in the
function's signature anyways. The parameters' names are enough.

```python
>>> params_to_refresh = tuple(params_to_refresh.keys())
```

## Call arguments

When a function is called the function's parameters are *bound* with
the arguments.

```python
>>> bound = sig.bind(1, b='z')  # same as foo(1, b='z')
>>> arguments = bound.arguments
```

Python binds only the parameters that have an explicit value:

 - if a parameter *without* a default is not bound, `TypeError` is
raised.
 - if a parameter *has* a default it is left *unbound*.

This is perfect because we can know which parameters are not bound yet:

```python
>>> set(params) - set(arguments)
{'c'}
```

## Bind a copy

This is the idea: we check the unbound parameters and if they are not
immutable we copy their default values and *bind* the copy like if the
user would passed it *explicitly*.

```python
>>> from copy import deepcopy
>>> arguments['c'] = deepcopy(params['c'].default)
```

`c` not longer is unbound:

```python
>>> set(params) - set(arguments) # c is bound now
set()
```

Because there could be still unbound parameters, we can let Python
follow the normal path and bind them with the respective defaults.

```python
>>> bound.apply_defaults()
```

Finally we can emulate a function call like this:

```python
>>> foo(*bound.args, **bound.kwargs)
a=1 b=z! c=[2]
```

To call it again we need to create another copy from parameter's
default:

```python
>>> arguments['c'] = deepcopy(params['c'].default)
>>> foo(*bound.args, **bound.kwargs)
a=1 b=z! c=[2]
```

## Wrap up

We can pack all this nicely in a decorator

```python
>>> def fresh_defaults(func):
...     sig = inspect.signature(func)
...     params = sig.parameters
...
...     to_refresh = tuple(
...             name for name, p in params.items()
...             if p.default is not p.empty and type(p.default) not in const_types
...             )
...
...     def wrapped(*args, **kargs):
...         bound = sig.bind(*args, **kargs)
...         arguments = bound.arguments
...
...         for name in to_refresh:
...             if name not in arguments:
...                 default = params[name].default
...                 arguments[name] = deepcopy(default)
...
...         bound.apply_defaults()
...
...         return func(*bound.args, **bound.kwargs)
...     return wrapped
```

Enjoy!

```python
>>> @fresh_defaults
... def foo(a, b='x', c=[]):
...     b += '!'
...     c += [2]
...     print(f"a={a} b={b} c={c}")

>>> foo(1)  # uses a copy of the default list
a=1 b=x! c=[2]

>>> foo(1)  # uses fresh copy of the default list
a=1 b=x! c=[2]

>>> foo(1, 'z', [3]) # uses another list
a=1 b=z! c=[3, 2]

>>> foo(1)  # uses another fresh default list.
a=1 b=x! c=[2]
```
