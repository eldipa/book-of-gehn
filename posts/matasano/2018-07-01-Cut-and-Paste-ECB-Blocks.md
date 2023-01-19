---
layout: post
title: "Cut and Paste ECB blocks"
tags: [cryptography, matasano, cryptonita, ECB, forgery, forge]
inline_default_language: python
---

In this game we control partially a plaintext that is encrypted
under ECB mode with a secret key.

This time the idea is not to reveal the key but to *forge* a plaintext.

{{ spoileralert() }}
Welcome to the [ECB cut-and-paste](https://cryptopals.com/sets/2/challenges/13)
challenge!<!--more-->

### Prelude: profile request

Imagen a scenario where two parties send encrypted messages using AES
in ECB mode.

<!--
>>> import sys
>>> sys.path.append("./posts/matasano/assets")
>>> from challenge import generate_config, enc_ecb, dec_ecb  # byexample: +timeout=10

>>> seed = 20180701   # make the tests 'random' but deterministic
>>> block_size = 16     # leave this fixed, it is what happen in practice

>>> # encrypt/decrypt under this 'random' environment
>>> cfg = generate_config(random_state=seed, block_size=block_size, enc_mode='ecb')
-->

Consider the following function that builds a ciphertext from an hypothetical
*"create profile for a new user"*:

```python
>>> from cryptonita import B                # byexample: +timeout=10

>>> def profile_request_for(email):
...     assert b'&' not in email
...     assert b'=' not in email
...     assert b'@'     in email
...
...     msg = B(b'email=%s&uid=10&role=user' % email)
...     msg = msg.pad(block_size, 'pkcs#7')
...     return enc_ecb(msg, cfg.key, block_size)

>>> c = profile_request_for(b'honest-email@example.com')
>>> c
<...>\xc1\xa4\x89<...>
```

The ``profile_request_for`` can create as many user as we want but all of them will
have the same privilege level or role: ``user``.

The adversary (us) can call this function as many times as he/she wants
but it cannot neither change it (like disabling the checks) nor peak the
secret key.

### Prelude: profile creation

Then the ciphertext can be sent to a server where the given credentials are
stored and the profile is *"created"*.

```python
>>> from urllib.parse import parse_qs
>>> def create_profile(encrypted_request):
...     msg = dec_ecb(encrypted_request, cfg.key, block_size)
...     msg = msg.unpad('pkcs#7')
...
...     return parse_qs(msg, strict_parsing=True)

>>> create_profile(c)
{b'email': [b'honest-email@example.com'], b'role': [b'user'], b'uid': [b'10']}
```

## Forgery (naive try)

It would be cool to forge ``role=admin`` *with an injection there*
but it is not possible.

```python
>>> profile_request_for(b'dishonest@evil.com&role=admin')
<...>
AssertionError
```

Let's forge **anyways** with [cryptonita](https://pypi.org/project/cryptonita/).

## Forgery (as crypto pro)

### Block alignment

In principle our partial plaintext is inserted at some *fixed but
unknown* position.

The first step is to know where.

The key insight is that if we insert 2 full and aligned blocks we will
get 2 identical ciphertext blocks.

So we insert these and slowly add one extra byte at time until we get
the two identical ciphertext blocks.

The alignment required was exactly the amount of extra bytes inserted.

```python
>>> for alignment in range(block_size):
...     c = profile_request_for(B('@' * (block_size * 2 + alignment)))
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

*Of course we could cheat a little!* If the *prefix is known*, we just
do the maths:

```python
>>> block_size - len("email=")
10
```

### Crafting the email

`profile_request_for` *will encrypt for us anything*, as long as the
email is a "valid email".

We can prepare specially crafted one:

```python
>>> align_pad = B('A' * alignment)
>>> target = B('admin').pad(block_size, 'pkcs#7')
>>> posfix = B('@evil.com')

>>> crafted_email = align_pad + target + posfix
>>> crafted_email
'A<...>AAAadmin\x0b\x0b\x0b<padding>\x0b@evil.com'
```

The `align_pad` ensures that what follows (`"admin"`) is
*at the begin* of a block.

The `target` is a full block with the string `"admin"` and a padding
**as if** it were at the end of the plaintext (which it is not).

The `posfix` just completes the crafting so the whole looks an email
address.

{% call	mainfig('cut_and_paste_align_before_cut.svg', width='60%') %}
{% endcall %}

### Cut the block

Now we encrypt the crafted profile. The trick is that **we know**
that a full block will be the encryption of `"admin"` and **we know**
exactly where.

This is because EBC encrypts all the blocks in the same way, no
matter where they are.

```python
>>> c = profile_request_for(crafted_email)
>>> cut = c.nblocks(block_size)[indexes[0]]
```

{% call	mainfig('cut_and_paste_align_cutting.svg' , width='60%') %}
{% endcall %}

### Paste the block

Now, the final step.

{% call	marginnotes() %}
In a real case you will also make your that the email is a valid one:
the whole thing is about getting *you* an admin.

If you cannot login later, it would be pointless.
{% endcall %}

We craft another email but this time the goal is to align the `role=`
plaintext *at the end* of the block.

In other words, what follows `role=` must be at the begin of the next
block.

{% call	mainfig('cut_and_paste_align_cutting2.svg', width='90%') %}
{% endcall %}

Then we *paste the block*.

In its replacement we will put our crafted cipher block.

```python
>>> c = profile_request_for(b'me-AAAAAAAAAAAAAAAAA@evil.com')
>>> forged = B(c, mutable=True)
>>> forged[-block_size:] = cut
```

{% call	mainfig('cut_and_paste_align_pasting.svg', width='90%') %}
{% endcall %}

How many ``A`` we need to add will depend: I tried several times using
``create_profile`` as oracle until I got the payload aligned such the
last *boundary* matched and no error was throw.

## Forge!

Voila!, the plaintext is recovered by the server, the padding removed and we
get a admin profile.

```python
>>> create_profile(B(forged))
{b'email': [b'me-AAAAAAAAAAAAAAAAA@evil.com'],
 b'role': [b'admin'],
 b'uid': [b'10']}
```


{% call	mainfig('cut_and_paste_align_pasted.svg' ) %}
{% endcall %}
