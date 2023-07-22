---
layout: post
title: "Document Building: from static web blogs to textbooks"
tags: [blog, latex]
artifacts:
    - build-blog.svg
    - qubes-net-path.svg
---

I've being writing for a long time. I'm far from being a good writer but
having the consistency to write at least a blog post every month gave me
more expressive power.

Being a non-English native speaker, that also put me in an uncomfortable
position --out of the confort zone-- but looking back, even with all my
mistakes, I really improved.

I'm using a bunch of different technologies to assist me:

 - the [blog site](https://book-of-gehn.github.io) is written in
[Markdown](https://guides.github.com/features/mastering-markdown/) and
turned into a static web site with [Jekyll](https://jekyllrb.com/).
 - the [C/C++ lectures](https://github.com/eldipa/taller-clases/) that I
give are made with [Latex/Beamer](https://ctan.org/pkg/beamer).
 - the [C/C++ textbook](https://github.com/eldipa/guia-taller) is also
in Markdown but it's compiled into a PDF using
[Pandoc](https://pandoc.org/) and
[Foliant](https://pypi.org/project/foliant/).

And while those have been incredible powerful, I hit the limitations of them
in time to time.

This writeup is meant to brainstorm and design a new way to work.<!--more-->

I don't want to have a single tool to do everything. I want to be more
humble and less ambitious and diagram a *pipeline* flexible enough to
help me to simplify and speed up my writings.


## Mathematics

Some of my posts are about cryptography, some about logic and certainly
I'm going to explore more related fields in the future like quantum computing,
mathematics and physics.

All of these posts have mathematical formulas and symbols.

Having the ability to write formulas in Markdown is super helpful (for me).
I use *inline* formulas, like `E = mc^2`{.mathjax}, and *block-level* formulas:

```tex;mathjax
K_{1,1} p_{1,1} + K_{1,2} p_{1,2} = c_{1,1} \quad(\textrm{mod } m) \\
K_{2,1} p_{1,1} + K_{2,2} p_{1,2} = c_{1,2} \quad(\textrm{mod } m) \\
K_{1,1} p_{2,1} + K_{1,2} p_{2,2} = c_{2,1} \quad(\textrm{mod } m) \\
K_{2,1} p_{2,1} + K_{2,2} p_{2,2} = c_{2,2} \quad(\textrm{mod } m) \\
```

Behind the scenes these are written as:

```tex;mathjax
K_{1,1} p_{1,1} + K_{1,2} p_{1,2} = c_{1,1} \quad(\textrm{mod } m) \\
K_{2,1} p_{1,1} + K_{2,2} p_{1,2} = c_{1,2} \quad(\textrm{mod } m) \\
K_{1,1} p_{2,1} + K_{1,2} p_{2,2} = c_{2,1} \quad(\textrm{mod } m) \\
K_{2,1} p_{2,1} + K_{2,2} p_{2,2} = c_{2,2} \quad(\textrm{mod } m) \\
```

The downside is that my Markdown editor believes that those pieces of
text are in Markdown notation so the highlighted syntax goes crazy.

It would be nicer to use Markdown's code-fenced blocks to make the
Markdown engine (and editor) aware of them and turn them into beautiful
math symbols later.

Something like:

```tex;mathjax
K_{1,1} p_{1,1} + K_{1,2} p_{1,2} = c_{1,1} \quad(\textrm{mod } m) \\
K_{2,1} p_{1,1} + K_{2,2} p_{1,2} = c_{1,2} \quad(\textrm{mod } m) \\
K_{1,1} p_{2,1} + K_{1,2} p_{2,2} = c_{2,1} \quad(\textrm{mod } m) \\
K_{2,1} p_{2,1} + K_{2,2} p_{2,2} = c_{2,2} \quad(\textrm{mod } m) \\
```

Neither Jekyll or Pandoc have something like this, but in Pandoc I could
write some [Pandoc filter](https://pandoc.org/filters.html) to turn a
Markdown code-fenced block tagged as `{.math}` into Tex/Latex.

And what it means *into Tex/Latex* exactly is not trivial.

For my blog I use [MathJax](https://www.mathjax.org/) to render
Tex/Latex in the browser; for my lectures/textbook, I use a Tex/Latex
engine like [pdflatex](https://linux.die.net/man/1/pdflatex) to get a
PDF.

But how to do it using a single pipeline, *I dunno*.


## Macros


While Tex/Latex makes beautiful documents, it is not the best language.

Typing `\hat{R}` to get `\hat{R}`{.mathjax} gets quickly annoying if
you have to write `\hat{R}`{.mathjax} several times.

In this case I use Tex/Latex *macros* to write `\R` instead of `\hat{R}`.

But what about other non-Tex stuff?

I write a lot about programming and it's handy to show code with
highlighted syntax:

```python
def foo():
  pass
```

```cpp
void bar(int i) {
}
```

Those were made with Markdown's *fenced-code blocks* where
you *tag* the block with the language to you are writing.

Jekyll doesn't, but Pandoc supports *tagged inline code*.

Just type `{.python}` after an inline and that's it but as you
may imagine, doing it for each inline code is tedious.

Most of my posts talks about a single language and my textbook is mostly
about C/C++ so why not make all the inline code highlighted with a
particular syntax by default?

Once again, Pandoc's filters fit perfect for the job.

## Fixing syntax highlighting

{% call marginnotes() %}
```nasm
pwndbg> pdisass &main
 ► 0x1044c <main>       push   {fp, lr}
   0x10450 <main+4>     add    fp, sp, #4
   0x10454 <main+8>     sub    sp, sp, #0x50
   0x10470 <main+36>    bl     #gets@plt <gets@plt>
```
{% endcall %}

For the blog, the code is highlighted with
[Rouge](https://github.com/rouge-ruby/rouge). It works like a charm but
no without some sharp corners.

Its support for assembly is limited. I cannot blame it, there are a lot
of assembly syntaxes out there!

A hack that I did was to run some Javascript to patch the HTML in
runtime and add the missing CSS classes to the unrecognized mnemonics.

```javascript
var xpath = ".//div[contains(@class,'language-nasm')]//span[(((text() = 'blt') or (text() = 'b'))]";
var elems_iter = document.evaluate(xpath, document, null, XPathResult.ANY_TYPE, null);

var elems = [];
var el = elems_iter.iterateNext();
while (el) {
    elems.push(el);
    el = elems_iter.iterateNext();
}
for (var i = 0; i < elems.length; i++) {
    var el = elems[i];
    el.classList.add('k'); // keyword
    el.classList.remove('n'); // noun
}
```

I could do the same with Pandoc that uses
[Pygments](https://pygments.org/) for the highlighting. I've already
have some experience with it from my [interactive assembler
*iasm*](https://github.com/bad-address/iasm) so it is factible.

Certainly is going to be useful for the textbook.


## Preprocessing

You cannot set any layout in Markdown: put some image in the
right margin, make a text an epigraph or a side-note.

It's on purpose: Markdown wants to be simple, in contrast with HTML. But
in some cases it too simple.

Jekyll allows you to pass HTML code along the Markdown. In my blog I use instead
[Liquid](https://jekyllrb.com/docs/liquid/) tags to make my live a
little easier.

This allows me not only to avoid writing HTML but also performing
arbitrary operations like creating images on the fly (see more later).

In my C/C++ lectures written in Tex/Latex, I required to generate
different *flavors* of slides.

Slides for presenting in class with little text but a lot of diagrams;
slides for reading with a lot of text, the *handout* for the students.

With the pandemic, I switched to virtual classes (no news here). Sharing
my screen allowed me to *draw* over the slides. They have incomplete
diagrams that I complete interactively with the students during the lecture.

Make this within Tex/Latex is possible but it is a pain.

So I resorted to use a preprocessor. Similar to Liquid I used
[Jinja2](https://jinja.palletsprojects.com/en/3.0.x/)

While all of these could be done, in theory, with Pandoc filters, I
think that having a preprocessor and *template engine* like Jinja2 can
be quite handy.


## Images and diagrams

{{ marginfig('seaborn-cheatsheet-v1.svg') }}

I make a lot of diagrams, state machines and plots but I try to not make
them by hand.

Tools that requires a human to do the layout are a waste of time (there
are exceptions like me [Seaborn Cheatsheet](/articles/2021/06/05/Seaborn-Cheatsheet.html)).

Instead I prefer to *describe* the diagram in text and let a
program to do the image and layout for me.

For a lot of them I use [PlantUML](https://plantuml.com). Despite the
name, it is for more than UML.

For simpler block diagrams I use [Ditaa](http://ditaa.sourceforge.net/)
and for graph-like I have the good old [Graphviz](https://graphviz.org/).

{% call margindiag('qubes-net-path.svg', 'plantuml')  %}
```plantuml
hide empty description
skinparam backgroundColor transparent

state "AppVM" as app1 {
state "route" as route

[*] --> route
}

state "ProxyVM" as proxy1 {
state "route" as route2

route -down[dashed]-> prerouting : ping from .7.27 to .8.8
prerouting -left-> filter
filter -down-> route2
route2 -right-> postrouting
}
```
{% endcall %}

So far I'm using these tools for by blog so I write the
PlantUML/Ditaa/Graphviz diagrams (text) inside a Liquid tag in the same
Markdown.

During the building, the correct tool is called and the image is
generated while the Liquid tag is replaced by some HTML `<img>` link.

For my C/C++ textbook, I use a Foliant plugin that does the same but
instead of Liquid tags, Foliant uses HTML tags as *hook points* to call
third party plugins.

Probably I'm going to use Jinja2 for these too. I'm not convinced of
using HTML tags/hooks or Pandoc filters here.

Related to this, make [Seaborn](https://seaborn.pydata.org/) and
[Matplotlib](https://matplotlib.org/) plots from the Markdown directly
would be nice too.

## Interactive diagrams

This applies only to my blog and Javascript is the thing that brings
life anything. From simple [Venn
diagrams](https://github.com/benfred/venn.js/) to arbitrary complex
[D3 diagrams](https://d3js.org/).

But I want those beautiful diagrams be part of my non-interactive
lectures and textbook.

How to do it is still an open question.

## Assembly

And not, I'm not talking about ARM.

All the Markdown files are meant to be integrated in some meaningful
way. Assembled. Linked.

For the blog, Jekyll generates an independent web page for each post. It
just put each in a file that follows the `year/month/day/post-name.html`
pattern name.

A textbook is more complicated however.

Foliant joins together all the Markdown files and call Pandoc *once* to
generate a single Tex/Latex file and from there, a *single* PDF.

This doesn't scale.

It would be much efficient to generate a Tex/Latex per Markdown file, a
PDF per file and join them together at the end.

Like in a C/C++ compilation schema, you compile each unit separately and
link them at the end: if you have to modify a single file, you just need
to compile that one only and not the whole thing.

Foliant does this on purpose and for a good reason: when you write a
textbook you want to have links and references to other parts including
parts of *other* Markdown files.

To *resolve* them, all the Markdown files need to be processed as a
single unit.

To have a separated unit compilation, I'm going to figure out how to
*resolve the links and references* at the Tex/Latex level.

A simple `cat *.pdf > final.pdf` will not work.

## Post-processing

A few things that I do manually:

 - optimize the size of the PNG files with
[optipng](https://linux.die.net/man/1/optipng)
 - check the grammar with [LanguageTool](https://languagetool.org/)
 - review broken links (this is not even automated!)

Some will still be manual (like checking the grammar) but the rest
should be part of the pipeline.

The review of any broken link could be done at the Pandoc filter level
for example.

## Pipeline

There are a lot of tools to call in sequence and to avoid recompilation,
a tool should not be called if its input didn't change since the last
time it was called.

I don't want to generate the same HTML page if the Markdown didn't
change.

Jekyll does a relative good thing here but Foliant doesn't.

I think that a plain [Makefile](https://www.gnu.org/software/make/)
should work. May be something on top to *visualize* the pipeline?

And the *toolchain* should be in its own
[Docker](https://www.docker.com/).

## Final thoughts

Rewrite my blog, lectures and the work-in-progress textbook is not going
to be trivial.

There are a lot of gaps and problems without solution but I bet that
this is going to improve my workflow.

So far, this is want I think it may work:

{% call maindiag('build-blog.svg', 'plantuml') %}
```plantuml
hide empty description
skinparam backgroundColor transparent

state "Markdown" as md1
state "Markdown" as md2

md1 -right-> md2 : Jinja2

state "Pandoc" as pandoc {
state "Json" as js1
state "Json" as js2

js1 -right[dashed]-> js2 : filters
}

md2 -right-> js1

state "Tex/Latex" as tex
js2 -> tex
js2 -down-> html

tex -> PDF : pdflatex
```
{% endcall %}

Fingers crossed.
