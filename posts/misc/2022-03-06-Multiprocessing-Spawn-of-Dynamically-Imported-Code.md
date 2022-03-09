---
layout: post
title: "Multiprocessing Spawn of Dynamically Imported Code"
tags: [python]
inline_default_language: python
---

The following snippet loads any Python module in the `./plugins/`
folder.

This is the Python 3.x way to load code dynamically.

```python
>>> def load_modules():
...     dirnames = ["plugins/"]
...     loaded = []
...
...     # For each plugin folder, see which Python files are there
...     # and load them
...     for importer, name, is_pkg in pkgutil.iter_modules(dirnames):
...
...         # Find and load the Python module
...         spec = importer.find_spec(name)
...         module = importlib.util.module_from_spec(spec)
...         spec.loader.exec_module(module)
...         loaded.append(module)
...
...         # Add the loaded module to sys.module so it can be
...         # found by pickle
...         sys.modules[name] = module
...
...     return loaded
```

The loaded modules work as any other Python module. In a plugin system
you typically will lookup for a specific function or a class that will
serve as entry point or hooks for the plugin.

For example, in [byexample](https://byexamples.github.io/byexample/contrib/how-to-support-new-finders-and-languages) 
the plugins must define classes that inherit from
`ExampleFinder`, `ExampleParser`, `ExampleRunner` or `Concern`. These
extend `byexample` functionality to find, parse and run examples in
different languages and hook --via `Concern`-- most of the execution
logic.

Imagine now that one of the plugins implements a function `exec_bg` that
needs to be executed in background, in a **separated Python process**.

We could do something like:

```python
>>> loaded = load_modules() # loading the plugins
>>> mod = loaded[0] # pick the first, this is just an example

>>> target = getattr(mod, 'exec_bg')  # lookup plugin's exec_bg function

>>> import multiprocessing
>>> proc = multiprocessing.Process(target=target)
>>> proc.start()    # run exec_bg in a separated process
>>> proc.join()
```

This is plain simple use of `multiprocessing`.... and it will **not**
work.

Well, it *will* work in Linux but not in MacOS or Windows.

In this post I will show why it will **not** work for dynamically loaded
code (like from a plugin) and how to fix it.<!--more-->

## `multiprocessing`'s start method

To gain truly parallelism in Python you need to use `multiprocessing`.

`multiprocessing.Process` takes a target callable and an optional list of
arguments and runs it in a separated Python process.

{% call marginnotes() %}
Actually there is a third mechanism, `forkserver`, but it works
similar and suffers from the same issues that `spawn`.
{% endcall %}

There are two mechanisms to have this separated Python process
running: you can `fork` the main process getting a copy of the Python
process or you can `spawn` a **fresh new** Python process.

This is the so called *start method* for `multiprocessing`.

`fork` is the default in Linux and it is the fastest. When the child
process gets alive, it is immediately ready to execute the target
callable: it has access to all the global state of the parent (a copy),
it has access to the target code to call and to its arguments.

*Ready to rumble.*

On the other hand `spawn` starts a **fresh new** Python server that has
no idea of the state or the code loaded in the parent process.

The parent needs to share to the child server the target callable and
its arguments via a pipe and for the serialization it uses `pickle`.

{% call marginnotes() %}
While technically `fork` should work fine in multithreaded apps, some
very common multithreaded libs in MacOS do not work well.
This brought [some headaches](https://bugs.python.org/issue33725)
in the past and since Python 3.8 `spawn` is the default in MacOS.

In Linux the most common multithreaded libs are prepared for `fork`
so the risk is minimum (I would like to say zero but, you know, ...)
{% endcall %}

`spawn` is slightly slower than `fork` but it is thread-safe and the
default in MacOS and Windows.

## `pickle`-ing a callable

So, what does it mean to `pickle` a callable?

One could think that the serialization is the dump of the bytecode of
the callable but `pickle` is less sophisticated.

`pickle.dumps(a_callable)` just dumps enough information so
`pickle.loads()` can **load the code** again.

Here are a few examples:

```python
>>> import pickle
>>> import re

>>> pickle.dumps(re.match)
b'\x80\x04\x95\x10\x00\x00\x00\x00\x00\x00\x00\x8c\x02re\x94\x8c\x05match\x94\x93\x94.'

>>> c = re.compile('')

>>> pickle.dumps(c.match)
b'\x80\x04\x95?\x00\x00\x00\x00\x00\x00\x00\x8c\x08builtins\x94\x8c\x07getattr\x94\x93\x94\x8c\x02re\x94\x8c\x08_compile\x94\x93\x94\x8c\x00\x94K \x86\x94R\x94\x8c\x05match\x94\x86\x94R\x94.'
```

There is no need to go into the details, we can use the intuition here.

`re.match` is a function so the only thing that we need to reload it is
where to find it. In the output of `pickle.dumps` we can see the strings
`re` and `match`.

For `c.match` is different. This is a *bound method*, so it is more
complex and involves modules (`builtins`, `re`) and functions/methods
(`getattr`, `match`) and some more bits.

So, what happen on `pickle.loads()` ?

`pickle` imports any necessary
module (`builtins`, `re`) and from there loads the code.

*It is like a recipe of how to (re)import the callable.*

{% call marginnotes() %}
`pickle` is not the only way to serialize things.
[dill](https://pypi.org/project/dill/) extends `pickle` and supports
much more things including `lambda` functions.
{% endcall %}

Not all the callable can be serialized however: `lambda` for example cannot be
imported from a module so they cannot be serialized.

## Not such module

Now why the following fails may be more obvious. Let's recap:

```python
>>> loaded = load_modules() # loading the plugins
>>> mod = loaded[0] # pick the first, this is just an example

>>> target = getattr(mod, 'exec_bg')  # lookup plugin's exec_bg function

>>> import multiprocessing
>>> proc = multiprocessing.Process(target=target)
>>> proc.start()    # run exec_bg in a separated process
>>> proc.join()
```

The child process, *spawned* by the parent, tries to unpickle the
`target` function and for such it will try to import the module `mod`.

The module is not loaded yet and not present in `sys.modules` in the
child process because it is a fresh Python process.

`pickle.loads()` does a normal `import` as usual but the module
`mod` will *not be found*, it is **not** a module in the standard path
(`sys.path`) but a module loaded from an arbitrary folder (`./plugins/`)

`pickle.loads()` just cannot know that!

That's why you cannot use
`multiprocessing` naively with dynamically imported code: the child
process has no idea how to load it!

This [issue](https://github.com/byexamples/byexample/issues/220)
hit `byexample` when a third-party plugin tried to run
in a subprocess part of its code in MacOS.

{% call marginnotes() %}
Well, it *is* possible to trigger it in Linux, you just need to change
the start method of `multiprocessing` calling `set_start_method()` or
`get_context()`.
{% endcall %}

In Linux, with `fork` being the default, no `pickle` is needed and
the bug was never triggered.

## The fix

What we need is to (re)load all the dynamically loaded modules in the
child process **before** the `pickle.loads()` takes place.

Instead of calling `target` on the child directly, we call a helper `trampoline`
that does the bootstrap, loads the modules, unpickles the real
`target` and calls it.

```python
>>> loaded = load_modules() # loading the plugins
>>> mod = loaded[0] # pick the first, this is just an example

>>> def trampoline(serialized_func):
...     # All of this happens in the *child* process
...     # We reload the modules (and possible we do any bootstrapping
...     # needed)
...     loaded = load_modules()
...
...     # Now this pickle.loads() shouldn't fail
...     target = pickle.loads(serialized_func)
...     return target()

>>> # We pickle the target ourselves so we can control *when*
>>> # it is unpickled later.
>>> target = getattr(mod, 'exec_bg')
>>> serialized_func = bytes(pickle.dumps(target))

>>> import multiprocessing
>>> proc = multiprocessing.Process(target=trampoline, args=(serialized_func,))
>>> proc.start()
>>> proc.join()
```

### `ForkingPickler`: a detail

To be more precise, `multiprocessing` uses a slightly improved `pickle`
implemented in `multiprocessing.reduction.ForkingPickler`.

We should use it too to keep the same behavior.

```python
>>> def trampoline(serialized_func):
...     # .....
...
...     fpickler = multiprocessing.reduction.ForkingPickler
...     target = fpickler.loads(serialized_func)
...     return target()

>>> fpickler = multiprocessing.reduction.ForkingPickler

>>> target = getattr(mod, 'exec_bg')
>>> serialized_func = bytes(fpickler.dumps(target))

>>> # ....
```
