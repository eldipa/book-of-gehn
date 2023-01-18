---
layout: post
title: "ECB/CBC Oracle"
tags: [cryptography, matasano, cryptonita, ECB, CBC, oracle PKCS#7]
inline_default_language: none
---

In this post will review the Cipher Block Chaining mode (or CBC)
and how we can build
[an ECB/CBC detection oracle](https://cryptopals.com/sets/2/challenges/11)
to distinguish ECB from CBC using
[cryptonita](https://pypi.org/project/cryptonita/)

{% call mainfig('ecb_cbc_prefix_aligned.svg', width="70%", indexonly=true) %}
{% endcall %}

{{ spoileralert() }}
This will be the bases for [breaking ECB](/articles/2018/06/10/Breaking-ECB.html)
in a later post.<!--more-->

### ``PKCS#7`` padding

[Implement PKCS#7 padding](https://cryptopals.com/sets/2/challenges/9),
easy cake.

```python
>>> from cryptonita import B, load_bytes     # byexample: +timeout=10

>>> m = B("YELLOW SUBMARINE")
>>> m.pad(20, 'pkcs#7')
'YELLOW SUBMARINE\x04\x04\x04\x04'
```

{% call marginnotes() %}
Yeup, [PKCS#7 padding validation](https://cryptopals.com/sets/2/challenges/15),
I know what is coming with this....
{% endcall %}

If a plaintext has an incorrect padding, the ``unpad`` will fail.

```python
>>> m = B("ICE ICE BABY\x05\x05\x05\x05")
>>> m.unpad('pkcs#7')
Traceback <...>
ValueError: Bad padding 'pkcs#7' with last byte 0x5
```

### CBC - Cipher block chaining

This time we need to [Implement CBC mode](https://cryptopals.com/sets/2/challenges/10)
ourselves, also known as *Cipher Block Chaining* mode.

At difference with the ECB, the CBC mode uses the previous ciphertext block
to XOR the current plaintext block before encrypting it.

For the first plaintext block we use an
[Initialization Vector](https://en.wikipedia.org/wiki/Initialization_vector)
for the XOR operation.

{{ mainfig('cbc-enc.png', max_width='60%') }}

This IV should be random but for the sake of the test it
will be full of zeros.


```python
>>> import sys
>>> sys.path.append("./posts/matasano/assets")

>>> from challenge import dec_cbc, enc_cbc, enc_ecb

>>> ciphertext = B(open('./posts/matasano/assets/10.txt'), encoding=64)

>>> iv = B(0) * 16
>>> key = B("YELLOW SUBMARINE")

>>> plaintext = dec_cbc(ciphertext, key, iv)
>>> print(plaintext.unpad('pkcs#7'))
b"I'm back and I'm ringin' the bell<...>Play that funky music \n"
```

{% call mainfig('cbc-dec.png', max_width='60%') %}
<br />
At difference with the encryption, the decryption of one block doesn&apos;t depend of any other:
you can decrypt any block at random or in parallel.
{% endcall %}

### Generating secrets

{% call marginnotes() %}
With the exception of the *seed* that will be fix to make the test
reproducible and the *block side* to make it a little easier.
{% endcall %}

Before doing real crypto, we need to generate a
*secret and random* configuration

This configuration will have all the components needed for the challenges:
the random key, the IV, the encryption mode and the *secret payload*.

This secret payload will be appended to the attacker-controlled plaintext
so the attacker controls the plaintext only partially.

```python
>>> from challenge import generate_config

>>> seed = 20180610
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
...     block_size = cfg.kargs['block_size']    # (known)
...
...     # prepend + append with two random strings; pad it later
...     plaintext = cfg.prefix + partial_plaintext + cfg.posfix
...     #            (unknown)        (known)         (unknown)
...
...     plaintext = plaintext.pad(block_size, cfg.pad_mode)
...
...     # encrypt the plaintext with one of the available modes
...     # but exactly which, ECB or CBC, is unknown to us
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

{% call marginnotes() %}
[An ECB/CBC detection oracle](https://cryptopals.com/sets/2/challenges/11)
{% endcall %}

In this challenge
we need to find when a secret encryption is using ECB or CBC mode.

Now, lets create a (partial) plaintext of *three times* the block size.

With a (partial) plaintext of twice the block size we can know if
the cipher is using ECB or CBC because if it is using ECB, two same
plaintext blocks will be encrypted to the same ciphertext block

{% call mainfig('ecb_cbc_no_prefix.svg', width='70%') %}
{% endcall %}

But because we have some *extra plaintext prepended*, we cannot know if our
two blocks will be *aligned to the block boundary*.

{% call mainfig('ecb_cbc_prefix_unaligned.svg', width='70%') %}
{% endcall %}

To workaround this we set a plaintext three times the block size:

{% call mainfig('ecb_cbc_prefix_aligned.svg', width='70%') %}
{% endcall %}

Now it is a matter of counting duplicated blocks.

In [cryptonita](https://pypi.org/project/cryptonita/) there is
a convenient ``iduplicates`` method for this.

If we found one block duplicated assume that we are using ECB
otherwise CBC (so we will use ``has_duplicates`` directly).

We will repeat this 1024 to prove that this works:

```python
>>> choosen_partial_plaintext = B('a' * block_size * 3)

>>> for i in range(1024):
...     c = encryption_oracle(choosen_partial_plaintext)
...     is_ecb = c.nblocks(block_size).has_duplicates(distance=0)
...     enc_mode = 'ecb' if is_ecb else 'cbc'
...
...     if cfg.enc_mode != enc_mode:  # is the same that the secret cfg chose?
...         print("Fail")
...         break
```

## Break it!

Of course, [keep reading.](/articles/2018/06/10/Breaking-ECB.html)
