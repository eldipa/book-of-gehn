
# See https://github.com/kolypto/j2cli
# pip install j2cli

import jinja2, re, os, glob, hashlib, frontmatter, base64, sys
from functools import partial
from datetime import datetime
from tempfile import NamedTemporaryFile
from subprocess import check_call, check_output, STDOUT



# NOTE: this "artifact thing" has a race condition
def create_artifact_file(output_file_path, type, *hash_items):
    if type == 'already-exists':
        return None, True
    s = (''.join(hash_items) + output_file_path)
    fname = os.path.basename(output_file_path) + ':' + type + ":" + hashlib.sha1(s.encode('utf8')).hexdigest()
    artifact_file_path = '/tmp/' + fname
    exists = os.path.exists(artifact_file_path)

    return artifact_file_path, exists


def output_updated_artifact(artifact_file_path, output_file_path):
    os.system(f'cp "{artifact_file_path}" "{output_file_path}"')


@jinja2.pass_context
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

@jinja2.pass_context
def glob_from_file_fn(ctx, fname, rel=None, fmt=None):
    ''' Like globfn, but take one or more glob-patterns from
        a file.
    '''
    ret = []
    home = os.path.dirname(fname)
    with open(fname, 'rt') as src:
        for pattern in src:
            pattern = pattern.strip()
            if not pattern or pattern.startswith('#'):
                continue

            pattern = os.path.join(home, pattern)
            ret.extend(globfn(ctx, pattern, rel=rel, fmt=fmt))

    ret.sort()
    return ret

@jinja2.pass_context
def artifacts_of(ctx, fname, rel=None, fmt=None):
    src = frontmatter.load(fname)
    home = os.path.dirname(fname)
    listing = (os.path.join(home, artifact) for artifact in src.get('artifacts', []))

    if rel is None:
        paths = (Path(f) for f in listing)
    else:
        paths = (Path(f).rel(rel) for f in listing)

    if fmt:
        paths = (f(fmt) for f in paths)

    return list(sorted(paths))

@jinja2.pass_environment
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
    # Encode this in Base64 so we can be sure that the content will
    # *not* be interpreted by Pandoc here but only for the Pandoc Hook
    s = base64.b64encode(s.encode('utf8')).decode('utf8')
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

def as_css_style(**kargs):
    chks = []
    for name, val in kargs.items():
        if val is not None:
            chks.append(f"{name}: {val};")

    if not chks:
        return ''

    style = ' '.join(chks)
    assert '"' not in style
    return f'style="{style}"'

@jinja2.pass_context
def _figures__fig(ctx, src, caption, max_width, width, cls, alt, location, home):
    ''' Generate HTML code to show an image that it is at <src>.

        If <src> is not absolute (see url_from), the image is searched
        in <home>. See the Jinja2 macro of how this <home> is set.

        The <cls> sets the class of the img tag and <alt> is the alternate
        text to show if the image cannot be loaded by the browser.

        The <max_width> sets the maximum width of the image and

        The rest of the parameters are used by put_figure_in_layout()
    '''

    src = url_from(src, home=home)

    if width is None and src.endswith('.svg'):
        # SVG image files are "elastic" by nature. Set them to the full
        # extend of the parent node in the HTML.
        width = '100%'

    # optional style
    style = as_css_style(
        max_width = max_width,
        width = width
        )

    img_cls = cls
    img_html = f'''<img {style} class='{img_cls}' alt='{alt}' src='{src}' />'''

    return put_figure_in_layout(ctx, img_html, caption, cls, location, home)

