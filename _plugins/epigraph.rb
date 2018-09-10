## Usage {% epigraph "the epigraph text here" "author and reference here" }

module Jekyll
  class RenderEpigraphTag < Liquid::Tag

    require "shellwords"

    def initialize(tag_name, text, tokens)
      super
      @text = text.shellsplit
    end

    def render(context)
      "<blockquote>
         <p class=\"epigraph\">#{@text[0]}<cite class=\"epigraph\">#{@text[1]}</cite></p>
       </blockquote>"
    end
  end
end

Liquid::Template.register_tag('epigraph', Jekyll::RenderEpigraphTag)
