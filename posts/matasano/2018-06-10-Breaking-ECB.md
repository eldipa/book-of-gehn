---
layout: post
title: "Breaking ECB"
tags: [cryptography, matasano, cryptonita, ECB]
inline_default_language: none
---

{{ spoileralert() }}
In the previous post we built
[an ECB/CBC oracle](/articles/2018/06/09/ECB-CBC-Oracle.html);
now it's time to take this to the next level and
break ECB [one byte at time](https://cryptopals.com/sets/2/challenges/14).
<!--more-->


### Generating secrets

We will use the same setup of the
[previous post](/articles/2018/06/09/ECB-CBC-Oracle.html)
but this time, our objective will decrypt ECB without the key.

{% call marginnotes() %}
In fact, there are two challenges: the
[simple](https://cryptopals.com/sets/2/challenges/12)
and the
[harder](https://cryptopals.com/sets/2/challenges/14)
versions. We will break the harder of course.
{% endcall %}

Remember that we will have a secret payload appended to the attacker-controlled plaintext
and it is the objective for the
[byte-at-a-time ECB decryption challenge](https://cryptopals.com/sets/2/challenges/14)..

```python
>>> import sys
>>> sys.path.append("./posts/matasano/assets")

>>> from cryptonita import B, load_bytes     # byexample: +timeout=10
>>> from challenge import enc_ecb, generate_config

>>> seed = 20180610
>>> block_size = 16
>>> secret = B('Um9sbGluJyBpbiBteSA1LjAKV2l0aCBteSByYWctdG9wIGRvd24gc28gbXkg' +
...            'aGFpciBjYW4gYmxvdwpUaGUgZ2lybGllcyBvbiBzdGFuZGJ5IHdhdmluZyBq' +
...            'dXN0IHRvIHNheSBoaQpEaWQgeW91IHN0b3A/IE5vLCBJIGp1c3QgZHJvdmUg' +
...            'YnkK', encoding=64)

>>> cfg = generate_config(random_state=seed, block_size=block_size, posfix=secret)

>>> # pick the random prefix and let it fixed (constant)
>>> cfg = generate_config(cfg, prefix=cfg.prefix)
```

This is our encryption oracle:

```python
>>> def encryption_oracle(partial_plaintext):
...     global cfg
...     cfg = generate_config(cfg) # update the random attributes
...
...     block_size = cfg.kargs['block_size']
...
...     # prepend + append with two random strings; pad it later
...     plaintext = cfg.prefix + partial_plaintext + cfg.posfix
...     plaintext = plaintext.pad(block_size, cfg.pad_mode)
...
...     return enc_ecb(plaintext, cfg.key, block_size)
```

### Block alignment

{% call marginfig('break_ecb_misalign_by2.svg') %}
{% endcall %}

The prepended payload is constant but it is still unknown to the
us/adversary.

Before proceed we need to know for how many bytes our attacker-controlled
payload is misaligned.

{% call marginfig('break_ecb_misalign_by1.svg') %}
{% endcall %}

Basically we start with a plaintext of *twice* the size of the block size
and we add one byte at time.

When we find two *consecutive* cipher blocks that are the same, we are done.


{% call marginfig('break_ecb_aligned.svg') %}
{% endcall %}

The amount of extra bytes that we added is the answer.

```python
>>> for alignment in range(block_size):
...     c = encryption_oracle(B('a' * (block_size * 2 + alignment)))
...     if c.nblocks(block_size).has_duplicates(distance=0):
...         break

>>> alignment
10

>>> len(cfg.prefix) == block_size - alignment
True
```

### Get the penguin!

Now, with our blocks aligned, we can set as our plaintext two identical blocks
but the last one will have one byte less.

This missing byte will be filled by the next *secret* plaintext byte ``?``, unknown by us:

{% call	mainfig('ecb_break_1_byte.svg', width='70%') %}
{% endcall %}


These two blocks will yield the same two cipher blocks only if the last byte
of the first block (``x``) is equal to the last byte of the second block (``?``)

{% call	marginnotes() %}
The beauty of this is that no matter if the key used to encrypt changes,
this will still work as long as the plaintext does not change.

Even if the length of the prefix (plaintext *before* our controlled part)
changes, as long as it changes in a small range, it is just a matter of
trying more times.

{% endcall %}

The first block (``aaax``) is our *probe block* used to probe and find the
unknown byte ``?``.

The second *partial* block (``aaa``) is used to align the unknown plaintext
so the *first unknown byte* is in place at the end of this block, named
as *align block*.

After found the value of ``?`` we *shift* the unknown plaintext on byte to
the left and we continue breaking one byte at time.

{% call	mainfig('ecb_break_2_byte.svg', width='70%') %}
{% endcall %}

After breaking ``block_size`` bytes, we cannot shift to the left further.

But what we can do is to add an extra block: the probe block will not
be testing its next block but the block that is 1 block to the right:

{% call	mainfig('ecb_break_n_byte.svg', width='70%') %}
{% endcall %}

The following is an implementation of the previous algorithm from
[cryptonita](https://pypi.org/project/cryptonita/)
that breaks the ECB cipher using a oracle.

```python
>>> from cryptonita.attacks.block_ciphers import decrypt_ecb_tail

>>> t = decrypt_ecb_tail(alignment, block_size, encryption_oracle)  # byexample: +timeout 10
>>> t = t.unpad('pkcs#7')
>>> t == secret
True

>>> t   # byexample: +norm-ws
"Rollin' in my 5.0\nWith my rag-top down so my hair can blow\nThe girlies on
standby waving just to say hi\nDid you stop? No, I just drove by\n"
```

