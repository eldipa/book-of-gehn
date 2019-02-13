---
layout: post
title: "Cape Encryption"
---

The Cape library{% sidenote
'https://github.com/gioblu/Cape/tree/294f810ac4831af26832e70e4ba5d073908232e2' %}
offers a symmetric stream cipher implemented in
``cape_decrypt`` and ``cape_encrypt``.

In addition, it offers another symmetric stream cipher, a slightly different
of the first one, implemented in ``cape_hash``{% sidenote
'``cape_hash`` is an unfortunately name for a cipher.'
%}

In this write-up we are going to analyze the ``cape_hash`` stream cipher
and see if we can break it.<!--more-->

<!--
>>> import sys
>>> sys.path.append("./assets/matasano")
>>> from challenge import generate_config                    # byexample: +timeout=10

>>> seed = 20190203   # make the tests 'random' but deterministic

>>> cfg = generate_config(random_state=seed)
>>> rnd = cfg.rnd

>>> with open("cape-secret", "wb") as f:
...     _ = f.write(rnd.bytes(1))
...     _ = f.write(rnd.bytes(65535))
-->

<!--
?: #include <stdio.h>
?: #include <stdlib.h>
?: #include <errno.h>
?: #include <stdint.h>

?: #include "assets/cape_encryption/cape.h"

?: typedef unsigned char uchar;

?: uchar* read(
::          const char *fname,
::          const char *mode,
::          unsigned int sz) {
::  FILE *f = fopen(fname, mode);
::  if (!f)
::      perror("File open failed");
::
::  uchar *buf = (unsigned char*) malloc(sz);
::  fread(buf, 1, sz, f);
::  fclose(f);
::
::  return buf;
:: }

?: void write(
::          const char *fname,
::          const char *mode,
::          const uchar* buf,
::          unsigned int sz) {
::  FILE *f = fopen(fname, mode);
::  if (!f)
::      perror("File open failed");
::
::  fwrite(buf, 1, sz, f);
::  fclose(f);
:: }
-->

### Warming up

First at all, let's load a secret and random salt and key
and an ASCII pseudo-English plaintext, unknown to us:

```cpp
?: unsigned char *secret = read("cape-secret", "rb", 1+65535);
?: uint8_t salt = secret[0];
?: unsigned char *key = &secret[1];

?: unsigned char *plaintext = read("assets/cape_encryption/1.txt", "rb", 2852);

?: cape_t cape;
?: cape_init(&cape, key, 65535, salt);
```

In this post we are going to analyze only the ``cape_hash`` cipher so
let's use it to encrypt the plaintext  and save it to disk:

```cpp
?: unsigned char *ciphertext = (unsigned char*) malloc(2852);
?: cape_hash(&cape, plaintext, ciphertext, 2852);

?: write("cape-ciphertext", "wb", ciphertext, 2852)
```

