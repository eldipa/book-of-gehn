## Liquid tag 'marginfigure' used to add image data in the side
## Usage {% marginfigure 'alternate text' 'path/to/image' 'This is the caption' 'style' 'class' %}
#
#  The caption, style and class are optional.
module Jekyll
  class RenderMarginFigureTag < Liquid::Tag

    require "shellwords"
    require "digest"

    def initialize(tag_name, text, tokens)
      super
      @text = text.shellsplit
    end

    def render(context)
      baseurl = context.registers[:site].config['baseurl']
      token = Digest::MD5.hexdigest "#{@text[0]}~#{@text[1]}~#{@text[2]}"
      id = "mf-#{token}"

      if @text[3]
        style = " style='#{@text[3]}' "
      else
        style = ""
      end

      if @text[4]
        cls = " #{@text[4]}"
      else
        cls = ""
      end

      if @text[1].start_with?('http://', 'https://', '//')
        img_html = "<img #{style} class='fullwidth' alt='#{@text[0]}' src='#{@text[1]}' />"
      elsif @text[1].start_with?('<')
        img_html = "#{@text[1]}"
      else
        img_html = "<img #{style} class='fullwidth' alt='#{@text[0]}' src='#{baseurl}/#{@text[1]}' />"
      end

      if @text[2]
        caption_html = "  <br>#{@text[2]}"
      else
        caption_html = ""
      end

      "<label for='#{id}' class='margin-toggle #{cls}'>&#8853;</label>"+
      "<input type='checkbox' id='#{id}' class='margin-toggle #{cls}'/>"+
      "<span class='marginnote #{cls}'>"+
        img_html +
      caption_html +
      "</span>"
    end
  end
end

Liquid::Template.register_tag('marginfigure', Jekyll::RenderMarginFigureTag)
