## Liquid tag 'maincolumn-figure' used to add image data that fits within the
## main column area of the layout
## Usage {% maincolumn 'path/to/image' 'This is the caption' 'style' %}
#   'path/to/image' can be:
#       an absolute path: http://... or https://...
#       a arbitrary html tag:  <div>...</div>
#       a relative path: foo/bar
#
module Jekyll
  class RenderMainColumnTag < Liquid::Tag

  	require "shellwords"

    def initialize(tag_name, text, tokens)
      super
      @text = text.shellsplit
    end

    def render(context)
      baseurl = context.registers[:site].config['baseurl']

      if @text[2]
        style = " style='#{@text[2]}' "
      else
        style = ""
      end

      if @text[0].start_with?('http://', 'https://','//')
        img_html = "<img #{style} src='#{@text[0]}' />"
      elsif @text[0].start_with?('<')
        img_html = "#{@text[0]}"
      else
        img_html = "<img #{style} src='#{baseurl}/#{@text[0]}' />"
      end

      return "<figure><figcaption><span markdown='1'>#{@text[1]}</span></figcaption>#{img_html}</figure>"
    end
  end
end

Liquid::Template.register_tag('maincolumn', Jekyll::RenderMainColumnTag)
