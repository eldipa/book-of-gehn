#!/usr/bin/env python3

from panflute import (run_filters, Code, Header, Str, Para, Space,
RawInline, Plain, Link, CodeBlock, RawBlock, convert_text, Table, Div,
Caption)

import sys, os, base64

trace_file=None

from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments import highlight as highlight_code

from candombe_style import CandombeStyle, NoStyle

def set_language_for_inline_code(elem, doc):
    ''' Takes an inline code and mark it as C++/Python/whatever code if
        no other language was specified.

        This applies to only the Markdown text `foo` (backticks)
        if and only if no other class was set like in `bar`{.java}

        Exactly which language will be set by default is based on
        the 'inline_default_language' metadata variable.

        In the example bellow we assume inline_default_language==cpp:

        Example:
        In Markdown     -->    After filtering
        `char*`         -->    `char*`{.cpp}
        `bool`{.java}   -->    `bool`{.java}

    '''

    if type(elem) == Code and not elem.classes:
        default = doc.get_metadata('inline_default_language', default='')
        if default:
            elem.classes.append(default)


def highlight_code_inline_and_blocks_with_pygments(elem, doc):
    ''' Take Code and CodeBlock items and highlight their context
        using pygments.

        One and only 1 class is expected. This class can contain
        attributes separated by semicolons.

        Think in

        ```python;showlinenums;startfrom=3
        >>> def bar():
        ...     pass
        ```

        Pandoc supports arbitrary attributes with the following syntax

        ```{.python .showlinenums startfrom=3}
        >>> def bar():
        ...     pass
        ```

        However the latter syntax is not recognized by Vim or other
        editors and the syntax highlight in the editor looks terrible.

        The former syntax, being a hack, is preferred and currently
        the ONLY supported for now.
    '''
    if type(elem) in {CodeBlock, Code} and elem.classes:
        lexer = None
        lang, *tmp = elem.classes[0].split(';')
        if lang == 'none':
            return # TODO

        # Map [showlinenums startfrom=3] to {showlinenums: True, startfrom: 3}
        key_values = [kv.split('=', 1) for kv in tmp]
        attributes = dict(kv if len(kv) == 2 else (kv[0], True) for kv in key_values)
        attributes.update(dict((cls, True) for cls in elem.classes))
        attributes.update(elem.attributes)

        if attributes.get('mathjax', False):
            return wrap_code_with_mathjax_tags(elem, doc, attributes)

        # Find a lexer to parse the syntax. Return the element as is
        # if no such lexer exist
        try:
            lexer = get_lexer_by_name(lang)
        except:
            pass

        if not lexer:
            return elem

        code = elem.text

        print("===> Elem attrs", elem.attributes, file=trace_file)
        print("===> Var attrs", attributes, file=trace_file)
        default_cssclass = 'highlight-candombe-inline' if type(elem) == Code else 'highlight-candombe'
        ops = {
                'cssclass' : attributes.get('cssclass', default_cssclass)
                }
        print("===> Ops", ops, file=trace_file)

        if type(elem) == Code:
            # We don't want to wrap the code with <div> and <pre> which
            # will break the layout/flow of the web page.
            # Instead we add a <span> manually later
            ops['nowrap'] = True

        formatter = HtmlFormatter(
                style=CandombeStyle,
                # Wrap the code with the tags <code> and </code> as it is
                # recommended by the HTML standard
                wrapcode=True,
                **ops
                )

        code_h = highlight_code(code, lexer, formatter)

        if type(elem) == Code:
            # We wrap the code with a non-layout-breaking container: <span>
            # Here we apply the style (cssclass).
            #
            # In a CodeBlock, we can relay on the <div> and <pre> tags
            # added by Pygments to have the correct style but for the
            # Code (inline) we need to do this by hand.
            code_h = f'<code><span class="{ops["cssclass"]}">{code_h.rstrip()}</span></code>'

            # Because the code is not wrapped with <pre> because it
            # breaks the layout of the webpage, if required we can add
            # a <span> with the class 'pseudo-pre' to "emulate" it via
            # CSS
            if attributes.get('wrap-with-pseudo-pre', False):
                code_h = '<span class="pseudo-pre">' + code_h + '</span>'

            return RawInline(text=code_h, format='html')
        elif type(elem) == CodeBlock:
            return RawBlock(text=code_h, format='html')
        else:
            assert False

