---
layout: home
---

## 3rd Parties - Stuff written by someone else

### Bit Twiddling Hacks by Sean Eron Anderson

A quite
[large collection of ingenious bit tricks](https://graphics.stanford.edu/~seander/bithacks.html):
counting bits,
reversing sequences, swapping, log/power 2 functions.

Some of them are already implemented by modern compilers so the
performance improvement is marginal but still it is worth reading.

### Disasters I've seen in a microservices world by João Alves

And "I saw them too", I would like to add. The post enumerates
the [dark side of the microservices.](https://world.hey.com/joaoqalves/disasters-i-ve-seen-in-a-microservices-world-a9137a51).

Today (~2020), microservices are seen as the magic solution where
everyone is happy and the development is easy and fast, nothing like
the old monolithic code.

People confuse microservices with modularity. Most of the benefits
of microservices comes from modularity: low coupling high cohesion.

It is not an exclusive property of microservices. What it is exclusive
(or at least very characteristic of them) is the separation in several
programs, even running in different machines.

This brings a new whole of challenges that most of the developers
(~2020) are not aware of.

Timeouts, retries, too many hops and inconsistent states are a few of
the classic problems that developers must face.

> "When people started to write services to generate CSVs. Why would
> someone introduce network hops to produce a worldwide known file format?
> Who would maintain that?
> Some teams were suffering from *servicitis*."

I know, I saw that too.

### The TTY demystified by Linus Åkesson

That thing that we call *terminal* is much more than you think.

The post [goes deeper in the rabbit
hole](http://www.linusakesson.net/programming/tty/index.php) and
explores the internals of the TTYs.

[Kernel's docs](https://www.kernel.org/doc/Documentation/serial/tty.rst)
can complement the reading.
