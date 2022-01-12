---
layout: post
title: "Blog Reference"
tags: [cryptography, matasano, cryptonita, repeating key]
inline_default_language: python
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

Fenced Code is **not supported** for now.
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
