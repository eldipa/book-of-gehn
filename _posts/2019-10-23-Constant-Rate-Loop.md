---
layout: post
title: Constant Rate Loop
---

{% marginfigure 'Bite' 'assets/distributing/constant_rate/examples/bite.gif'
'Same animation that last 1 second in a loop. From top to down, the first
is an animation without any frame lost, the second had lost some frames
but ``draw()`` is still in sync, the last one lost the same amount
of frames but ``draw()`` used its own notion of time an got out of sync.
 [<i class="fab fa-github"></i> code](https://github.com/book-of-gehn/book-of-gehn.github.io/blob/master/assets/distributing/constant_rate/examples/drop_iterations.py)'
'' 'in-index-only' %}

{% maincolumn 'assets/distributing/constant_rate/examples/rest-nodrop.png'
'' '' 'in-index-only' %}

{% maincolumn 'assets/distributing/constant_rate/examples/rest-drop.png'
'' '' 'in-index-only' %}

<!--more-->

## Motivation

Consider a ``draw()`` function that renders an animation. An animation
is just a list of images or frames that ``draw()`` will render
one frame per iteration.

```python
>>> def draw():
...     global it
...     it += 1     # pick the "next" frame
...
...     n = len(frames)
...     f = frames[it % n]  # keep looping
...
...     render(f)
```

To get the animation effect we want to call ``draw()`` in a loop.

We may do this:

```python
def loop():
    while True:
        draw()
```

But then the animation speed will be determinate by the speed of
the machine: faster machines will render faster animations.

Adding a ``sleep()`` solves this partially

```python
def fixed_sleep_loop():
    while True:
        draw()
        sleep(1/60)
```

{% marginfigure 'Clock drift' 'assets/distributing/constant_rate/examples/clock_drift.png'
'Plot the difference between the real time ``now()`` and the expected in
each iteration ``it * rate`` looping during 1 second at a rate of ``1/60``.
Using a *fixed sleep* loop the difference
increase linearly while using a *constant rate* loop the difference is
quite low and relatively constant.
 [<i class="fab fa-github"></i> code](https://github.com/book-of-gehn/book-of-gehn.github.io/blob/master/assets/distributing/constant_rate/examples/clock_drift.py)' %}

The problem is that we are not considering neither the time elapsed
in ``draw()`` nor the fact that ``sleep()`` may sleep more than it
should be.

> "If the interval specified not an exact multiple of the
> granularity underlying clock, then the interval will be rounded up to
> the next multiple. Furthermore, after the sleep completes, there may still be a
> delay before the CPU becomes free to once again execute the calling thread."
> From [nanosleep(2)](http://man7.org/linux/man-pages/man2/nanosleep.2.html)

This error is *accumulative*, increasing in each iteration, making
the ``draw()`` out of synchronization very quickly.

## Problem

You want to do an action every X time maintaining a constant rate.

## Solution

The idea is to have a loop that can call a function `foo()` every
X time, like a precise clock.

If the loop gets out of sync and begins to be *behind* schedule, the
loop needs to compensate somehow to catch up.

Two alternatives are possible: *drop & rest* and *no rest-keep working*

### If behind, drop & rest

```python
>>> def constant_rate_loop(func, rate):
...     t1 = now()
...     it = 0
...     while True:
...         func(it)
...
...         t2 = now()
...         rest = rate - (t2 - t1)
...         if rest < 0:
...             behind = -rest  # this is always positive
...             rest = rate - behind % rate
...             lost = behind + rest
...             t1 += lost
...             it += int(lost // rate)  # floor division
...
...         sleep(rest)
...         t1 += rate
...         it += 1
```

The difference between ``t2`` and ``t1`` yields how much time we were in the
``func()`` call.

In a normal situation, this should be *less* than the expected rate and
the loop sleeps the remaining time to complete the current iteration.

The *next* ``t1`` is increased by ``rate``: we don't call ``now()``
again otherwise will be introducing a clock drift due the extra
delays of ``sleep()``.


{% maincolumn 'assets/distributing/constant_rate/examples/rest-nodrop.png'
'' %}


That's the happy path.

But what happen if ``func()`` is too slow and takes more
time than the expected for one iteration?

First we determinate how much time we are *behind schedule*:

```python
    behind = -rest  # this is always positive
```

Then, it is very likely that we are in some point in the middle, and incomplete
iteration, so we calculate how much time we should sleep to synchronize
ourselves with the *next* iteration -- this is the *drop & rest*:

```python
    rest = rate - behind % rate
```

Finally, how many iterations we lost or skipped:

```python
    lost = behind + rest

    it += int(lost // rate)  # floor division
    t1 += lost
```

The ``t1 += lost`` is crucial otherwise ``t1`` will be always behind like
if the following ``func()`` calls were always too slow.

{% maincolumn 'assets/distributing/constant_rate/examples/rest-drop.png'
'The iteration 1 took too long and the iteration 2 was lost.
<br />
Note how the begin of the iteration 3 starts at the begin of
a new slot.' %}

Full code in [<i class="fab fa-github"></i> github](https://github.com/book-of-gehn/book-of-gehn.github.io/blob/master/assets/distributing/constant_rate/constant_rate.py).

### If behind, keep working

```python
>>> def constant_rate_loop(func, rate):
...     t1 = now()
...     it = 0
...     while True:
...         func(it)
...
...         t2 = now()
...         rest = rate - (t2 - t1)
...         if rest < 0:
...             behind = -rest  # this is always positive
...             lost = behind - behind % rate
...             t1 += lost
...             it += int(lost // rate)  # floor division
...         else:
...             sleep(rest)
...
...         t1 += rate
...         it += 1
```

Like in *drop & rest*, the happy path is the same: if we finish an
iteration before the deadline we take some rest until the next
iteration.

{% maincolumn 'assets/distributing/constant_rate/examples/rest-nodrop.png'
'' %}


{% marginfigure 'no rest keep working' 'assets/distributing/constant_rate/examples/norest-nolost.png'
'Iteration 2 is not dropped and begins as soon as possible.
<br />
Contrast this with the *drop & rest* strategy:
' %}

{% marginfigure 'drop and rest' 'assets/distributing/constant_rate/examples/rest-drop.png' '' %}

But if we are behind schedule we do something different: the last
partially consumed iteration is not considered lost.

```python
    lost = behind - behind % rate
```

While *drop & rest* consideres an
iteration lost if `func()` cannot be called at the begin of the
iteration, *no rest-keep working* consideres an iteration lost if
it was totally consumed without calling `func()`.

If there is room to call it even if it is not at the begin of the
iteration, *no rest-keep working* will call it immediately -- it will
not rest, it will keep working.

{% maincolumn 'assets/distributing/constant_rate/examples/norest-nolost.png'
'`func()` is called in the iteration 2 as soon as the previous finishes.
<br />
No rest is taken, trying to *catch up* as soon as possible without
loosing any frame even if that means call `func()` in the middle of an
iteration.
' %}

*No rest-keep working* is suitable for situations where we want to
minimize the drops; *drop & rest* is better when we want to call
`func()` at specific times even if we have to drop an iteration.

Of course, if `func()` spans 2 or more iterations, *no rest-keep
working* will be forced to drop the iterations in the middle.

{% maincolumn 'assets/distributing/constant_rate/examples/norest-lost.png'
'`func()` took more than 2 iterations to complete so the iteration
2 is considered lost.
' %}


### Synchronization on Drops

The ``func()`` may need to know when it is not being called
as expected, when some iterations are being dropped.

{% marginfigure 'Bite' 'assets/distributing/constant_rate/examples/bite.gif'
'Same animation that last 1 second in a loop. From top to down, the first
is an animation without any frame lost, the second had lost some frames
but ``draw()`` is still in sync, the last one lost the same amount
of frames but ``draw()`` used its own notion of time an got out of sync.
 [<i class="fab fa-github"></i> code](https://github.com/book-of-gehn/book-of-gehn.github.io/blob/master/assets/distributing/constant_rate/examples/drop_iterations.py)' %}

If ``draw()`` is too slow, the loop will drop some iterations as shown.

But ``draw()`` will never notice this and instead of *skipping* some frames
it will render the *next* frame *accordingly to him*.

The animation will appear smooth to the user but behind the scene
the ``draw()`` will be out of sync: the animation will take more time
to complete or it will be cut in the middle.

Instead, we can pass to ``func()`` the iteration number explicitly.

The ``draw()`` must be updated accordingly:

```python
>>> def draw(it):
...     n = len(frames)
...     f = frames[it % n]      # pick what correspond to "this" iteration
...
...     render(f)
```

In a normal situation, this is always an sequential number but
if iterations are being dropped, there will be *shifts* in the count
and ``draw()`` will skip some frames but it will remain in sync.

{% maincolumn 'assets/distributing/constant_rate/examples/bite_frames.png'
'The first row shows all the frames that forms the animation. The other two
are the frames plotted by a *slow* ``draw()`` with some frames dropped.
But the first ``draw()`` (second row) kept in sync while the other did not.
 [<i class="fab fa-github"></i> code](https://github.com/book-of-gehn/book-of-gehn.github.io/blob/master/assets/distributing/constant_rate/examples/drop_iterations.py)' %}

## Known Uses

Game and rendering loops.

## Also Known as

Frame-rate limiting.

### Attributions

The *werewolf* images were made by
[MindChamber](https://opengameart.org/users/mindchamber), licensed CC-BY 3.0,
from [OpenGameArt](https://opengameart.org/content/dark-saber-werewolf)