def put_figure_in_layout(ctx, img_html, caption, cls, location, home):
    ''' Generate HTML code to show a figure defined in the HTML
        <img_html> parameter.

        This HTML could be a <img>, <object> or other thing that makes
        sense.

        The <cls> sets the class of the figure tag (applies to fullfig
        only)

        <caption> is the caption of the image, added after the image or
        next to it depending of the layout (<location>).

        <location> defines the flavour for figure (html code and position):

            - marginfig: the figure goes into the margin with the caption
              below of it
            - fullfig: the figure expands across the whole page with the caption
              below of it. Useful for figures that are really wide.
            - mainfig: the figure expands across the main column with the caption
              in the margin.
    '''

    lbl_cls = 'margin-toggle'
    input_cls = 'margin-toggle'
    span_cls = 'marginnote'
    fig_cls = cls

    id = base64.b64encode((img_html + caption + location).encode('utf8')).decode('utf8')

    if location == 'margin':
        return ensure_html_block(
f'''<p><label for='{id}' class='{lbl_cls}'>&#8853;</label>
<input type='checkbox' id='{id}' class='{input_cls}'/>
<span class='{span_cls}'>
{img_html}''') + \
post_process_by_hook(caption, input_format='markdown', output_format='plain-block') + \
ensure_html_block('''</span></p>''')

    elif location == 'full':
        return ensure_html_block(
f'''<p><figure class='{fig_cls}'>{img_html}
<figcaption>''') +\
post_process_by_hook(caption, input_format='markdown', output_format='plain-block') + \
ensure_html_block('''</figcaption></figure></p>''')

    elif location == 'main':
        return ensure_html_block(
f'''<p><figure><figcaption><span markdown='1'>''') +\
post_process_by_hook(caption, input_format='markdown', output_format='plain-block') + \
ensure_html_block(f'''</span></figcaption>
{img_html}</figure></p>''')
    else:
        assert False


@jinja2.pass_context
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


@jinja2.pass_context
def asset(ctx, src):
    home = ctx.get('assestshome')
    assert home
    return url_from(src, home=home)

@jinja2.pass_context
def img(ctx, src):
    home = ctx.get('imghome')
    assert home
    return url_from(src, home=home)


@jinja2.pass_context
def _diagrams_diag(ctx, fname, source_code, type, max_width, cls, location, home):
    # Drop the "fences" of the code fenced block and split
    # the diagram source code from the caption (this last optional)
    source_code = source_code.strip()
    lines = source_code.split('\n')

    assert lines[0].startswith('```')
    del lines[0]
    separator_at = lines.index('```')
    assert separator_at > 0

    source_code = '\n'.join(lines[:separator_at])
    caption = '\n'.join(lines[separator_at+1:])

    # Location of the final diagram in the web site
    data_path = url_from(fname, home=home)

    # Location of the final diagram in the file system.
    # This is a HACK XXX because we are hardcoding the site location
    file_path = 'out/site/' + data_path
    img_format = os.path.splitext(fname)[1][1:]

    # This is another HACK XXX because j2 does not know when or when not
    # to generate the diagram. Touching the file system in the incorrect
    # moment and Tup will complain.
    #
    # To sort this out we activate the "environment" from j2's command line
    # in the Tupfile and we see this as a variable named ENV. A really
    # dirty hack XXX.
    #
    # The artifact-hack is also another hack to avoid recomputing the same
    # diagram again if the source code didn't change. This speeds up quite
    # a lot the compilation.
    if ctx.get('ENV') != None:
        artifact_file_path, exists = create_artifact_file(file_path, type, source_code, img_format)

        if not exists:
            if type == 'plantuml':
                generate_plantuml_diagram(artifact_file_path, source_code, img_format)
            elif type == 'ditaa':
                generate_ditaa_diagram(artifact_file_path, source_code, img_format)
            elif type == 'dot':
                generate_dot_diagram(artifact_file_path, source_code, img_format)
            else:
                assert False

        # We need to call this even if the artifact didn't require generation
        # This is because Tup will delete the output file before calling us
        # so we are forced to create the output file again. Fortunately,
        # if the artifact file exists, we didn't have to pay the generation
        # cost, only the copy.
        #
        # The type 'already-exists' is a HACK to make _diagrams_diag to not
        # generate any new diagram but to assume that the diagram exists
        # or eventually will exist.
        if type != 'already-exists':
            output_updated_artifact(artifact_file_path, file_path)

    style_for_centering = 'display: block; margin-left: auto; margin-right: auto;'

    # optional style
    style_for_max_width = ''
    if max_width is not None:
        style_for_max_width = f'max-width: {max_width};'

    style = f'style="{style_for_centering}{style_for_max_width}"'

    img_cls = cls

    img_html = f'''<object {style} class='{img_cls}' align='middle' data='{data_path}' type='image/{img_format}+xml'></object>'''

    return put_figure_in_layout(ctx, img_html, caption, cls, location, home)

