$(document).ready(function () {
var create_html_text_for_post = function create_html_text_for_post (doc) {
    const txt = `
        <span class="index-single-post">
            <a href="articles/${doc.path}">
                <h3 class="larger">${doc.title}</h2>
            </a>
        </span>
        `

    return txt;
}

const blog_search_lunr_idx = lunr.Index.load(blog_search_index.lunr_idx);

var searchForm = document.querySelector('#blog-search-form'),
    searchField = searchForm.querySelector('input')

$('#search_results').hide();
$('#reset_search').hide();

searchForm.addEventListener('reset', function (event) {
    $('#search_error').empty();
    $('#search_error').hide();

    $('#search_results').empty();
    $('#search_results').hide();

    $('#reset_search').hide();
    $('#article_main_group').show();
})

filterPostsByQuery = function (query) {
    $('#search_error').empty();

    var results = undefined,
        search_results = $('#search_results')

    if (!query)
        return;

    $('#article_main_group').hide();
    $('#reset_search').show();

    try {
        results = blog_search_lunr_idx.search(query)
    } catch(e) {
        if (e instanceof lunr.QueryParseError) {
            $('#search_error').append(`<p>Sorry, I couldn't understand you: "syntax error".</p>`);
            $('#search_error').show();
            return
        } else {
            throw e
        }
    }

    if (results.length == 0) {
        $('#search_error').append(`<p>Sorry, I couldn't find any post.</p>`);
        $('#search_error').show();
        return
    }

    search_results.empty();

    results.forEach(function (result) {
        var doc = blog_search_index.ref2doc[result.ref],
            txt = create_html_text_for_post(doc)

        search_results.append(txt);
    })
    search_results.show();
};

searchForm.addEventListener('submit', function (event) {
    event.preventDefault()

    var query = searchField.value

    filterPostsByQuery(query)
})
});
