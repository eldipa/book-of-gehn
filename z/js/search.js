$(document).ready(function () {

const blog_search_lunr_idx = lunr.Index.load(blog_search_index.lunr_idx);

var searchForm = document.querySelector('#blog-search-form'),
    searchField = searchForm.querySelector('input')

$('#reset_search').hide();
$('#search_msg').hide();

searchForm.addEventListener('reset', function (event) {
    $('#search_msg').empty();
    $('#search_msg').hide();

    $('#reset_search').hide();
    $('.index-single-post').show();
})

filterPostsByQuery = function (query) {
    $('#search_msg').empty();

    var results = undefined;

    if (!query)
        return;

    $('#reset_search').show();

    try {
        results = blog_search_lunr_idx.search(query)
    } catch(e) {
        if (e instanceof lunr.QueryParseError) {
            $('#search_msg').append(`<p>Sorry, I couldn't understand you: "syntax error".</p>`);
            $('#search_msg').show();
            return
        } else {
            throw e
        }
    }

    if (results.length == 0) {
        $('#search_msg').append(`<p>Sorry, I couldn't find any post.</p>`);
        $('#search_msg').show();
        return
    }

    $('.index-single-post').hide();

    results.forEach(function (result) {
        var doc = blog_search_index.ref2doc[result.ref],
            post_id = doc.post_id;

        $('#'+post_id).show();
    });

    var plural = "";
    if (results.length > 1) {
        plural = "s"
    }

    $('#search_msg').append(`<p>I found ${results.length} post${plural}.</p>`);
    $('#search_msg').show();
};

searchForm.addEventListener('submit', function (event) {
    event.preventDefault()

    var query = searchField.value

    filterPostsByQuery(query)
})
});
