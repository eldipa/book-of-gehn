---
layout: post
title: "Key Recovering from CBC with `IV = K`{.mathjax}"
tags: [cryptography, matasano, cryptonita, CBC]
inline_default_language: python
---

{% call	marginfig('k-eq-iv-enc.svg', indexonly=True ) %}
{% endcall %}

CBC requires an *initialization vector* (IV) that needs to be agreed
by both encryption and decryption peers.

IV needs to be random so you may be get tempted and use the secret key
as IV.

No, please don't.

The IV is not required to be secret and there is a good reason for that:
it can be recovered with a **single** *chosen ciphertext attack*.

Using `IV = K`{.mathjax} means that the adversary can recover the secret key with a
single message.

In this post I describe the attack in 3 simple diagrams.
<!--more-->

## Setup

{% call	mainfig('k-eq-iv-enc.svg', width='50%' ) %}
Encryption of a plaintext.

Note how the secret key is used incorrectly as IV.
{% endcall %}

## Chosen ciphertext

{% call	mainfig('k-eq-iv-attack.svg', width='45%') %}
Decryption of a *chosen ciphertext*.

It is a 3-block ciphertext with the first and third blocks being the
same and the block in the between being full of zeros.

Note that `c_1`{.mathjax} can be an arbitrary encrypted block.
{% endcall %}

## Key recovering

{% call	mainfig('k-eq-iv-recover.svg', width='70%') %}
The third block is decrypted and then xored with zeros, making the xor a
no-operation.

This leaves the direct decryption `D[c_1]`{.mathjax} at the end of the
plaintext.

This is the same value obtained for the *first* ciphertext block
**before** the xor with the IV.

Knowing the first block of the plaintext then it is possible to recover
the IV.

This is in general true for any CBC setup and it does not imply any
vulnerability as *the IV does not require to be secret*.

But as in this case, if the IV was initialized with the secret key, this
now becomes a real attack with a **full recover of the key**.
{% endcall %}


