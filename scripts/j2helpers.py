
# See https://github.com/kolypto/j2cli
# pip install j2cli

import jinja2, re, os, glob, base64
from functools import partial
from datetime import datetime

from jinja2.filters import environmentfilter

@jinja2.contextfunction
def globfn(ctx, pattern, rel=None, fmt=None):
    ''' Allow the listing of some files in the filesystem.

        {% for f in glob('foo/**/*.bar') %}
            {{ f }}
        {% endfor %}

        -> foo/2.bar
        -> foo/zaz/1.bar

        Note: glob() scans the filesystem by real, it does not
        work on "non-existing-yet-files" like Tup uses.

        If rel is not None, all the paths will be relative to
        the given rel path.

        {% for f in glob('foo/**/*.bar', rel='foo/') %}
            {{ f }}
        {% endfor %}

        -> 2.bar
        -> zaz/1.bar

        If fmt is not None, all the paths are re-formatted (see Path
        class):

        {% for f in glob('foo/**/*.bar', fmt='out/{:f}') %}
            {{ f }}
        {% endfor %}

        -> out/foo/2.bar
        -> out/foo/zaz/1.bar

    '''
    listing = glob.glob(pattern, recursive=True)
    if rel is None:
        paths = (Path(f) for f in listing)
    else:
        paths = (Path(f).rel(rel) for f in listing)

    if fmt:
        paths = (f(fmt) for f in paths)

    return list(sorted(paths))

@environmentfilter
def date(env, val, outfmt, infmt='%Y-%m-%d'):
    ''' Take a date <val> in a particular format <infmt> and output
        the same date but in a differrent format <outfmt>.

        Use it like:

            -> {{ "2017-04-16" | date("%B %-d, %Y") }}

            -> April 16, 2017
    '''
    d = datetime.strptime(val, infmt)
    return d.strftime(outfmt)

@jinja2.pass_context
def j2(ctx, val, altctx=None):
    ''' Take the given string and process it with Jinja2
        as any other template using the given "alternative" context.

        If no alternative context is passed, use the current
        context to populate any variable in the template.
    '''
    if altctx is None:
        altctx = ctx

    return ctx.environment.from_string(val).render(altctx)

class Path(str):
    def __new__(cls, *args, **kw):
        return str.__new__(cls, *args, **kw)

    def __init__(self, s):
        self.s = s
        self._reset()

    '''
    s = posts/bar/2017-04-16-foo.md

    Basename (name + extesion, without the path)
    out/posts/j2md/{:b}
    out/posts/j2md/2017-04-16-foo.md

    out/posts/j2md/{:b}.yml
    out/posts/j2md/2017-04-16-foo.md.yml

    Name (name, without the path or extension)
    out/posts/j2md/{:n}.html
    out/posts/j2md/2017-04-16-foo.html

    Full (file path as is)
    out/posts/j2md/{:f}
    out/posts/j2md/posts/bar/2017-04-16-foo.md

    Full (file path as is but with the extension changed)
    out/posts/j2md/{:f.html}
    out/posts/j2md/posts/bar/2017-04-16-foo.html

    Name plus extension(s)
    out/posts/j2md/{:n.html}
    out/posts/j2md/2017-04-16-foo.html

    out/posts/j2md/{:n.html, yml}
    out/posts/j2md/2017-04-16-foo.html
    out/posts/j2md/2017-04-16-foo.yml

    Date+Name (name, without the path or extension but with a name format)
    out/posts/j2md/{:D}.html
    out/posts/j2md/2017/04/16/foo.html
    '''
    def __format__(self, format):
        if format in ('b', 'basename'):
            val = os.path.basename(self.s)

        elif format in ('n', 'name') or format.startswith('n.'):
            val, _ = os.path.splitext(os.path.basename(self.s))
            if format.startswith('n.'):
                val = self._handle_extensions(format[2:], val)

        elif format in ('f', 'full') or format.startswith('f.'):
            val = self.s
            if format.startswith('f.'):
                val, _ = os.path.splitext(val)
                val = self._handle_extensions(format[2:], val)

        elif format in ('D',):
            val, _ = os.path.splitext(os.path.basename(self.s))
            year, month, day, name = val.split('-', 3)

            val = os.path.join(year, month, day, name)

        return val


    def _handle_extensions(self, format, val):
        extensions = [e.strip() for e in format.split(',')]
        ext = extensions[self.ext_ix]

        if ext.startswith(os.path.extsep):
            ext = ext[len(os.path.extsep):]

        val = os.path.extsep.join((val, ext))

        self.ext_ix += 1
        self.more = self.ext_ix < len(extensions)

        return val

    def _reset(self):
        self.more = False
        self.ext_ix = 0

    def rel(self, r):
        return Path(os.path.relpath(self, r))

    def fmt(self, fmt):
        self._reset()
        out = fmt.format(self)

        while self.more:
            out += ' ' + fmt.format(self)

        return out

    def __call__(self, fmt, rel=None):
        if rel:
            p = self.rel(rel)
        else:
            p = self

        return p.fmt(fmt)

def ensure_html_block(s):
    # Note: leave the newlines before the begin of and after
    # the end of the fenced-code to ensure that they are properly
    # recognized by Pandoc
    return '''
```{=html}
%s
```
''' % s

