---
layout: post
title: "Index of Coincidence Explained"
tags: [cryptography, index of coincidence]
---

The concept of Index of Coincidence was introduced by William Friedman
in 1922-1923 in the paper titled
"The Index of Coincidence and its Applications in Cryptoanalysis"
[[1]({{ asset('biblio/index_of_coincidence_1923.pdf') }})].

The Navy Department (US) worked in the following years on this topic
coming, in 1955, with a paper titled "The Index of Coincidence"
by Howard Campaigne [[2]({{ asset('biblio/index_of_coincidence_1955.pdf') }})].

However I found some confusing and misleading concepts in the *modern*
literature.

This post is a summary of what I could understand from Howard's work.<!--more-->

## Count Coincidences

How similar are two strings?

{% call marginfig('align1.png') %}
Two strings aligned have 6 coincidences.
{% endcall %}

Put the two strings one below the other, perfectly aligned.
Now, column by column, count how many times the same letter
appear in the same column.

Two strings that have substrings in common and *aligned* have
a lot of coincidences.

We will call this Aligned Count of Coincidences or
`AC(s_1,s_2)`{.mathjax}.

{% call marginfig('align2.png') %}
Two strings, the second shifted 4 positions to the right, have 3 coincidences.
{% endcall %}

But if the substrings are not *aligned* we may think, incorrectly,
that two strings does not have nothing in common.

{% call marginfig('align3.png') %}
Two strings, the second shifted 6 positions to the left, have 3 coincidences too.
{% endcall %}

So we define the Count of Coincidences `C(s_1,s_2)`{.mathjax}
between two strings as how
many columns have the same letter for *every* possible alignment.

It's more simple than it looks.

### Count for Every Possible Alignment

Pick the first ``e`` of the first string. It will have a coincidence
with every possible ``e`` in the second string.

{% call marginfig('e_coincidences.png') %}
Coincidences of the first ``e`` with all the ``e`` of the second string.
{% endcall %}

There are 5 letters ``e`` in the second string, so we will have
5 coincidences.

Then pick the second ``e`` of the first string and repeat. Another
5 coincidences.

The first string has 3 letters ``e`` so at the end we will have 3 times 5,
15 coincidences.

In general for a particular byte we will have `n_i m_i`{.mathjax} coincidences
where `n_i`{.mathjax} is the count of that byte in the *first* plaintext and
`m_i`{.mathjax} in the second.

For all the possible bytes `i`{.mathjax}, the count of coincidences for
all the possible shifts and alignments is:

```tex;mathjax
    C(s_1,s_2) = \sum_{\forall i} n_i m_i \tag{1}\label{Coincs1s2}
```

## Expected Count

The equation `(\ref{Coincs1s2})`{.mathjax} counts the coincidence between two particular
*instances*.

{% call marginfig('families.png') %}
Two sets or families of strings `S_1`{.mathjax} and `S_2`{.mathjax}; `s_1`{.mathjax} and `s_2`{.mathjax} are just two examples of those.
{% endcall %}

Instead of comparing two particular strings we compare two *families* of strings
where the probability of each symbol `i`{.mathjax} is `p_i`{.mathjax} in the first family
and `q_i`{.mathjax} in the second.

Because `p_i`{.mathjax} and `q_i`{.mathjax} are independent, the probability of picking the
same letter or symbol `i`{.mathjax} is `p_i q_i`{.mathjax}.

Picking one letter or other are mutually exclusive events (disjoin events) so
the probability of having *any* coincidence is the sum:

```tex;mathjax
    PrC(S_1,S_2) = \sum_{\forall i} p_i q_i \tag{3}\label{PrCoincS1S2}
```

The equation `(\ref{PrCoincS1S2})`{.mathjax} is shown in [Howard], equation (25)

With `(\ref{PrCoincS1S2})`{.mathjax}, the *expected count* for two strings of length `N`{.mathjax}
taken from the families `S_1`{.mathjax} and `S_2`{.mathjax} is:

```tex;mathjax
    EC(S_1,S_2) = N \sum_{\forall i} p_i q_i \tag{4}\label{ExpCoincS1S2}
```

[Howard], equation (pseudo 2.5)

### Expected Coincidences Between Two Random Strings

If we are comparing two *uniformly distributed* random strings,
all the letters or symbols have the same probability so
` p_i = q_i = \frac{1}{c} `{.mathjax} where `c`{.mathjax} is the length of the alphabet (256 for bytes,
26 for English letters, ...)

