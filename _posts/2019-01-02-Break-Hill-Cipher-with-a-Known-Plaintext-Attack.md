---
layout: post
title: "Break Hill Cipher with a Known Plaintext Attack"
tags: cryptography cryptonita hill cipher
---

Given a matrix secret key $$K$$ with shape $$n\textrm{x}n$$, the
[Hill cipher](https://en.wikipedia.org/wiki/Hill_cipher) splits
the plaintext into blocks of length $$n$$ and for each block, computes
the ciphertext block doing a linear transformation in module $$m$$

$$ K p_i = c_i\quad(\textrm{mod } m)$$

For decrypting, we apply the inverse of $$K$$

$$ p_i = [K]^{-1} c_i \quad(\textrm{mod } m)$$

To make sense, the secret key $$K$$ must be chosen such as its inverse
exists in module $$m$$.

Ready to break it?<!--more-->

## Known plaintext attack

Because the Hill cipher is a linear cipher, it is vulnerable to a known
plaintext attack.

For a secret key $$K$$ with shape $$n\textrm{x}n$$, we need $$n$$ pairs of
known plaintext and ciphertext blocks, each of length $$n$$.

> The resulting equations no only need to be *linear independent*
> in general but in modulo $$m$$ too.
> If not, the calculus of the inverse of the system matrix will fail.

Let's be the following ciphertext encrypted with an unknown matrix $$K$$
with shape $$2\textrm{x}2$$ module $$251$$.

```python
>>> from cryptonita import B

>>> ciphertext = B(
...     b'\x19\xdb&\x05,\x9f\x8a2\xeb.\x8fJ\x9b\xbcZb]7e\xe2f\x83\x96'
...     b'\xa8j[\xb2\x15\x89\x95\x19\xf04p\x061\xc8\xbf\xa0\xd8\xd0\xba'
...     b'L\xa4Jl\x98\xd9\x89\x95\n\x9b\xa8\x88=KL\xa0#\xddJl\xbcE\xb3'
...     b'\xad\xf5\xa5e\xe26\xf9\xc1Y\xb2\x15\x87\x08?\x95\xf4\r\xcb\x9e"'
...     b'\x85\xd8\xa0\xc8lMA\xcb\x9eZb\x97-\xb7\xd9~\xb7Bq\t\x03\x94\x1c'
...     b'@\x01/n\x83\x891\x92p\x10F\xech\xf7\xb8\xc5\xbb\xa8\x9cY\xcf\n')

>>> n = 2
>>> m = 251
```

Let's be a known (partial) plaintext of 4 bytes (2 blocks of length 2)

```python
>>> known_plaintext = B('Hill')
>>> at = 4

>>> partial_ciphertext = ciphertext[at:at+len(known_plaintext)]
>>> partial_ciphertext
',\x9f\x8a2'
```

With these two pairs ``Hi -> ,\x9f`` and ``ll -> \x8a2`` we can
build the following equation system:

$$
K p_1 = c_1 \quad(\textrm{mod } m) \\
K p_2 = c_2 \quad(\textrm{mod } m)
$$

Each pair adds one equation or two if we see them in an unrolled way
(we decompose each vector and matrix and make the dot product explicit):

$$
K_{1,1} p_{1,1} + K_{1,2} p_{1,2} = c_{1,1} \quad(\textrm{mod } m) \\
K_{2,1} p_{1,1} + K_{2,2} p_{1,2} = c_{1,2} \quad(\textrm{mod } m) \\
K_{1,1} p_{2,1} + K_{1,2} p_{2,2} = c_{2,1} \quad(\textrm{mod } m) \\
K_{2,1} p_{2,1} + K_{2,2} p_{2,2} = c_{2,2} \quad(\textrm{mod } m) \\
$$

All those equations can be seen as a single one if we see all the plaintext
and ciphertext blocks/vectors as two matrices.

$$K P = C \quad(\textrm{mod } m)$$

```python
>>> import numpy as np

>>> P = np.array(list(known_plaintext)).reshape(2,2).T
>>> P
array([[ 72, 108],
       [105, 108]])

>>> C = np.array(list(partial_ciphertext)).reshape(2,2).T
>>> C
array([[ 44, 138],
       [159,  50]])
```

### Find the secret key matrix K

Then:

$$ K = C [P]^{-1} \quad(\textrm{mod } m)$$

Where $$[P]^{-1}$$ is the inverse of the matrix $$P$$ *in* $$(\textrm{mod } m)$$ so
we cannot apply a standard inverse operation.

Thankfully [cryptonita](https://pypi.org/project/cryptonita/)
already implements this inverse for us.

```python
>>> from cryptonita.mod import inv_matrix

>>> iP = inv_matrix(P, m)

>>> np.dot(P, iP) % m
array([[1, 0],
       [0, 1]])

>>> K = np.dot(C, iP) % m
>>> K
array([[  4,  67],
       [123, 161]])

>>> (np.dot(K, P) % m == C).all()
True
```

### Decrypt the plaintext

To decrypt the ciphertext we need the inverse of $$K$$ in $$(\textrm{mod } m)$$

```python
>>> iK = inv_matrix(K, m)
>>> iK
array([[ 95,   1],
       [ 88, 191]])

>>> (np.dot(iK, C) % m == P).all()
True
```

Finally:

```python
>>> cblocks = ciphertext.nblocks(2)

>>> plaintext = []
>>> for cblk in cblocks:
...     ci = np.array(list(cblk)).reshape(2, 1)
...     pi = np.dot(iK, ci) % m
...
...     plaintext.append(B(list(pi.ravel())))

>>> plaintext = b''.join(plaintext)
>>> print(plaintext)           # byexample: +norm-ws
b'The Hill cipher is a polygraphic substitution cipher based on linear
  algebra invented by Lester S. Hill in 1929. - From Wikipedia.'
```

## Beyond a known plaintext attack (open questions)

Some open questions for a future post:

 - How to determinate the block length ``n``?
 - And the module ``m``?
 - Beyond a linear polynomial: what about a cipher using a polynomial of order ``q``?
 - If no known plaintext exists, how we can *guess* one?
 - May be a *differential* attack?
