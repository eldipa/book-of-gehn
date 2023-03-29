---
layout: page
title: ""
ispost: false
---
<script>
$(document).ready(function () {
    const queryString = window.location.search;
    const urlParams = new URLSearchParams(queryString);

    const re = /[^a-zA-Z0-9+\-*\s]+/g;

    const tag = urlParams.get("tag").replace(re, " ")

    const searchForm = document.querySelector('#blog-search-form');
    const searchField = searchForm.querySelector('input');

    searchField.value = tag;
    filterPostsByQuery(tag);
});
</script>

{% for post in posts %}
{% if 'DRAFT' not in post.tags and 'HIDDEN' not in post.tags %}
<div class="index-single-post" id="{{ post['post_id'] }}">
<hr class="slender post-layout" />
<a href="{{ post['url'] }}"><h2 class="larger">{{ post['title'] }}</h2></a>
<p class="small-subtitle">Tags:
{% if post['tags'] -%}
{% for tag in post['tags'][:-1] -%}
<a href='{{ site.url }}/?tag="{{tag}}"'>{{tag}}</a>,
{% endfor -%}
<a href='{{ site.url }}/?tag="{{post['tags'][-1]}}"'>{{post['tags'][-1]}}</a>
{% endif -%}
</p>
<p class="small-subtitle">{{ post['date'] | date("%B %-d, %Y") }}</p>
<div>
{% include post['refs']['excerpt-j2'] %}
</div>
</div>
{% endif %}
{% endfor %}

