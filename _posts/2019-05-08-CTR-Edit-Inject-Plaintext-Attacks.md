---
layout: post
title: "CTR Edit/Inject Plaintext Attacks"
---

A CTR-mode cipher turns a block cipher into a stream cipher.

With this, a ciphertext can be edited *in place* generating
enough of the key stream, decrypting and re-encrypting the edited
portion.

One can replace part of the plaintext, extend it or even reduce it.

But this beautiful property of a CTR mode (and any other stream cipher)
is actually a booby-trap.
<!--more-->

<!--
>>> import sys
>>> sys.path.append("./assets/matasano")
>>> from challenge import generate_config, enc_ctr, dec_ctr # byexample: +timeout=10

>>> seed = 20190508
>>> secret_cfg = generate_config(random_state=seed)
-->

Imagine the following function:

```python
>>> def edit(ctext, patch, offset, secret_cfg):
...     # we don't need to decrypt the whole ctext but this is easier
...     ptext = dec_ctr(ctext, secret_cfg.key, secret_cfg.nonce)
...     ptext = B(ptext, mutable=True)
...     ptext[offset:offset+len(patch)] = patch
...     return enc_ctr(ptext, secret_cfg.key, secret_cfg.nonce)
```

The ``edit`` function allows us edit or patch a ciphertext modifying
the plaintext.

{% marginnote 'This unlocks the
[Break "random access read/write" AES CTR](https://cryptopals.com/sets/1/challenges/25)
challenge.' %}

This generates two different ciphertexts
encrypted with the **same** key stream which breaks CTR
with a simple known-plaintext attack.

```python
>>> from cryptonita import B, load_bytes     # byexample: +timeout=10

>>> ptext = B(open('./assets/matasano/25.txt', 'rt'), encoding=64)
>>> ctext = enc_ctr(ptext, secret_cfg.key, secret_cfg.nonce)

>>> patch = B('A') * len(ctext)
>>> cpatched = edit(ctext, patch, 0, secret_cfg)

>>> kstream = cpatched ^ patch
>>> ptext == ctext ^ kstream
True
```

If the ``edit`` function has some kind of limitation on the size of
the patch, we only need to edit it by pieces:

```python
>>> tmp = []
>>> N = 16
>>> for n, pb in enumerate(patch.nblocks(N)):        # byexample: +timeout=10
...     offset = n*N
...     tmp.append(edit(ctext, pb, offset, secret_cfg)[offset:offset+N])

>>> cpatched = B.join(tmp)

>>> kstream = cpatched ^ patch
>>> ptext == ctext ^ kstream
True
```

## Known Partial Plaintext Window

Imagine that you have access to an ``inject_pad`` function that allows
you to inject a random padding at an unknown position in the plaintext
but you can control the length of the padding inserted.

```python
>>> def inject_pad(ctext, length, secret_cfg):
...     # get some random and unknown padding
...     p = secret_cfg.prefix
...
...     # repeat 'p' enough times to cover 'length' bytes of padding
...     # making 'p' infinite and xor with 'length' zeros makes the trick
...     padding = p.inf() ^ (B(0) * length)
...     assert len(padding) == length
...
...     # we don't need to decrypt the whole ctext but this is easier
...     ptext = dec_ctr(ctext, secret_cfg.key, secret_cfg.nonce)
...
...     # inject the padding at some random but lesser value
...     # than the known partial plaintext
...     offset = secret_cfg.n8
...     ptext = ptext[:offset] + padding + ptext[offset:]
...     return enc_ctr(ptext, secret_cfg.key, secret_cfg.nonce)
```

This *feature* makes the system vulnerable.

Because the original and the new ciphertexts are encrypted in CTR
with the *same* secret, both will use the *same* key stream and therefor
both stream will *share the same prefix* until the offset were the
injection was done.

```python
>>> ctext2 = inject_pad(ctext, 1, secret_cfg)

>>> clen = len(ctext)
>>> x_ctexts = ctext ^ ctext2[:clen]

>>> next((i for i, c in enumerate(x_ctexts) if c != 0), None)
187
```

Now imagine that you know a fraction of the plaintext but
you don't know *where* is in the plaintext but you know
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

Now, with this we can recover ``N`` bytes of the key stream. No much.

But if we *inject* more padding, let's say ``N`` bytes the known
plaintext will move to the right the same amount allowing us to recover
the *next* ``N`` bytes of the key stream.

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
>>> pbroken = ctext[pknown_offset:] ^ kstream

>>> ptext[pknown_offset:] == pbroken
True
```

A similar attack can be done with a ``delete`` primitive: instead of
injecting padding we remove plaintext therefor moving the known
plaintext window to the left instead to the right.
