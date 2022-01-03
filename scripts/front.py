#!/usr/bin/env python3

'''
Read a file with a front matter (yaml) and split it into
two files, one with the content and the other with the metadata.
'''
import frontmatter
import sys, os, yaml

src_filename, content_filename, excerpt_filename, yaml_filename, site_filename = sys.argv[1:]

# Load site's configuration
with open(site_filename, 'rt') as f:
    site = yaml.safe_load(f.read())

# Read the source file
with open(src_filename, 'rt') as f:
    page = frontmatter.loads(f.read())


# Add any default for the page from the site config if the given
# page does not have a value for it
for k, v in site.get('page_defaults', {}).items():
    if k not in page:
        page[k] = v

# We don't want to expose this any further. Removing it.
site.pop('page_defaults', None)


# Extract the 'excerpt', a kind of summary if such
# exists.
excerpt_token = page['excerpt_token']
excerpt_end = page.content.find(excerpt_token)
if excerpt_end > 0:
    excerpt = page.content[:excerpt_end]
else:
    excerpt = ''

page['excerpt_file'] = excerpt_filename
page['raw_excerpt'] = excerpt


# Read source file content (without the metadata)
content = page.content


# Post pages are special.
ispost = page['ispost']

# Set the date of the page from the file and save it into
# metadata.
#
# This is only for post pages
if ispost:
    y, m, d, _ = os.path.basename(src_filename).split('-', 3)
    page['date'] = '-'.join((y, m, d))

# Set the home of the image and assets for this page
# This will be the same folder structure that the page has
# but without the root folder (posts/ for posts, pages/ for index)
#
# Eg:
#   for pages/foo/bar.md you will get /img/foo/ and /assets/foo/
rel_folder = 'posts/' if ispost else 'pages/'
page_home = os.path.dirname(os.path.relpath(src_filename, rel_folder))
for name, home in zip(('imghome', 'assestshome'), ('/img', '/assets')):
    page[name] = os.path.join(home, page_home)


# Load all the site config into the template
tmp = []
for k, v in site.items():
    tmp.append(f'{k} = {repr(v)}')

metadata_str = ', '.join(tmp)
setsitevars = '{% set site = namespace(' + metadata_str + ') %}\n'



# Make the metadata available in the template as
# a Jinja Namespace under the name 'page'.
# This is a handy object so the keys can be accessed
# as page.foo in addition to the traditional page['foo'].
tmp = []
for k, v in page.metadata.items():
    tmp.append(f'{k} = {repr(v)}')

metadata_str = ', '.join(tmp)
setpagevars = '{% set page = namespace(' + metadata_str + ') %}\n'

# The page is not an excerpt (that will be for later)
setexcerptvar = '{% set isexcerpt = False %}\n'

# Define which macros will be imported by default
imports = '''
{% from 'z/j2/figures.j2' import marginfig, fullfig, mainfig with context %}
{% from 'z/j2/notes.j2' import marginnotes, spoileralert with context %}
'''

# If the page has a 'layout' field in its metadata
# assume that it is the name of a template from which the page wants
# to extend.
#
# The name of the template can be a plain name (like 'page' or a file path
# (like './page.html')
#
# The page's content is modified to inherit from the template and to
# wrap the content of the page in a block named 'content' so the parent
# template can use it.
if 'layout' in page:
    layout_template = page['layout']

    if os.path.sep not in layout_template:
        layout_template = os.path.join('z', 'layouts', layout_template)

        if not os.path.splitext(layout_template)[1]:
            layout_template = os.path.extsep.join((layout_template, 'html'))

    extends = '{% extends "' + layout_template + '" %}\n'
    block_begin = '{% block content %}\n'
    block_end = '\n{% endblock content %}\n'

    content = extends + setpagevars + setsitevars + setexcerptvar + imports + block_begin + content + block_end
else:
    content = setpagevars + setsitevars + setexcerptvar + imports + content

# Finally, write down the page content (without the metadata)
with open(content_filename, 'wt') as f:
    f.write(content)


# Like the page content, add the variables/imports to the excerpt
# and save it
# Here we override 'isexcerpt' to True because it *is* an excerpt
setexcerptvar = '{% set isexcerpt = True %}\n'
excerpt = setpagevars + setsitevars + setexcerptvar + imports + excerpt
with open(excerpt_filename, 'wt') as f:
    f.write(excerpt)


# Write the metadata in a separated file.
page.content = ''
metadata = frontmatter.dumps(page)
# strips the "---" that delimit a yaml document
metadata = '\n'.join(metadata.split('\n')[1:-1])
with open(yaml_filename, 'wt') as f:
    f.write(metadata)

