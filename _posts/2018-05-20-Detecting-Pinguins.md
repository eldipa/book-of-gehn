---
layout: post
title: "Detecting Pinguins"
---

Can you see the pinguin?{% sidenote '**-- Spoiler Alert! --**' %}
<!--more-->

{% marginfigure '' 'assets/matasano/tux.png' 'The ECB encrypted image on the right
and its plaintext original version on the left. Image taken from
[wikipedia](https://en.wikipedia.org/wiki/Block_cipher_mode_of_operation).' %}


## Warming up

The following ciphertext was encrypted with AES in ECB mode (Electronic Code
Book) with the given key.

Decrypting is a piece of cake; this is just to get practice about
[AES in ECB mode](https://cryptopals.com/sets/1/challenges/7)

```python
>>> from cryptonita import B, load_bytes     # byexample: +timeout=10

>>> ciphertext = B(open('./assets/matasano/7.txt', 'rb').read(), 64)
>>> blocks = ciphertext.nblocks(16)

>>> key = B('YELLOW SUBMARINE')

>>> from Crypto.Cipher import AES
>>> plaintext = b''.join(AES.new(key, AES.MODE_ECB).decrypt(b) for b in blocks)

>>> print(plaintext)
b"I'm back and I'm ringin' the bell<...>Play that funky music \n\x04\x04\x04\x04"
```

## Detecting Pinguins

If two plaintext *blocks* are the same, ECB
will encrypt them to the *same* ciphertext block.

[Detect AES in ECB mode](https://cryptopals.com/sets/1/challenges/8)
from a pool of random strings is easy.

This is possible because if the plaintext has two or more equal blocks,
the ciphertext will have the same pattern and therefor it will have
more duplicated bytes than the expected from a random string.

We can use the same technique done in
[the previous post](/book-of-gehn/articles/2018/04/01/A-string-of-coincidences-is-not-a-coincidence.html).

```python
>>> ciphertexts = list(load_bytes('./assets/matasano/8.txt', encoding=16))

>>> from cryptonita.scoring import icoincidences
>>> scores = [icoincidences(c) for c in ciphertexts]

>>> scores_and_indexes = [(s, i) for i, s in enumerate(scores)]
>>> scores_and_indexes.sort()
>>> scores_and_indexes[-3:] # higher values, less random
[(0.00526729<...>, 92),
 (0.00526729<...>, 173),
 (0.01305031<...>, 132)]

>>> methods = {}
>>> methods['IC - Byte sequence'] = scores
```

Instead of working at the byte level, we can work with blocks:
a coincidence of two or more blocks is much less likely to be random
than a coincidence of two or more bytes:

```python
>>> scores = [icoincidences(c.nblocks(16)) for c in ciphertexts]

>>> scores_and_indexes = [(s, i) for i, s in enumerate(scores)]
>>> scores_and_indexes.sort()
>>> scores_and_indexes[-1:] # higher values, less random
[(0.133333333<...>, 132)]

>>> methods['IC - Nblocks sequence'] = scores
```

{% fullwidth 'assets/matasano/score_pinguins.png' 'Scores by methods. For the Nblocks method, the size of the block is of 16 bytes.' %}

<br />

<!--
>>> import sys
>>> sys.path.append("./assets/plotting")

>>> from plotting import plt, show                      # byexample: +timeout=10
>>> import pandas as pd                                 # byexample: +timeout=10

>>> methods = pd.DataFrame(methods)

>>> def min_max_normalizer(c):
...     return (c - c.min()) / (c.max() - c.min())

>>> methods = methods.apply(min_max_normalizer, axis=0)

>>> with show(save='./assets/matasano/score_pinguins.png', latexify_kargs={'columns':2}): # byexample: +timeout=600 +skip
...     axes = methods.plot(style='o', subplots=True, layout=(2, 1))
...
...     _ = [ax.vlines(132, 0, 1, linestyles='dashed') for ax in axes.flat]
-->

### Break it?

Well, it is not possible to break AES easily,
may be a *dictionary attack*?.

The 132th plaintext  will remain encrypted, for now.

