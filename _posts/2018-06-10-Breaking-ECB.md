---
layout: post
title: "Breaking ECB"
---

In this post I will show how to use
[an ECB/CBC detection oracle](https://cryptopals.com/sets/2/challenges/11)
to break ECB,
[one byte at time](https://cryptopals.com/sets/2/challenges/14),
using
[cryptonita](https://pypi.org/project/cryptonita/){% sidenote '**-- Spoiler Alert! --**' %}.<!--more-->

### ``PKCS#7`` padding

[Implement PKCS#7 padding](https://cryptopals.com/sets/2/challenges/1),
easy cake.

```python
>>> from cryptonita.bytestring import B, load_bytes     # byexample: +timeout=10

>>> m = B("YELLOW SUBMARINE")
>>> m.pad(20, 'pkcs#7')
'YELLOW SUBMARINE\x04\x04\x04\x04'

```

If a plaintext has an incorrect padding, the ``unpad`` will fail{% sidenote
'Yeup, [PKCS#7 padding validation](https://cryptopals.com/sets/2/challenges/15),
I know what is coming with this....' %}.

```python
>>> m = B("ICE ICE BABY\x05\x05\x05\x05")
>>> m.unpad('pkcs#7')
<...>
ValueError: Bad padding 'pkcs#7' with last byte 5

```

### Cipher block chaining

This time we need to [Implement CBC mode](https://cryptopals.com/sets/2/challenges/10)
ourselves, also known as *Cipher Block Chaining* mode.

At difference with the ECB, the CBC mode uses the previous ciphertext block
to XOR the current plaintext block before encrypting it.

For the first plaintext block we use an
[Initialization Vector](https://en.wikipedia.org/wiki/Initialization_vector)
for the XOR operation.

This IV should be random but for the sake of the test it
will be full of zeros.


```python
>>> import sys
>>> sys.path.append("./assets/matasano")

>>> from challenge import dec_cbc, enc_cbc, enc_ecb

>>> ciphertext = B(open('./assets/matasano/10.txt', 'rb').read(), encoding=64)

>>> iv = B(0) * 16
>>> key = B("YELLOW SUBMARINE")

>>> plaintext = dec_cbc(ciphertext, key, iv)
>>> print(plaintext.unpad('pkcs#7'))
b"I'm back and I'm ringin' the bell<...>Play that funky music \n"

```

### Generating secrets

Before doing real crypto, we need to generate a
*secret and random* configuration{% sidenote
'With the exception of the *seed* that will be fix to make the test
reproducible and the *block side* to make it a little easier.' %}

This configuration will have all the components needed for the challenges:
the random key, the IV, the encryption mode and the *secret payload*.

This secret payload will be appended to the attacker-controlled plaintext
and it is the objective for the next challenge
[Byte-at-a-time ECB decryption](https://cryptopals.com/sets/2/challenges/14){% sidenote
'In fact, there are two challenges: the
[simple](https://cryptopals.com/sets/2/challenges/12)
and the
[harder](https://cryptopals.com/sets/2/challenges/14)
versions. We will break the harder of course.'%}.

```python
>>> from challenge import generate_config

>>> seed = 4
>>> block_size = 16
>>> secret = B('Um9sbGluJyBpbiBteSA1LjAKV2l0aCBteSByYWctdG9wIGRvd24gc28gbXkg' +
...            'aGFpciBjYW4gYmxvdwpUaGUgZ2lybGllcyBvbiBzdGFuZGJ5IHdhdmluZyBq' +
...            'dXN0IHRvIHNheSBoaQpEaWQgeW91IHN0b3A/IE5vLCBJIGp1c3QgZHJvdmUg' +
...            'YnkK', encoding=64)

>>> cfg = generate_config(random_state=seed, block_size=block_size, posfix=secret)

```

Now, let's create the encryption oracle: a function that encrypts
a plaintext under a secret encryption mode.

The attacker/adversary will be in control of part of the plaintext to which
the secret payload will be appended later before the encryption.

Everything else is secret for the adversary: the key, the IV, the mode.

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
...     # encrypt the plaintext with one of the available modes
...     if cfg.enc_mode == 'ecb':
...         ciphertext = enc_ecb(plaintext, cfg.key, block_size)
...     elif cfg.enc_mode == 'cbc':
...         ciphertext = enc_cbc(plaintext, cfg.key, cfg.iv)
...     else:
...         raise ValueError("Invalide chain mode %s" % enc_mode)
...
...     return ciphertext

```

On each call, the secret random configuration is regenerated. So everything
changes on each call with the exception of the ``block_size`` and
``posfix`` (secret).

Those two where fixed during the construction of the configuration and they will
remain fixed.

## The ECB/CBC oracle

Now this is where the action begins.

In this challenge{% sidenote
'[An ECB/CBC detection oracle](https://cryptopals.com/sets/2/challenges/11)' %}
we need to find when a secret encryption is using ECB or CBC mode.

Now, lets create a (partial) plaintext of *three times* the block size.

With a (partial) plaintext of twice the block size we can know if
the cipher is using ECB or CBC because if it is using ECB, two same
plaintext blocks will be encrypted to the same ciphertext block

```
|----|----|----|----|
 AAAA AAAA .... ....    plaintext
  |    |
  V    V
|----|----|----|----|
  CA   CA  .... ....    ciphertext
```

But because we have some *extra plaintext prepended*, we cannot know if our
two blocks will be *aligned to the block boundary*.

```
|----|----|----|----|
 xAAA AAAA Ayyy ....    plaintext (not aligned)
  |    |    |
  V    V    V
|----|----|----|----|
  C1   CA   C2  ....    ciphertext


|----|----|----|----|
 xxxx AAAA AAAA ....    plaintext (aligned)
       |    |
       V    V
|----|----|----|----|
       CA   CA  ....    ciphertext

```

To workaround this we set a plaintext three times the block size:

```
|----|----|----|----|
 xAAA AAAA AAAA Ayyy    plaintext (always aligned)
  |    |    |    |
  V    V    V    V
|----|----|----|----|
  C1   CA   CA   C2     ciphertext
```

Now it is a matter of counting duplicated blocks.

In [cryptonita](https://pypi.org/project/cryptonita/) there is
a convenient ``iduplicates`` method for this.

If we found one block duplicated assume that we are using ECB
otherwise CBC.

We will repeat this 1024 to prove that this works:

```python
>>> choosen_partial_plaintext = B('A' * block_size * 3)

>>> for i in range(1024):
...     c = encryption_oracle(choosen_partial_plaintext)
...     is_ecb = c.nblocks(block_size).iduplicates(distance=0)
...     enc_mode = 'ecb' if is_ecb else 'cbc'
...
...     if cfg.enc_mode != enc_mode:  # is the same that the secret cfg chose?
...         print("Fail")

```

## Breaking ECB

This is it.

For this challenge we will set the encryption mode to ECB and the prepended payload
to some arbitrary but constant text.

```python
>>> # keep the prefix and the enc mode fixed
>>> cfg = generate_config(cfg, prefix=cfg.prefix, enc_mode='ecb')

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
...     if c.nblocks(block_size).iduplicates(distance=0):
...         break

>>> alignment
4

>>> len(cfg.prefix) == block_size - alignment
True

```

### Get the pinguin!

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
>>> from cryptonita.attacks import decrypt_ecb_tail

>>> t = decrypt_ecb_tail(alignment, block_size, encryption_oracle)  # byexample: +timeout 10
>>> t = t.unpad('pkcs#7')
>>> t == secret
True

>>> t
("Rollin' in my 5.0\nWith my rag-top down so my hair can blow\nThe girlies o"
 'n standby waving just to say hi\nDid you stop? No, I just drove by\n')

```

