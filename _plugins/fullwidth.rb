## This has a fairly harmless hack that wraps the img tag in a div to prevent it from being
## wrapped in a paragraph tag instead, which would totally fuck things up layout-wise
## Usage {% fullwidth 'path/to/image' 'caption goes here in quotes' %}
#
module Jekyll
  class RenderFullWidthTag < Liquid::Tag

    require "shellwords"

    def initialize(tag_name, text, tokens)
      super
      @text = text.shellsplit
    end

    def render(context)
      baseurl = context.registers[:site].config['baseurl']
      if @text[0].start_with?('http://', 'https://','//')
        img_html = "<img src='#{@text[0]}' />"
      elsif @text[0].start_with?('<')
        img_html = "#{@text[0]}"
      else
        img_html = "<img src='#{baseurl}/#{@text[0]}' />"
      end

      "<figure class='fullwidth'>#{img_html}"+
      "<figcaption>#{@text[1]}</figcaption></figure>"
    end
  end
end

Liquid::Template.register_tag('fullwidth', Jekyll::RenderFullWidthTag)
