## Usage {% sidenote 'Your text here' %}
module Jekyll
  class RenderSideNoteTag < Liquid::Tag

    require "shellwords"
    require "digest"

    def initialize(tag_name, text, tokens)
      super
      @text = text.shellsplit
    end

    def render(context)
      token = Digest::MD5.hexdigest "#{@text[0]}"
      id = "sn-#{token}"
      "<label for='#{id}' class='margin-toggle sidenote-number'></label>"+
      "<input type='checkbox' id='#{id}' class='margin-toggle'/>"+
      "<span class='sidenote'>#{@text[0]}</span>"
    end
  end
end

Liquid::Template.register_tag('sidenote', Jekyll::RenderSideNoteTag)

