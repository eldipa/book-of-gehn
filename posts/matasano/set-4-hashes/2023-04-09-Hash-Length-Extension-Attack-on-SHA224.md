---
layout: post
title: "Follow up: Length Extension Attack on SHA-224"
tags: [cryptography, matasano, cryptonita, hash, extension]
inline_default_language: mathjax
---

In the
[previous post](/articles/2023/04/05/Hash-Length-Extension-Attack.html)
we reviewed why and how an extension length
attack is possible on some hash function and how we can use
it to break a prefix-keyed MAC.

Long story short: when the full internal state of the hashing
is exposed, an extension attack is possibly.

So hash functions that **don't** expose their internal state are okay,
right?

Yes in general but the *devil is in the details*...

SHA-224 does not expose its full state and it is one of those *"safe"* hash
functions (sometimes it is found in the literature as such) **but...**

In this quick post we will see why SHA-224 is vulnerable to
*length extension attack* **even** if its internal state is not fully
exposed.<!--more-->

## What is SHA-224?

SHA-224 is based on SHA-256.

It has 8 `uint32_t`{.cpp} registers like SHA-256 but the hash digest is made
of all except the last register, yielding hashes of 224 bits
instead of 256 bits.

At first glance this truncated output should prevent a length extension
attack but take a closer look.

Only 32 bits are missing!

<!--
>>> from cryptonita import B
>>> from cryptonita.toys.hashes.sha256 import sha224
>>> from cryptonita.toys.hashes.keyed import prefix_key_hash

>>> key = B('foobar') # unknown

>>> def login(login_req, unverified_hash, verbose=True):
...     h = prefix_key_hash(sha224, key, login_req)
...     if h != unverified_hash:
...         if verbose: print(f"Bad MAC. Login aborted. Ours: {h}, Theirs: {unverified_hash}")
...         return False
...
...     if b"admin=True" in login_req.split(b";"):
...         if verbose: print("Logged as admin")
...     else:
...         if verbose: print("Logged as normal user")
...
...     return True

>>> def pad_like_sha224(msg_length):
...     bit_len = msg_length * 8
...
...     # Padding used by SHA224
...     padding = b'A' * msg_length
...     padding += b'\x80'
...     while (len(padding) * 8 + 64) % 512 != 0:
...         padding += b'\x00'
...
...     padding += bit_len.to_bytes(8, 'big')
...
...     return padding[msg_length:]

>>> from cryptonita.conv import repack
>>> def extract_hash_fun_state(hash_hex):
...     words_bytes = B(hash_hex, encoding=16).nblocks(4)
...
...     return repack(words_bytes, ifmt='4s', ofmt='>I')
-->

## Scenario setup

Like in the previous post, we will assume a `login()`{.python} function
that verifies the authenticity of a login request, this time using
SHA-224

```python
>>> login_req = B('user=john;comment=cheese')
>>> mac = prefix_key_hash(sha224, key, login_req)

>>> login(login_req, mac)
Logged as normal user
True
```

## The attack

From the digest we extract 7 of the 8 state registers. Only 2 unknowns
remains: the length of the original message (including
the secret key) and the value of the 8th register `h7`{.python}

```python
>>> h0, h1, h2, h3, h4, h5, h6 = extract_hash_fun_state(mac)
>>> ('%08x%08x%08x%08x%08x%08x%08x' % (h0, h1, h2, h3, h4, h5, h6)) == mac
True
```

{% call marginnotes() %}
Brute-forcing `2^{32}` is perfectly possible but a little slow for me so I
would do some cheating: the magic number 777489100 was picked on purpose
to speedup the things.
{% endcall %}

We compute the *Cartesian product* of the two `IntSpace`{.python} to describe
any possible message length and `h7`{.python} combination:

```python
>>> from cryptonita.space import IntSpace, product

>>> minimum = len(login_req)
>>> msg_length_space = IntSpace(minimum, minimum+256, start=minimum+16)

>>> h7_space = IntSpace(0, 0xffffffff, start=777489100)

>>> params_space = product(h7_space, msg_length_space)
```

As before we need an *oracle* function to tell us if a particular
message length/`h7`{.python} combination produced a valid MAC or not:

```python
>>> def is_ok(params):
...     h7, msg_length = params
...
...     pad = pad_like_sha224(msg_length)
...     new_mac = sha224(b'', h0, h1, h2, h3, h4, h5, h6, h7, forged_message_len=msg_length+len(pad))
...
...     new_login_req = login_req + pad
...     return login(new_login_req, new_mac, verbose=False)
```

Explore the *parameters space*...

```python
>>> from cryptonita.attacks import search

>>> brute_forced_h7, guessed_msg_length = search(params_space, is_ok)    # byexample: +timeout=30

>>> (brute_forced_h7, guessed_msg_length)
(777489071, 30)
```

And finally forge the MAC and profit!

```python
>>> ext = B(';admin=True')

>>> pad = pad_like_sha224(guessed_msg_length)

>>> new_login_req = login_req + pad + ext

>>> new_mac = sha224(ext, h0, h1, h2, h3, h4, h5, h6, brute_forced_h7, forged_message_len=guessed_msg_length + len(pad) + len(ext))

>>> login(new_login_req, new_mac)
Logged as admin
True
```

## Final thoughts

We were lucky: for SHA-224 only 32 bits are missing. Other truncated
hashes are much harder to break.

For example SHA-512/224 is the 224 bits version based on SHA-512: 228
bits are missing!

Nevertheless take this as a lesson: **do not overlook**, sometimes
you may find vulnerabilities and attack vectors just by seeing the
things closely.
