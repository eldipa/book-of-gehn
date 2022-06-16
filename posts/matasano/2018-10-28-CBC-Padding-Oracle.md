---
layout: post
title: "CBC Padding Oracle Attack"
tags: [cryptography, matasano, cryptonita, CBC, cipher block chaining, padding oracle]
inline_default_language: python
---

AES and other ciphers work on blocks; if the plaintext length
is not multiple of the block size a padding is added.

If during the decryption the pad is checked and returns an error,
we can use this to build a *padding oracle*:
a function that will tell us if an encrypted plaintext
has a valid pad or not.

Armed with this *padding oracle* we can break CBC
one byte at time.

{{ spoileralert() }}
Ready? *Go!*<!--more-->

## Padding oracle

Consider the following plaintext of 15 bytes:

```python
>>> from cryptonita import B, load_bytes     # byexample: +timeout=10
>>> m = B('AAAABBBBAAAA\x03\x03\x03')
>>> len(m)
15
```

Now, if we pad this using ``pkcs#7``{.none} to complete a 16 bytes block,
the last byte will be ``01``:

```python
>>> mpadded = B(m.pad(16, 'pkcs#7'), mutable=True)
>>> mpadded[-1]
1
```

Now, if we change the last byte (we forge it), the unpad of the forged
block will success or not based on what byte we set.

There are three possible outcomes based on this last byte:

 - the unpad works because the last byte matches the original padding byte (``01``).
 - the unpad works because the last byte matches *another* padding sequence (``03``).
 - the unpad fails.

The first case happen with the forged byte is actually the original the
last byte.

```python
>>> mpadded[-1] = 0x01
>>> mpadded.unpad('pkcs#7')
'AAAABBBBAAAA\x03\x03\x03'
```

The second case happen because our forged byte generates, by luck, another
valid padding sequence.

```python
>>> mpadded[-1] = 0x03
>>> mpadded.unpad('pkcs#7')
'AAAABBBBAAAA\x03'
```

The third and last case happen with any other byte:

```python
>>> mpadded[-1] = 0x02
>>> mpadded.unpad('pkcs#7')
Traceback (most recent call last):
<...>
ValueError: Bad padding 'pkcs#7' with last byte 0x2

>>> mpadded[-1] = 0xff
>>> mpadded.unpad('pkcs#7')
Traceback (most recent call last):
<...>
ValueError: Bad padding 'pkcs#7' with last byte 0xff
```

Armed with this we can build a padding oracle for CBC:
a function that will tell us if an encrypted plaintext
has a valid pad or not.

<!--
>>> import sys
>>> sys.path.append("./posts/matasano/assets")
>>> from challenge import generate_config, enc_cbc, dec_cbc  # byexample: +timeout=10

>>> seed = 20181028
>>> bsize = 16

>>> cfg = generate_config(random_state=seed, block_size=bsize)
-->

```python
>>> def decrypt_and_unpad_oracle(c):
...     iv, c = c[:bsize], c[bsize:]
...     p = dec_cbc(c, cfg.key, iv) # do not use cfg.iv ;)
...     try:
...         p.unpad('pkcs#7')
...         return True
...     except Exception as e:
...         return False
```

## CBC decryption and padding

Let's be `m`{.mathjax} the ith plaintext block,
`c`{.mathjax} the i-1th ciphertext block and
`x`{.mathjax} the decryption of the ith ciphertext block.

Then, we can say that for CBC the plaintext block `m`{.mathjax}
is reconstructed from this:

```tex;mathjax
x \oplus c = m
```

Let's say now that instead of `c`{.mathjax}
we use `f`{.mathjax}, a *forged* ciphertext block,
if we are reconstructing the last plaintext block, this one will be:

```tex;mathjax
x \oplus f = ?
```

Now, because this is the last block, this will affect the padding
of the final plaintext.

The padding will be ok *only if* `x \oplus f`{.mathjax} is
equals to one of these:

```
    [?  ?  ?  ... ?  ?  01]
    [?  ?  ?  ... ?  02 02]
    [?  ?  ?  ... 03 03 03]
    [?  0f 0f ... 0f 0f 0f]
    [10 10 10 ... 10 10 10]
```

Given this fact and using a *padding oracle* we can break CBC
one byte at time.

## Guess the last byte

For the plaintext block `m`{.mathjax}, let's be `m_1`{.mathjax},
the last byte of the block.
Using the same convention, this last byte is

```tex;mathjax
x_1 \oplus c_1 = m_1
```

If instead of `c_1`{.mathjax} we use a forged last byte
`f_1`{.mathjax}, the decrypted byte will be

```tex;mathjax
x_1 \oplus f_1 = ?
```

The decrypted message will have a valid padding only if:

```tex;mathjax
\begin{cases}
x_1 \oplus f_1 = 01 & (1)\\
x_1 \oplus f_1 = pp & (2)
\end{cases}
```

The case 2 means that `x_1 \oplus f_1`{.mathjax} is equal to
the original padding byte and this will happen only if
`f_1 = c_1`{.mathjax} or in other words if we didn't
forge anything.

It doesn't add much info.

The case 1 is more juicy as this is the other case with a valid
padding and, by definition, it must be ``01``.

Then,

```tex;mathjax
\begin{align*}
x_1 \oplus f_1 & = 01                           \\
           x_1 & = 01 \oplus f_1
\end{align*}
```

So we *learnt* `x_1`{.mathjax} and from here it is trivial
to break the last plaintext byte:

```tex;mathjax
\begin{align*}
                x_1 \oplus c_1 & = m_1          \\
    (01 \oplus f_1) \oplus c_1 & = m_1
\end{align*}
```

