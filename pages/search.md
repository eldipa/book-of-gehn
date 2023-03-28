---
layout: page
title: ""
ispost: false
---
<script>
$(document).ready(function () {
    const queryString = window.location.search;
    const urlParams = new URLSearchParams(queryString);

    const tag = urlParams.get("tag")

    const re = /[^a-zA-Z0-9+\-*\s]+/g;

    filterPostsByQuery(tag.replace(re, ""));
});
</script>

