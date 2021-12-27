#!/usr/bin/env python3

'''
Read a file with a front matter (yaml) and split it into
two files, one with the content and the other with the metadata.
'''
import frontmatter
import sys, os, yaml

src_filename, content_filename, yaml_filename, site_filename = sys.argv[1:]
with open(src_filename, 'rt') as f:
    post = frontmatter.loads(f.read())

content = post.content

excerpt_end = post.content.find('<!--more-->')
if excerpt_end > 0:
    excerpt = post.content[:excerpt_end]
else:
    excerpt = ''

post['excerpt'] = excerpt

# Set the date of the post from the file and save it into
# metadata
y, m, d, _ = os.path.basename(src_filename).split('-', 3)
post['date'] = '-'.join((y, m, d))


imgs_home = '/img'
post_home = os.path.dirname(os.path.relpath(src_filename, 'posts'))

post['imghome'] = os.path.join(imgs_home, post_home)

with open(site_filename, 'rt') as f:
    site = yaml.safe_load(f.read())

# Add any default for the page from the site config if the given
# post does not override it
for k, v in site.get('page-defaults', {}).items():
    if k not in post:
        post[k] = v

# TODO we must remove this
site.pop('page-defaults', None)

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
for k, v in post.metadata.items():
    tmp.append(f'{k} = {repr(v)}')

metadata_str = ', '.join(tmp)
setpagevars = '{% set page = namespace(' + metadata_str + ') %}\n'

imports = '''
{% from 'z/j2/figures.j2' import marginfig, fullfig, mainfig with context %}
'''

# This is a shortcut. If the post has a 'layout' field in its metadata
# assume that it is the name of a template from which the post wants
# to extend.
#
# The name of the template can be a plain name (like 'post' or a file path
# (like './post.html')
#
# The post's content is modified to inherit from the template and to
# wrap the content of the post in a block named 'content' so the parent
# template can use it.
if 'layout' in post:
    layout_template = post['layout']

    if os.path.sep not in layout_template:
        layout_template = os.path.join('z', 'layouts', layout_template)

        if not os.path.splitext(layout_template)[1]:
            layout_template = os.path.extsep.join((layout_template, 'html'))

    extends = '{% extends "' + layout_template + '" %}\n'
    block_begin = '{% block content %}\n'
    block_end = '{% endblock content %}\n'

    content = extends + setpagevars + setsitevars + imports + block_begin + content + block_end
else:
    content = setpagevars + setsitevars + imports + content

with open(content_filename, 'wt') as f:
    f.write(content)

post.content = ''
metadata = frontmatter.dumps(post)
# strips the "---" that delimit a yaml document
metadata = '\n'.join(metadata.split('\n')[1:-1])
with open(yaml_filename, 'wt') as f:
    f.write(metadata)