def post_process_by_hook(s, **opts):
    ''' Create a CodeBlock with a special class 'post_process_by_hook'
        and with zero or more options (opts).

        This CodeBlock will be post-processed by a Pandoc Hook (see
        Panflute) to do post processing like converting Markdown text
        into HTML.
    '''
    opt_str = ' '.join(f'{k}={v}' for k, v in opts.items())
    return '''
```{.post_process_by_hook %s}
%s
```
''' % (opt_str, s)

def url_from(src, home):
    if any(src.startswith(x) for x in ('http://', 'https://', '//')):
        return src

    else:
        return os.path.join(home, src)

@jinja2.contextfunction
def _figures__fig(ctx, src, caption, max_width, cls, alt, kind, home):
    ''' Generate HTML code to show an image that it is at <src>.

        If <src> is not absolute (see url_from), the image is searched
        in <home>. See the Jinja2 macro of how this <home> is set.

        The <cls> sets the class of the img tag and <alt> is the alternate
        text to show if the image cannot be loaded by the browser.

        <max_width> sets the maximum width of the image and
        <caption> is the caption of it, added after the image.

        <kind> defines the flavour for figure (html code and position):

            - marginfig: the figure goes into the margin with the caption
              below of it
            - fullfig: the figure expands across the whole page with the caption
              below of it. Useful for figures that are really wide.
            - mainfig: the figure expands across the main column with the caption
              in the margin.
    '''
    src = url_from(src, home=home)

    lbl_cls = 'margin-toggle'
    input_cls = 'margin-toggle'
    span_cls = 'marginnote'
    img_cls = fig_cls = cls

    # optional style
    if max_width is not None:
        style = f'style="max-width: {max_width}"'
    else:
        style = ''

    id = base64.b64encode((src + caption + kind).encode('utf8')).decode('utf8')

    if kind == 'marginfig':
        return ensure_html_block(
f'''<p><label for='{id}' class='{lbl_cls}'>&#8853;</label>
<input type='checkbox' id='{id}' class='{input_cls}'/>
<span class='{span_cls}'>
<img {style} class='{img_cls}' alt='{alt}' src='{src}' />''') + \
post_process_by_hook(caption, input_format='markdown', output_format='plain-block') + \
ensure_html_block('''</span></p>''')

    elif kind == 'fullfig':
        return ensure_html_block(
f'''<p><figure class='{fig_cls}'><img {style} class='{img_cls}' alt='{alt}' src='{src}' />
<figcaption>''') +\
post_process_by_hook(caption, input_format='markdown', output_format='plain-block') + \
ensure_html_block('''</figcaption></figure></p>''')

    elif kind == 'mainfig':
        return ensure_html_block(
f'''<p><figure><figcaption><span markdown='1'>''') +\
post_process_by_hook(caption, input_format='markdown', output_format='plain-block') + \
ensure_html_block(f'''</span></figcaption>
<img {style} class='{img_cls}' alt='{alt}' src='{src}' /></figure></p>''')


@jinja2.contextfunction
def _notes__notes(ctx, caption, kind):
    wrapper_cls = 'as-paragraph'
    lbl_cls = 'margin-toggle'
    input_cls = 'margin-toggle'
    span_cls = 'marginnote'

    id = base64.b64encode((caption + kind).encode('utf8')).decode('utf8')

    if kind == 'marginnotes':
        return ensure_html_block(
f'''<p><label for='{id}' class='{lbl_cls}'> &#8853;</label>
<input type='checkbox' id='{id}' class='{input_cls}'/>
<span class='{span_cls}'>''') + \
        post_process_by_hook(caption, input_format='markdown', output_format='plain-block') + \
        ensure_html_block('''</span></p>''')


@jinja2.contextfunction
def asset(ctx, src):
    home = ctx.get('assestshome')
    assert home
    return url_from(src, home=home)


# DO NOT RENAME THIS FUNCTION (required by j2cli)
def j2_environment_params():
    # Jinja2 Environment configuration hook
    # http://jinja.pocoo.org/docs/2.10/api/#jinja2.Environment
    return dict()

# DO NOT RENAME THIS FUNCTION (required by j2cli)
def j2_environment(env):
    # Public functions
    env.globals['glob'] = globfn
    env.globals['asset'] = asset

    # Private functions called from J2 macros
    env.globals['_figures__fig'] = _figures__fig
    env.globals['_notes__notes'] = _notes__notes


# DO NOT RENAME THIS FUNCTION (required by j2cli)
def extra_filters():
    return dict(
            date=date,
            j2=j2
            )

# DO NOT RENAME THIS FUNCTION (required by j2cli)
def extra_tests():
    true_kind = ('true', '1', 'y', 'yes')
    false_kind = ('false', '0', 'n', 'no')

    def is_on(n):
        n = str(n).lower()
        if n in true_kind:
            return True
        if n in false_kind:
            return False
        raise Exception("Unknown value '%s'" % n)

    return dict(
        # Example: {% if a is on %}It is on!{% endif %}
        on=lambda n: is_on(n),
        off=lambda n: not is_on(n)
    )

