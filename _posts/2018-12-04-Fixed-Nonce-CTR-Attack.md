---
layout: post
title: "Fixed Nonce CTR Attack"
---

The Counter mode, or just CTR mode, turns a block cipher into a stream cipher.

More specifically, it builds a pseudo random generator (PRG)
from a block cipher and then generates a random string using
the PRG to encrypt/decrypt the payload performing a simple xor.

## Warming up

Let's implement a CTR
{% sidenote '[Implement CTR, the stream cipher mode](https://cryptopals.com/sets/3/challenges/18)' %}

```python
>>> from cryptonita import B, load_bytes     # byexample: +timeout=10

>>> import sys
>>> sys.path.append("./assets/matasano")
>>> from challenge import generate_config, enc_ctr, dec_ctr  # byexample: +timeout=10

>>> seed = 20181204
>>> bsize = 16

>>> cfg = generate_config(random_state=seed, block_size=bsize,
...                       nonce=0, key=B('YELLOW SUBMARINE'))
```

Now let's check that our AES cipher in Counter mode works

```python
>>> ciphertext = B('L77na/nrFsKvynd6HzOoG7GHTLXsTVu9qvY/2syLXzhPweyyMTJULu/6/kXX0KSvoOLSFQ==', encoding=64)

>>> dec_ctr(ciphertext, cfg.key, cfg.nonce)
"Yo, VIP Let's kick it Ice, Ice, baby Ice, Ice, baby "
```

## Break fixed-nonce CTR

If the nonce is fixed, then several *independent* ciphertext
will be encrypted with the same key stream.

Let's load some plaintexts and let's encrypt them in that way
and see if we can break the encryption.

```python
>>> from cryptonita.conv import transpose, uniform_length    # byexample: +timeout=10
>>> plaintexts = list(load_bytes('./assets/matasano/20.txt', encoding=64))

>>> ciphertexts = [enc_ctr(p, cfg.key, cfg.nonce) for p in plaintexts]
```

The vulnerability resides in reusing the nonce.

With the same nonce, CTR generates the same random sequence that
uses to xor the payload.

In other words, it performs a xor *reusing* the key stream and
we already know how to
[break a repeating xor key cipher](/book-of-gehn/articles/2018/03/01/In-XOR-We-Trust.html).

But first, not all the ciphertexts are of the same length so to simplify we need
to uniform their lengths.

For example, we could truncate all the ciphertexts to the length of the smallest.

```python
>>> tciphertexts = uniform_length(ciphertexts)
>>> tplaintexts = uniform_length(plaintexts)
```

Now, because the repeating key is along the column axis (eg, the first byte of
all the plaintexts were xored with the same key byte), it is more
convenient to *transpose* them.

```python
>>> tciphertexts_transposed = transpose(tciphertexts)
```

### Plaintext statistic model

To perform a frequency attack we need the most common letters of
the plaintext.

