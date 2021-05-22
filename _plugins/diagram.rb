# (The MIT License)
#
# Copyright (c) 2014-2019 Yegor Bugayenko
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the 'Software'), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

# See original code in
# https://github.com/yegor256/jekyll-plantuml/blob/master/lib/jekyll-plantuml.rb
require 'digest'
require 'fileutils'

module Jekyll
  class DiagramBlock < Liquid::Block
    def initialize(tag_name, markup, tokens)
      super
      @attributes = {}
      markup.scan(Liquid::TagAttributes) do |key, value|
          @attributes[key] = value.gsub(/^'|"/, '').gsub(/'|"$/, '')
      end
    end

    def get_engine
      raise "No Diagram Engine was defined!"
    end

    def generate_diagram(context, text)
      site = context.registers[:site]
      conf = site.config['diagrams'] || {}

      plantumljar = conf['plantuml-jar'] || './plantuml.jar'
      ditaajar = conf['ditaa-jar'] || './ditaa.jar'
      dotbin = conf['dot-bin'] || 'dot'

      umlpath = conf['umlpath'] || 'uml'
      img_format = conf['format'] || 'svg'

      unless ['svg'].include? img_format
        puts "Invalid format for DiagramBlock diagram #{img_format}"
        raise "Error"
      end

      engine = get_engine

      unless ['plantuml', 'ditaa', 'dot'].include? engine
        puts "Invalid engine for DiagramBlock diagram #{engine}"
        raise "Error"
      end

      name = Digest::MD5.hexdigest(text)
      pluginame = Digest::MD5.hexdigest(File.expand_path(File.dirname(__FILE__)))[0, 8] # first 8

      # note: if this size changes, you need to change the Makefile
      name = name + pluginame
      if name.length != 40
        raise "Error"
      end

      fname = "#{name}.#{img_format}"
      src = File.join(site.source, umlpath, "#{name}.uml")
      dst = File.join(site.source, umlpath, fname)
      dst_site = File.join(site.dest, umlpath, "#{name}.#{img_format}")

      if !File.exists?(dst_site)
        if File.exists?(dst)
          puts "File #{dst} already exists (#{File.size(dst)} bytes)"
          `touch #{dst}`
        else
          FileUtils.mkdir_p(File.dirname(src))
          if engine == 'plantuml'
            process_input_with_plantuml(src, text, plantumljar, img_format, dst)
          elsif engine == 'ditaa'
            process_input_with_ditaa(src, text, ditaajar, img_format, dst)
          elsif engine == 'dot'
            process_input_with_dot(src, text, dotbin, img_format, dst)
          else
            raise 'Error'
          end
          site.static_files << Jekyll::StaticFile.new(
            site, site.source, umlpath, fname
          )
          puts "File #{dst} created (#{File.size(dst)} bytes)"
        end
      else
        `touch #{dst}`
        `touch #{dst_site}`
      end

      html = "<object align='middle' data='#{site.baseurl}/#{umlpath}/#{fname}' type='image/#{img_format}+xml'></object>"
      return [site, umlpath, fname, img_format, html]
    end

    def process_input_with_plantuml(src, text, jar, img_format, dst)
      File.open(src, 'w') { |f|
        f.write("@startuml\n")
        f.write(text)
        f.write("\n@enduml")
      }
      args = "#{@attributes['args'] || ''}"
      cmd = "java -Djava.awt.headless=true -jar #{jar} -t#{img_format} #{src} #{args}"
      r = system(cmd)
      if r.nil? || !r
        puts "Plantuml ('#{jar}') failed (exit code #{$?})"
        puts "Command: #{cmd}"
        puts "Bogus snippet:"
        puts text
      end
    end

    def process_input_with_ditaa(src, text, jar, img_format, dst)
      if img_format != 'svg'
        raise "Error"
      end

      File.open(src, 'w') { |f|
        f.write(text)
      }

      args = "#{@attributes['args'] || '--no-shadows --no-separation'}"
      cmd = "java -Djava.awt.headless=true -jar #{jar} --overwrite --transparent --svg #{src} #{args}"
      r = system(cmd)
      if r.nil? || !r
        puts "Ditaa ('#{jar}') failed (exit code #{$?})"
        puts "Command: #{cmd}"
        puts "Bogus snippet:"
        puts text
      end
      style = <<EOF
        <style type='text/css'>
            /* <![CDATA[ */
                text {
                      fill: black !important;
                      font-family: Consolas, "Liberation Mono", Menlo, Courier, monospace !important;
                }
                path {
                      stroke-width: 1.5 !important;
                }
            /* ]]> */
        </style>
EOF

      script = <<EOF
      <script type="text/javascript">
        <![CDATA[
        setTimeout(function() {
            // make all the "white" closed shapes transparent.
            var paths = document.getElementsByTagName('path');
            for (var i = 0; i < paths.length; i++) {
                var path = paths[i];
                if (path.getAttribute("fill") == "white") {
                    path.setAttribute("fill", "#ffffff00"); // transparent
                }
            }
        }, 1000);
        ]]>
    </script>
EOF

      svg = File.read(dst)

      r = / width='([0-9]*)'.*?height='([0-9]*)'.*?shape-rendering=/m
      m = r.match(svg)
      m = [m[1].to_i, m[2].to_i]

      # fix at the moment of the load
      fixbox = " viewBox='0 0 #{m[0]} #{m[1]}' shape-rendering="
      svg.sub!(r, fixbox)

      svg.sub!('<defs>', script + style + '<defs>')
      File.write(dst, svg, mode: 'w')
    end

    def process_input_with_dot(src, text, bin, img_format, dst)
      if img_format != 'svg'
        raise "Error"
      end

      File.open(src, 'w') { |f|
        f.write(text)
      }
      cmd = "#{bin} -Tsvg -o#{dst} #{src}"
      r = system(cmd)
      if r.nil? || !r
        puts "Dot('#{bin}') failed (exit code #{$?})"
        puts "Command: #{cmd}"
        puts "Bogus snippet:"
        puts text
      end
    end
  end
  # https://css-tricks.com/scale-svg/

  class FullWidthDiagramBlock < DiagramBlock
    def render(context)
      site, umlpath, fname, img_format, html = generate_diagram(context, super)

      # NB: if we use single quotes instead of double quotes to wrap the html
      # Jekyll will escape it using html entities
      tag = "{% fullwidth \"#{html}\" '#{@attributes['caption']||''}' %}"
      Liquid::Template.parse(tag).render(context)
    end
  end

  class MainColumnDiagramBlock < DiagramBlock
    def render(context)
      site, umlpath, fname, img_format, html = generate_diagram(context, super)

      # NB: if we use single quotes instead of double quotes to wrap the html
      # Jekyll will escape it using html entities
      tag = "{% maincolumn  \"#{html}\" '#{@attributes['caption']||''}' %}"
      Liquid::Template.parse(tag).render(context)
    end
  end

  class MarginDiagramBlock < DiagramBlock
    def render(context)
      site, umlpath, fname, img_format, html = generate_diagram(context, super)

      # NB: if we use single quotes instead of double quotes to wrap the html
      # Jekyll will escape it using html entities
      tag = "{% marginfigure '' \"#{html}\" '#{@attributes['caption']||''}' %}"
      Liquid::Template.parse(tag).render(context)
    end
  end


  # Specialization classes for PlantUML
  class FullWidthPlantUMLBlock < FullWidthDiagramBlock
    def get_engine
      'plantuml'
    end
  end
  class MainColumnPlantUMLBlock < MainColumnDiagramBlock
    def get_engine
      'plantuml'
    end
  end
  class MarginPlantUMLBlock < MarginDiagramBlock
    def get_engine
      'plantuml'
    end
  end


  # Specialization classes for Ditaa
  class FullWidthDitaaBlock < FullWidthDiagramBlock
    def get_engine
      'ditaa'
    end
  end
  class MainColumnDitaaBlock < MainColumnDiagramBlock
    def get_engine
      'ditaa'
    end
  end
  class MarginDitaaBlock < MarginDiagramBlock
    def get_engine
      'ditaa'
    end
  end


  # Specialization classes for Dot
  class FullWidthDotBlock < FullWidthDiagramBlock
    def get_engine
      'dot'
    end
  end
  class MainColumnDotBlock < MainColumnDiagramBlock
    def get_engine
      'dot'
    end
  end
  class MarginDotBlock < MarginDiagramBlock
    def get_engine
      'dot'
    end
  end
end

# {% fullwidthplantuml caption:'a caption here' %}
# diagram code here
# {% endfullwidthplantuml %}
Liquid::Template.register_tag('fullwidthplantuml', Jekyll::FullWidthPlantUMLBlock)

# {% maincolumnplantuml caption:'a caption here' %}
# diagram code here
# {% endmaincolumnplantuml %}
Liquid::Template.register_tag('maincolumnplantuml', Jekyll::MainColumnPlantUMLBlock)

Liquid::Template.register_tag('marginplantuml', Jekyll::MarginPlantUMLBlock)


# Ditaa diagrams
Liquid::Template.register_tag('fullwidthditaa', Jekyll::FullWidthDitaaBlock)
Liquid::Template.register_tag('maincolumnditaa', Jekyll::MainColumnDitaaBlock)
Liquid::Template.register_tag('marginditaa', Jekyll::MarginDitaaBlock)


# Dot diagrams
Liquid::Template.register_tag('fullwidthdot', Jekyll::FullWidthDotBlock)
Liquid::Template.register_tag('maincolumndot', Jekyll::MainColumnDotBlock)
Liquid::Template.register_tag('margindot', Jekyll::MarginDotBlock)
