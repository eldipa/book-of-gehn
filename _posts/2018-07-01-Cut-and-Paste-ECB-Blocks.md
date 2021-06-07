---
layout: post
title: "Cut and Paste ECB blocks"
tags: cryptography matasano cryptonita ECB forgery forge
---

In this game we control partially a plaintext that is encrypted
under ECB mode with a secret key.

This time the idea is not to reveal the key but to *forge* a plaintext.

Welcome to the [ECB cut-and-paste](https://cryptopals.com/sets/2/challenges/13)
challenge!{% marginnote '**-- Spoiler Alert! --**' %}<!--more-->

### Prelude: profile creation

Imagen a scenario where two parties send encrypted messages using AES
in ECB mode:

```python
>>> import sys
>>> sys.path.append("./assets/matasano")
>>> from challenge import generate_config, enc_ecb, dec_ecb  # byexample: +timeout=10

>>> seed = 20180701   # make the tests 'random' but deterministic
>>> block_size = 16     # leave this fixed, it is what happen in practice

>>> # encrypt/decrypt under this 'random' environment
>>> cfg = generate_config(random_state=seed, block_size=block_size, enc_mode='ecb')
```

Consider the following function that builds a ciphertext from an hypothetical
"create profile for a new user":

```python
>>> from cryptonita import B                # byexample: +timeout=10

>>> def profile_for(email):
...     assert b'&' not in email
...     assert b'=' not in email
...     assert b'@'     in email
...
...     msg = B(b'email=%s&uid=10&role=user' % email)
...     msg = msg.pad(block_size, 'pkcs#7')
...     return enc_ecb(msg, cfg.key, block_size)

>>> c = profile_for(b'honest-email@example.com')
>>> c
<...>\xc1\xa4\x89<...>
```

The ``profile_for`` can create as many user as we want but all of them will
have the same privilege level or role: ``user``.

Then the ciphertext can be sent to a server where the given credentials are
stored and the profile is "created".

```python
>>> from urllib.parse import parse_qs
>>> def create_profile(ciphertext):
...     msg = dec_ecb(ciphertext, cfg.key, block_size)
...     msg = msg.unpad('pkcs#7')
...
...     return parse_qs(msg, strict_parsing=True)

>>> create_profile(c)
{b'email': [b'honest-email@example.com'], b'role': [b'user'], b'uid': [b'10']}
```

## Forgery

It would be cool to forge ``role=admin`` there but it is not possible.

```python
>>> profile_for(b'dishonest@evil.com&role=admin')
<...>
AssertionError
```

Let's forge this with [cryptonita](https://pypi.org/project/cryptonita/).

### Block alignment

We want to know how many bytes are needed so the plaintext
at its right is aligned with the block boundary.

In other words, given the prefix ``email=`` we now that we need 10 bytes
to append and complete the block leaving the rest of our own plaintext
aligned with the block boundary:

```python
>>> block_size - len("email=")
10
```

We already know how to do this even if we don't know the prefix...
when we have two blocks encrypted with to the same ciphertext block we are done:

```python
>>> for alignment in range(block_size):
...     c = profile_for(B('@' * (block_size * 2 + alignment)))
...     indexes = list(c.nblocks(block_size).iduplicates(distance=0, idx_of='both'))
...     if indexes:
...         break

>>> alignment
10
```

``iduplicates`` gives us the index of the ``first`` of the duplicated blocks,
marking the *end* of the needed padding:

```python
>>> indexes[0]
1
```

### Cut a block

```python
>>> align_block = B('A' * alignment)
>>> target = B('admin').pad(block_size, 'pkcs#7')
>>> posfix = B('@evil.com')

>>> crafted_email = align_block + target + posfix
>>> crafted_email
'A<...>AAAadmin\x0b\x0b\x0b<padding>\x0b@evil.com'
```

Now, when ``crafted_email`` gets encrypted, the ``admin\x0b...\x0b``
will be aligned to the block boundary and it will be a full block
ready to be cut:

```python
>>> c = profile_for(crafted_email)
>>> cut = c.nblocks(block_size)[indexes[0]]
```

```
   add enough As to align the next block
     |
|--------|--------|---------|
 email=AA adminPPP @foo.....
              |
              V
|--------|--------|---------|
         :   C1   :
         :.......cut
```

where ``PPP`` is a ``pkcs#7`` padding such as if the whole ``C1`` block was
the last block of the ciphertext, the decryption + un-padding would success.

### Paste a block

Now, the final step.

We will use our valid email (at the end *we* want to be admin) but it has
to be special: it has to contain enough padding to align the *last* block
so we can cut it and throw it away.

In its replacement we will put our crafted cut cipher block.

```python
>>> c = profile_for(b'me-AAAAAAAAAAAAAAAAA@evil.com')
>>> forged = B(c, mutable=True)
>>> forged[-block_size:] = cut
```

The email address ``me-AAAAAAAAAAAAAAAAA@evil.com`` should be a valid
one and with an account controlled by us if we want to do something
beyond the cryptography exercise later.

How many ``A`` we need to add will depend: I tried several times using
``create_profile`` as oracle until I got the payload aligned such the
last *boundary* matched with the ``role=|user`` boundary.

The following diagram show this:

```
  insert a valid email, with As to align the last block
       |     |
       |     |
|--------|--------|--------|--------|    <= original
 email=me -AAA@evi ...role= userQQQQ           |
     |        |        |                       |
     |        |        |                       V
    Ca       Cb       Cc       C1 (cut)  <=  encrypt
     |        |        |        |              |
     V        V        V        V              V
|--------|--------|--------|--------|    <= decrypted
 email=me -AAA@evi ...role= adminPPP
```

Voila!, the plaintext is recovered and the padding removed and we
get a admin profile.

```python
>>> create_profile(B(forged))
{b'email': [b'me-AAAAAAAAAAAAAAAAA@evil.com'],
 b'role': [b'admin'],
 b'uid': [b'10']}
```

