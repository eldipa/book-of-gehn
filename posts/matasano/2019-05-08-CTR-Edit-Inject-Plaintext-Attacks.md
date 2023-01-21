---
layout: post
title: "CTR Edit/Inject Plaintext Attacks"
tags: [cryptography, matasano, cryptonita, CTR, counter, forgery]
inline_default_language: python
---

A CTR-mode cipher turns a block cipher into a stream cipher.

With this, a ciphertext can be edited *in place* generating
enough of the key stream, decrypting and re-encrypting the edited
portion.

{{ spoileralert() }}

One can replace part of the plaintext, extend it or even reduce it.

But this beautiful property of a CTR mode (and any other stream cipher)
is actually a booby-trap.

{% call	mainfig('ctr-edit-slicing-window.svg', width='80%', indexonly=True ) %}
{% endcall %}
<!--more-->

<!--
>>> import sys
>>> sys.path.append("./posts/matasano/assets")
>>> from challenge import generate_config, enc_ctr, dec_ctr # byexample: +timeout=10

>>> seed = 20190508
>>> secret_cfg = generate_config(random_state=seed)
-->

Imagine the following function:

```python
>>> def edit(ctext, new_ptext, offset, secret_cfg):
...     sz = len(new_ptext)
...     # dummy plaintext to "encrypt" and obtain the secret stream
...     # we make it large enough to cover the new_ptext size at the given
...     # offset
...     dummy = B(0) * (offset + sz)
...
...     # partial encrypting stream
...     stream = enc_ctr(dummy, secret_cfg.key, secret_cfg.nonce)
...
...     # keep only the bytes needed to decrypt and re-encrypt at the
...     # offset
...     stream = stream[offset:]
...     assert len(stream) == sz
...
...     # override the specific part
...     # here the advantage of CTR: we don't need to decrypt everything
...     new_ctext = ctext.splice(offset, sz, new_ptext ^ stream)
...     return new_ctext
```

The ``edit`` function allows us edit or patch a ciphertext modifying
the plaintext  *knowing the secret key*.

No magic.

