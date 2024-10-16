#!/usr/bin/env python3

"""Module for calling mdslides as an executable."""

'''
MIT License

Copyright (c) 2020 da_doomer - https://gitlab.com/da_doomer/markdown-slides
Copyright (c) 2024 eldipa - https://book-of-gehn.github.io/

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

from pathlib import Path
import sys
import shutil
import re
from typing import List, Union

import subprocess


SUPPORTED_BROWSERS = ["chromium"]


def pdf_chromium_export(index_html_path: Path, output_pdf_path: Path):
    """Use Chromium to export an HTML file to PDF. On failure raises
    `subprocess.CalledProcessError`."""
    command = [
        'chromium',
        '--headless',
        '--print-to-pdf={}'.format(output_pdf_path),
        index_html_path.resolve().as_uri()+'?print-pdf',
    ]
    subprocess.run(command, check=True)


def export(index_html_path: Path, output_pdf_path: Path):
    """Export an HTML file to PDF."""
    try:
        pdf_chromium_export(index_html_path, output_pdf_path)
    except subprocess.CalledProcessError as exception:
        print("PDF exporting failed")
        print(exception)
        print(
                "Make sure a supported browser is installed and in your path"
                f" {SUPPORTED_BROWSERS}"
            )

DATA_WORD = "DATA"
TITLE_WORD = "TITLE"
OPTIONS_WORD = "Reveal.initialize({"
THEME_WORD = '<link rel="stylesheet" href="dist/theme'
CODE_THEME_WORD = '<link rel="stylesheet" href="plugin/highlight'

TITLE_TEMPLATE = "<title>{}</title>"
SECTION_TEMPLATE = "<section data-markdown {}><textarea data-template>\n{}\n</textarea></section>"
VERTICAL_SECTION_TEMPLATE = "<section>\n{}\n</section>"
THEME_TEMPLATE = '<link rel="stylesheet" href="dist/theme/{}.css" id="theme">'
CODE_THEME_TEMPLATE = '<link rel="stylesheet" href="plugin/highlight/{}.min.css" id="highlight-theme">'

# Read both comment formats (first one is CommonMark compliant, second one
# is common format).
# [comment]: (stuff)
# [comment]: "stuff"
# [comment]: 'stuff'
RE_TEMPLATE = r"\[comment\]: # [(\"\']{0}[)\"\']"
OPTION_RE_PATTERN = r"[ ]*(\S+)[ ]*:[ ]*(\S+)[ ]*"
DELIMITER_RE_PATTERN = r"\!\!\![ ]*(.*)"
VERTICAL_DELIMITER_RE_PATTERN = r"\|\|\|[ ]*(.*)"
THEME_RE_PATTERN = r"[ ]*THEME[ ]*=[ ]*(\S+)[ ]*"
CODE_THEME_RE_PATTERN = r"[ ]*CODE_THEME[ ]*=[ ]*(\S+)[ ]*"
TITLE_RE_PATTERN = r"#[#]*[ ]*(.*)"
option_re = re.compile(RE_TEMPLATE.format(OPTION_RE_PATTERN))
delimiter_re = re.compile(RE_TEMPLATE.format(DELIMITER_RE_PATTERN))
vertical_delimiter_re = re.compile(RE_TEMPLATE.format(VERTICAL_DELIMITER_RE_PATTERN))
theme_re = re.compile(RE_TEMPLATE.format(THEME_RE_PATTERN))
code_theme_re = re.compile(RE_TEMPLATE.format(CODE_THEME_RE_PATTERN))
title_re = re.compile(TITLE_RE_PATTERN)

DEFAULT_ATTRIBUTES = ""
DEFAULT_THEME = "white"
DEFAULT_CODE_THEME = "base16/zenburn"
DEFAULT_OPTIONS = {
        "controls": "false",
        "markdown": "{smartypants: true}",
    }


def build_slides(
        markdown_file: Path,
        include_paths: List[Path],
        output_file: Path,
        ):
    """Build slides in the given markdown file."""
    resource_path = Path(__file__).parent.absolute()

    index_file_original = resource_path/"index_template.html"

    # Open markdown file
    with open(markdown_file) as f_p:
        presentation_markdown = list(f_p)

    # Build presentation
    presentation = list()
    slide: List[str] = list()
    vertical_slide: List[str] = list()
    options = ["{} : {},".format(key, val)
               for key, val in DEFAULT_OPTIONS.items()]
    theme = DEFAULT_THEME
    code_theme_name = DEFAULT_CODE_THEME
    attributes = DEFAULT_ATTRIBUTES
    title = None

    verbatim_intro = []

    first_header_found = False
    for line in presentation_markdown:
        line = line[:-1]

        # Anything before the first HEADER is passed verbatim
        if not first_header_found and title_re.match(line) == None:
            verbatim_intro.append(line)
            continue
        else:
            first_header_found = True

        # Is the line setting an option?
        match = option_re.match(line)
        if match is not None:
            options.append("{} : {},".format(match.group(1), match.group(2)))
            continue

        # Is the line a slide break?
        match = delimiter_re.match(line)
        if match is not None:
            attributes = DEFAULT_ATTRIBUTES + " " + match.group(1)
            if vertical_slide:
                vertical_slide.append(
                    SECTION_TEMPLATE.format(attributes, "\n".join(slide))
                )
                presentation.append(
                    VERTICAL_SECTION_TEMPLATE.format("\n".join(vertical_slide))
                 )
                vertical_slide = list()
            else:
                presentation.append(
                    SECTION_TEMPLATE.format(attributes, "\n".join(slide))
                )
            slide = list()
            continue

        # Is the line a vertical slide break?
        match = vertical_delimiter_re.match(line)
        if match is not None:
            attributes = DEFAULT_ATTRIBUTES + " " + match.group(1)
            vertical_slide.append(
                SECTION_TEMPLATE.format(attributes, "\n".join(slide))
            )
            slide = list()
            continue

        # Is the line setting a theme?
        match = theme_re.match(line)
        if match is not None:
            theme = match.group(1)
            continue

        # Is the line setting a code theme?
        match = code_theme_re.match(line)
        if match is not None:
            code_theme_name = match.group(1)
            continue

        # Is the line the first heading?
        match = title_re.match(line)
        if match is not None:
            header = match.group(1)
            if title is None:
                title = header

        # Else, we assume the line is markdown
        slide.append(line)

    # Did the user forget to insert the final slide break?
    if vertical_slide:
        presentation.append(
            VERTICAL_SECTION_TEMPLATE.format("\n".join(vertical_slide))
         )
    if len(slide) > 0 and any(l.strip() for l in slide):
        presentation.append(
                SECTION_TEMPLATE.format(DEFAULT_ATTRIBUTES, "\n".join(slide))
            )

    # Replacement strings
    if title is None:
        title = "Slides"
    title = TITLE_TEMPLATE.format(title)
    presentation_str = "\n".join(verbatim_intro + presentation + [""])
    options_str = "\n".join([OPTIONS_WORD] + options + [""])
    theme = THEME_TEMPLATE.format(theme)
    code_theme = CODE_THEME_TEMPLATE.format(code_theme_name.split("/")[-1])

    with open(output_file, "w") as f_p:
        f_p.write(presentation_str)

if __name__ == "__main__":

    assert(len(sys.argv) == 3)
    _, markdown_file, output_file = sys.argv
    build_slides(
            markdown_file = Path(markdown_file),
            include_paths = [],
            output_file=Path(output_file),
        )
