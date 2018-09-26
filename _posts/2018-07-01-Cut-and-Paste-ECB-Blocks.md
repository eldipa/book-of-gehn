---
layout: post
title: "Cut and Paste ECB blocks"
---

## ECB malleability

In this game we have control partially of a plaintext that is encrypted
under a ECB mode with a secret key.

```python
>>> from cryptonita.bytestring import B, load_bytes     # byexample: +timeout=10

>>> import sys
>>> sys.path.append("./assets/matasano")

>>> from challenge import generate_config, enc_ecb, dec_ecb

>>> seed = 89
>>> block_size = 16

>>> cfg = generate_config(random_state=seed, block_size=block_size, enc_mode='ecb')

```

This time the idea is not to reveal the key but to forge a plaintext.

CHALLENGE 13: ECB cut-and-paste

Consider the following function that builds a ciphertext with some credentials.

```python
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
<...>\xb4\xe3\xe8<...>

```

Then the ciphertext can be sent to a server where the given credentials are
stored (like a profile is created)

```python
>>> from urllib.parse import parse_qs
>>> def create_profile(ciphertext):
...     msg = dec_ecb(ciphertext, cfg.key, block_size)
...     msg = msg.unpad('pkcs#7')
...
...     return parse_qs(msg, strict_parsing=True)

>>> create_profile(c)
{'email': ['honest-email@example.com'], 'role': ['user'], 'uid': ['10']}

```

It would be cool to forge ``role=admin`` there but it is not possible.

```python
>>> profile_for(b'dishonest@evil.com&role=admin')
<...>
AssertionError

```

### Block alignment

We want to know how many bytes are needed so the plaintext
at its right is aligned with the block boundary.

We already know how to do this... when we have two blocks
encrypted with to the same ciphertext block we are done:

```python
>>> for alignment in range(block_size):
...     c = profile_for(B('@' * (block_size * 2 + alignment)))
...     indexes = c.nblocks(block_size).iduplicates(distance=0, idx_of='both')
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

where ``PPP`` is a ``pkcs#7`` padding such as if the whole ``C1`` block were
the last block of the ciphertext, the decryption + unpadding would success.

### Paste a block

Now, the final step.

We will use our valid email (at the end *we* want to be admin) but it has
to be special: it has to contain enough padding to align the *last* block
so we can cut it and throw it away.

In its replace we will put our crafted cut cipher block.

```python
>>> c = profile_for(b'me-AAAAAAAAAAAAAAAAA@evil.com')
>>> forged = c[:-block_size] + cut

```

The email address ``me-AAAAAAAAAAAAAAAAA@evil.com`` should be a valid
one if we want be owned by us if we want to elevate our priviledges.

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
{'email': ['me-AAAAAAAAAAAAAAAAA@evil.com'], 'role': ['admin'], 'uid': ['10']}

```

