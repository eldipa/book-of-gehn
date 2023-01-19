---
layout: post
title: "Breaking MT19937 Crypto"
tags: [cryptography, matasano, cryptonita, MT19937, PRG]
inline_default_language: python
---

The Mersenne-Twister 19937 or just MT19937 is one of the most
used pseudo random number generator with a quite large cycle length
and with a nice random quality.

However it was not designed to be used for crypto.

{{ spoileralert() }}
But some folks may not know this...<!--more-->

## Warming up

{#
<!--
>>> import sys
>>> sys.path.append("./posts/matasano/assets")
>>> from challenge import generate_config            # byexample: +timeout=10

>>> seed = 20181223
>>> cfg = generate_config(random_state=seed)
-->
 #}

Before anything, let's
[implement the MT19937 Mersenne Twister RNG](https://cryptopals.com/sets/3/challenges/21)

For testing, I'm going to use the following
[test vector](https://gist.githubusercontent.com/mimoo/8e5d80a2e236b8b6f5ed/raw/20a704e0ccb3d50ea574cf6fe81fcb07cd9a66a3/gistfile1.txt)

```python
>>> from cryptonita.attacks.prng import MT19937
>>> from cryptonita import B

>>> f = open('posts/matasano/assets/MT19937.vector', 'rt')
>>> seed = int(f.readline())

>>> expected_rnd_seq = [int(line) for line in f]

>>> g = iter(MT19937(seed))
>>> gen_rnd_seq = [next(g) for i in range(len(expected_rnd_seq))]

>>> expected_rnd_seq == gen_rnd_seq
True
```

## Cracking (seed space exploration)

It is quite common to find people that use the current time
as their *secret* seed for the generator.

Some even say *"but I'm using 64 bits with microsecond resolution
so it will impossible to find it by brute force"*

```python
>>> import time
>>> secret_seed = int(time.time())
>>> x = next(iter(MT19937(secret_seed)))
```

Exploring 64 bits is quite hard but the seed is **not random**,
therefore
we do not need to explore the *whole space* but a **smaller space**.

Instead we just explore the numbers in the vicinity of the current time
which turns the
[crack an MT19937 seed](https://cryptopals.com/sets/3/challenges/22)
into a much simpler task.

First, assuming that we known the first output of the PRNG, we build an
oracle function to tell if we have found or not the secret seed.

```python
>>> from functools import partial

>>> def MT19937_oracle(seed, first_known_output):
...     g = iter(MT19937(seed))
...     return next(g) == first_known_output

>>> oracle = partial(MT19937_oracle, first_known_output=x)
```

Then, it just rest to test the seed space starting from an *educated guess*
for the secret seed.

For example we could guess that the seed is between 2048 seconds ago and
2 times that in the future.

```python
>>> delta = 2048
>>> start = int(time.time()) - delta
>>> stop = start + delta*2
```

Now we test each possible seed in that range. `search` is a handy
function for testing that implements some heuristics like trying first
the numbers in the middle of the range before in the extremes.

```python
>>> from cryptonita.attacks import search    # byexample: +timeout=10
>>> search(start, stop, oracle, likely='middle') == secret_seed      # byexample: +timeout=10
True
```

Gotcha!

## Cloning

{% call marginnotes() %}
Formally, there is not such efficient algorithm that allow an attack
to distinguish even with a small probability for large but finite
sequences. Eventually with a *really large* sequences the attacker may
break it.
{% endcall %}

A property that all PRNG cryptographically secure must hold is that
even if the attacker knows the partial output of the PRNG he cannot distinguish
it from a truly random sequence.

In particular he cannot predict any future output.

The MT19937 does not hold this and it is possible to
[clone an MT19937 RNG from its output](https://cryptopals.com/sets/3/challenges/23)
allowing an attacker to predict any future value:

```python
>>> from cryptonita.attacks.prng import clone_mt19937               # byexample: +timeout=10

>>> g = iter(MT19937(secret_seed))
>>> out = [next(g) for i in range(624)]

>>> cg = iter(clone_mt19937(out))

>>> all((next(g) == next(cg)) for i in range(624))
True
```

The fundamental problem of the MT19937 is that part of the
output generation is a *reversible* operation.

{% call marginnotes() %}
And this is how we could make the MT19937 a little harder:
make the operation non-invertible *and* making each output
byte a function based on the whole secret state adding more
entropy and shuffling into the mix.
{% endcall %}

And because each output byte has a dependency with one and
just one single secret byte, from that output byte an attacker
can get the single secret byte.

For a 624 output samples, the full secret state of the MT19937
can be obtained.

## Cracking a cipher based on a MT19937

From a pseudo random generator we can build a stream of pseudo random bytes,
just seeing each number as 4 or 8 bytes:

```python
>>> from cryptonita.conv import repack          # byexample: +timeout=10

>>> prng = iter(MT19937(cfg.n16))
>>> kstream = repack(prng, ifmt='>I', ofmt='>BBBB')
```

Given this stream we can build a stream cipher just xoring the random stream
with the plaintext in a similar way like CTR works

```python
>>> secret = cfg.lnonce     # quite large random "secret" stuff
>>> ciphertext = B(s ^ next(kstream) for s in secret)

>>> clen = len(ciphertext)
>>> clen
128
```

Now, let's assume that we know some part of the plaintext from
an unknown position:

```python
>>> at = cfg.n8 % (clen-8)
>>> known_plaintext = secret[at:at+8]

>>> plen = len(known_plaintext)     # quite arbitrary, it could work with less
>>> plen
8
```

{% call marginnotes() %}
[Create the MT19937 stream cipher and break it](https://cryptopals.com/sets/3/challenges/24)
{% endcall %}

Because the cipher does not use a *random* secret key (the seed),
it is possible to break this ciphering.

First, lets see all the possible substrings of the same length than
the known plaintext:

```python
>>> cngrams = ciphertext.ngrams(plen)
```

Then we could try to xor them with the plain text: all except one
of the substring will be just garbage but one will be part of
the original secret key stream product of the PRNG.

```python
>>> pngrams = [c ^ known_plaintext for c in cngrams]
```

Of course we do not know which substring is garbage and which is not.

Out best strategy is to generate a long enough key stream with our
guessed seed and see if a substring matches or not.

```python
>>> def oracle(seed):
...     g = iter(MT19937(seed))
...     tmp = repack(g, ifmt='>I', ofmt='>BBBB')
...     stream = B(next(tmp) for _ in range(clen))
...
...     sngrams = stream.ngrams(plen)
...     count = sum(s == p for s, p in zip(sngrams, pngrams))
...     return count == 1

>>> seed = search(0, 2**16, oracle)                         # byexample: +timeout=300
>>> prng = iter(MT19937(seed))
>>> kstream = repack(prng, ifmt='>I', ofmt='>BBBB')

>>> B(c ^ next(kstream) for c in ciphertext) == secret
True
```