as `f_1`{.mathjax} is our forged byte and `c_1`{.mathjax}
is the last byte of the previous ciphertext block, all of them known by us.

The case 1 and 2 are easily identified as in the second case
`f_1 = c_1`{.mathjax}.

There is, however, a special situation in which the case 1 and 2 are
the same: this happens when the original padding byte is actually ``01``.

Nevertheless, the equation `(01 \oplus f_1) \oplus c_1 = m_1`{.mathjax}
is still true.

## Guess the penultimate byte

Knowing `x_1`{.mathjax} we can forge the value
of `m_1`{.mathjax} to ``02``:

```tex;mathjax
\begin{align*}
      x_1 \oplus f_1 & = 02                     \\
                 f_1 & = (02 \oplus x_1)
\end{align*}
```

This `f_1`{.mathjax} is **not** the same than the previous section:
it is a different
forged byte used to forge a ``02`` in the last value of the plaintext.

With this, the penultimate byte will forge a plaintext with a
*valid padding* only if:

```tex;mathjax
x_2 \oplus f_2 = 02
```

Then, for the case of a valid padding we can guess
`x_2`{.mathjax} and therefore `m_2`{.mathjax}:

```tex;mathjax
\begin{align*}
      x_2 \oplus f_2 & = 02                     \\
                 x_2 & = (02 \oplus f_2)
\end{align*}
```

```tex;mathjax
\begin{align*}
                   x_2 \oplus c_2 & = m_2                     \\
      (02 \oplus f_2) \oplus c_2  & = m_2
\end{align*}
```

At difference with guessing the last byte, in this scenario there is
only one possible value for a valid padding: ``02``

## Guessing the rest of the bytes in a block

Now we just repeat.

Break the last byte first, use that to forge the last byte in
the plaintext to ``01`` and break the penultimate byte.

Then use those two to forge the last two bytes of the
plaintext to ``02 02`` and break the third.

And so on till you break the whole block

```python
>>> def break_cbc_last_block(cblocks, bsize, oracle):
...     prev_cblock = cblocks[-2]
...
...     x = B(range(bsize, 0, -1), mutable=True)
...     x ^= prev_cblock
...     for i in range(bsize-1, -1, -1):
...         prefix = prev_cblock[:i]
...         padn   = B(bsize-i)
...         posfix = B(padn * (bsize-i-1)) ^ x[i+1:]
...
...         # forge the penultimate ciphertext block
...         cblocks[-2] = B(prefix + B(0) + posfix, mutable=True)
...         for n in range(256):
...             if prev_cblock[i] == n:
...                 continue
...
...             # update the forged byte
...             cblocks[-2][i] = n
...             forged_ciphertext = B.join(cblocks)
...
...             good = oracle(forged_ciphertext)
...             if good:
...                 x[i] = (padn ^ B(n))
...                 break
...
...     cblocks[-2] = prev_cblock   # restore backup
...     x ^= prev_cblock
...     return x    # plain text block
```

```python
>>> plaintext = B('MDAwMDAwTm93IHRoYXQgdGhlIHBhcnR5IGlzIGp1bXBpbmc=', encoding=64)
>>> ciphertext = cfg.iv + enc_cbc(plaintext.pad(bsize, 'pkcs#7'), cfg.key, cfg.iv)

>>> cblocks = list(ciphertext.nblocks(bsize))

>>> break_cbc_last_block(cblocks, bsize, decrypt_and_unpad_oracle)
'ing\r\r\r\r\r\r\r\r\r\r\r\r\r'
```

## Break CBC

Now we just need to repeat the whole thing again for each block:
once we break the last block we remove it from the ciphertext
and we repeat the attack to until all the ciphertext blocks are decrypted.

```python
>>> p = []
>>> while len(cblocks) > 1:
...     p.append(break_cbc_last_block(cblocks, bsize, decrypt_and_unpad_oracle))
...     del cblocks[-1]

>>> p.reverse()
>>> decripted = B('').join(p).unpad("pkcs#7")

>>> decripted
'000000Now that the party is jumping'

>>> decripted == plaintext
True
```

This attack is implemented in
[cryptonita](https://pypi.org/project/cryptonita/). Here is a set of
different ciphertexts to break.

{% call marginnotes() %}
This unlocks the
[The CBC padding oracle](https://cryptopals.com/sets/3/challenges/17)
challenge.
{% endcall %}

Enjoy!

```python
>>> plaintexts = list(load_bytes('./posts/matasano/assets/17.txt', encoding=64))
>>> ciphertexts = [cfg.iv + enc_cbc(p.pad(bsize, 'pkcs#7'), cfg.key, cfg.iv) for p in plaintexts]

>>> from cryptonita.attacks.block_ciphers import decrypt_cbc_padding_attack
>>> brokens = [decrypt_cbc_padding_attack(c, bsize, decrypt_and_unpad_oracle) for c in ciphertexts] # byexample: +timeout 20
>>> brokens = [p.unpad("pkcs#7") for p in brokens]

>>> plaintexts == brokens
True

>>> brokens
['000000Now that the party is jumping',
 "000001With the bass kicked in and the Vega's are pumpin'",
 '000002Quick to the point, to the point, no faking',
 "000003Cooking MC's like a pound of bacon",
 "000004Burning 'em, if you ain't quick and nimble",
 '000005I go crazy when I hear a cymbal',
 '000006And a high hat with a souped up tempo',
 "000007I'm on a roll, it's time to go solo",
 "000008ollin' in my five point oh",
 '000009ith my rag-top down so my hair can blow']
```