Given an English text, these are the classical
[ETAOIN-SHRDLU](https://en.wikipedia.org/wiki/Etaoin_shrdlu).

```python
>>> from cryptonita.scoring.freq import etaoin_shrdlu
```

But consider the first byte of all the plaintexts.

If they are the
begin of a sentence it is very likely that they are in uppercase and
the first letter of a word **may not** (and will not) follow the ETAOIN-SHRDLU
frequency.

Therefor we need *another* statistical model, one for the upper case:

```python
>>> from cryptonita.scoring.freq import tsamcin_brped
```

### Score a decryption using Chi-square test

The frequency attack (``freq_attack``) implemented in
[cryptonita](https://pypi.org/project/cryptonita/)
returns a guess: a set of possible key bytes.

To narrow this down we try each one (brute force) and
score each potential plaintext.

For this we take the frequency of the letters in the plaintext
and compare them with the expected frequency using a
[Chi-square test](https://en.wikipedia.org/wiki/Chi-squared_test).

In [cryptonita](https://pypi.org/project/cryptonita/), this
is implemented in the ``fit_freq_score`` function:

```python
>>> from cryptonita.scoring import fit_freq_score
```

But ``fit_freq_score`` can be a little drastic; if the brute force
yields none key we roll back and score using a more relaxed score function:

```python
>>> from cryptonita.scoring import all_ascii_printable
```

### Guess the CTR key stream

Mixing all this together:

```python
>>> from cryptonita.attacks import brute_force, freq_attack
>>> from functools import partial

>>> guesses = []
>>> for i, c in enumerate(tciphertexts_transposed):
...     if i == 0:  # first letter, use a special statistical model
...         most_common = etaoin_shrdlu() | tsamcin_brped()
...     else:
...         most_common = etaoin_shrdlu()
...
...     byte_guess = freq_attack(c, most_common, 1)
...     g = brute_force(c, partial(fit_freq_score, expected_prob=most_common), byte_guess)
...     if not g:   # fit_freq_score was too hard, rollback to a more soft score func
...         g = brute_force(c, all_ascii_printable, byte_guess)
...
...     byte_guess = g
...     guesses.append(byte_guess)
```

Let's peek how large is our key stream (determined by how we cut the
ciphertexts with ``uniform_length``) and how many different keys we
have (we are still guessing so there is not one single answer yet)

```python
>>> klength = len(guesses)
>>> klength
53

>>> from cryptonita.fuzzy_set import len_join_fuzzy_sets
>>> len_join_fuzzy_sets(guesses)
10985
```

### Correct the key stream

Let's build the key stream (still a guess):

```python
>>> from cryptonita.fuzzy_set import join_fuzzy_sets
>>> kstream_guess = join_fuzzy_sets(guesses, cut_off=0, j=B(''))
```

Now, we take the most likely of our guesses:

```python
>>> kstream = kstream_guess.most_likely()
```

However this is not enough. This key stream is not the correct one:

```python
>>> tplaintexts[0] == tciphertexts[0] ^ kstream
False
```

But we are *very close*:

```python
>>> sum(p == q for p, q in zip(tplaintexts[0], tciphertexts[0] ^ kstream)) / klength
0.9811<...>
```

So our current key stream is *almost* correct, only a few bytes need
to be tweaked.

Some possible next steps:

 - Use ``etaoin_shrdlu`` to correct them? No really. We used this to build
the initial key stream so it is unlikely that we can fix the key stream
using this or any other model at the *character level*.
 - Then use a bigram model? Much better but a bigram model uses only two
characters and may not be robust enough. Worst, we are working with a very
short plaintexts/ciphertexts (~50 characters) and this is too short for
a bigram model (the model is too sparse and mostly flat so it will be hard
to draw any conclusion.
 - So, what about some a more *specific* model? Bingo!

With a more specific model we can get more info from the short sequences
but this requires to know much about the plaintext.

If we assume that most of the plaintext is built from English words
then we could use a *spell checker* to correct any misspelled word
product of a incorrect key.

```python
>>> import aspell
>>> from cryptonita.suggesters import good_written_word_suggester

>>> gword_suggester = partial(good_written_word_suggester, speller=aspell.Speller())
```

With this *suggester* we can try to *correct* the key:

```python
>>> from cryptonita.attacks import correct_key

>>> tmp = correct_key(kstream, ciphertexts, gword_suggester)
>>> correction = B('').join(k.most_likely() for k in tmp)
```

The ``correct_key`` method works like ``brute_force`` but from another
point of view.

``brute_force`` tries each possible key, decrypting the same ciphertext
and then scoring each decryption independently.

``correct_key``, instead, try the same key to decrypt several different
ciphertexts and try to get the most likely corrections that improve
all the decryption (it does not score independently).

Okay, how well was our correction? How many bytes did we correct?
And how the decrypted texts looks like?

```python
>>> len([c for c in correction if c != 0])
1

>>> tciphertexts[0] ^ kstream
':\'m rated "R"...this is a warning, ya better void / P'

>>> tciphertexts[0] ^ kstream ^ correction
'i\'m rated "R"...this is a warning, ya better void / P'
```

So we got the correct key stream? Well, we didn't:

```python
>>> tplaintexts[0]
'I\'m rated "R"...this is a warning, ya better void / P'
```

### Undistinguishable

Unless we have more knowledge about the plaintexts, we cannot distinguish
between ``i'm rated`` and ``I'm rated``.

:,|

```python
>>> fix = B(b'i') ^ B(b'I')

>>> kstream = kstream ^ correction
>>> kstream = (kstream[:1] ^ fix) + kstream[1:]
```

And we are done!
{% sidenote '[Break fixed-nonce CTR statistically](https://cryptopals.com/sets/3/challenges/20)' %}

```python
>>> all(p == c ^ kstream for p, c in zip(tplaintexts, tciphertexts))
True

>>> [(c ^ kstream) for c in tciphertexts]
['I\'m rated "R"...this is a warning, ya better void / P',
 'Cuz I came back to attack others in spite- / Strike l',
 "But don't be afraid in the dark, in a park / Not a sc",
 'Ya tremble like a alcoholic, muscles tighten up / Wha',
 'Suddenly you feel like your in a horror flick / You g',
 "Music's the clue, when I come your warned / Apocalyps",
 "Haven't you ever heard of a MC-murderer? / This is th",
 'Death wish, so come on, step to this / Hysterical ide',
 'Friday the thirteenth, walking down Elm Street / You ',
 'This is off limits, so your visions are blurry / All ',
 "Terror in the styles, never error-files / Indeed I'm ",
 'For those that oppose to be level or next to this / I',
 "Worse than a nightmare, you don't have to sleep a win",
 'Flashbacks interfere, ya start to hear: / The R-A-K-I',
 'Then the beat is hysterical / That makes Eric go get ',
 'Soon the lyrical format is superior / Faces of death ',
 "MC's decaying, cuz they never stayed / The scene of a",
 "The fiend of a rhyme on the mic that you know / It's ",
 'Melodies-unmakable, pattern-unescapable / A horn if w',
 'I bless the child, the earth, the gods and bomb the r',
 'Hazardous to your health so be friendly / A matter of',
 "Shake 'till your clear, make it disappear, make the n",
 "If not, my soul'll release! / The scene is recreated,",
 'Cuz your about to see a disastrous sight / A performa',
 'Lyrics of fury! A fearified freestyle! / The "R" is i',
 "Make sure the system's loud when I mention / Phrases ",
 'You want to hear some sounds that not only pounds but',
 'Then nonchalantly tell you what it mean to me / Stric',
 "And I don't care if the whole crowd's a witness! / I'",
 'Program into the speed of the rhyme, prepare to start',
 "Musical madness MC ever made, see it's / Now an emerg",
 "Open your mind, you will find every word'll be / Furi",
 "Battle's tempting...whatever suits ya! / For words th",
 "You think you're ruffer, then suffer the consequences",
 'I wake ya with hundreds of thousands of volts / Mic-t',
 'Novocain ease the pain it might save him / If not, Er',
 "Yo Rakim, what's up? / Yo, I'm doing the knowledge, E",
 'Well, check this out, since Norby Walters is our agen',
 'Kara Lewis is our agent, word up / Zakia and 4th and ',
 "Okay, so who we rollin' with then? We rollin' with Ru",
 'Check this out, since we talking over / This def beat',
 'I wanna hear some of them def rhymes, you know what I',
 "Thinkin' of a master plan / 'Cuz ain't nuthin' but sw",
 'So I dig into my pocket, all my money is spent / So I',
 "So I start my mission, leave my residence / Thinkin' ",
 'I need money, I used to be a stick-up kid / So I thin',
 "I used to roll up, this is a hold up, ain't nuthin' f",
 "But now I learned to earn 'cuz I'm righteous / I feel",
 'Search for a nine to five, if I strive / Then maybe I',
 "So I walk up the street whistlin' this / Feelin' out ",
 'A pen and a paper, a stereo, a tape of / Me and Eric ',
 'Fish, which is my favorite dish / But without no mone',
 "'Cuz I don't like to dream about gettin' paid / So I ",
 'So now to test to see if I got pull / Hit the studio,',
 'Rakim, check this out, yo / You go to your girl house',
 "'Cause my girl is definitely mad / 'Cause it took us ",
 "Yo, I hear what you're saying / So let's just pump th",
 'And count our money / Yo, well check this out, yo Eli',
 'Turn down the bass down / And let the beat just keep ',
 'And we outta here / Yo, what happened to peace? / Pea']
```

## Break fixed-nonce CTR - Second chance

{% sidenote '[Break fixed-nonce CTR mode using substitutions](https://cryptopals.com/sets/3/challenges/19)' %}

```python
>>> plaintexts = list(load_bytes('./assets/matasano/19.txt', encoding=64))
>>> ciphertexts = [enc_ctr(p, cfg.key, cfg.nonce) for p in plaintexts]

>>> tplaintexts = uniform_length(plaintexts)
>>> tciphertexts = uniform_length(ciphertexts)
>>> tciphertexts_transposed = transpose(tciphertexts)
```

```python
>>> guesses = []
>>> for i, c in enumerate(tciphertexts_transposed):
...     if i == 0:  # first letter, use a special statistical model
...         most_common = etaoin_shrdlu() | tsamcin_brped()
...     else:
...         most_common = etaoin_shrdlu()
...
...     byte_guess = freq_attack(c, most_common, 1)
...     g = brute_force(c, partial(fit_freq_score, expected_prob=most_common), byte_guess)
...     if not g:   # fit_freq_score was too hard, rollback to a more soft score func
...         g = brute_force(c, all_ascii_printable, byte_guess)
...
...     byte_guess = g
...     guesses.append(byte_guess)

>>> klength = len(guesses)
>>> klength
20

>>> len_join_fuzzy_sets(guesses)
23712

>>> kstream_guess = join_fuzzy_sets(guesses, cut_off=0, j=B(''))
>>> kstream = kstream_guess.most_likely()

>>> tciphertexts[1] ^ kstream
'7*ming {ith vivid fa'
```

Quite close. By manual inspection the correct plaintext should be
``Coming with vivid fa``.

With a *known plaintext* breaking the rest of the key bytes is trivial:

```python
>>> correction = tciphertexts[1] ^ kstream ^ B(b'Coming with vivid fa')
>>> kstream = kstream ^ correction

>>> all(p == c ^ kstream for p, c in zip(tplaintexts, tciphertexts))
True

>>> [(c ^ kstream) for c in tciphertexts]
['I have met them at c',
 'Coming with vivid fa',
 'From counter or desk',
 'Eighteenth-century h',
 'I have passed with a',
 'Or polite meaningles',
 'Or have lingered awh',
 'Polite meaningless w',
 'And thought before I',
 'Of a mocking tale or',
 'To please a companio',
 'Around the fire at t',
 'Being certain that t',
 'But lived where motl',
 'All changed, changed',
 'A terrible beauty is',
 "That woman's days we",
 'In ignorant good wil',
 'Her nights in argume',
 'Until her voice grew',
 'What voice more swee',
 'When young and beaut',
 'She rode to harriers',
 'This man had kept a ',
 'And rode our winged ',
 'This other his helpe',
 'Was coming into his ',
 'He might have won fa',
 'So sensitive his nat',
 'So daring and sweet ',
 'This other man I had',
 'A drunken, vain-glor',
 'He had done most bit',
 'To some who are near',
 'Yet I number him in ',
 'He, too, has resigne',
 'In the casual comedy',
 'He, too, has been ch',
 'Transformed utterly:',
 'A terrible beauty is']
```


