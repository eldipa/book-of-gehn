const fs = require('fs');
const path = require('path');
const child_process = require("child_process");
const lunr = require('lunr');

const target_dir = process.argv[2];
const listing = child_process.execSync(`find ${target_dir} -name '*.md'`, {'maxBuffer':128*1024*1024});

const fnames = listing.toString().split(/(?:\r\n|\r|\n)/g);
fnames.sort();

// Go from a file name to the name of a URL
//
// Go from "../_posts/2016-12-18-Forensics-911-recovering-thesis.md"
// to "2016/12/18/Forensics-911-recovering-thesis.html"
function to_url_name(fname) {
    fname = path.basename(fname);

    for (var i = 0; i < 3; ++i) {
        fname = fname.replace("-", "/");
    }

    return fname.replace(/[.]md$/, ".html");
}

var ref2doc = {};
var id = 0;
var doc_count = 0;
var not_indexed = [];
const lunr_idx = lunr(function () {
    this.ref('id');
    this.field('content');

    fnames.forEach(function (fname) {
        if (!fname) {
            return;
        }

        const lines = fs.readFileSync(fname, 'utf8').split(/\r?\n/)

        let tags_str = "";
        let title_str = "";
        if (lines[0].startsWith('---')) {
            let ix = 1;
            // Try to find the title of the post and its tags *before*
            // reaching the end of the "front-matter" section (marked
            // with at least three '-')
            while (lines[ix] !== undefined && !lines[ix].startsWith('---')) {
                if (lines[ix].startsWith('tags:')) {
                    tags_str += lines[ix].substring(5) + " ";
                }
                else if (lines[ix].startsWith('title:')) {
                    title_str += lines[ix].substring(6) + " ";
                }

                if (tags_str && title_str)
                    break;

                ix += 1;
            }
        }

        const content_for_indexing = title_str + " " + tags_str;
        process.stderr.write("- " + fname + ": " + content_for_indexing + "\n");

        if (content_for_indexing) {
            const elem = {
                "id": id,
                "content": content_for_indexing
            };

            this.add(elem);
            ref2doc[id] = {
                'title': title_str,
                'path': to_url_name(fname)
            };

            id++;
            doc_count++;
        } else {
            not_indexed.push(fname);
        }
    }, this);
});

// Warn about files that where not indexed
if (not_indexed.length > 0) {
    process.stderr.write("\n\n[Warn] Not indexed:\n");
    not_indexed.forEach(function (fname) {
        process.stderr.write("- " + fname + "\n");
    });
}

const idx = {
    // Map lunr documents' ids to our documents
    'ref2doc': ref2doc,
    // This is the lunr's index
    'lunr_idx': lunr_idx
};


// Store the index as a valid Javascript statement (literal)
// so it can be included with <script src="..."> by the web page
const idx_str = JSON.stringify(idx)
process.stdout.write('const blog_search_index = ');
process.stdout.write(idx_str);
process.stdout.write(';');

// Testing: reload the serialized index, search for a word
// and print the matching posts.
const idx2 = JSON.parse(idx_str);
idx2.lunr_idx = lunr.Index.load(idx2.lunr_idx);

const found = idx2.lunr_idx.search("+arm +qemu");
found.forEach(function (match) {
    process.stderr.write(idx2.ref2doc[match.ref].path + "\n");
    process.stderr.write(JSON.stringify(match, null, 2) + "\n");
}, this);
