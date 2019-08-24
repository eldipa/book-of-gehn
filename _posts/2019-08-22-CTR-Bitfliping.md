---
layout: post
title: "CTR Bitflipping"
---

No much to explain: encryption **does not** offer any
protection against forgery.

We saw this in the [CBC Bitflipping post](/book-of-gehn/articles/2018/07/03/CBC-Bitflipping.html)
and we will see it again here but this time it will be
the CTR encryption mode our victim.{% sidenote '**-- Spoiler Alert! --**' %}<!--more-->

<!--
>>> from cryptonita import B, load_bytes     # byexample: +timeout=10

>>> import sys
>>> sys.path.append("./assets/matasano")
>>> from challenge import generate_config, enc_ctr, dec_ctr  # byexample: +timeout=10

>>> seed = 20190822   # make the tests 'random' but deterministic
>>> block_size = 16     # leave this fixed, it is what happen in practice
-->

Recall from [CBC Bitflipping post](/book-of-gehn/articles/2018/07/03/CBC-Bitflipping.html)
the scenario where we have a ``add_user_data`` function to *user*
profiles:

```python
>>> cfg = generate_config(random_state=seed, block_size=block_size,
...         enc_mode='ctr',
...         prefix = "comment1=cooking%20MCs;userdata=",
...         posfix = ";comment2=%20like%20a%20pound%20of%20bacon")

>>> def add_user_data(m):
...     assert ';' not in m and '=' not in m
...     msg = B(cfg.prefix + m + cfg.posfix)
...     return enc_ctr(msg, cfg.key, cfg.nonce)
```

We control the user's data but we cannot control the entire profile.
In particular, we cannot say that we have the administration role
adding ``admin=true``.

```python
>>> def is_admin(c):
...     msg = dec_ctr(c, cfg.key, cfg.nonce)
...     return b'admin=true' in msg.split(b';')
```

In [CBC Bitflipping post](/book-of-gehn/articles/2018/07/03/CBC-Bitflipping.html)
we saw that CBC does not offer any protection agaisnt foregery and how to
break it.

In this post we will do the same but attacking the CTR mode.

First we will create our *target* plaintext and a *padding* plaintext.
The former is the plaintext that we *want* to inject and the latter is
the one that we are *allowed* to inject.

```python
>>> target = B(';admin=true;')
>>> padding = 'A' * len(target)
```

Then we create our profile:

```python
>>> ctext = add_user_data(padding)
```

Now, because CTR turns a block cipher into a stream cipher using
*xor*, we can *patch it* trivially:

```python
>>> patch = target ^ B(padding)
```

The only catch is that we don't know *where* our padding is located
so we don't know where to patch.

For this we can use ``is_admin`` as an *oracle* function, trying
each position and knowning the correct one only when we get
``is_admin(..) == True``

```python
>>> l = len(patch)
>>> for i in range(len(ctext) - l + 1):
...     cpatched = ctext[:i] + (ctext[i:i+l] ^ patch) + ctext[i+l:]
...     assert len(cpatched) == len(ctext)
...
...     if is_admin(cpatched):
...         print("Priv escalated! Patch at %i" % i)
Priv escalated! Patch at 32
```

Broken!
[CTR bitflipping](https://cryptopals.com/sets/2/challenges/26)
challenge unlock!
