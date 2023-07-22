---
layout: post
title: "Keyed Hash Length Extension Attack"
tags: [cryptography, matasano, cryptonita, hash, extension]
inline_default_language: mathjax
---

How can we know if a message is authentic or not?

A trusted party with access to a private key `k`
can compute an *authentication code* or MAC.

{% call	marginfig('hash-verifier-generic.svg') %}
Compute the *message authentication code* (MAC) doing `H(k ∥ m)`.

In theory only who knows the secret key `k` can create and verify those,
but no, this schema es broken.

This post covers *matasano challenges* from
[28 to 30](https://cryptopals.com/sets/4) so *spoiler alert*.
{% endcall %}

A *keyed hash* prefixes the message with the key `k` and
computes a hash like SHA-1. The resulting hash is the MAC for
the given message.

Then, someone that knows also `k` can verify if a message
is authentic or not computing the MAC and comparing it with the one provided
with the message.

If the computed hash matches the one provided, the message is authentic,
otherwise it is not.

Unfortunately this *prefix-keyed hash* for MAC is **broken**.

Some very well known hash functions *expose* their internal states that
allows an adversary to **append** data to the message and
**continue** the hash computation and generate a **new valid MAC**.

Hence the name *"length extension attack"*.<!--more-->

## Overview of keyed SHA-1

Let's take a look as how SHA-1 is used as a MAC.

The plaintext message is prefixed with the secret key and hashed.

SHA-1 pads the inputs to encode its length and to end with data multiple
of 64 bytes (512 bits).

The padding is a single bit 1 followed by a bunch of bits 0.

The last 8 bytes of the padding are reserved for storing the length of
the un-padded input in bits.

{% call	mainfig('hash-overview.svg') %}
{% endcall %}


## Hash's states

Initially SHA-1 begins with a well known state (composed by 5
`uint32_t`{.cpp} integers).

```python
h0 = 0x67452301
h1 = 0xEFCDAB89
h2 = 0x98BADCFE
h3 = 0x10325476
h4 = 0xC3D2E1F0
```

Once the input is padded, the resulting data is chopped into 64 bytes blocks
and for each block the state of the hash evolves.

Starting from the initial state `h_0`, it evolves to `h_1` after
having processed the block `b_0`. Then, it evolves to `h_2` after
the block `b_1` and so on.

The final state is then used to compute the final hash.

{% call	mainfig('hash-states.svg') %}
{% endcall %}

Note how the hash states `h_1` depends of the first block `b_0` that
contains the secret key (or at least the begin of it).

Therefore, the `h_1` cannot be guessed by an adversary or any other
internal state.



The final state however is *totally exposed* by SHA-1: the concatenation
of the state's variables **is** the resulting hash.

```python
def sha1(msg):
    h0 = 0x67452301
    h1 = 0xEFCDAB89
    h2 = 0x98BADCFE
    h3 = 0x10325476
    h4 = 0xC3D2E1F0

    # pad msg and evolve h0, h1, h2, h3, h4
    # ....

    return '%08x%08x%08x%08x%08x' % (h0, h1, h2, h3, h4)
```

And **that** can be a problem.

## Length Extension Attack

The idea is to recover the hashing state from a MAC and continue
the hashing *as if* we were hashing a *longer* message.

This allows us to *extend* a authentic message with arbitrary payload
and compute a valid MAC for it without knowing the secret key.

In the diagram below, we take the original MAC (the "final" hash state `h_8`)
and compute the hash of the "remaining" message `ext`{.cpp}.

{% call	mainfig('hash-ext-states.svg') %}
Knowing `H(k ∥ ptext)` we use it as the starting state and compute
`H(ext)`.

The resulting hash will be *equivalent* to `H(k ∥ ptext ∥ pad ∥ ext)`:
a valid MAC for the message `ptext ∥ pad ∥ ext`.

An adversary can submit `ptext ∥ pad ∥ ext` and pass it as authentic
without knowing the key `k`.

`ptext` is assumed to be known by the adversary; `pad` isn't but it can
be guessed.
{% endcall %}

The extended message must be padded *as if* we were padding the whole
message: in `pad'` we need to write the length of the whole message.

From the perspective of SHA-1 the whole input is the original message `ptext`,
the padding of the original SHA-1 call and the appended message `ext`.

In other words, we compute `H(ext)` starting not from the initial
hashing state `h_0` but from `h_8 = H(k ∥ ptext)`.

The resulting hash will be equivalent to compute `H(k ∥ ptext ∥ pad ∥ ext)`
but without the requiring of knowing the key.


## Proof of concept (code!)

Assume that someone checks is the user is admin or not
verifying and reviewing a plaintext.


```python
>>> from cryptonita import B
>>> from cryptonita.toys.hashes.sha1 import sha1
>>> from cryptonita.toys.hashes.keyed import prefix_key_hash

>>> key = B('foobar') # unknown

>>> def login(login_req, unverified_hash, verbose=True):
...     h = prefix_key_hash(sha1, key, login_req)
...     if h != unverified_hash:
...         if verbose: print("Bad MAC. Login aborted.")
...         return False
...
...     if b"admin=True" in login_req.split(b";"):
...         if verbose: print("Logged as admin")
...     else:
...         if verbose: print("Logged as normal user")
...
...     return True
```

So a normal user would be logged as a "normal user"

```python
>>> login_req = B('user=john;comment=cheese')
>>> mac = prefix_key_hash(sha1, key, login_req)

>>> login(login_req, mac)
Logged as normal user
True
```

Without knowing the key we cannot just "hack" the logging request
and pretend to be admin:

```python
>>> login(login_req + B(';admin=True') , mac)
Bad MAC. Login aborted.
False
```

But we can do an length extension attack.

### Get the hash state from the MAC

First, we extract the hash state (a fancy way to say "decode 5 `uint32_t`{.cpp}"):

```python
>>> from cryptonita.conv import repack
>>> def extract_hash_fun_state(hash_hex):
...     words_bytes = B(hash_hex, encoding=16).nblocks(4)
...
...     return repack(words_bytes, ifmt='4s', ofmt='>I')

>>> h0, h1, h2, h3, h4 = extract_hash_fun_state(mac)
>>> ('%08x%08x%08x%08x%08x' % (h0, h1, h2, h3, h4)) == mac
True
```

### Guess the padding

Let's create a padding function like SHA-1 defines based on a given
message length:

```python
>>> def pad_like_sha1(msg_length):
...     bit_len = msg_length * 8
...
...     # Padding used by SHA1
...     padding = b'\x80'
...     padding += b'\x00' * ((56 - (msg_length + 1) % 64) % 64)
...     padding += bit_len.to_bytes(8, 'big')
...
...     return padding
```

We know the length of `login_req`{.python}
but we don't know the length of `key`{.python} so we cannot reconstruct
the original padding of the original MAC.

Nevertheless it can be brute-forced.

Basically we create a pad for a possible message length and extend the
hashing of the original MAC with an empty string.

Then we submit to `login`{.python} the new login request with the new (forged)
MAC and see if it is valid or not:

```python
>>> def is_ok(msg_length):
...     pad = pad_like_sha1(msg_length)
...     new_mac = sha1(b'', h0, h1, h2, h3, h4, forged_message_len=msg_length+len(pad))
...
...     new_login_req = login_req + pad
...     return login(new_login_req, new_mac, verbose=False)
```

The minimum message length is the length of the plaintext (`login_req`{.python});
an educated guess for the key length would be 16 and a maximum of 256.

So the space is defined as:

```python
>>> from cryptonita.space import IntSpace

>>> minimum = len(login_req)
>>> msg_length_space = IntSpace(minimum, minimum+256, start=minimum+16)
```

Let's use `is_ok`{.python} as an *oracle* function to *explore* the space of possible
lengths.

```python
>>> from cryptonita.attacks import search

>>> guessed_msg_length = search(msg_length_space, is_ok)
>>> guessed_msg_length
30
```

### Login as admin

Now we can extend the original `login_req`{.python} with anything and
compute for it a valid MAC.

```python
>>> ext = B(';admin=True')

>>> pad = pad_like_sha1(guessed_msg_length)

>>> new_login_req = login_req + pad + ext

>>> new_mac = sha1(ext, h0, h1, h2, h3, h4, forged_message_len=guessed_msg_length + len(pad) + len(ext))

>>> login(new_login_req, new_mac)
Logged as admin
True
```

Note how `login_req + pad`{.python} will be always part of your
messages.

Therefore it could be possible that a more sophisticated `login`{.python}
function may detect the forgery but certainly it was not the crypto
so prefix-keyed hashes as MAC are a bad idea.

## Beyond SHA-1

SHA-1 exposes its entire state but it is not the only one.

{% call marginnotes() %}
Check [hash_extender](https://github.com/iagox86/hash_extender) tool
{% endcall %}

The bibliography says that more are susceptible:

 - MD4
 - MD5
 - RIPEMD-160
 - SHA-0
 - SHA-1
 - SHA-256
 - SHA-512
 - WHIRLPOOL

This doesn't mean that those are broken: a hash function by itself not
really care if you can extend the hashing.

It is when a MAC is constructed as `H(k ∥ m)` when the extension
capability becomes a problem and breaks the MAC construction.

While you could use a hash function that does not expose all its
internal state (like SHA-512/224) it is still a too risky decision.

And the *suffix-keyed hash*, `H(m ∥ k)`, is also broken but it is not
so trivial (it requires a collision).

Prefer [HMAC](https://en.wikipedia.org/wiki/HMAC) instead.
