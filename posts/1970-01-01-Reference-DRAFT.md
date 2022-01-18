---
layout: post
title: "Blog Reference"
tags: [cryptography, matasano, cryptonita, repeating key]
inline_default_language: python
artifacts:
 - label.svg
---

## Front matter

`layout`: actualmente solo `post`. Esto le dice al sistema que otros
codigos HTML deben ser incluidos por default.

`title`: titulo

`tags`: usado para el `search.js`, junto a titulo, para armar los
indices.

`inline_default_language`: cada vez que se usen los backticks para
resaltar un codigo con `pygments`, el resaltado usara como lenguaje de
programacion para la syntaxis el lenguage definido. Por ejemplo esto
seria codigo Python: `yield from (42 for _ in range(10))`.

## Spoiler

{{ spoileralert() }}

Usar `{ { spoileralert() }}` para poner un mini cartelito de advertencia

## Abstract

Usar el tag `<!--more-->` para marcar el fin del *abstract*.<!--more-->

## Notes

{% call marginnotes() %}
Use me for small things.

Multiple paragraphs are allowed as also *markdown* **of**
`any` [kind]().
{% endcall %}

Margin notes son notas de texto que apareceran en el margen de la
pagina.

Acepta un parametro opcional `indexonly` que dice si el texto aparecera
solo en las paginas que muestran solo los abstract (paginas index) o si
el texto aparecera siempre.

## Code Fenced Block

```python
def syntax_highlighting_powered_by_pygments():
    return True
```

## Figures

{{ marginfig('img-ref.png') }}

A *margin figure* is a figure that it is put in the margin. When the
inline tag is used  `{ { marginfig(src) }}`, only the image is put
but if the `call` tag is used, a caption can be set to put it below the
image.

{% call marginfig('img-ref.png') %}
A caption. Like the `marginnotes` it supports *markdown*.
{% endcall %}

The images are loaded from the post's folder.

Similarly, `fullfig` and `mainfig` are used to put an image at full
width (occupying the main part and the margin; with the caption below it)
and to put it at the main part only (with the caption on the margin)
respectively.

Maximum width can be set with `max_width="nn%"`.

## Latex

Tex/Latex can be inline like in `p^2`{.mathjax} or in a block like:

```tex;mathjax
\begin{align*}
      x_2 \oplus f_2 & = 02                     \\
                 x_2 & = (02 \oplus f_2)
\end{align*}
```

And

```tex;mathjax
x_2 \oplus f_2 = 02
```

For the inline math we use backticks and the `{.mathjax}` attribute
and for the bloc we use three backticks (code fenced block) with
the class `tex;mathjax`.

Special symbols can be set using Unicode like ⊕ which it is cool
in the markdown text. This may not always look good in the webpage
however.

These Unicode can be written inside a MathJax inline/block with some
okay results in general:

```tex;mathjax
x_2 ⊕ f_2 = 02
```

## Tables

Tables are supported by Pandoc's Markdown in different formats.

The *pipe* table is one of the simplest:

     Center       |   Left                 |     Right
 :-------------:  |  :-------------------  | ---------:
     None         |  2586369892            |         0
     LZMA         |  153390408             |   94.069%
     *Split* LZMA |  60047300              |   96.715%

Table: This is a caption for the table. It is the first line after
the table that begins with `Table:` or `:`.

Depending on the location of the `:` the columns are aligned
differently. (to center, to left
and to right respectively in the example above)

Columns' sizes are based on their content like in the table above.

However if one content is too large, the content will wrap and
the columns' sizes will be based on the relative size of the dashes lines.

  Small         |   Widest                      |  Too Long: Wrapped
 :-----         |  :--------------------------- | :---------
  None          |  258                          |   aaaaaaaaa aaaaaaaaaaaa aaaaaaaaaaa aaaaaaaaaaa aaaaaaaaaaaaaaa aaaaaaaaaa aaaaaaaaaaaaaa
  LZMA          |  153                          |  bb
  *Split* LZMA  |  600                          |  cx

Tables that are so wide can use the extend of the webpage
adding the attribute `.fullwidth` to the caption (`Table:`). This is a hack made by us
and not officially supported by Pandoc but it works.

  Small         |   Widest                      |  Too Long: Wrapped
 :-----         |  :--------------------------- | :---------
  None          |  258                          |   aaaaaaaaa aaaaaaaaaaaa aaaaaaaaaaa aaaaaaaaaaa aaaaaaaaaaaaaaa aaaaaaaaaa aaaaaaaaaaaaaa
  LZMA          |  153                          |  bb
  *Split* LZMA  |  600                          |  cx

Table:{.fullwidth}

There are **more** kind of tables in Pandoc.

## Diagrams

In order to support diagrams, the name of each file generated must
be listed in the `artifacts` field of the post's metadata.

{% call maindiag('label.svg', 'plantuml') %}
```plantuml
hide empty description

[*] -> [*] : a
```
Optional captions can be set here, after the code fenced block
{% endcall %}


## Code link

Use `{ { codelink(url, [link name]}}` to generate a link to some nice
code like {{codelink("foo.py")}}

## Horizontal line

Bla bla bla
{{ hline() }}
Bla bla bla


## Quotes


> "The virtual interfaces in client VMs are called `ethX`,
> and are provided by the `xen_netfront` kernel module, and
> the corresponding interfaces in the Net/Proxy VM are
> called `vifX.Y` and are created by the `xen_netback` module."
> <cite class="epigraph">[Playing with Qubes networking for fun](https://theinvisiblethings.blogspot.com/2011/09/playing-with-qubes-networking-for-fun.html)</cite>

Highlight/Take home message

>>> "This is important"