{% call marginnotes() %}
This unlocks the
[Break "random access read/write" AES CTR](https://cryptopals.com/sets/4/challenges/25)
challenge. {% endcall %}

But if the adversary has access to `edit` and he/she can call it with
and arbitrary *new plaintext* (`new_ptext`), we can recover the secret
stream.

The vulnerability is that the original ciphertext and the one returned
by `edit` were both encrypted with the **same** key stream.

This is a simple **known-plaintext attack**.

```python
>>> from cryptonita import B, load_bytes     # byexample: +timeout=10

>>> ptext = B(open('./posts/matasano/assets/25.txt', 'rt'), encoding=64)
>>> ctext = enc_ctr(ptext, secret_cfg.key, secret_cfg.nonce)

>>> new_ptext = B('A') * len(ctext)  # B(0) would be much easier (but boring)
>>> cpatched = edit(ctext, new_ptext, 0, secret_cfg)

>>> kstream = cpatched ^ new_ptext
>>> ptext == ctext ^ kstream
True
```

If the ``edit`` function has some kind of limitation on the size of
the patch, we only need to edit it by pieces:

```python
>>> tmp = []
>>> N = 16
>>> for n, pb in enumerate(new_ptext.nblocks(N)):        # byexample: +timeout=10
...     offset = n*N
...     tmp.append(edit(ctext, pb, offset, secret_cfg)[offset:offset+N])

>>> cpatched = B.join(tmp)

>>> kstream = cpatched ^ new_ptext
>>> ptext == ctext ^ kstream
True
```

## Known Partial Plaintext Window

Imagine that you have access to an ``inject_pad`` function that allows
you to inject a *secret padding at an unknown position* in the plaintext
but you can control the **length** of the padding inserted.

```python
>>> def inject_pad(ctext, pad_len, secret_cfg):
...     # get some random and unknown padding
...     p = secret_cfg.prefix
...
...     # repeat 'p' enough times to cover 'pad_len' bytes of padding
...     # making 'p' infinite and slicing 'pad_len' zeros makes the trick
...     padding = p.inf()[:pad_len]
...     assert len(padding) == pad_len
...
...     # we don't need to decrypt the whole ctext but this is easier
...     ptext = dec_ctr(ctext, secret_cfg.key, secret_cfg.nonce)
...
...     # pick a random and secret position where to do the injection
...     # of the known partial plaintext (padding)
...     offset = secret_cfg.n8
...
...     # inject the padding (know plaintext) at random location
...     ptext = ptext.splice(offset, 0, padding)
...
...     # encrypt back again (here again the same error: we are reusing
...     # the key and nonce)
...     return enc_ctr(ptext, secret_cfg.key, secret_cfg.nonce)
```

This *feature* makes the system **vulnerable**.

### Finding the padding injection offset

Because the original and the new ciphertexts are encrypted in CTR
with the *same* secret, both will use the *same* key stream and
therefore
both streams will *share the same prefix* until the *offset* were the
injection was done.

```python
>>> ptext = B(open('./posts/matasano/assets/25.txt', 'rt'), encoding=64)
>>> ctext = enc_ctr(ptext, secret_cfg.key, secret_cfg.nonce)

>>> ctext2 = inject_pad(
...             ctext,
...             pad_len = 1,
...             secret_cfg = secret_cfg
...         )
```

If we do a xor between them we will get a bunch of zeros until the first
moment in which the plaintext differ: the offset at where the injection
happen.

```python
>>> clen = len(ctext)
>>> x_ctexts = ctext ^ ctext2[:clen]

>>> next((i for i, c in enumerate(x_ctexts) if c != 0), None)
187
```

### Finding the known partial plaintext offset

Now imagine that you know a fraction of the plaintext but
**you don't know where** is in the plaintext but you know
that it is *after* the injection point:

```python
>>> N = 16
>>> pknown = ptext[secret_cfg.n8:secret_cfg.n8+N]
```

Under the assumption that the known plaintext is on the right *after*
the padding, we can detect where it is: we just need to search
for the self-xor of it:

```python
>>> x_pknowns = pknown[1:] ^ pknown[:-1]
>>> pknown_offset = x_ctexts.index(x_pknowns) - 1

>>> 187 <= pknown_offset
True
```

### Moving window: recover the whole key stream

Knowing where the `N` bytes long known plaintext is we can recover
`N` bytes of the CTR key stream.

We just xor the known plaintext with the ciphertext at the correct
location. No big deal.

{% call	mainfig('ctr-edit-first-slice.svg', width='70%' ) %}
{% endcall %}

But with the `inject_pad` function we are adding padding *before*
the location of the known plaintext and indeed
**we are moving its offset**.

So if we inject `N` bytes the padding, *the window will move N bytes*
and we will able to recover *another* `N` bytes of the key stream.

{% call	mainfig('ctr-edit-second-slice.svg', width='75%' ) %}
{% endcall %}


Repeating this we can recover all the key stream (except the begin):

```python
>>> tmp = []
>>> for l, o in enumerate(range(pknown_offset, len(ctext), N)): # byexample: +timeout=10
...     ctext2 = inject_pad(ctext, l*N, secret_cfg)
...     assert len(ctext2) == len(ctext) + (l*N)
...     tmp.append(ctext2[o:o+N] ^ pknown)
```

In essential we use the partial known plaintext as a window to see a
piece of the key stream and the ``inject_pad`` to *move* the window to the
right and recover more of it.

{% call	mainfig('ctr-edit-slicing-window.svg', width='80%' ) %}
{% endcall %}

The last key stream chunk recovered may contain bytes that does not belong
to the original key stream.

We are not interested in those:

```python
>>> nlast = len(ctext[pknown_offset:]) % N
>>> if nlast:
...     tmp[-1] = tmp[-1][:nlast]
```

Finally, from the key stream we can break the ciphering and recover
the plaintext (except the begin):

```python
>>> kstream = B.join(tmp)
>>> recoverd_ptext = ctext[pknown_offset:] ^ kstream

>>> ptext[pknown_offset:] == recoverd_ptext
True
```

A similar attack can be done with a ``delete`` primitive: instead of
injecting padding we remove plaintext therefor moving the known
plaintext window to the left instead to the right.
