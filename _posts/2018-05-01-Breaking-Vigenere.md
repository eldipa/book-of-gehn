---
layout: post
title: "Breaking Vigenere"
---

A plaintext was encrypted via a XOR with key of unknown bytes of length,
repeating this key as much as needed to cover the full length of
the plaintext.

This is also known as the
[Vigenere cipher](https://en.wikipedia.org/wiki/Vigen%C3%A8re_cipher).

It is 101 cipher, which it is easy to break in theory, but it has more than
one challenge hidden to be resolve in the practice.

Shall we?{% sidenote '**-- Spoiler Alert! --**' %}<!--more-->

## Guessing the length of the key

``guess_key_length`` will score each possible length using a scoring
function.

For this, we will explore the full range of possible lengths from 1 to 40
and we will score each one with the
[Hamming Distance](https://en.wikipedia.org/wiki/Hamming_distance).

```python
>>> from cryptonita.bytestring import B, load_bytes     # byexample: +timeout=10

>>> ciphertext = B(open('./assets/matasano/6.txt', 'rb').read(), 64)

>>> from cryptonita.attacks import guess_key_length
>>> from cryptonita.scoring import key_length_by_hamming_distance

>>> lengths_hd = guess_key_length(ciphertext, length_space=40,
...                            score_func=key_length_by_hamming_distance)

```

There isn't a single response, of course.

This method *guesses* the length of
the key so we have a set of possible values, ones more likely than
others.

For this, ``guess_key_length`` returns a
[Fuzzy Set](https://en.wikipedia.org/wiki/Fuzzy_set) where each possible
length has a probability linked to it.

We could cut the set further and keep only the top 5 more likely lengths:

```python
>>> l = lengths_hd.copy()
>>> l.cut_off(n=5)
>>> l
{5 -> 0.8500, 3 -> 0.7500, 2 -> 0.6875, 13 -> 0.6827, 11 -> 0.6705}

```

But because we are rebels, we will guess the length of the key using
another scoring function: the
[Index of Coincidences](https://en.wikipedia.org/wiki/Index_of_coincidence).

```python
>>> from cryptonita.scoring import key_length_by_ic

>>> lengths_ic = guess_key_length(ciphertext, length_space=40,
...                            score_func=key_length_by_ic, min_score=0.01)

>>> l = lengths_ic.copy()
>>> l.cut_off(n=5)
>>> l
{29 -> 0.0598, 40 -> 0.0235, 30 -> 0.0232, 10 -> 0.0230, 26 -> 0.0223}

```

> Interesting, both guesses have one guess that has a value higher than the
> rest. However both methods suggest two different sets (at least for the top 5
> guesses)

Before you think that I didn't programmed the Hamming distance correctly:

```python
>>> B('this is a test').hamming_distance(B('wokka wokka!!!'))
37

```

{% fullwidth 'assets/matasano/kl_guesses.png' 'Score of each guess by method. The maximum score using the Hamming distance is at 5. Using the Index of Coincidence is at 29.' %}

<br />

```python
>>> import sys
>>> sys.path.append("./assets/plotting")

>>> from plotting import plt, show                      # byexample: +timeout=10
>>> import pandas as pd                                 # byexample: +timeout=10

>>> guesses = pd.DataFrame({'Hamming Distance': lengths_hd,
...                         'Index of Coincidence': lengths_ic})

>>> with show(save='./assets/matasano/kl_guesses.png', latexify_kargs={'columns':2}): # byexample: +timeout=600 +skip
...     _ = guesses.plot(style='o', subplots=True, layout=(2, 1))
...

```

I will take my changes with the length of 29 found using the IC.

## Guessing one byte at time

What I will do now is to pick the ``0``, ``l``, ``2l`` ... bytes from
the ciphertext (multiples of the particular length ``l``).

If the length guessed is correct, all those bytes should had been encrypted
with the same byte key.

And we already know [how to break a ciphertext encrypted with a single byte
key](/book-of-gehn/articles/2018/04/01/A-string-of-coincidences-is-not-a-coincidence.html)!

So we need to do this for all the offsets between 0 and l. In other words:

```
    0,  0+l,  0+2l    ... to break key[0]
    1,  1+l,  1+2l    ... to break key[1]
    2,  2+l,  2+2l    ... to break key[2]
    :,   : ,   :           :   :
  l-1, 2l-1,  3l-1    ... to break key[l-1]
```

To break this, we will need the frequency of ``etaoin shrdlu`` (I'm
assuming that the plaintext is in ASCII human plain English):

```python

>>> from cryptonita.fuzzy_set import FuzzySet
>>> most_common_plain_ngrams = FuzzySet({
...     B('a'): 0.072466082820916, B(' '): 0.112705299864243,
...     B('d'): 0.037737020966984, B('e'): 0.112705299864243,
...     B('h'): 0.054072279749071, B('i'): 0.061809566907126,
...     B('l'): 0.035713968820153, B('n'): 0.059884118153344,
...     B('o'): 0.066609879237984, B('r'): 0.053122864925777,
...     B('s'): 0.05613969707456,  B('t'): 0.08035421158641,
...     B('u'): 0.02447183254807,})

```

Now, we will break the key byte a byte using a
[frequency attack](/book-of-gehn/articles/2018/03/01/In-XOR-We-Trust.html):

```python
>>> from cryptonita.attacks import brute_force, freq_attack
>>> from cryptonita.scoring import all_ascii_printable

>>> length = lengths_ic.most_likely()
>>> bytes_of_key = []

>>> for i in range(length):
...     c = B(ciphertext[i::length])
...
...     byte_guess = freq_attack(c, most_common_plain_ngrams, 1)
...     byte_guess = brute_force(c, all_ascii_printable, byte_guess, min_score=0.01)
...
...     bytes_of_key.append(byte_guess)

```

## Breaking the key

Now what we got is a *guess for each byte* of the key.

All the keys possible are the combination of those:

```
       guesses for 1st byte  <-  bytes_of_key[0]
         |        guesses for 2nd byte  <-  bytes_of_key[1]
         |          |      guesses for 3rd byte  <-  bytes_of_key[2]
      --------    -----    -----
    [{a0 a1 a2}, {b0 b1}, {c0 c1}, ...] = bytes_of_key

        a0          b0      c0     ...  = possible key 0
        a0          b0      c1     ...  = possible key 1
        a0          b1      c0     ...  = possible key 2
        a0          b1      c1     ...  = possible key 3
        :           :       :                   :   :
        a2          b1      c1     ...  = possible key
```

Fortunately we can use the probabilities in our favor.

Each byte guess is a fuzzy set where some possible bytes are more
likely than others:

```python
>>> bytes_of_key[3]
{'m' -> 0.1127, '!' -> 0.0357}

```

So, for the 4th byte, it is more likely that is a ``'m'`` than a ``'!'``

What we need is to join all the sets
discard the unlikely keys and just save the most likely:

```python
>>> from cryptonita.fuzzy_set import join_fuzzy_sets
>>> keys = join_fuzzy_sets(bytes_of_key, cut_off=0.0, j=B(''))

>>> len(keys)
120

```

``120`` is a really small number compared with the whole key space ``2^(8*29)``{% sidenote
'More keys than grams of ordinay mass in the
[observable universe](https://en.wikipedia.org/wiki/Observable_universe)' %}

And only a few of them are more likely than others:

```python
>>> keys.cut_off(n=2)
>>> tuple(sorted(keys.keys()))
('Terminator X: Br,ng the noise', 'Terminator X: Bring the noise')

Voila! These two keys are the two most probably ones. In fact, those
two have the same probability to be correct.

You probably guessed which is the one

```python
>>> key = tuple(sorted(keys.keys()))[1]

>>> ciphertext ^ key.inf()
<...>I'm back and I'm ringin' the bell<...>Play that funky music<...>

```

[Break repeating-key XOR](https://cryptopals.com/sets/1/challenges/6) *done*{% sidenote
'[Vanilla Ice - Play that Funky Music](https://www.youtube.com/watch?v=n2Ubq9XII8c)' %}.


