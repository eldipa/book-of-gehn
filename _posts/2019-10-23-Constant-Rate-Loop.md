---
layout: post
title: Constant Rate Loop
---

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
...     f = frames[it % n]
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
 [<i class="fab fa-github"></i> code](https://github.com/eldipa/book-of-gehn/blob/master/assets/distributing/constant_rate/examples/clock_drift.py)' %}

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
...             lost = (behind - behind % rate)
...             rest = rate - behind % rate
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

That's the happy path. But what happen if ``func()`` is too slow and takes more
time than the expected for one iteration?

First we determinate how much time we lost:

```python
    behind = -rest  # this is always positive
    lost = (behind - behind % rate)
```

Then, it is very likely that we are in some point in the middle, and incomplete
iteration, so we calculate how much time we should sleep to synchronize
ourselves with the *next* iteration:

```python
    rest = rate - behind % rate
    t1 += lost
```

The ``t1 += lost`` is crucial otherwise ``t1`` will be always behind like
if the following ``func()`` calls were always too slow.

Full code in [<i class="fab fa-github"></i> github](https://github.com/eldipa/book-of-gehn/blob/master/assets/distributing/constant_rate/constant_rate.py).

### Synchronization on Drops

The ``func()`` may need to know when it is not being called
as expected, when some iterations are being dropped.

{% marginfigure 'Bite' 'assets/distributing/constant_rate/examples/bite.gif'
'Same animation that last 1 second in a loop. From top to down, the first
is an animation without any frame lost, the second had lost some frames
but ``draw()`` is still in sync, the last one lost the same amount
of frames but ``draw()`` used its own notion of time an got out of sync.
 [<i class="fab fa-github"></i> code](https://github.com/eldipa/book-of-gehn/blob/master/assets/distributing/constant_rate/examples/drop_iterations.py)' %}

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
 [<i class="fab fa-github"></i> code](https://github.com/eldipa/book-of-gehn/blob/master/assets/distributing/constant_rate/examples/drop_iterations.py)' %}

## Known Uses

Game and rendering loops.

## Also Known as

Frame-rate limiting.

### Attributions

The *werewolf* images were made by
[MindChamber](https://opengameart.org/users/mindchamber), licensed CC-BY 3.0,
from [OpenGameArt](https://opengameart.org/content/dark-saber-werewolf)
