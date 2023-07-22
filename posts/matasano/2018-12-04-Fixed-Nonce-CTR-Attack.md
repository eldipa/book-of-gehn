---
layout: post
title: "Fixed Nonce CTR Attack"
tags: [cryptography, matasano, cryptonita, CTR, counter nonce, PRG, chi-square, undistinguishable]
inline_default_language: python
---

The Counter mode, or just CTR mode, turns a block cipher into a stream cipher.

More specifically, it builds a pseudo random generator (PRG)
from a block cipher and then generates a random string using
the PRG to encrypt/decrypt the payload performing a simple xor.

The idea is to initialize the PRG with a different *seed* each time
but if this does not happen, all the plaintexts will be encrypted
with the *same* pseudo random key stream -- totally insecure.

{{ spoileralert() }}
Ready to break it?<!--more-->

## Warming up

{% call marginnotes() %}
[Implement CTR, the stream cipher mode](https://cryptopals.com/sets/3/challenges/18)
{% endcall %}

Let's implement a CTR. As usual we generate a pseudo-random
configuration to parametrize the CTR.

<!--
>>> from cryptonita import B, load_bytes     # byexample: +timeout=10

>>> import sys
>>> sys.path.append("./posts/matasano/assets")
>>> from challenge import generate_config, enc_ctr, dec_ctr  # byexample: +timeout=10

>>> seed = 20181204
-->

```python
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

Let's load some plaintexts and let's encrypt them reusing the same
nonce over and over and see if we can break the encryption later.

```python
>>> from cryptonita.conv import transpose, uniform_length    # byexample: +timeout=10
>>> plaintexts = list(load_bytes('./posts/matasano/assets/20.txt', encoding=64))

>>> ciphertexts = [enc_ctr(p, cfg.key, cfg.nonce) for p in plaintexts]
```

The vulnerability resides in reusing the nonce.

With the same nonce, CTR generates the same random sequence that
uses to xor the payload.

In other words, it performs a xor *reusing* the key stream and
we already know how to
[break a repeating xor key cipher](/articles/2018/03/01/In-XOR-We-Trust.html).

> Quick recap: because the key stream was reused, the ith byte of all
> the ciphertexts was xor'd with the *same* key byte and therefore,
> xor'ing two ciphertexts will remove the key stream leaving us the xor
> of the two underlying plaintexts.

We notice that not all the ciphertexts are of the same length so to simplify
we need to uniform their lengths.

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

>>> len(tciphertexts_transposed)    # rows
53

>>> len(tciphertexts_transposed[0]) # columns
60
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

Therefore we need *another* statistical model, one for the upper case:

```python
>>> from cryptonita.scoring.freq import tsamcin_brped
```

> Yes, I know, `tsamcin_brped` is a terrible name but it is aligned with
> `etaoin_shrdlu`.

### Score a decryption using Chi-square test

The frequency attack (``freq_attack``) implemented in
[cryptonita](https://pypi.org/project/cryptonita/)
returns a guess: a set of possible key bytes.

To determine the correct key we need to try each of them by brute force
(`brute_force`) and *"see"* which looks more "human text".

For this we *observe* the frequency of the letters in the deciphered plaintext
and compare them with the *expected* frequency using a
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

As you may guess, `all_ascii_printable` returns `1` if all the
characters in the deciphered plaintext are ASCII and `0` otherwise.

### Guess the CTR key stream

Mixing all this together:

```python
>>> from cryptonita.attacks import brute_force, freq_attack
>>> from functools import partial

>>> guesses = []
>>> # we iterate over each column (the i==0 correspond to the first letter)
>>> for i, c in enumerate(tciphertexts_transposed):
...     if i == 0:  # first letter, use a special statistical model
...         most_common = tsamcin_brped()
...     else:
...         most_common = etaoin_shrdlu()
...
...     # frequency attack, try to find the most likely key bytes
...     # for the ith letter
...     byte_guess = freq_attack(c, most_common, 1)
...
...     # build a score function using the fit_freq_score parametrized
...     # with the "expected" probabilities from our model
...     # fit_freq_score will take an input and from there it will obtain
...     # the "observed" probabilities and will compare them with the
...     # expected using Chi-Square.
...     score_fun = partial(fit_freq_score, expected_prob=most_common)
...
...     # Try every possible key byte from our freq_attack scoring
...     # the deciphered outputs with the fit_freq_score. Poor scored
...     # are drop so we should only have left the most likely keys.
...     g = brute_force(c, score_fun, byte_guess)
...     if not g:
...         # but may be fit_freq_score is too restrictive.
...         # rollback to a much lax/loose score function (but with
...         # more false positives)
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
1690
```

Considere for a moment those numbers. Of 53 characters we initially have
a key space of `256^{53}`{.mathjax}, a number that has more than 100
digits.

But with a frequency attack and a good score function we managed to
reduce the key space to only 1690.

### How close are out guesses?

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

Not only it is very close, the true key stream is there, in one of our
guesses!

```python
>>> any(tplaintexts[0] == tciphertexts[0] ^ kstream for kstream in kstream_guess)
True
```

But how we can pick it without cheating? without using `tplaintexts` as
it is supposed to be the unknown here?

Yes, with more brute force!

### Speller based score

Brute force, but clever.

We can use a score based on well English written text using a *speller*

In this case, `good_written_word_score` takes a `aspell.Speller` and it
will return a score based on how many words in the deciphered text are
correctly spelled (weighting each word by its length)

```python
>>> import aspell
>>> from cryptonita.scoring import good_written_word_score

>>> score = partial(good_written_word_score, speller=aspell.Speller(), word_weight_fun=len)
```

```python
>>> kstream_guess = brute_force(tciphertexts[0], score, kstream_guess)
>>> kstream_guess.cut_off(n=10)

>>> [(p, tciphertexts[0] ^ kstr) for kstr, p in kstream_guess.sorted_items()]     # byexample: +norm-ws
[(1.4946588552783956e-56,   'I\'m rated "R"...this is a warning, ya better void / P'),
 (1.4036747792866314e-56,   'N\'m rated "R"...this is a warning, ya better void / P'),
 (7.026934200276732e-57,    'I\'m ratede"R"...this is a warning, ya better void / P'),
 (6.374212793632498e-57,    'N\'m ratede"R"...this is a warning, ya better void / P'),
 (5.972894070235226e-57,    'I\'m rated "R"...this is a warning, yaebetter void / P'),
 (5.490470454496446e-57,    'I\'m rated "R"...t\'is is a warning, ya better void / P'),
 (5.265568867883322e-57,    'I\'m rated "R"...t&is is a warning, ya better void / P'),
 (5.25603393501155e-57,     'I\'m rated "R"...t!is is a warning, ya better void / P'),
 (5.249351712403237e-57,    'N\'m rated "R"...this is a warning, yaebetter void / P'),
 (5.156250121008111e-57,    'N\'m rated "R"...t\'is is a warning, ya better void / P')]
```

Our winner is on the top!

```python
>>> kstream = kstream_guess.most_likely()
>>> tciphertexts[0] ^ kstream == tplaintexts[0]
True
```

### About undistinguishable

Unless we have more knowledge about the plaintexts, we cannot distinguish
between ``i'm rated``{.none} and ``I'm rated``{.none}. ``:´|``{.none}

The fact that we hit the correct key stream comes from *"we guessed"*
that the first letter was in uppercase.


## Full break (enjoy!)

{% call marginnotes() %}
[Break fixed-nonce CTR statistically](https://cryptopals.com/sets/3/challenges/20)
{% endcall %}

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

{% call marginnotes() %}
[Break fixed-nonce CTR mode using substitutions](https://cryptopals.com/sets/3/challenges/19)
{% endcall %}

Let's take another set of plaintexts,
encrypt them with a fixed-nonce CTR and break the encryption.

```python
>>> plaintexts = list(load_bytes('./posts/matasano/assets/19.txt', encoding=64))
>>> ciphertexts = [enc_ctr(p, cfg.key, cfg.nonce) for p in plaintexts]

>>> tplaintexts = uniform_length(plaintexts)
>>> tciphertexts = uniform_length(ciphertexts)
>>> tciphertexts_transposed = transpose(tciphertexts)
```

```python
>>> guesses = []
>>> for i, c in enumerate(tciphertexts_transposed):
...     if i == 0:  # first letter, use a special statistical model
...         most_common = etaoin_shrdlu()
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
2496

>>> kstream_guess = join_fuzzy_sets(guesses, cut_off=0, j=B(''))
>>> kstream = kstream_guess.most_likely()

>>> tciphertexts[1] ^ kstream
'c*ming {ith vivid fa'
```

Quite close. By manual inspection the correct plaintext should be
``Coming with vivid fa``{.none}.

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

## Final thoughts

``ETAOIN SHRDLU`` is a statistical model for letter frequency in English
and it was used to break most of the key stream bytes but its strength
depends exclusively in how well the model represents the underlying plaintext.

For the case of the first letter of all the plaintexts it was upper case and
the ``ETAOIN SHRDLU`` model didn't work and it was extended later.

Once that we have a guess, filter them out requires more knowledge about the
plaintext.

Requiring to be the decrypted text plain ASCII is simple but too open;
requiring to follow the English statistical model using a Chi-square
test (``fit_freq_score``) is stricter.

However, like before, the statistical model only applies for long
sequences (samples) and only if the underlying plaintexts are what
one could expect.

A *liberal* scoring function like ``all_ascii_printable`` serves
as a backup and it is better than nothing.

Even with all of this, the most likely key stream guess may not be
the correct one, inclusive, none of the key stream guesses may be the
correct one!

Correcting a key stream using more information about the plaintext
like using a speller can narrow the search area further but there is no
warranties.

Sometimes you will need to relay in your own brain and do a manual fix.
