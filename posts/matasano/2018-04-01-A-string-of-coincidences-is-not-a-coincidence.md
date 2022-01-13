---
layout: post
title: "A string of coincidences is not a coincidence"
tags: [cryptography, matasano, cryptonita, index coincidence]
inline_default_language: python
---

A cipher is *semantically secure* if given a randomly chosen key, its ciphertext
cannot be distinguishable from a truly random string.

Detecting a ciphertext from a pool is enough to consider
the cipher as not secure even of we can't break it.

In the following pool of random strings one is actually a ciphertext
that is the ``xor`` encryption of a plaintext using a single-byte key.

```python
>>> from cryptonita import B, load_bytes     # byexample: +timeout=10
>>> ciphertexts = list(load_bytes('./assets/matasano/4.txt', encoding=16))

>>> methods = {}
```

{{ spoileralert() }}

This is obviously a poor and not secure encryption mechanism; let's find
the ciphertext then!<!--more-->

## Distinguish a ciphertext

{% call marginnotes() %}
[Detect single-character XOR](https://cryptopals.com/sets/1/challenges/4)
challenge
{% endcall %}

The basic idea is that some patterns in the plaintext are propagated
to the ciphertext and those we will be enough to distinguish it from
the rest of the pool.

### Index of coincidence

One possibility could be that the ciphertext shows more repeated bytes
(something that clearly is not random).

A string with a *lot of coincidences is not a coincidence*.

For this we can calculate the
[index of coincidences](https://en.wikipedia.org/wiki/Index_of_coincidence).

```python
>>> from cryptonita.scoring import icoincidences
>>> scores = [icoincidences(c) for c in ciphertexts]

>>> scores_and_indexes = [(s, i) for i, s in enumerate(scores)]
>>> scores_and_indexes.sort()
>>> scores_and_indexes[-3:] # higher values, less random
[(0.02298<...>, 101),
 (0.02988<...>, 102),
 (0.04597<...>, 170)]

>>> methods['Index of Coincidence'] = [1-s for s in scores]
```

### Entropy

The entropy measures the information that a sequence has based on
the probability of its events.

If all the events are equally likely, the sequence looks more random
and carry more information (or it has less redundancy if you want).

The entropy is defined as:

```tex;mathjax
S=\sum_{\forall p_{x}}p_{x}\textrm{log}_{n}\left(p_{x}\right)
```

Where each `p_{x}`{.mathjax} is the probability of the event
`x`{.mathjax} and
`n`{.mathjax} is the number of event types.

What is an event, it is up to you.

### Entropy at the bit level

The entropy is not an intrinsic value of the sample, it is a value relative
to a particular model.

If we are interested in only the individual bits we could set
two possible events: ``0`` and ``1``.

We can calculate the probability of each event as:

```python
>>> def bit_freq(x):
...     ones = x.count_1s()
...     zeros = (len(x)*8) - ones
...     return zeros, ones
```

A truly random string should yield ``[n/2, n/2]`` (half bits are ``1``,
the other half are ``0``.

Under this module, we can calculate the entropy for all
the strings in the pool:

```python
>>> import scipy.stats as stats
>>> scores = [stats.entropy(bit_freq(c), base=2) for c in ciphertexts]

>>> scores_and_indexes = [(s, i) for i, s in enumerate(scores)]
>>> scores_and_indexes.sort()
>>> scores_and_indexes[:4] # lower values, less random
[(0.9097<...>, 311),
 (0.9182<...>, 230),
 (0.9377<...>, 68),
 (0.9377<...>, 138)]

>>> methods['Entropy bit-level'] = [s for s in scores]
```

The entropy defined as we did performed poorly as discriminant.

This is because we are are considering the bits independently one of each
other: the sequence ``0101010101`` has the same amount of ``1`` and ``0``
so its a entropy is 1.0 and it would look random because the model
doesn't capture a pattern of more than one bit.

To be effective, *the entropy must have a useful model*.

### Entropy at the byte level

We could change the model as define the byte as the unit for the entropy:

```python
>>> def byte_freq(x):
...     f = [0] * 256
...     for b in x:
...         f[b] += 1
...     return f
```

This time, the entropy is:

```python
>>> scores = [stats.entropy(byte_freq(c), base=256) for c in ciphertexts]

>>> scores_and_indexes = [(s, i) for i, s in enumerate(scores)]
>>> scores_and_indexes.sort()
>>> scores_and_indexes[:4] # lower values, less random
[(0.4983211558075781, 170),
 (0.5399878224742447, 102),
 (0.5404039285997025, 101),
 (0.548737261933036, 232)]

>>> methods['Entropy byte-level'] = [s for s in scores]
```

Much better!

### Entropy at xor level

Remember that the ciphertext that we are looking for was encrypted doing
a xor with a single byte.

Therefore we could use the first byte and xor it with the rest of the
string.

If the string is random, the xor will just shuffle more bits and the string
will remain random.

But if it is not the xor will remove the entropy added by the key from the
ciphertext and it should be easier to spot because the resulting string
will be the xor of two ASCII strings.

```python
>>> ascii_bytes = [n for n in range(32, 127)] + [n for n in range(9, 14)]
>>> ascii_xor_set = set([a ^ b for a in ascii_bytes for b in ascii_bytes])
>>> def in_xor_set_freq(x):
...     f = [0] * 2
...     y = B(x[0]).inf() ^ B(x[1:])
...     for b in y:
...         f[b in ascii_xor_set] += 1
...
...     return f

>>> scores = [stats.entropy(in_xor_set_freq(c), base=2) for c in ciphertexts]

>>> scores_and_indexes = [(s, i) for i, s in enumerate(scores)]
>>> scores_and_indexes.sort()
>>> scores_and_indexes[:10] # lower values, less random
[(0.0, 35),
 (0.0, 149),
 (0.0, 165),
 (0.0, 170),
 (0.0, 195),
 (0.0, 225),
 (0.0, 230),
 (0.0, 289),
 (0.0, 295),
 (0.21639693245126465, 8)]

>>> methods['Entropy xor-level'] = [s for s in scores]
```

Interesting, this method has more false positives than others but at the
same time, this method makes a clear distinction between a few really non
random strings and the rest of the strings in the pool.

### Kolmogorov complexity

As an alternative way to see this, a random string cannot be compressed. So
the string with the shortest compressed version will be likely to be a
non-random string.

```python
>>> import lzma
>>> def compress_score(x):
...     return len(lzma.compress(x.tobytes(), lzma.FORMAT_ALONE))

>>> scores = [compress_score(c) for c in ciphertexts]

>>> scores_and_indexes = [(s, i) for i, s in enumerate(scores)]
>>> scores_and_indexes.sort()
>>> scores_and_indexes[:3] # lower values, less random
[(53, 170), (55, 3), (55, 8)]

>>> methods['Kolmogorov Complexity'] = [s for s in scores]
```

It works.... slowly, but it works.

## Break it

Now let's break the ciphertext using a frequency attack (implemented in
[cryptonita](https://pypi.org/project/cryptonita/)).

```python
>>> from cryptonita.scoring import all_ascii_printable         # byexample: +timeout 10
>>> from cryptonita.attacks import brute_force, freq_attack
>>> most_common_plain_ngrams = [B(b) for b in 'etaoin shrdlu']

>>> ciphertext = ciphertexts[170]

>>> keys = freq_attack(ciphertext, most_common_plain_ngrams, 1)
>>> keys = brute_force(ciphertext, all_ascii_printable, keys)

>>> len(keys)
3
```

We narrow this down to 3 keys only. I'll do a little cheat here

```python
>>> B('5') in keys
True

>>> ciphertext ^ B('5').inf()
'Now that the party is jumping\n'
```

## Conclusion

Claiming that a string is uniformly random if *far from trivial*.

Even the NSA battery tests for randomness fail to measure the randomness
of crafted strings.

Here is the plot of the scores calculated by the different methods:

{% call fullfig('scores_by_method.png') %}
Scores by method. Notice how the element 170th gets the lower value in most cases indicating that the string is not random.
{% endcall %}

<br />

<!--
>>> import sys
>>> sys.path.append("./assets/plotting")

>>> from plotting import plt, show                      # byexample: +timeout=20
>>> import pandas as pd                                 # byexample: +timeout=20

>>> methods = pd.DataFrame(methods)

>>> def min_max_normalizer(c):
...     return (c - c.min()) / (c.max() - c.min())

>>> methods = methods.apply(min_max_normalizer, axis=0)

>>> with show(save='./assets/matasano/scores_by_method.png', latexify_kargs={'columns':2}): # byexample: +timeout=600 +skip
...     axes = methods.plot(style='o', subplots=True, layout=(3, 2))
...
...     _ = [ax.vlines(170, 0, 1, linestyles='dashed') for ax in axes.flat]
-->