def wrap_code_with_mathjax_tags(elem, doc, attributes):
    if type(elem) not in {CodeBlock, Code}:
        assert False

    if type(elem) == Code:
        return RawInline(text=r"\("+elem.text+r"\)", format='html')
    elif type(elem) == CodeBlock:
        return RawBlock(text="$$"+elem.text+"$$", format='html')
    else:
        assert False

def post_process_by_hook(elem, doc):
    ''' Perform a post-processing of the CodeBlock if it is marked
        for such thing (class 'post_process_by_hook').

        Currently the post-processing consists in converting the block
        text in something else with Panflute's convert_text.

        For example a Markdown can be converted to HTML.

        CodeBlock's expected attributes:
         - input_format: the format of the input (CodeBlock's text) (markdown)
         - output_format: currently only supported 'plain-block'
    '''
    if type(elem) in {CodeBlock} and elem.classes:
        if 'post_process_by_hook' not in elem.classes:
            return elem

        elem.classes.remove('post_process_by_hook')

        # The content of the post_process_by_hook is always in base64
        # to avoid the need to escape any character that could confuse
        # Pandoc before reaching us.
        elem_text = base64.b64decode(elem.text.encode('utf8')).decode('utf8')
        elems = convert_text(elem_text, input_format=elem.attributes['input_format'])

        if not elems:
            return

        # Plain block means: convert all the paragraphs in Plain texts
        # and separate them with <br /> breaks.
        # Visually should be the same but this output format is suitable
        # when the final location of the text cannot contain paragraphs.
        #
        # An exception to this are the CodeBlock which are passed as
        # they are
        assert elem.attributes['output_format'] == 'plain-block'

        newelems = []
        for el in elems:
            assert type(el) in {Para, CodeBlock}
            if type(el) == Para:
                newelems.append(Plain(*el.content))
            elif type(el) == CodeBlock:
                inline = Code(
                        text=el.text,
                        identifier=el.identifier,
                        classes=el.classes,
                        attributes=el.attributes
                        )

                # Set the attributes to mimic the style of a CodeBlock
                inline.attributes['cssclass'] = 'highlight-candombe'
                inline.attributes['wrap-with-pseudo-pre'] = 'pseudo-pre'
                newelems.append(Plain(inline))

            else:
                assert False
            newelems.append(RawBlock('<br /><br />', format='html'))

        # Drop last <br /><br />
        del newelems[-1]

        return newelems

def wrap_table_into_div(elem, doc):
    if type(elem) not in {Table}:
        return

    attributes = []

    # Search for the first Plain Str of the Caption and see if it starts
    # with {...}.
    # It it does, assume that it is a Pandoc Attributes syntax and parse
    # it.
    if elem.caption.content and type(elem.caption.content[0]) in {Plain}:
        tmp = elem.caption.content[0].content[0].text
        if tmp.startswith('{') and tmp.find('}') > 0:
            attributes = tmp[1:tmp.find('}')].split()
            tmp = tmp[tmp.find('}')+1:]

            # Remain something?
            if tmp:
                elem.caption.content[0].content[0].text = tmp
            else:
                del elem.caption.content[0].content[0]

    if ".fullwidth" in attributes:
        return Div(elem, classes=["fullwidth"])

    return Div(elem, classes=["table-wrapper"])

def what(elem, doc):
    ''' Debugging / exploring / tracing. '''
    global trace_file
    if trace_file is None:
        fname = os.getenv("PANFLUTE_TRACE_FILENAME", 'unknown.panflute-trace')
        trace_file = open(fname, 'wt')

    print(type(elem), file=trace_file)
    if type(elem) in {Table, Caption}:
        print("-----", elem, "-----", file=trace_file)
        print(dir(elem), getattr(elem, 'classes', None), getattr(elem, 'attributes', None), file=trace_file)
        print(doc, file=trace_file)

    #if type(elem) in {Str}:
    #    print(elem, file=trace_file)

    #if type(elem) == Link:
    #    print(elem, file=trace_file)

if __name__ == '__main__':
    try:
        run_filters([
            what,
            wrap_table_into_div,
            post_process_by_hook,
            set_language_for_inline_code,
            highlight_code_inline_and_blocks_with_pygments,
            ])
    finally:
        if trace_file is not None:
            trace_file.close()
