---
layout: post
title: "Quick Guide / Template"
latex_macros: "R: '{\\\\hat{R}}', s: ['{\\\\overline{#1}}', 1]"
---

About how to write a post.<!--more-->

Use me as a template or as a repository of small snippets.

## Excerpt

Use `< !-- more -- >` to mark the end of the post's excerpt.

Use `{ % marginfigure % }` with the CSS class `in-index-only` to show the
margin figure in the index but not in the post.

```
{   % marginfigure 'IPs' 'assets/qubes/qubes-ips.png' '' '' 'in-index-only' %  }
```

## Links

To an *external resource*:
[DPDK](http://git.dpdk.org/dpdk/tree/lib/librte_ring/rte_ring_c11_mem.h)

To a *local post*
[Other implementations](/book-of-gehn/articles/2018/09/16/Ouroboros-Circular-Buffer.html)

Link to a Asset
For this [we can create a small C program](/book-of-gehn/assets/azeria-arm-challenges-assets/test-egg.c)

## Math / Latex

**beware:** vertical bars `|` may be interpreted as Markdown tables.
Use `\vert`

Inline latex $$n\textrm{x}n$$ stuff.

Block level latex:

$$ K p_i = c_i\quad(\textrm{mod } m)$$

Multi line block level latex:

$$
K_{1,1} p_{1,1} + K_{1,2} p_{1,2} = c_{1,1} \quad(\textrm{mod } m) \\
K_{2,1} p_{1,1} + K_{2,2} p_{1,2} = c_{1,2} \quad(\textrm{mod } m) \\
K_{1,1} p_{2,1} + K_{1,2} p_{2,2} = c_{2,1} \quad(\textrm{mod } m) \\
K_{2,1} p_{2,1} + K_{2,2} p_{2,2} = c_{2,2} \quad(\textrm{mod } m) \\
$$


In the "front matter" of the page/post, set the 'latex_macros' variable
to define handy macros for latex, specially aliases.

For example you can define `\R` as an alias for the latex
command `\hat{R}` (zero arguments) or `\s` as an alias for
`\overline{#1}` (one argument).

In the front matter you will have to define the `latex_macros` variable:

```
latex_macros: "R: '{\\\\hat{R}}', s: ['{\\\\overline{#1}}', 1]"
```

Note the double escape of the `\`

Usage:

$$ \R  \s{foo} $$

## Apostrophe

In the macros/Liquid tags the `'` is used to delimit the parameters.

Because of that, it cannot be used in the content of them. Instead
use the `&apos;` entity.

{% marginnote 'This&apos;s really cool' %}


## Images

{% maincolumn 'assets/memory/rc/cnt-cpu-2ndcpu-heatmap.png'
'Image in the main column,
<bt />
and this comment to its right.' %}

{% maincolumn '<img style="max-width:60%;" alt="CBC Enc" src="/book-of-gehn/assets/matasano/cbc-enc.png">' '' %}

{% marginfigure 'Alternative name' 'assets/eko2019-writeups/rpg-dir/second_indirection.png'
'Image on the right of the main column,
<bt />
and this comment below of it. Captions and CSS style are optional' 'max-width: 100%;'
'more optional classes here' %}


{% marginfigure '' '<img class="fullwidth" alt="Alternative name" src="/book-of-gehn/assets/foo.png" />'
'Full control of html if needed. Note that the src must start with /book-of-gehn/' %}

{% fullwidth 'assets/mpmc-queue/relativity-quantic-concurrent-programming.png'
'Full-width images expand to the whole page beyond the main column.' %}

## Notes

{% marginnote
'It is best to put this in its own paragraph above the target text
<br />
That will make the note to appear on the right of the target text,
vertically aligned.
' %}

## Notes with markdown

{% marginmarkdowncode
'
```cpp
if (data[i] % 2 == n)
    while (1);

++data[i];
```
'
'caption here' %}

## Quotes


> "The virtual interfaces in client VMs are called `ethX`,
> and are provided by the `xen_netfront` kernel module, and
> the corresponding interfaces in the Net/Proxy VM are
> called `vifX.Y` and are created by the `xen_netback` module."
> <cite class="epigraph">[Playing with Qubes networking for fun](https://theinvisiblethings.blogspot.com/2011/09/playing-with-qubes-networking-for-fun.html)</cite>

Highlight/Take home message

>>> "This is important"

## Diagrams

State machine diagrams `marginplantuml` and `maincolumnplantuml`

Use http://www.plantuml.com/plantuml/uml/ for testing online.


{% marginplantuml caption:'Caption $$sm_1$$ and $$sm_2$$ (``ab``).' %}
`
@startuml
hide empty description

state "<math>sm_1</math>" as sm1
state "other state name" as sm2

[*] -> sm1 : a description
sm1 -> sm2
sm2 -> [*] : <math>\epsilon</math>

@enduml
`
{% endmarginplantuml %}

"Ditaa" diagrams **must** be explicitly set

{% maincolumnplantuml engine: 'ditaa' args: '--no-shadows --no-separation' %}

sp             sp+4           sp+8           sp+12
 |              |              |              |
 +--------------+--------------+--------------+--------------+
 |    &argv0    |    &argv1    |    &argv2    |    &argv3    |  < stack
 +-------+------+-------+------+-------+------+----(zero)----+
         |              |              |
   /-----/            /-/      /-------/
   |                  |        |
   V                  v        v
   /bin/bash\x00      -c       echo 'pwn!'...
{% endmaincolumnplantuml %}
