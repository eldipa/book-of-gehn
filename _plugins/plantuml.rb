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
# {% plantuml %}
# [First] - [Second]
# {% endplantuml %}

# https://github.com/yegor256/jekyll-plantuml/blob/master/lib/jekyll-plantuml.rb
require 'digest'
require 'fileutils'

module Jekyll
  class PlantumlBlock < Liquid::Block
    def initialize(tag_name, markup, tokens)
      super
      @html = (markup or '').strip
    end

    def render(context)
      site = context.registers[:site]
      conf = site.config['plantuml'] || {}

      jar = conf['jar'] || './plantuml.jar'
      umlpath = conf['umlpath'] || 'uml'
      img_format = conf['format'] || 'svg'

      text = super
      name = Digest::MD5.hexdigest(text)

      fname = "#{name}.#{img_format}"
      src = File.join(site.source, umlpath, "#{name}.uml")
      dst = File.join(site.source, umlpath, fname)
      dst_site = File.join(site.dest, umlpath, "#{name}.#{img_format}")

      if !File.exists?(dst_site)
        if File.exists?(dst)
          puts "File #{dst} already exists (#{File.size(dst)} bytes)"
        else
          FileUtils.mkdir_p(File.dirname(src))
          File.open(src, 'w') { |f|
            f.write("@startuml\n")
            f.write(text)
            f.write("\n@enduml")
          }
          r = system("java -Djava.awt.headless=true -jar #{jar} -tsvg #{src}")
          if r.nil? || !r
            puts "Plantuml ('#{jar}') failed (exit code #{$?})"
            puts "Bogus snippet:"
            puts text
          end
          site.static_files << Jekyll::StaticFile.new(
            site, site.source, umlpath, fname
          )
          puts "File #{dst} created (#{File.size(dst)} bytes)"
        end
      end
      "<p><object data='#{site.baseurl}/#{umlpath}/#{fname}' type='image/#{img_format}+xml' #{@html}></object></p>"
    end
  end
end

Liquid::Template.register_tag('plantuml', Jekyll::PlantumlBlock)
