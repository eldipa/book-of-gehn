const fs = require('fs');
const path = require('path');
const child_process = require("child_process");
const lunr = require('lunr');

const target_dir = process.argv[2];
const listing = child_process.execSync(`find ${target_dir} -name *.md`, {'maxBuffer':128*1024*1024});

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

var ref2path = {};
var id = 0;
const lunr_idx = lunr(function () {
    this.ref('id');
    this.field('content');

    fnames.forEach(function (fname) {
        if (!fname) {
            return;
        }

        process.stderr.write("- " + fname + "\n");
        const doc = {
            "id": id,
            "content": fs.readFileSync(fname, 'utf8')
        };

        this.add(doc);
        ref2path[id] = to_url_name(fname);

        id++;
    }, this);
});

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
process.stdout.write(idx_str);

const idx2 = JSON.parse(idx_str);
idx2.lunr_idx = lunr.Index.load(idx2.lunr_idx);


const found = idx2.lunr_idx.search("arm");
found.forEach(function (match) {
    process.stderr.write(idx2.ref2path[match.ref] + "\n");
    process.stderr.write(JSON.stringify(match, null, 2) + "\n");
}, this);
