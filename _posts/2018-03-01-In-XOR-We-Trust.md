---
layout: post
title: "In XOR we trust"
---

This is the first set of exercises for the [Matasano Challenge](https://cryptopals.com/) (also known as
the Cryptopals Challenge)

It starts from the very begin, really easy, but it goes up to more
challenging exercises quickly.

Ready?{% sidenote '**-- Spoiler Alert! --**' %} *Go!*<!--more-->

## Warming up

During this challenge I will be using and implementing a set of tools
to break crypo: [cryptonita](https://pypi.org/project/cryptonita/)

Working with bytes can be a mess so let's use some nice object that
would help us in our journey.

We can use ``bytestring`` or just ``B`` to convert strings encoded
in base 16 or 64 into bytes{% sidenote 'This unlocks the
[Convert hex to base 64](https://cryptopals.com/sets/1/challenges/1)
challenge.' %}.

```python
>>> from cryptonita.bytestring import B, load_bytes     # byexample: +timeout=10

>>> b = B('49276d206b696c6c696e6720796f75'
...       '7220627261696e206c696b65206120'
...       '706f69736f6e6f7573206d757368726f6f6d', encoding=16)

>>> b.encode(64)
'SSdtIGtpbGxpbmcgeW91ciBicmFpbiBsaWtlIGEgcG9pc29ub3VzIG11c2hyb29t'
```

But ``bytestring`` is a little more than a decoder: it has a convenient
interface to to manipulate the bytes.

For example, you can perform a ``xor`` between two strings in
one instruction:

```python
>>> a = B('1c0111001f010100061a024b53535009181c', encoding=16)
>>> b = B('686974207468652062756c6c277320657965', encoding=16)

>>> c = a ^ b
>>> c.encode(16)
'746865206B696420646F6E277420706C6179'
```

Even you can perform the ``xor`` of two strings of different lengths: you
just say that the shorter string will be repeated to infinitum and everything
will work{% sidenote 'These last two examples solve the challenges
[Fixed XOR](https://cryptopals.com/sets/1/challenges/2) and
[Implement repeating-key XOR](https://cryptopals.com/sets/1/challenges/5)'
%}.

```python
>>> plaintext = B("Burning 'em, if you ain't quick and nimble\n"
...               "I go crazy when I hear a cymbal")

>>> key = B("ICE")

>>> c = plaintext ^ key.inf()
>>> print(c.encode(16))
b'0B3637272A2B2E63622C2E69692A23693A2A3C6324202D623D63343C2A26226324272765272A282B2F20430A652E2C652A3124333A653E2B2027630C692B20283165286326302E27282F'
```

## Break 1-byte key XOR

### Break it by Brute Force

With a so small key space (1 byte means 256 different keys) we
can brute force the decryption of the ciphertext just trying
all the possible keys.

If we want to automate the process we will need a *scoring function*
to rank how likely the decrypted text is the real plaintext.

The scoring function will depend of the our knowledge about the real
plaintext.

If we assume that the text is written in *human ascii* we could assign a
higher value to the plaintexts that have only printable symbols (letters,
numbers, punctuation symbols and whitespaces).

A plain text with a byte ``0xf1`` is unlikely to be a *human ascii* text. (Such
weird bytes *could* be part of a human text using another encoding like
``utf-8``)

```python
>>> from cryptonita.scoring import all_ascii_printable         # byexample: +timeout 10

>>> all_ascii_printable(B('hello!'))
1

>>> all_ascii_printable(B('hi\x00!'))
0
```

Now, the attack

```python
>>> from cryptonita.attacks import brute_force

>>> ciphertext = B('1b37373331363f78151b7f2b783'
...                '431333d78397828372d363c7837'
...                '3e783a393b3736', encoding=16)

>>> keys = brute_force(ciphertext, all_ascii_printable, key_space=1)
>>> len(keys)
21
```

Not bad, but we are smarter than this.

### Frequency attack

Brute forcing is expensive even for a small key space. And it is not
very cleaver either as we are not using any information about the plaintext to
our favor.

If we assume that the plaintext is in English, it is likely that one of
the most common bytes in the ciphertext is actually *one of the most common*
bytes in English but encrypted{% sidenote
'``ETAOIN SHRDLU`` Achievement Unlocked' %}.

The ``xor`` between them will give us the key or at least we will narrow
to a small subset of possible keys.

```python
>>> from cryptonita.attacks import freq_attack

>>> most_common_plain_ngrams = [B(b) for b in 'etaoin shrdlu']
>>> cipher_ngram_top = 1

>>> keys = freq_attack(ciphertext, most_common_plain_ngrams, cipher_ngram_top)

>>> len(keys)
13
```

We got 13 different possible keys, doing a small brute force we
can reduce the set further:

```python
>>> keys = brute_force(ciphertext, score_func=all_ascii_printable,
...                                 key_space=keys)

>>> keys
{'X' -> 1.0000}
```

Finally, the plaintext is{% sidenote
'[Single-byte XOR cipher](https://cryptopals.com/sets/1/challenges/3)
challenge done.' %}

```python
>>> ciphertext ^ B('X').inf()
"Cooking MC's like a pound of bacon"
```

