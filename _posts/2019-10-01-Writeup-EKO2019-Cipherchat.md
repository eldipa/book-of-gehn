---
layout: post
title: "Cipherchat (Crypto writeup - EKO 2019)"
---

We start with a [communication](/book-of-gehn/assets/eko2019-writeups/cipherchat-dir/cipherchat.pcap)
between two machines, encrypted with an unknown algorithm and
the challenge is to break it.

As a *hint* we have the code that the client used to talk with the server.<!--more-->


## Decompile

It is a Python 3 [compiled code](/book-of-gehn/assets/eko2019-writeups/cipherchat-dir/client.min.pyc)
so our first task is to decompile it.

For this I'm going to use [uncompyle6](https://github.com/rocky/python-uncompyle6)

```
$ uncompyle6 --encoding utf-8 -o . client.min.pyc       # byexample: +skip
```

This is what we got:

```python
<...>
ۈ = True
𢜁 = False
ې = chr
𐬴 = print
import socket
䈶 = socket.gethostbyname
چ = socket.socket
ޠ = socket.error
𨐜 = socket.AF_INET
𐫛 = socket.SOCK_STREAM
import sys
نحي = sys.stdin
𐤭 = sys.exit
𣏲 = 'localhost'
ࡃ = 12345
珽 = 0
𐠨 = 0

def 𡛓(t):
    敩 = ''
    𨆂 = 珽
    for n in t.encode('latin-1'):
        if n == 0:
            break
<...>
```

The ``ۈ`` looks like a variable where ``䈶`` is just
an alias of ``socket.gethostbyname``.

{% marginnote
'Vim tip: ``:%s//x/g`` replaces the last searched string by ``x``.
Combined with ``*`` it is very useful to replace hard-to-write words
like ``ۈ``.' %}

I did a little of search-and-replace to have better names, I filtered out
artificial constructions like using a variable to hold the constant ``True``
and things like that.

Finally, I tried to rename the variables to have a meaningful name.

The decompiled code is
[here](/book-of-gehn/assets/eko2019-writeups/cipherchat-dir/client.min.py).

## Analysis of the Cipher

This is the cipher function:

```python
>>> key_seed = 0
>>> key_shift = 0

>>> def encxor(t):
...     out = ''
...     key = key_seed
...     for n in t.encode('latin-1'):
...         if n == 0:
...             break
...
...         while 1:
...             x = n ^ key
...             key = (key + key_shift) % 256
...             if x == 0 or x == key:
...                 pass
...             else:
...                 break
...
...         out += chr(x)
...
...     out += chr(0)
...     return out.encode('latin-1')
```

It is a *stream cipher* where the key stream evolves doing *shifts*
of ``key_shift`` starting from ``key_seed``.

On particularity is that if the output byte ``x`` is 0 or it is
equal to the (next) ``key`` byte, the ``key`` byte is ignored and the
key stream is moved forward one byte.

So in the output ``out`` we will never see a 0 or a key byte.

This is the same function but simplified:

```python
>>> key_seed = 0
>>> key_shift = 0

>>> def encxor(t):
...     out = ''
...     key = key_seed
...     for n in t.encode('latin-1'):
...         if n == 0:
...             break
...
...         x = 0
...         while x == 0 or x == key:
...             x = n ^ key
...             key = (key + key_shift) % 256
...
...         out += chr(x)
...
...     out += chr(0)
...     return out.encode('latin-1')
```

{% marginnote
'We say *almost* because to runs of the key stream will be identical until
one of them, based on the plaintext, hit the ``x == 0 or x == key`` condition
*shifting* with respect the other.' %}

Another particularity is that the cipher is *stateless*: two
plaintexts will be encrypted with *almost* the same key stream.

The other interesting part is how the ``key_seed`` and
``key_shift`` are initialized.

```python
_, srcport = sk.getsockname()
key_seed = (srcport & 65280) >> 8
key_shift = srcport & 255
```

{% marginnote
'The pcap had only one single TCP stream but in much nosier captures
it is handy to use ``Statistic > Conversations`` in ``wireshark``
to summarize the protocols, addresses and ports.' %}

Not secret at all. ``srcport`` is the source port chosen by the OS which
from the [pcap](/book-of-gehn/assets/eko2019-writeups/cipherchat-dir/cipherchat.pcap)
we know that it is 47898.

So

```python
>>> srcport = 47898
>>> key_seed = (srcport & 65280) >> 8
>>> key_shift = srcport & 255

>>> key_seed, key_shift
(187, 26)
```

## Decrypting

With this and the ``encxor`` function we can decrypt every message sent from the
client to the server.

{% marginnote
'Another ``wireshark`` tip: select one packet, then
``Follow TCP stream``, filter to see only the ``client->server`` packets
and select ``show data`` as ``raw``.' %}

Which by the way are these:

```python
>>> raw = '''
... cba28100
... 94bd8a655300
... 94a586674400
... 94b08c614c1d1f18abc7cdb600
... 94b08c614c1d26e3c4cbf9927f4261221afa89a7b29e7f4c7a00
... 94b08c614c1d1e51ffcdd6b7982d53293a01afd0aca8d77059207f15fcc2ac8895720f2f0c0fb7c5a380df7f5f2ce600
... 94b08c614c1d341ee4c993f9ba2d4f202d10afddabb484314d2a2d59eac2b2dbdb506406180de4d4be819046432815e7fed6bbb6707854230ee6e6e68bdd555c00
... 94b08c614c1d301eabc2d0f8d36148203f55e6dde3b49931522a2a59f1c2a6939f00
... 94a586674400
... 94a49a605700
... '''
```


```python
>>> from cryptonita import B            # byexample: +timeout=10
>>> msgs = [B(msg, encoding=16) for msg in filter(None, raw.split('\n'))]

>>> for msg in msgs:
...     tmp = msg.decode('latin-1')
...     tmp = encxor(tmp)
...     print(tmp)
b'pwn\x00'
b'/help\x00'
b'/ping\x00'
b'/echo Hi bro\x00'
b'/echo What are you doing?\x00'
b'/echo I think that you are looking for the flag\x00'
b'/echo cool, I have this for you: EKO{pseudo_perfect_secrecy_X0R}\x00'
b'/echo go go! load it in you board\x00'
b'/ping\x00'
b'/quit\x00'
```

That's it: ``EKO{pseudo_perfect_secrecy_X0R}``.

