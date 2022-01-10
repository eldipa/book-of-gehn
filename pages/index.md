---
layout: page
title: ""
ispost: false
---
{% for post in posts %}
   <span class="index-single-post">
      <hr class="slender post-layout">
      <a href="{{ post['url'] }}"><h2 class="larger">{{ post['title'] }}</h2></a>
      <br><span class="smaller">{{ post['date'] | date("%B %-d, %Y") }}</span>  <br/>
      <div>
{% include post['refs']['excerpt-j2'] %}
</div>
   </span>
{% endfor %}