def generate_plantuml_diagram(artifact_file_path, source_code, img_format):
    with NamedTemporaryFile(delete=False, mode='wt') as f:
        src_fname = f.name
        f.write("@startuml\n")
        f.write(source_code)
        f.write("\n@enduml")

    jar_path = './scripts/x/plantuml-1.2022.0.jar'
    args = '-nometadata'
    try:
        cmd = f"java -Djava.awt.headless=true -jar {jar_path} -t{img_format} {src_fname} {args}".split()
        out = check_output(cmd, stderr=STDOUT)
        if out:
            print(out, file=sys.stderr)
            raise Exception("Plantuml failed")
        os.system(f'mv "{src_fname}.{img_format}" "{artifact_file_path}"')
    finally:
        os.remove(src_fname)


def generate_ditaa_diagram(artifact_file_path, source_code, img_format):
    with NamedTemporaryFile(delete=False, mode='wt') as f:
        src_fname = f.name
        f.write(source_code)

    jar_path = './scripts/x/ditaa.jar'
    args = '--no-shadows --no-separation'
    try:
        cmd = f"java -Djava.awt.headless=true -jar {jar_path} --overwrite --transparent --svg {src_fname} {args}".split()
        out = check_output(cmd, stderr=STDOUT)
        if b'error' in out.lower():
            print(out, file=sys.stderr)
            raise Exception("Ditaa failed")
        patch_ditaa_svg(f"{src_fname}.{img_format}")
        os.system(f'mv "{src_fname}.{img_format}" "{artifact_file_path}"')
    finally:
        os.remove(src_fname)

def patch_ditaa_svg(svg_fname):
    style = '''
      <style type='text/css'>
          /* <![CDATA[ */
              text {
                    fill: black !important;
                    font-family: Consolas, "Liberation Mono", Menlo, Courier, monospace !important;
              }
              path {
                    stroke-width: 1.5 !important;
              }
          /* ]]> */
      </style>
    '''

    script = '''
      <script type="text/javascript">
        <![CDATA[
        setTimeout(function() {
            // make all the "white" closed shapes transparent.
            var paths = document.getElementsByTagName('path');
            for (var i = 0; i < paths.length; i++) {
                var path = paths[i];
                if (path.getAttribute("fill") == "white") {
                    path.setAttribute("fill", "#ffffff00"); // transparent
                }
            }
        }, 1000);
        ]]>
      </script>
    '''
    with open(svg_fname, 'rt') as f:
        svg = f.read()


    r = re.compile(
            r'''width='([0-9]*)'.*?height='([0-9]*)'.*?shape-rendering=''',
            re.DOTALL
            )

    m = r.search(svg)
    width, height = m.group(1), m.group(2)

    fixbox = f" viewBox='0 0 {width} {height}' shape-rendering="
    svg = r.sub(fixbox, svg, count=1)

    svg = svg.replace('<defs>', script + style + '<defs>', 1)

    with open(svg_fname, 'wt') as f:
        f.write(svg)

def generate_dot_diagram(artifact_file_path, source_code, img_format):
    with NamedTemporaryFile(delete=False, mode='wt') as f:
        src_fname = f.name
        f.write(source_code)

    bin_path = 'dot'
    args = ''
    try:
        cmd = f"{bin_path} -T{img_format} -o{src_fname}.{img_format} {args} {src_fname}".split()
        out = check_output(cmd, stderr=STDOUT)
        if out:
            print(out, file=sys.stderr)
            raise Exception("Graphviz failed")
        os.system(f'mv "{src_fname}.{img_format}" "{artifact_file_path}"')
    finally:
        os.remove(src_fname)



# DO NOT RENAME THIS FUNCTION (required by j2cli)
def j2_environment_params():
    # Jinja2 Environment configuration hook
    # http://jinja.pocoo.org/docs/2.10/api/#jinja2.Environment
    return dict()

# DO NOT RENAME THIS FUNCTION (required by j2cli)
def j2_environment(env):
    # Public functions
    env.globals['glob'] = globfn
    env.globals['glob_from_file'] = glob_from_file_fn
    env.globals['asset'] = asset
    env.globals['img'] = img
    env.globals['artifacts_of'] = artifacts_of

    # Private functions called from J2 macros
    env.globals['_figures__fig'] = _figures__fig
    env.globals['_notes__notes'] = _notes__notes
    env.globals['_diagrams_diag'] = _diagrams_diag


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

