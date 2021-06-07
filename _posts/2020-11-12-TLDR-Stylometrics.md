---
layout: post
title: "TL;DR Stylometrics"
tags: tldr tl;dr stylometric
---

A ghost writer is a person that writes a document, essay or paper but
the work is presented by other person who *claims* to be the author.

[Detecting deterring ghostwritten papers](https://thebestschools.org/resources/detecting-deterring-ghostwritten-papers-best-practices/)
is an article written by a (ex)ghost writer and explains what happens
behind the scene when a student pays for this *dark* service.

Would be possible to detect this in an automated way?

Given a set of documents, could we determine of they were written or not
by the person or people who claim to be the authors?

This problem is known as *authorship attribution* and I will show a few
papers that I read about this, in particular around the concept of
*stylometric*, fingerprints that the real author leaves when he or she
writes.<!--more-->

## Application papers

### *Who Wrote the 15th Book of Oz? An Application of Multivariate Analysis to Authorship Attribution*

{% marginnote
'Authors:
José Nilo G. Binongo
' %}

An application case for authorship attribution called also *a
non-traditional method of attibuting authorship*.

The author categories several writings of the universe of Oz to
determine the author of "The Royal Book of Oz" among two options: Lyman
Frank Baum, the creator of the Oz universe and Ruth Plumly Thompson,
a children's writer that continued the work of Baum.

The feature selected was the frequency of the *functional words*.

*"Among the parts of speech, function words are made up of pronouns,
auxiliary verbs, prepositions, conjunctions, determiners, and degree
adverbs. These parts of speech have a more grammatical than
lexical function."*

Some functional words are more specific and inherent has more meaning
(content). Depending of the book these may appear more or less.

Because the frequency depends of the content and not on the author,
these "more specific" functional words are removed.

The author of the paper takes the top 50 of the most frequency
functional words to remove these "too specific" words.

The 50 dimensionality is then mapped (reduced) to 2 using principal
component analysis (PCA).

> A very good paper.



### *Delta for Middle DutchAuthor and Copyist Distinction in Walewein*

{% marginnote
'Authors:
Karina van Dalen-Oskam and Joris van Zundert<br />
Huygens Instituut, The Hague, The Netherlands
' %}

The Walewein text is known to be written by one author and then
continued by a second author.

The authors of the paper used stylometric to determine where one author
picked and continued the work of the former.

The authors decided to lemmatize the text.

Lemmatize a text means to take the words and rewrite them in a
normalized way. For example words like "play, playing, played" are
mapped to a single "play" verb.

Then they used Yule's K and Burrows' Delta metrics over a rolling window
of 2000 lines of text.

Yule's Characteristic K is a estimation of the richness of a text:
text with a lot of repeated words are said to be less rich while the
text with less repeated words *has more vocabulary*.

K is defines as:

$$ K = 10^4 \left( -\frac{1}{N} + \sum_{i = 1}^{N} V_i \left( \frac{i}{N} \right)^2 \right) $$

where $$N$$ is the count of words in a text and $$V_i$$ the number of words that
appeared $$i$$ times.

Burrows' Delta models a set of documents as a matrix.

Each document is modeled as a algebraic vector where each position
represent a word and contains the frequency of that word.

The frequencies per document are normalizes so they sum up 1.

The vectors are then stacked forming a matrix having in each column the
frequencies of a particular word in all the documents.

Each column is normalized such the mean or average of them is 0 and the
standard deviation is 1. A procedure common in ML.

The Delta between to documents is then the Manhattan distance between
their two vectors.

> Interesting reading.



## Survey Papers


### *A Framework for Authorship Identification of Online Messages: Writing-Style Features and Classification Techniques*

{% marginnote
'Authors:
Rong Zheng, Jiexun Li, Hsinchun Chen, and Zan Huang
<br />
New York University, University of Arizona
' %}

*"key-word-based features are widely
accepted to be ineffective in author identification in multiple-
topic corpora"* But there are exception if the content-words denotes a
particular knowledge about a topic that could be correlated with the
author.

> An example of this is the "Walewein" paper where the 100-150 most common words
> which are principally composed of content-words were able to
> distinguish the two authors of a text while the 1-50 most common
> words, principally function-words, were able to detect the scribes
> that also modified the text.

The paper summarizes the features used by several papers (2006):

 - lexical: average word/sentence length, vocabulary richness
 - syntactic: freq of words, use of punctuation
 - structural: paragraph length, indentation, greeting/farewell
   statements
 - content-specific: freq of keywords

> The structural seems very interesting. Opening phrases (like
> "In my opinion I ...") could be very characteristic of the author.
> The use of listing (the ones that begin with `'-'` or `'*'`) also.

Table 3 describes more of these in details.

*"Structural features and
content-specific features showed particular discriminating
capabilities for authorship identification on online messages.
SVM and neural networks outperformed C4.5 and neural
networks significantly for the authorship-identification task."*

Most of the cited papers analyze very small set of documents (~80)
and a very small set of authors (~4).

Some exceptions have 300 or even 1200 documents and 7, 10 and 45
authors.

> Quite small

*"Content-specific features
improved the performance of the three classifiers signifi-
cantly for the English datasets [...] e.g., some people preferred check
as a payment method; some people mostly sell Microsoft products)."*

> I don't think that this is true in general (like a characteristic of
> the author). The dataset used in the paper has a very broad topic so
> it is possible that some people wrote only about a sub topic and other
> people about another hence having the discriminant.

> Very good paper to read it again.


### *A Prototype for Authorship Attribution Studies*

{% marginnote
'Authors:
Patrick Juola, John Sofko, Patrick Brennan
<br />
Duquesne University
' %}

A survey of the current state of the art. It points to some other
resources and shows some results but nothing concrete.

The authors proposes a three-phases "framework" to develop/research
stylometrics: canonization, determination of the event set and
statistical inference.

In short: extract text from the media, remove spurious noise and apply
other kind of filtering/normalization (canonization); from there select
the features to analyze and possible eliminate uninteresting events
(determination) and finally perform a machine learning technique
(inference).

A current practice these days.

The *Java Graphical Authorship Attribution Program* or JGAAP program is
mentioned.

A substantial part of the paper focus in uninteresting parts of JGAAP
like the Graphical User Interface (GUI), saving/loading files and high
level code description.



## More Theoretical-like Papers


### *Computational Constancy Measures of TextsYule’s K and Rényi’s Entropy*

{% marginnote
'Authors:
Kumiko Tanaka-Ishii, Shunsuke Aihara
<br />
Kyushu University, JST-PRESTO, Gunosy Inc.
' %}

*"A constancy measure for a natural language text is [...] a computational
measure that converges to a value for a certain amount of text and remains
invariant for any larger size [...], its value could be considered as a
text characteristic."*

Yule's K is defined as

$$ K = C \left( -\frac{1}{N} + \sum_{i = 1}^{imax} V(i,N) \left( \frac{i}{N} \right)^2 \right) $$

<!-- _a -->

where $$N$$ is the total number of words in the text, $$V(N)$$ the number of
distinct words, $$V(i,N)$$ the number of words that appear $$i$$ times and $$imax$$
the largest frequency of a word.

> We could use $$N$$ as $$imax$$ because for the $$i$$ that $$imax < i <= N$$ the
> value of $$V(i,N)$$ is zero but using $$imax$$ directly is faster.

The constant $$C$$ was defined by Yule to $$10^4$$.


Golcher's V is defines as $$k/N$$ where $$N$$ is the length of the string and $$k$$
the number of inner nodes of a Patricia suffix tree of the text.

The paper describes other metrics including $$H_a$$, the
Renyi Entropy, a generalization of the Shannon entropy defined as:

$$ H_a(X) = \frac{1}{1-a} \textrm{log} \left( \sum_{\forall X} P(X)^a \right) $$

<!-- _a -->

Where $$a >= 0$$, $$a != 1$$, $$P(X)$$ the probability function of $$X$$.

When $$a == 0$$, it reduces to $$H_0(X) = 1 \textrm{log} \left( \sum_{\forall X} 1 \right) $$ <!-- _a -->
$$H_0(X) = \textrm{log} ( |X| ) $$  (aka indicates the number of distinct occurrences
of $$X$$)

When a approximates to 1 (limit), $$H$$ reduces to Shannon entropy.

For $$H_2(X)$$ the authors shown that *"[$$H_2$$] immediately shows the
essential equivalence to Yule’s K*"

The authors shown empirically that $$H_2$$ converges to a value for texts of
between $$10^2$$ and $$10^4$$ words/characters depending of $$H_2$$ was defined for
words or characters respectively.

The authors also shown that $$H_2$$ is not a good discriminant for
authorship: *"Examining the nature of the convergent values
revealed that K does not possess the discriminatory power
of author identification as Yule had hoped."*

> $$H_2$$ or Yule's Y converges fast so it could be applied to short
> terms. Defined as it was in the paper (for words and characters) it will
> not work for authorship attribution but it may work under a different
> feature set (input) instead of words/characters.





### *Cross-entropy and linguistic typology*


{% marginnote
'Authors:
Patrick Juola
<br />
University of Oxford
' %}

Describes briefly the application of the *cross-entroy* for language
categorization.

*"Cross-entropy appears to be a meaningful and easy to measure method of
determining "linguistic distance" that is more sensitive
to variances in lexical choice, word usage, style, and syntax than
conventional methods."*






### *Understanding and explaining Delta measures for authorship attribution*

{% marginnote
'Authors:
Stefan Evert, Thomas Proisl, Fotis Jannidis, Isabella Reger, Steffen Pielström, Christof Schöch and Thorsten Vitt
<br />
Friedrich-Alexander-Universität Erlangen-Nürnberg and Julius-Maximilians-Universität Würzburg
' %}

Describes and analyzes Burrows' Delta distance based on the Manhattan
distance and different variations of it including Euclidean, Linear and
Cosine distances.

> A paper to review later if required.




## Good but no so good papers

### *Who's At The Keyboard? Authorship Attribution in Digital Evidence Investigations*

{% marginnote
'Authors:
Carole E. Chaski.
<br />
Institute for Linguistic Evidence, Inc
' %}

The paper presents the results of some other researches. The one that
scored the highest authorship attribution was:

*"counting particular errors or idiosyncrasies and inputting this into a
statistical classification procedure [...](using) supported vector machines
(SVM) and C4.5 analysis"*

The paper names these as *"stylemarkers"*.

For stylometrics, the paper mentions references to other papers where
they used
*"word length, phrase length, sentence length, vocabulary frequency,
distribution of words of different lengths"* as features and SVM (with
accuracy that oscillated between 46% and 100%), discriminant function analysis
(accuracy between 87% and 89%) and using neural networks (accuracy 84%).

The dataset for the paper consisted on several writings from several
authors about 10 different topics.

While the paper takes into consideration some biases like age and gender
the 10 topics are to my opinion biased to "personal topics".

*"Describe a traumatic or terrifying event in your life and how you
overcame it."* is an example.

The paper uses the ALIAS software and restricts the analysis of the
samples to only *"punctuation, syntactic and lexical"* features.

The punctuation consists of counting the *placement* of the punctuation
marks: at the end of clause (EOC), at the end of phrase (EOP) and in the
middle of a word (like the dash in "re-invent" or the apostrophe in
"don'")

The author claims that this is *"slighter better performance"* than the
counting of the punctuation mark alone where the placement is ignored.

The syntactic structures refers to the way that a "common" construction
deviates to an "uncommon" construction.

The "common/uncommon" are named "unmarked/marked" constructions. This is
the technical name and "common/uncommon" are the names that I gave them
due my lack of expertise in the topic.

A "common" (unmarked) construction could be "how old are you?". In
English we could say "old" and "young" but it is very common to use
"old" for some reason. The "uncommon" (marked) would be "how young are
you?".

The "common/uncommon" does not limit to words but to phrases as well, no
only in literal phrases but in the *syntax* of these.

"the white house" follows the `<adjetive> <noun>` "common" pattern.

While it is clear that these "common/uncommon" feature could spot
non-native writers, it is not very clear to me how to use it for
authorship attribution in general.

Perhaps seeing repetitive patterns in the "uncommon" parts of a phrase?
Like "the big white house" and "the white big house": the order of the
adjetives may leave a fingerprint of the author.

The last feature is lexical features (word lengths, and stuff like
that). The paper distinguishes between functional and content
words but use both.

These features (punctuation, syntactic and lexical) are extracted using
ALIAS. Sadly it is a paid, closed source software (done by the author of
the paper) and the dataset seems to be closed too.

For the "machine learning" part, the paper used linear
discriminant function analysis (DFA).







### *Determination of writing styles to detect similarities in digital documents*

{% marginnote
'Authors:
Yohandri Ril Gil, Yuniet del Carmen Toll Palma, Eddy Fonseca Lahens
<br />
University of Information Sciences, Havana
' %}

The paper describes a stylometric mathematical model:

 - frequency of stop words: articles, prepositions, adverbs and conjunctions.
 - level of difficulty: what's the *education level* required to understand
   the text. It uses the Flesch-Kincaid index (English only).
 - richness of vocabulary
 - mean sentence length
 - mean word length

The authors claim that
*"The proposed method for determining writing styles can be used in a
scenario where it is necessary to describe documents whose authorship
has been validated."*

But the "discussion and conclusions" section talks more about the
underlying motivation for a person to do plagiarism than about the
model.

They also claim

*"The extraction of the style vector marks the
difference between authors, whether or not they cover the same topic. By
applying the proposed mathematical model to a considerable set of documents,
it was found that trends really do exist when it comes to drafting, and
that such trends put a stamp of authenticity onto a document."*

> In a personal opinion, I'm have my doubts about these statements based
> on the few numbers shown in the paper.





### *Stylometry-based Approach for Detecting Writing Style Changes in Literary Texts*

{% marginnote
'Authors:
Helena Gómez-Adorno, Juan-Pablo Posadas-Duran, Germán Rios-Toledo, Grigori Sidorov, Gerardo Sierra
<br />
Instituto Politécnico Nacional, Mexico; Universidad Nacional Autónoma de México, Mexico; Instituto Politécnico Nacional (IPN), Mexico; Centro Nacional de Investigación y Desarrollo Tecnológico, Mexico
' %}

The paper compares the performance of different algorithms (Logistic Regression
and two implementation of Support Vector Machine) and different sets of
features (statistics like mean, average of word length, sentences
length, punctuation and stop words among others) to classify
writings of different authors.

The Figure 1 of the paper shows that
 - using SVM over punctuation feature only yields a very good results.
 - using Logistic Regression as default for other combination of
   features yields very good results.

While those are interesting facts, there is no clear evidence of it (a
very small corpus was used).

The paper shows that some authors' styles are more sensible to some
features and algorithms than others.

From a total of 6 authors:

*"[Punctuation-based models] classified
the writing stage of a work above 70% of the times
for two authors [...], [in the case of other two authors] 
the combination
of phraseology-and punctuation-based features obtained the best
performance. The combination
of all types of features obtained the best
performance for [the remaining two authors]"*

> It doesn't look solid.


## What kicked everything

### *Detecting deterring ghostwritten papers, best practices*

{% marginnote
'Authors:
David A. Tomar (Ed Dante)
' %}

[It is what started this.](https://thebestschools.org/resources/detecting-deterring-ghostwritten-papers-best-practices/)

Classify the students paying for a ghost writer in three categories:

 - Non native language: students that they need to write an essay in a
   foreign language, let's say English. The student knows that he/she will have
   more opportunities to succeed if the essay is written by a native
   English speaker.
 - Composition/Research deficient students: students that, while they
   can speak and write in the target language, they have hard time to
   write an essay or doing the homework.
 - Lazy students: they prefer to pay for a service instead of doing the
   work.

Detecting a ghost writer is hard and having solid proof of it is harder.

The best strategy is to disallow the possibility from the begin making
the decision of hiring a ghost writer much expensive, riskier.

 - In-class writing: the students write during the class so it is hard
   for a ghost writer to be there
 - Multi-draft process: have a periodic review with the students and
   check the evolution of the essay/work.
 - Personalization of the subject matter: use topics that are more
   personal and can be bind to the author. That part is important, the
   subject must be bound to the student in some verificable way
   otherwise a ghost writer could just write a personal subject about
   him/her!
 - Original course materials: make the topic have something very unique.
   Don't repeat yourself.

These should be combined and adapted to the particular class.

> Having 1o1 meetings with the students randomly chosen to discuss the
> implementation details of a work makes the "multi-draft process"
> scalable.

Exit interviews (interviews that happen when the student does a
final submission) are an example of that.

> A very nice article to read.


## Resources

NLTK's [punkt](https://www.nltk.org/_modules/nltk/tokenize/punkt.html) module: Punkt Sentence Tokenizer

*"This tokenizer divides a text into a list of sentences
by using an unsupervised algorithm to build a model for abbreviation
words, collocations, and words that start sentences.  It must be
trained on a large collection of plaintext in the target language
before it can be used."*

*"The NLTK data package includes a pre-trained Punkt tokenizer for
English."*

It is used to determine when a period marks the end of a sentence and
when it doesn't and things like that.








[PDFMiner](https://github.com/euske/pdfminer/) (community): parser for PDF files


[Blog post](https://cligs.hypotheses.org/577) that explains how to call R code from Python using the `rpy2`
module. In particular how to call the R package `stylo` from Python


[Stylo](https://github.com/computationalstylistics/stylo): R package for stylometric analyses


[JGAAP](https://github.com/evllabs/JGAAP): Java Graphical Authorship Attribution Program is a tool to allow
nonexperts to use cutting edge machine learning techniques on text
attribution problems


[NTLK](https://www.nltk.org/): Natural Language Toolkit for Python


[Stanza](https://stanfordnlp.github.io/stanza/index.html): A Python NLP Package for Many Human Languages


[Weka](https://github.com/chrisspen/weka): a toolset/framework for ML like skilearn but with a GUI. It is
very interesting.


[Nolds](https://cschoel.github.io/nolds/nolds.html): Python package with algorithms to analyze random sequences (signals,
market time series, text perhaps?)


## Some other resources

[Identifying Different Writing Styles in a Document Intrinsically Using Stylometric Analysis](https://github.com/Hassaan-Elahi/Writing-Styles-Classification-Using-Stylometric-Analysis)
It is a single Python file with several metrics poorly documented.
It could be useful to see the code for some cases because it has a lot
of metrics, most of them mentioned in the paper of Zheng.



[Turnitin](https://www.turnitin.com/): among other stuff, it has a plagiarism detection.


[ALIAS](https://aliastechnology.com) is program developed by Carole E.
Chaski for *"lemmatizing, computing
lexical frequency ranking, calculating lexical, sentential and text lengths,
punctuation-edge counting, Part-Of-Speech-tagging (POS-tagging) , n-graph
and n-gram sorting, and markedness subcategorizing"*.

Sadly it is a paid, closed source software.

> n-gram is used to denote the sequence of $$n$$ elements like words or
> POS tags while n-graph denotes sequences of $$n$$ characters.

