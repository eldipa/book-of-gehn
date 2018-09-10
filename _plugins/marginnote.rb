## Usage {% marginnote 'Your text here' %}
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

Liquid::Template.register_tag('marginnote', Jekyll::RenderMarginNoteTag)

