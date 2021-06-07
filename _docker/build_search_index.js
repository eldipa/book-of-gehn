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


/*
 * The following was a serie of filters to remove words before indexing them
 * but now that we use the tags of each post, we want to index all the words
 * in the tags.
 *
// Things like:
//  123
//  0.1
//  2*3
//  1..
//  1**
const num_like_regex = /\d[\d*.]+/;
const max_token_len = 40;

// Things like:
//  123
//  _foo
//  ___
//  _@.
//  f@b
const word_like_regex = /^[\w_.@:]*$/;

const split_token_regex = /[_.@:]/;
function filter_spurious_token(token, pos, all_tokens) {
    const str = token.str;

    // reject
    if (str.length >= max_token_len)
        return null;

    const substrs = str.split(split_token_regex);
    const filtered_tokens = [];
    substrs.forEach((substr) => {
        // reject
        if (substr.length <= 1)
            return

        // reject
        if (num_like_regex.test(substr))
            return;

        // allow
        if (!word_like_regex.test(substr))
            return;

        filtered_tokens.push(new lunr.Token(substr, token.metadata));
    });

    // Note: we can return 'null' to remove the token;
    // we can return an array of tokens (to replace 1 by N);
    // or we can return a string for a simple replacement (1 by 1).
    return filtered_tokens;
}

function remove_spurious_tokens_plugin(builder) {
    // We *don't* register the pipeline function: this will give us
    // a warning because the function will not be unserialized properly.
    // It is okay because we want (and *must*) remove this function
    // from the pipeline *after* building the index (we want to apply
    // the filter during the index creation, not during the query time)
    // lunr.Pipeline.registerFunction(filter_spurious_token, 'filter_spurious_token');

    // Apply this filter after doing the stop-words phase
    builder.pipeline.after(lunr.stopWordFilter, filter_spurious_token);
}

*/

var ref2path = {};
var id = 0;
var doc_count = 0;
const lunr_idx = lunr(function () {
    // Enable the plugin to remove any token that is just garbage
    // Not longer needed
    // this.use(remove_spurious_tokens_plugin);

    this.ref('id');
    this.field('content');

    fnames.forEach(function (fname) {
        if (!fname) {
            return;
        }

        const lines = fs.readFileSync(fname, 'utf8').split(/\r?\n/)

        let tags_str = "";
        if (lines[0].startsWith('---')) {
            let ix = 1;
            while (lines[ix] !== undefined && !lines[ix].startsWith('---')) {
                if (lines[ix].startsWith('tags:')) {
                    tags_str = lines[ix].substring(5);
                    break;
                }
                ix += 1;
            }
        }

        process.stderr.write("- " + fname + ": " + tags_str + "\n");

        if (tags_str) {
            const doc = {
                "id": id,
                "content": tags_str
            };

            this.add(doc);
            ref2path[id] = to_url_name(fname);

            id++;
            doc_count++;
        }
    }, this);
});

// We don't want to use this filter during the query time
// Not longer needed
// lunr_idx.pipeline.remove(filter_spurious_token);

/*
const inv = lunr_idx.invertedIndex;
for (const term of Object.keys(inv)) {
    const doc_indexed_by_this_term = Object.keys(inv[term]).length * 1.0;
    if (doc_indexed_by_this_term / doc_count > 0.0001) {
        process.stderr.write(term + "\n");
    }
}
process.stderr.write(JSON.stringify(lunr_idx.invertedIndex['arm'], null, 2) + "\n");
process.stderr.write(`----> ${Object.keys(inv).length}\n`);
*/

const idx = {
    // Map lunr documents' ids to URL paths
    'ref2path': ref2path,
    // This is the lunr's index
    'lunr_idx': lunr_idx
};


// https://github.com/olivernn/lunr.js/issues/316
/*
function pruneIndex (index) {
  const empty = {}
  const handler = {
    get: function (target, name, receiver) {
      return target[name] || empty
    }
  }

  for (const key of Object.keys(index.invertedIndex)) {
    const val = index.invertedIndex[key]
    for (const field of Object.keys(val)) {
      if (field === '_index') {
        continue
      }

      if (Object.keys(val[field]).length === 0) {
        delete val[field]
      }
    }
    index.invertedIndex[key] = new Proxy(val, handler)
  }
}


function prune_objects_key(object, key, handler) {
    const val = object[key];
    var pruned = false;
    for (const val_key of Object.keys(val)) {
        if (typeof val[val_key] != 'object' || val[val_key] === null) {
            continue;
        }

        if (Object.keys(val[val_key]).length == 0) {
            delete val[val_key];
            pruned = true;
        }
        else {
            prune_objects_key(val, val_key, handler);
        }
    }

    if (pruned) {
        object[key] = new Proxy(val, handler);
    }

    return pruned
}

function prune_index (index) {
  const empty = {}
  const handler = {
    get: function (target, name, receiver) {
      return target[name] || empty
    }
  }

  prune_objects_key(index, 'invertedIndex', handler);
}
*/


const idx_str = JSON.stringify(idx)
process.stdout.write('const blog_search_index = ');
process.stdout.write(idx_str);
process.stdout.write(';');

const idx2 = JSON.parse(idx_str);
idx2.lunr_idx = lunr.Index.load(idx2.lunr_idx);


const found = idx2.lunr_idx.search("arm");
found.forEach(function (match) {
    process.stderr.write(idx2.ref2path[match.ref] + "\n");
    process.stderr.write(JSON.stringify(match, null, 2) + "\n");
}, this);
