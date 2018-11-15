

## Success or not of the unpad

Consider the following plaintext of 15 bytes:

```python
>>> from cryptonita import B, load_bytes     # byexample: +timeout=10
>>> m = B('AAAABBBBAAAA\x03\x03\x03')
>>> len(m)
15
```

Now, if we pad this using ``pkcs#7`` to complete a 16 bytes block,
the last byte will be 0x01:

```python
>>> mpadded = B(m.pad(16, 'pkcs#7'), mutable=True)
>>> mpadded[-1]
1
```

If we forge the last byte, there are three possible outcomes:

 - the unpad works because the byte forged matches the original padding byte (0x01).
 - the unpad works because the byte forged matches *another* padding sequence (0x03).
 - the unpad fails.

The first case happen with the forged byte is actually the orignal the
last byte.

```python
>>> mpadded[-1] = 0x01
>>> mpadded.unpad('pkcs#7')
'AAAABBBBAAAA\x03\x03\x03'
```

The second case happen because our forged byte generate, by luck, another
padding sequence.

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

## CBC last byte

>>> import sys
>>> sys.path.append("./assets/matasano")
>>> from challenge import generate_config, enc_cbc, dec_cbc  # byexample: +timeout=10

>>> seed = 20181028
>>> bsize = 16

>>> cfg = generate_config(random_state=seed, block_size=bsize)

>>> def decrypt_and_unpad_oracle(c):
...     iv, c = c[:bsize], c[bsize:]
...     p = dec_cbc(c, cfg.key, iv) # do not use cfg.iv ;)
...     try:
...         p.unpad('pkcs#7')
...         return True
...     except Exception as e:
...         return False



>>> plaintext = B('MDAwMDAwTm93IHRoYXQgdGhlIHBhcnR5IGlzIGp1bXBpbmc=', encoding=64)
>>> ciphertext = cfg.iv + enc_cbc(plaintext.pad(bsize, 'pkcs#7'), cfg.key, cfg.iv)

>>> decrypt_and_unpad_oracle(ciphertext)
True


>>> cblocks = list(ciphertext.nblocks(bsize))


## CBC decryption and padding

Let's be m the ith plaintext block, c the i-1th ciphertext block and
x the decryption of the ith ciphertext block.

Then, we can say that for CBC the plaintext block m is reconstructed
from this:
    x ^ c = m

Let's say now that instead of c we use f, a forged ciphertext block,
if we are reconstructing the last plaintext block, this one will be:
    x ^ f = ?

Now, because this is the last block, this will affect the padding
of the final plaintext.

The padding will be ok only if one of this is true
    x ^ f = [?  ?  ?  ... ?  ?  01]
          = [?  ?  ?  ... ?  02 02]
          = [?  ?  ?  ... 03 03 03]
          = [?  0f 0f ... 0f 0f 0f]
          = [10 10 10 ... 10 10 10]

We can use this to break CBC one byte at time

## Guess the last byte

The last byte of the plaintext is m1 = x1 ^ c1.
Then, the last byte forged is x1 ^ f1.

The decrypted message will have a valid padding only if:

    x1 ^ f1 = 01    case 1
    x1 ^ f1 = pp    case 2

The case 2 means that x1 ^ f1 is equal to the original padding byte
and this will happen only if f1 = c1 or in other words if we didn't
forged anything.

It doesn't add much info.

The case 1 is more juidgsy as this is the other case with a valid
padding and, by definition, it must be 01.

Then,
    x1 ^ f1 = 01
         x1 = 01 ^ f1

So we learnt x1 and from here it is trivial to break the last plaintext
byte:
    x1 ^ c1 = m1
    (01 ^ f1) ^ c1 = m1

as f1 is our forged byte and c1 is the last byte of the previous ciphertext
block, all of them known by us.

The case 1 and 2 are eaisly identified as in the second case f1 = c1.

There is, however, a special situation in which the case 1 and 2 are
the same: this happens when the original padding byte is actually 01.

Nevertheless, the equation (01 ^ f1) ^ c1 = m1 is still true.

## Guess the penultimate byte

Knowing x1 we can forge the value of m1 to 02:
    x1 ^ f1 = 02
         f1 = 02 ^ x1

This f1 is not the same than the previous section: it is a different
forged byte used to forge a 02 in the last value of the plaintext.

With this, the penultimate byte will forge a plaintext with a
valid padding only if:
    x2 ^ f2 = 02

Then, for the case of a valid padding we can guess x2 and therefore m2:
    x2 ^ f2 = 02
         x2 = 02 ^ f2

    x2 ^ c2 = m2
    (02 ^ f2) ^ c2 = m2

At difference with guessing the last byte, this scenario there is
only one possible value for a valid padding: 02

## Guessing the rest of the bytes in a block

Now we just repeat.

Break the last byte first, use that to forge the last byte in
the plaintext and break the preultimate byte.

Then use those two to forge the last two bytes of the
plaintext and break the third.


```python
>>> def break_cbc_block(cblocks, bsize, oracle):
...     prev_cblock = cblocks[-2]
...
...     x = B(range(bsize, 0, -1), mutable=True)
...     x ^= prev_cblock
...     for i in range(bsize-1, -1, -1):
...         prefix = prev_cblock[:i]
...         padn = B(bsize-i)
...         posfix = B(padn * (bsize-i-1)) ^ x[i+1:]
...
...         forged_cblock = B(prefix + B(0) + posfix, mutable=True)
...         for n in range(256):
...             if prev_cblock[i] == n:
...                 continue
...
...             forged_cblock[i] = n
...             cblocks[-2] = forged_cblock
...             forged_ciphertext = B('').join(cblocks)
...
...             good = oracle(forged_ciphertext)
...             cblocks[-2] = prev_cblock   # restore backup
...             if good:
...                 x[i] = (padn ^ B(n))
...                 break
...     x ^= prev_cblock
...     return x
```

```python
>>> break_cbc_block(cblocks, bsize, decrypt_and_unpad_oracle)
'ing\r\r\r\r\r\r\r\r\r\r\r\r\r'
```

## Break CBC

Now we just need to repeat the whole thing again for each block:

```python
>>> p = []
>>> while len(cblocks) > 1:
...     p.append(break_cbc_block(cblocks, bsize, decrypt_and_unpad_oracle))
...     del cblocks[-1]

>>> p.reverse()
>>> decripted = B('').join(p).unpad("pkcs#7")

>>> decripted
'000000Now that the party is jumping'

>>> decripted == plaintext
True
```

This attack is implemented in
[cryptonita](https://pypi.org/project/cryptonita/):

```python
>>> plaintexts = list(load_bytes('./assets/matasano/17.txt', encoding=64))
>>> ciphertexts = [cfg.iv + enc_cbc(p.pad(bsize, 'pkcs#7'), cfg.key, cfg.iv) for p in plaintexts]

>>> from cryptonita.attacks import decrypt_cbc_padding_attack
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
