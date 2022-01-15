---
layout: post
title: "Affine Cipher"
tags: [cryptography, cryptonita, affine, differential attack]
---

A *linear* cipher like the Hill Cipher is
[vulnerable](/articles/2019/01/02/Break-Hill-Cipher-with-a-Known-Plaintext-Attack.html)
to a known plaintext attack: just resolve a set of linear
equations and get the secret key.

An *affine* cipher is a little harder to break, however it could
be vulnerable to a *differential* attack.
<!--more-->

Formerly, an *affine* encryption looks like this

```tex;mathjax
 A p_i + B = c_i\quad(\textrm{mod } m)
```

and the decryption like this:

```tex;mathjax
 p_i = [A]^{-1} (c_i - B)\quad(\textrm{mod } m)
```

where `A`{.mathjax} and `B`{.mathjax} are secret and unknown to the attacker
but we can assume that have known shapes of `n\textrm{x}n`{.mathjax} and
`n\textrm{x}1`{.mathjax} respectively.

## Differential cryptanalysis

Consider the following ciphertext and the partial known plaintext:

```python
>>> from cryptonita import B as asbytes
>>> import numpy as np

>>> m = 251
>>> ciphertext = asbytes(b'"\x93&\xd3)\x97\xb0\xa8\xa6\xf17@,f\xb2\x17LsNs\xe0\xd7').toarray()
>>> kplaintext = asbytes(b'..fi....ra..fo..at....').toarray()
```

From there we can take two plaintexts `p_i`{.mathjax} and `p_j`{.mathjax} with their associated
ciphertexts `c_i`{.mathjax} and `c_j`{.mathjax}.

```tex;mathjax
 A p_i + B = c_i\quad(\textrm{mod } m)
```

```tex;mathjax
 A p_j + B = c_j\quad(\textrm{mod } m)
```

If we *substract* both equations we obtain a *linear* system
like the Hill Cipher:

```tex;mathjax

A (p_i - p_j) = (c_i - c_j)\quad(\textrm{mod } m)

```

{% call marginnotes() %}
Keep in mind the affine transformation is a *block cipher* with blocks
of `n`{.mathjax} bytes.
So the plaintext/ciphertext pairs **must** be `n`{.mathjax}-bytes *aligned*
(they **must** come from positions multiple of `n`{.mathjax}).
{% endcall %}


In order to break an affine cipher we need `2n`{.mathjax} independent
plaintext-ciphertext pairs (for a linear cipher we need just
`n`{.mathjax})

Here is the first two pairs and the first difference:

```python
>>> p11, c11 = kplaintext[2:4].reshape(2,1), ciphertext[2:4].reshape(2,1)
>>> p12, c12 = kplaintext[12:14].reshape(2,1), ciphertext[12:14].reshape(2,1)

>>> dp1 = (p11 - p12) % m
>>> dc1 = (c11 - c12) % m
```

Here we build the second difference:

```python
>>> p21, c21 = kplaintext[8:10].reshape(2,1), ciphertext[8:10].reshape(2,1)
>>> p22, c22 = kplaintext[16:18].reshape(2,1), ciphertext[16:18].reshape(2,1)

>>> dp2 = (p21 - p22) % m
>>> dc2 = (c21 - c22) % m
```

Stacking all this together we build the difference matrices for
the plaintexts and ciphertexts of shapes `n\textrm{x}n`{.mathjax}.

```python
>>> dP = np.hstack((dp1, dp2))
>>> dC = np.hstack((dc1, dc2))
```

Remembering that the linear cipher is:

```tex;mathjax
 A\ dP = dC \quad(\textrm{mod } m)
```

From here we can obtain `A`{.mathjax}:

```tex;mathjax
 A = dC\ [dP]^{-1} \quad(\textrm{mod } m)
```

```python
>>> from cryptonita.mod import inv_matrix
>>> idP = inv_matrix(dP, m)

>>> A = np.dot(dC, idP) % m
>>> A
array([[ 95,   1],
       [ 88, 191]])

>>> iA = inv_matrix(A, m)
>>> iA
array([[  4,  67],
       [123, 161]])
```

Using one of the plaintext-ciphertext pairs we can obtain
the remaining unknown value: the `B`{.mathjax} vector.

```tex;mathjax
 B = c - A p \quad(\textrm{mod } m)
```

```python
>>> B = (c11 - np.dot(A, p11)) % m
```

Finally, let's decrypt the message!

```python
>>> cblocks = asbytes(ciphertext).nblocks(2)
>>> pblocks = []

>>> for cb in cblocks:
...     cb = cb.toarray().reshape(2,1)
...     pb = np.dot(iA, cb - B) % m
...     pb = asbytes(pb.reshape(-1))
...     pblocks.append(pb)

>>> plaintext = b''.join(pblocks)
>>> plaintext
'Affine transformation!'
```
