#!/usr/bin/env python3

from feedgen.feed import FeedGenerator
import sys, yaml, datetime

rss_filename, atom_filename, site_filename, *post_metadata_filenames = sys.argv[1:]

with open(site_filename, 'rt') as f:
    site = yaml.safe_load(f.read())


fg = FeedGenerator()
fg.id(site['url'])
fg.title(site['title'])
fg.author(name=site['author'], email=site['email'])
fg.link(href=site['url'], rel='alternate')
fg.description(site['description'])
fg.language('en')

for fname in post_metadata_filenames:
    with open(fname, 'rt') as f:
        post = yaml.safe_load(f.read())

    if 'DRAFT' in post['tags'] or 'HIDDEN' in post['tags']:
        continue

    fe = fg.add_entry()
    fe.title(post['title'])
    fe.link(href=post['url'], title=post['title'], rel='alternate', type="text/html")
    fe.id(post['url'])

    date = datetime.datetime.strptime(post['date'], '%Y-%m-%d')
    date = date.replace(tzinfo=datetime.timezone.utc)

    fe.published(date)
    fe.updated(date)

    fe.content(open(post['refs']['content-html'], 'rt').read(), type="html")

    for cat in post['tags']:
        fe.category(term=cat, label=cat)

    fe.author(name=site['author'])


fg.link(href=site['url'] + '/' + site['name_atom'], rel='self')
fg.atom_file(atom_filename, extensions=False, pretty=True)

fg.link(href=site['url'] + '/' + site['name_rss'], rel='self')
fg.rss_file(rss_filename, extensions=False, pretty=True)
