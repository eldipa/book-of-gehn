#!/bin/bash
set -e
set -o pipefail

if [ "$#" != 3 ]; then
    echo "Invalid number of arguments: $#."
    echo "Usage: $0 <input markdown> <input yaml> <output html>"
    exit 1
fi


. scripts/x/run_in_docker.sh

# This is the way that we have to communicate to Panflute's filter
# which file must log
mkdir -p dbg/
export PANFLUTE_TRACE_FILENAME="dbg/$(basename "$3").panflute-trace"

mkdir -p "$(dirname $3)"
pandoc                                                                      \
    `# Disable the syntax highlighting. We use Pygments for that`           \
    `# called from Panflute hook. We that we have much more control over`   \
    `# the HTML code generated and the style.`                              \
    --no-highlight                                                          \
                                                                            \
    `# Pass the metadata file (Front Matter) so we can access it through`   \
    `# Panflute's doc.get_metadata() function to customize the hooks.`      \
    --metadata-file "$2"                                                    \
                                                                            \
    `# Set the Panflute hooks file. After Pandoc parsed the input Markdown` \
    `# but before generating the output HTML, the parsed tokens/elements`   \
    `# are passed through the hooks in a way to filter them, change them`   \
    `# or add more of them effectively changing/tweaking the final output`  \
    -F scripts/x/panflute_hooks.py3 \
                                                                            \
    `# Set as the input file Markdown and disable any Latex/Tex/Math`       \
    `# symbols. We are going to use MathJax for render those on the browser`\
    `# side.`                                                               \
    -f markdown-tex_math_dollars-tex_math_single_backslash-tex_math_double_backslash \
    -t html \
    -o "$3" \
    "$1"
