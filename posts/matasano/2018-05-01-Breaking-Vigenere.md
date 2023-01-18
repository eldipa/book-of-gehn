---
layout: post
title: "Breaking Vigenere"
tags: [cryptography, matasano, cryptonita, vigenere]
inline_default_language: python
---

A plaintext was encrypted via a XOR with key of unknown bytes of length,
repeating this key as much as needed to cover the full length of
the plaintext.

This is also known as the
[Vigenere cipher](https://en.wikipedia.org/wiki/Vigen%C3%A8re_cipher).

It is 101 cipher, which it is easy to break in theory, but it has more than
one challenge hidden to be resolve in the practice.

{{ spoileralert() }}
Shall we?

{% call mainfig('break_repeat_key_transpose.svg', indexonly=True) %}
{% endcall %}

<!--more-->

## Hamming distance (at bit level)

Given two messages of the same length, the
[Hamming Distance](https://en.wikipedia.org/wiki/Hamming_distance)
consists in counting how many bits one differ of the other.

In other words, we do an xor between the messages and count how many
ones we get.

```tex;mathjax
\mbox{count-1-bits} \left( c_1 ⊕ c_2 \right) \rightarrow \mbox{hamming-distance} \left( c_1, c_2 \right)
```

Here is an example:

```python
>>> from cryptonita import B                # byexample: +timeout=10
>>> B('this is a test').hamming_distance(B('wokka wokka!!!'))
37
```

## Guessing the length of the key


We will compute the Hamming distance between blocks of different
lengths.

Most of the case we will be computing the distance between 2 random
ciphertext blocks.

```tex;mathjax
\begin{align*}  \\
c_1 ⊕ c_2 & = \left( p_1 ⊕ k_i \right)  ⊕ \left( p_2 ⊕ k_j \right)  \\
          & = \left( p_1 ⊕ p_2 \right)  ⊕ \left( k_i ⊕ k_j \right)
\end{align*}
```

But if we hit the length of the key, `k_i = k_j`{.mathjax} and
the xor of 2 ciphertext blocks
will cancel out the random bits from the key exposing the xor
of 2 plaintext blocks.

```tex;mathjax
\begin{align*}  \\
c_1 ⊕ c_2 & = \left( p_1 ⊕ k_i \right)  ⊕ \left( p_2 ⊕ k_j \right)  \\
          & = \left( p_1 ⊕ p_2 \right)  ⊕ \left( k_i ⊕ k_j \right)  \\
          & = \left( p_1 ⊕ p_2 \right)
\end{align*}
```

The idea is that the Hamming distance of them will be significantly
shorter.

{% call marginfig('hamming1.svg') %}
Compute the Hamming distance between consecutive blocks of the same
length and takes the maximum. Then scores it.

Scores closer to 1
means smaller distances and therefore the blocks of ciphertext looks
that were xor'd with *the same key* as the xor of two blocks looks
*less random*.

Scores closer to 0 are the opposite: the xor of two blocks still looks
random.
{% endcall %}

This is exactly what `key_length_by_hamming_distance` does: scores how
likely a length is computing the Hamming distance between blocks of a
given length.

```python
>>> from cryptonita.scoring import key_length_by_hamming_distance

>>> ciphertext = B(open('./posts/matasano/assets/6.txt'), encoding=64)

>>> key_length_by_hamming_distance(ciphertext, length=3)
0.291<...>

>>> key_length_by_hamming_distance(ciphertext, length=29)
0.5818<...>
```

Instead of testing by hand we can use the `scoring` function
and explore the full range of possible lengths and score each one
keeping only the more likely.

An educated guess would be to explore the lengths between 1 and 40

```python
>>> from cryptonita.scoring import scoring

>>> lengths_hd = scoring(ciphertext, space=range(1, 41),
...                      score_func=key_length_by_hamming_distance)
```

There isn't a single response, of course.

This method *guesses* the length of
the key so we have a set of possible values, ones more likely than
others.

For this, ``scoring`` returns a
[Fuzzy Set](https://en.wikipedia.org/wiki/Fuzzy_set) where each possible
length has a probability linked to it.

Here are the top 5 more likely lengths that got the highest scores (and
the lowest Hamming distance)

```python
>>> l = lengths_hd.copy()
>>> l.cut_off(n=5)
>>> l
{29 -> 0.5819, 40 -> 0.5500, 36 -> 0.5417, 38 -> 0.5362, 35 -> 0.5357}
```

## Index of coincidence

But because we are rebels, we will guess the length of the key using
another scoring function: the
[Index of Coincidences](https://en.wikipedia.org/wiki/Index_of_coincidence).

```python
>>> from cryptonita.scoring import key_length_by_ic

>>> lengths_ic = scoring(ciphertext, space=range(1, 41),
...                      score_func=key_length_by_ic, min_score=0.01)

>>> l = lengths_ic.copy()
>>> l.cut_off(n=5)
>>> l
{29 -> 0.0598, 40 -> 0.0235, 30 -> 0.0232, 10 -> 0.0230, 26 -> 0.0223}
```

{% call mainfig('kl_guesses.svg') %}
Score of each guess by method.

Both methods agree on being 29 the most likely length
but as the plot shows, both methods have quite different behaviours too.
{% endcall %}

<!--
>>> import sys
>>> sys.path.append("./z/py/plotting")

>>> from plotting import plt, show                      # byexample: +timeout=10
>>> import pandas as pd                                 # byexample: +timeout=10

>>> guesses = pd.DataFrame({'Hamming Distance': lengths_hd,
...                         'Index of Coincidence': lengths_ic})

>>> with show(save='./posts/matasano/kl_guesses.svg', columns = 2, transparent = True): # byexample: +timeout=600 +skip
...     _ = guesses.plot(style='o', subplots=True, layout=(2, 1))
...
-->

## Guessing one byte at time

What I will do now is to pick the ``0``, ``l``, ``2l`` ... bytes from
the ciphertext (multiples of the particular length ``l``).

If the length guessed is correct, all those bytes should had been encrypted
with the same byte key.

And we already know [how to break a ciphertext encrypted with a single byte
key](/articles/2018/03/01/In-XOR-We-Trust.html)!

So we need to do this for all the offsets between 0 and l. In other words:


{% call mainfig('break_repeat_key_transpose.svg') %}
{% endcall %}

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
[frequency attack](/articles/2018/03/01/In-XOR-We-Trust.html):

```python
>>> from cryptonita.attacks import brute_force, freq_attack
>>> from cryptonita.scoring import all_ascii_printable

>>> length = (lengths_hd | lengths_ic).most_likely()
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
>>> keys = FuzzySet.join(bytes_of_key, cut_off=0.0, j=B(''))

>>> len(keys)
120
```

{% call marginnotes() %}
More keys than grams of ordinary mass in the
[observable universe](https://en.wikipedia.org/wiki/Observable_universe)
{% endcall %}

``120`` is a really small number compared with the whole key space ``2^(8*29)``

And only a few of them are more likely than others:

```python
>>> keys.cut_off(n=2)
>>> print(repr(keys))
{'Terminator X: Bring the noise' -> 0.0000, 'Terminator X: Br,ng the noise' -> 0.0000}

```

Voila! These two keys are the two most probably ones. In fact, those
two have the same probability to be correct.

You probably guessed which is the one

```python
>>> key = sorted(keys)[1]

>>> ciphertext ^ key.inf()
<...>I'm back and I'm ringin' the bell<...>Play that funky music<...>
```
{% call marginnotes() %}
[Vanilla Ice - Play that Funky Music](https://www.youtube.com/watch?v=n2Ubq9XII8c)
{% endcall %}

[Break repeating-key XOR](https://cryptopals.com/sets/1/challenges/6) *done*.