```tex;mathjax

\begin{align*}
    PrC(R)         & = \sum_{\forall i} p_i q_i  \tag{3}\\
                   & = \sum_{\forall i} \frac{1}{c} \frac{1}{c} \\
                   & = c \frac{1}{c} \frac{1}{c}    \\
                   & = \frac{1}{c}   \tag{5}\label{PrCoincR}
\end{align*}

```

And therefore the *expected count* is

```tex;mathjax
    EC(R) = N \sum_{\forall i} p_i q_i = \frac{N}{c} \tag{6}\label{ExpCoincR}
```


## Cross Index of Coincidence

Finally, we define the Cross Index of Coincidence, `IC(s_1,s_2)`{.mathjax} for short,
as the ratio between the count of coincidences between two strings
(`s_1`{.mathjax} and `s_2`{.mathjax}) of the same length `N`{.mathjax} and the *expected* coincidences assuming
uniformly distributed random strings.

In other words is the ratio between equations
`(\ref{Coincs1s2})`{.mathjax} and
`(\ref{ExpCoincR})`{.mathjax}

```tex;mathjax
    IC(s_1,s_2) = \frac{C(s_1,s_2)}{EC(R)} = \frac{c}{N} \sum_{\forall i} n_i m_i  \tag{7}\label{IdxCoincs1s2}
```

We can also use `AC(s_1,s_2)`{.mathjax} instead of `C(s_1,s_2)`{.mathjax} and we will
get another variant of `IC(s_1,s_2)`{.mathjax}.

### `c`{.mathjax} is Not a Normalization Factor

I found in modern literature than the term `c`{.mathjax} is explained as
a normalization factor. Far from being truth.

In fact, the values that `IC(s_1,s_2)`{.mathjax}
go from 0 to `cN`{.mathjax}.

A *normalized* IC can be obtained from `(\ref{IdxCoincs1s2})`{.mathjax} if we divide it
by `cN`{.mathjax} which it is the same to ask for `PrC(S_1,S_2)`{.mathjax}:

```tex;mathjax

\begin{align*}
IC_N(s_1,s_2) & = \frac{c}{N} \sum_{\forall i} n_i m_i \frac{1}{cN}    \\
              & = \frac{c}{c} \sum_{\forall i} \frac{n_i}{N} \frac{m_i}{N}  \\
              & = \sum_{\forall i} p_i q_i \\
              & = PrC(S_1,S_2)    \tag{3}
\end{align*}

```

### Cross Index of Coincidence between Two Families

If we calculate the ratio between
`(\ref{PrCoincS1S2})`{.mathjax} and `(\ref{PrCoincR})`{.mathjax} we have a way to
compare families without needing the length:

```tex;mathjax
 IC(S_1,S_2) = c \sum_{\forall i} p_i q_i \tag{9}\label{IdxCoincS}
```


## Auto Index of Coincidences

There is another definition of IC that compares a string
with itself.

It follows a similar counting process: put the string and its
copy in two rows, count the coincidences, shift one place and repeat.

Of course there is a case where both will have a full match. That
case is ignored.

The count of *auto* coincidences is:

```tex;mathjax

    C(s) = \sum_{\forall i} n_i (n_i-1) \tag{10}\label{Coincs}

```

In term of the probabilities:

```tex;mathjax
    PrC(S) = \sum_{\forall i} p_i (p_i-1)  \tag{11}\label{PrCoincS}
```

Once again, the IC is a ratio between the actual coincidences
`C(s)`{.mathjax}
and the expected coincidences `\frac{N}{c}`{.mathjax}:

```tex;mathjax
    IC(s) = \frac{c}{N} \sum_{\forall i} n_i (n_i-1)    \tag{12}\label{IdxCoincs}
```

Or it is the ratio between the probabilities:

```tex;mathjax
 IC(S) = c \sum_{\forall i} p_i (p_i - 1) \tag{13}\label{IdxCoincNormS}
```

## Final Thoughts

This post took me a lot of time. The topic is not complex and the
maths are very simple but it is the amount of several and slightly
different definitions that makes hard to read and interpret.

Counting the coincidences between two strings aligned
`AC(s_1,s_2)`{.mathjax},
not aligned `C(s_1,s_2)`{.mathjax}, the probability of having a coincidence
`PrC(S_1,S_2)`{.mathjax}, the expected count, the `IC`{.mathjax}, ...

I hope to got it right in this post :D

