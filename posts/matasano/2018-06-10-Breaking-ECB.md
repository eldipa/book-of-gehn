---
layout: post
title: "Breaking ECB"
tags: [cryptography, matasano, cryptonita, ECB]
inline_default_language: python
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

{% marginnote
'In fact, there are two challenges: the
[simple](https://cryptopals.com/sets/2/challenges/12)
and the
[harder](https://cryptopals.com/sets/2/challenges/14)
versions. We will break the harder of course.' %}

Remember that we will have a secret payload appended to the attacker-controlled plaintext
and it is the objective for the
[byte-at-a-time ECB decryption challenge](https://cryptopals.com/sets/2/challenges/14)..

```python
>>> import sys
>>> sys.path.append("./assets/matasano")

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

The prepended payload is constant but it is still unknown to the
us/adversary.

Before proceed we need to know for how many bytes our attacker-controlled
payload is misaligned.

Basically we start with a plaintext of *twice* the size of the block size
and we add one byte at time.

When we find two *consecutive* cipher blocks that are the same, we are done.

The amount of extra bytes that we added is the answer.

```python
>>> for alignment in range(block_size):
...     c = encryption_oracle(B('A' * (block_size * 2 + alignment)))
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

This missing byte will be filled by the next plaintext byte ``?``, unknown by us:

```
|----|----|----|----|
 AAAA AAA? .... ....
```

These two blocks will yield the same two cipher blocks only if the last byte
of the first block (``A``) is equal to the last byte of the second block (``?``)

We can extrapolate this testing for all the possible bytes ``x``, until we find
an ``x`` that it is equals to ``?``.

```
|----|----|----|----|
 AAAx AAA? .... ....
    ^    ^
```

The first block (``AAAx``) is our *probe block* used to probe and find the
unknown byte ``?``.

The second *partial* block (``AAA``) is used to align the unknown plaintext
so the *first unknown byte* is in place at the end of this block, named
as *align block*.

```
  align block
      :::
|----|----|----|----|
 AAAx AAA? .... ....

AAAx    probe block
AAA     align block (3)
distance = 0

  align block
      :::
|----|---:|----|----|
 AAAa AAAa .... ....    'a' found
    ^    ^
```

The beauty of this is that no matter if the key used to encrypt changes,
this will work.

Even if the length of the prefix (plaintext *before* out controlled part)
changes, as long as it changes in a small range, it is just a matter of
trying more times.

After found the value of ``?`` we *shift* the unknown plaintext on byte to
the left and we continue breaking one byte at time.

```
  align block
      ::
|----|----|----|----|
 AAax AAa? .... ....    shift and test next byte
    ^    ^

AAax    probe block
AAa     align block (2)
distance = 0

      :
|----|----|----|----|
 Aabc Aabc .... ....    more bytes decrypted
    ^    ^

|----|----|----|----|
 abcx abc? .... ....    test next byte
    ^    ^

abcx    probe block
        align block (0)
distance = 0
```

After breaking ``block_size`` bytes, we cannot shift to the left further.

But what we can do is to add an extra block: the probe block will not
be testing its next block but the block that is 1 block to the right:

```
  align block
      :::
|----|----|----|----|
 bcdx AAAa bcd? ....    insert a pad block in the between, the test block
    ^         ^         is 1-block far form the probe block

bcdx    prob block
AAA     align block (3)
distance = 1


|----|----|----|----|
 bcde AAAa bcde ....    'e' found
    ^         ^
```

And the cycle repeats again:

```
  align block
      ::
|----|----|----|----|
 cdex AAab cde? ....    shift and test next byte
 ^^^^ ^^

cdex    probe block
AA      align block 2
distance = 1
```

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

