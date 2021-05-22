---
layout: post
title: "CBC Bitflipping"
---

{% marginfigure '' '<img style="max-width:60%;" alt="CBC Dec" src="/book-of-gehn/assets/matasano/cbc-dec.png">' '' '' 'in-index-only'%}

CBC does not offer any protection against an active attacker.

Flipping some bits in a ciphertext block totally scrambles its
plaintext but it has a very specific effect in the *next* plaintext
block.

Without any message integrity, a CBC ciphertext can be patched
to modify the plaintext at will.{% marginnote '**-- Spoiler Alert! --**' %}<!--more-->

### Warming up

But first, let's define a random configuration with some fixed values like
the block size or the encryption mode:

```python
>>> from cryptonita import B                # byexample: +timeout=10

>>> import sys
>>> sys.path.append("./assets/matasano")
>>> from challenge import generate_config, enc_cbc, dec_cbc  # byexample: +timeout=10

>>> seed = 20180703   # make the tests 'random' but deterministic
>>> block_size = 16     # leave this fixed, it is what happen in practice

>>> cfg = generate_config(random_state=seed, block_size=block_size,
...         enc_mode='cbc',
...         prefix = "comment1=cooking%20MCs;userdata=",
...         posfix = ";comment2=%20like%20a%20pound%20of%20bacon")
```

Take the following toy-function to insert the user's data (possibly
its profile) between the ``cfg.prefix`` and ``cfg.posfix`` strings
and then encrypt it:

```python
>>> def add_user_data(m):
...     assert ';' not in m and '=' not in m
...     msg = B(cfg.prefix + m + cfg.posfix).pad(block_size, 'pkcs#7')
...     return enc_cbc(msg, cfg.key, cfg.iv)
```

Now imagine this quite-dumb role check function that process the
previous ciphertext: if one of the fields is ``admin=true``
the user will be considered an Administrator:

```python
>>> def is_admin(c):
...     msg = dec_cbc(c, cfg.key, cfg.iv).unpad('pkcs#7')
...     return b'admin=true' in msg.split(b';')
```

We cannot add just ``admin=true``, it would be too easy:

```python
>>> add_user_data('some;admin=true;bar')
Traceback<...>
AssertionError
```

So the idea is to patch the ciphertext.

## Bit flipping attack

Recall that in CBC a ciphertext block is xored with the output of the decryption
of the *next* ciphertext block to get the *next* plaintext block.

If we modify one ciphertext block its decryption will be totally scrambled
but we will have control of the *next* plaintext block.

{% maincolumn '<img style="max-width:60%;" alt="CBC Dec" src="/book-of-gehn/assets/matasano/cbc-dec.png">' '' %}

{% marginnote "We don't know if our inject plaintext
will be aligned to the block size boundary. To ensure that we inject
padding of twice the block size which warranties that at least one block
will be full with our ``A``s" %}

Let's create a ciphertext with enough ``A``s to get at least one plaintext block
full of ``A``s

```python
>>> c = add_user_data('A' * block_size * 2)
>>> is_admin(c)
False
```

Now we can create the patch: the plaintext that we want
xored with the plaintext that was encrypted:

```python
>>> patch = B(';admin=true;') ^ B('A').inf()
>>> patch = patch.pad(block_size, 'zeros')
```

Finally, we apply the patch targeting the ciphertext block of the
full of ``A``s

```python
>>> c = B(c, mutable=True)
>>> cblocks = c.nblocks(block_size)
>>> cblocks[2] ^= patch

>>> is_admin(B(c))
True
```

[CBC bitflipping attacks](https://cryptopals.com/sets/2/challenges/16)
challenge unlock!
