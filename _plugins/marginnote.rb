## Usage (for simple texts)
#   {% marginnote 'Your text here' %}
#
## Usage (for code and text)
#   {% marginmarkdowncode
#   '
#   ```cpp
#   while (1)
#      more code
#   ```
#   '
#
#   'text here'
#   %}
module Jekyll
  class RenderMarginNoteTag < Liquid::Tag

    require "shellwords"
    require "digest"

    def initialize(tag_name, text, tokens)
      super
      @text = text.shellsplit
    end

    def render(context)
      token = Digest::MD5.hexdigest "#{@text[0]}"
      id = "mn-#{token}"
      "<label for='#{id}' class='margin-toggle'> &#8853;</label>"+
      "<input type='checkbox' id='#{id}' class='margin-toggle'/>"+
      "<span class='marginnote'>#{@text[0]} </span>"
    end
  end
end

module Jekyll
  class RenderMarginMarkdownCodeTag < Liquid::Tag

    require "shellwords"
    require "digest"

    def initialize(tag_name, text, tokens)
      super
      @text = text.shellsplit
    end

    def render(context)
      comments = @text[1] || ""

      token = Digest::MD5.hexdigest "#{@text[0] + comments}"
      id = "mmkd-#{token}"

      site = context.registers[:site]
      markdown = Converters::Markdown.new(site.config)
      markdown.setup
      payload = markdown.convert("#{@text[0]}").strip

      # escape any single quote
      #payload = payload.gsub(/\\([\s\S])|(')/,"\\$1$2");

      "<label for='#{id}' class='margin-toggle'> &#8853;</label>"+
      "<input type='checkbox' id='#{id}' class='margin-toggle'/>"+
      "\n<div id='mk-#{id}'><span class='marginnote marginmarkdowncode'>#{payload}#{comments}</span></div>\n"+
      "<div><script>$(document).ready(function () {$('#mk-#{id} > span').insertAfter($('##{id}'))});</script></div>"
    end
  end
end

Liquid::Template.register_tag('marginnote', Jekyll::RenderMarginNoteTag)
Liquid::Template.register_tag('marginmarkdowncode', Jekyll::RenderMarginMarkdownCodeTag)