For breaking the cipher we are going to use
[cryptonita](https://pypi.org/project/cryptonita/), a Python lib for
cryptanalysis.

```python
>>> from cryptonita import B                 # byexample: +timeout=10
>>> ciphertext = B(open("cape-ciphertext", "rb").read())
>>> plaintext = B(open("assets/cape_encryption/1.txt", "rt").read())
```

## Too short key stream

The ``cape_hash`` cipher is as follows:

```.cpp
uint8_t srk = cape->salt ^ cape->reduced_key;
for(uint16_t i = 0; i < length; i++) {
    uint8_t isrk = srk ^ i;
    destination[i] = source[i] ^ isrk ^ cape->key[isrk % cape->length];
}
```

``cape->reduced_key`` is a 8 bits secret value derived from
the secret key ``cape->key``.

We will consider that ``cape->salt`` as secret too.

Despite that ``cape->key`` can hold 65535 bytes{% sidenote
'Technically, it can hold 65536 bytes but the length is a 16 bits
unsigned integer so we lost one number wasted by representing the 0 length'
%}, ``isrk`` has only
8 bits and therefor the ``isrk ^ cape->key[ .. ]`` can only give 256 bytes
and after that it will repeat itself.

That means that plaintext of more than 256 bytes will be xored
with a *repeating* key stream and we know
[how to break this](/book-of-gehn/articles/2018/03/01/In-XOR-We-Trust.html).

## (Partially) Known plaintext attack

Because the key stream is repeating *within* the encryption of a single
plaintext, if we know a part of the plaintext we can break the rest.

Given the first 256 bytes of the plaintext, the 256 key stream are trivially
found:

```python
>>> known_plaintext = plaintext[:256]
>>> kstream = known_plaintext ^ ciphertext[:256]
```

Then, we decrypt the rest of the message just xoring the ciphertext with
the key stream reapeating it each 256 bytes:

```python
>>> dmsg = ciphertext ^ kstream.inf()
>>> dmsg == plaintext
True
```

If the original ``key`` has less than 256 bytes, the amount of known plaintext
required is less: the same amount of bytes that the key has.

## Ciphertext only attack

Even if we don't have access to a known plaintext, we can mount an
*ciphertext only attack*.

Take the ciphertext and split it in blocks of 256 bytes each.
Then, stack them so you will have a matrix of 256 columns.

The last row, however it could contain less bytes (because
the ciphertext length is not multiple of 256); for simplicity
we are dropping it.

```python
>>> from cryptonita.conv import transpose, uniform_length

>>> len(ciphertext)
2852

>>> tmp = ciphertext.nblocks(256)
>>> tmp = uniform_length(tmp, length=256)   # drop any shorter row
```

Because the key stream is repeated, each column will be xored
with the *same* key stream byte.

If this matrix is transposed, each *row* will be xored with
the same key stream byte:

```python
>>> tciphertexts = transpose(tmp)
>>> len(tciphertexts) # rows
256

>>> len(tciphertexts[0]) # columns
11
```

### Frequency attack

Given the fact that the plaintext is written in ASCII English,
we can mount a frequency attack.

``freq_attack`` assume that one of the ``most_common`` plaintext symbols
is in the ``ntop`` of the ciphertext symbols, encrypted of course.

In this case we are going to use the famous ``ETAOIN SHRDLU`` model.

For longer ciphertexts{% sidenote
'As rule of thumb 64 bytes is cool.' %}
you can set ``ntop = 1`` and assume that the most
frequent cipher-symbol is one of the most common plaintext symbols encrypted.

But with only ``len(tciphertexts[0]) == 11``, we need to set ``ntop`` to
higher value.

```python
>>> from cryptonita.scoring.freq import etaoin_shrdlu   # byexample: +timeout 10
>>> from cryptonita.attacks import freq_attack

>>> most_common = etaoin_shrdlu()
>>> ntop = 5
```

Under this hypothesis, a possible byte key is just the xor of those two:
in the worst case we will have ``len(most_common) * ntop`` guesses:

```python
>>> len(most_common) * ntop
65
```

But in the practice we have less (duplicated are removed):

```python
>>> gkey1 = freq_attack(tciphertexts[0], most_common, ntop)

>>> len(gkey1)
44
```

``gkey1`` is *a guess*: the most likely possible values for the first byte
of the key stream{% sidenote
'Without a frequency attack we could try the whole space of 256 bytes. It is
totally feasible but it is faster to do a frequency attack first to reduce
the search space' %}.

### Brute force

We can discard some guesses if they produce the wrong plaintext.

Knowing that the plaintext has a reduced set of ASCII printable of letters, numbers
and only a few punctuation symbols we can narrow the set of guesses further{% sidenote
'Even if the alphabet of all ASCII printable has 100 symbols and the proposed has
64 symbols (more than half), the impact of this is **enormous** reducing the guesses
in two or more orders of magnitude.' %}:

```python
>>> from functools import partial
>>> from cryptonita.scoring import all_in_alphabet

>>> alphabet = B(b"\n !',-.012356789?ABCDEFGHIJLMORSTVWY[]abcdefghijklmnopqrstuvwxyz")

>>> all_in_alphabet = partial(all_in_alphabet, alphabet=alphabet)
```

Now, we filter out any key which decrypted message does not fit in
out plaintext model.

Once again we will obtain a **guess**, but a shorter one this time:

```python
>>> from cryptonita.attacks import brute_force
>>> gkey1 = brute_force(tciphertexts[0], score_func=all_in_alphabet, key_space=gkey1)

>>> len(gkey1)
1
```

Repeating this for all the 256 ciphertexts should yield a 256 list of
guesses:

```python
>>> gkeys = []
>>> for c in tciphertexts:                          # byexample: +timeout=10
...     gk = freq_attack(c, most_common, ntop)
...     gk  = brute_force(c, score_func=all_in_alphabet, key_space=gk)
...     gkeys.append(gk)
```

This a *product* and the set will grow exponentially:

```python
>>> from cryptonita.fuzzy_set import len_join_fuzzy_sets
>>> len_join_fuzzy_sets(gkeys)
626513003<...>
```

Considering only the *most likely key stream*:

```python
>>> from cryptonita.fuzzy_set import join_fuzzy_sets
>>> kstream = join_fuzzy_sets(gkeys, cut_off=1, j=B('')).most_likely()
```

The resulting decrypted text was nice performance of almost 60% of success:

```python
>>> decrypted = ciphertext ^ kstream.inf()

>>> hits = sum((p==d for p, d in zip(plaintext, decrypted)))
>>> hits / len(plaintext)
0.59<...>
```

Here are some extract of the decrypted text. See how some words are
perfectly visible like "aitn't", "soul", "I'm" and "degree".

```python
>>> [d[:80] for d in decrypted.nblocks(256)[:8]]
["[IntsyH\nOtaf.9wanillas' dsond'tit worae5ln\na chair,7yea3\nVfoCltxi'll lhock 'tj'c",
 "rn mx6foxvsd ciis ain't yh.jorropl\nIt-cyfmCshed my ehymw, edIamj, I'm'brawin6'so",
 "quipqsq axt  cie best\nMael.anhtitr onh!slr\nice, let7the2midsEppv'e retr\nJust1knt",
 "nce\nCsvacbehI7sock with qkovou,!yard lr5oiLesaver\nYxu aakec!Loj9-ope,'na...tyfs ",
 "eal fyzd8?.!ncn a new phvtk, mulain' xq5whO airwaved\nAnv nhv\nywlnre ajgzed 'rfrt",
 "w my!eayzt,hmn!soul, up xi.thb epnce kmzlr I wanna'7see2ya !Yhyr,, shfme and1ton",
 " thao6ahs1t iee degree\nYxr.trnee1my syxyf Hut I bury yog sbd I?tiice fhd I'm1dhk",
 "us]\nHb2s6p 8aeuy...come xi .. lde's db!akiY..\n\n[Verde 3O\nYht\ntpp'k it u funy1sh'"]
```

## Final thoughts

``cape_hash`` is symmetric cipher which, despising of having a 65536 bytes
length key, the key stream is repeated each 256
of plaintext enabling a *cipher only attack*.

Even with a short plaintext of just 2852 we got 11 bytes xored with the
same key byte and this was enough to get almost 60% of the plaintext.

With a theoretical maximum length of 65534 bytes{% sidenote
'Based on the documentation' %} for a single plaintext, we
can obtain 256 bytes xored with the same key byte. Virtually any plaintext
of that size can be broken completely.

But if such scenario is not plausible, knowing a little more about the
plaintext can really improve the attack.

A *partially known plaintext* of just 256 bytes is fulminant and breaks
the ciphering completely.

Crypto is hard and developing a new cipher is harder. The only way
to improve in this field is trying, failing, and trying again.

A special thank you to Giovanni Blu Mitolo, the author of ``cape``
who made the project *open source* and asked for *feedback* to the community.

<!--
$ rm -f cape-ciphertext cape-secret         # byexample: -skip +pass

?: free(ciphertext);    // byexample: +pass
?: free(plaintext);     // byexample: +pass
?: free(secret);        // byexample: +pass
-->

