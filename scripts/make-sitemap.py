#!/usr/bin/env python3
from xml.dom import minidom

import xml.etree.cElementTree as ET
import sys, yaml, datetime

sitemap_filename, site_filename, *post_metadata_filenames = sys.argv[1:]

with open(site_filename, 'rt') as f:
    site = yaml.safe_load(f.read())

# Expected file format
'''
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
   <url>
      <loc>http://www.example.com/</loc>
      <lastmod>2005-01-01</lastmod>
   </url>
</urlset>
'''


def add_url_entry(root, url, lastmod):
    if not url.startswith("http"):
        print("ERROR!!", url)
        sys.exit(1)

    doc = ET.SubElement(root, "url")
    ET.SubElement(doc, "loc").text = f"{url}"
    ET.SubElement(doc, "lastmod").text = lastmod

root = ET.Element("urlset")
root.attrib['xmlns'] = "http://www.sitemaps.org/schemas/sitemap/0.9"

latest_date = '0000-00-00'
for fname in post_metadata_filenames:
    with open(fname, 'rt') as f:
        post = yaml.safe_load(f.read())

    if 'DRAFT' in post['tags'] or 'HIDDEN' in post['tags']:
        continue

    add_url_entry(root, post['puburl'], post['date'])

    if post['date'] > latest_date:
        latest_date = post['date']

for url in site['sitemap_adds']:
    add_url_entry(root, url, latest_date)

xmlstr = minidom.parseString(ET.tostring(root)).toprettyxml(indent="   ",  encoding='utf-8')
with open(sitemap_filename, "wb") as f:
    f.write(xmlstr)

