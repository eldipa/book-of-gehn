#DOCKERIMG=personal-jekyll
#DOCKERIMG=jekyll/jekyll:3.6
DOCKERIMG=gehnjekyll

all:
	@echo ":´("

create:
	# if fails, rm Gemfile.lock
	@[ -f _config.yml ] || ( echo "Are you sure that your working directory is a Jekyll repo?" && exit 1 )
	sudo docker run \
		--name GehnPages \
		-v `pwd`:/srv/jekyll \
		-p 127.0.0.1:4000:4000 \
		${DOCKERIMG} \
		jekyll serve --watch --drafts

build:
	sudo docker build -t ${DOCKERIMG} .
start:
	@sudo docker stop GehnPages || true
	@sudo rm -Rf _site
	sudo docker start GehnPages
	@sleep 5
	@sudo docker ps | grep GehnPages

start-attach:
	@sudo docker stop GehnPages || true
	@sudo rm -Rf _site
	sudo docker start -a GehnPages

stop:
	sudo docker stop GehnPages

index:
	@node ./_docker/build_search_index.js ./_posts/ > js/search_index.js

publish:
	@sudo docker stop GehnPages || true
	@sudo rm -Rf _site
	@# Use this file to mark which files were "recreated" by "jekyll build"
	@# and which weren't.
	@touch uml/.token-reference
	@#@sudo docker run --rm -v `pwd`:/srv/jekyll ${DOCKERIMG} bundle exec jekyll build
	@sudo docker run --rm -v `pwd`:/srv/jekyll ${DOCKERIMG} jekyll build
	@[ -d _site ] || ( echo "Missing _site (source), aborting" && exit 1 )
	@[ -d _public ] || ( echo "Missing _public (destination), aborting" && exit 1 )
	@[ -d _public/.git ] || ( echo "Missing _public/.git (git repository), aborting" && exit 1 )
	rm -Rf _public/*
	@# Delete any file that was not recreated by "jekyll build"
	@# With this we can remove not-longer-used files
	find uml/ -not -newer uml/.token-reference -type f -delete
	@# Copy the output of "jekyll build" to _public for publishing
	cp -R _site/* _public
	@# Get what 'svg' files from "uml/" are *required* by the posts
	@# Then list what 'svg' files *are* in "uml/"
	@# And finally compare: we expect both to be the same (we have in "uml/"
	@# the svg files that are required, no more, no less)
	@grep -R '[0-9a-f]\{40\}\.svg' _public/articles/ | sed 's/^.*\([0-9a-z]\{40\}\.svg\).*$$/_public\/uml\/\1/g' - | sort -u > _tmp_uml_svg_in_articles
	@find _public/uml/ -name '*.svg' | sort -u > _tmp_uml_svg_in_folder
	@diff _tmp_uml_svg_in_articles _tmp_uml_svg_in_folder || ( echo "Mismatch in the uml/.svg files used in the articles and the ones stored in the _public/uml folder. Aborting" && exit 1 )
	@# Check for this cookie. If we found it means that we are publishing
	@# draft articles. Abort!
	@grep -q -v -R 'OI/tb2g5khoRa5v3srldjQiPFqlbcFlnYpk99k0wEwE=' _public/ || ( echo "Draft are beign published. Aborting" && exit 1 )
	@git diff --quiet _config.yml css/ fonts/ _includes/ js/ _layouts/ _plugins/ _sass/ ||  ( echo "Some 'root' folders are not commited. Commit them first before publishing. Aborting" && exit 1 )
	( cd _public && git status )

test-shellshock:
	@echo "Build the Shellshock image to play with it (without the tests)"
	@rm -f assets/shellshock/files/20*.md
	@rm -f assets/shellshock/files/shellshock
	@sudo docker build -q -t shellshock assets/shellshock/
	@echo
	@echo "From that, build the Shellshock image for testing"
	@cp _posts/2018-10-01-Magic-Bash-Runes.md assets/shellshock/files/
	@cp _tests/shellshock assets/shellshock/files/
	@sudo docker build -q -t shellshock-test -f assets/shellshock/Dockerfile.test assets/shellshock/
	@rm -f assets/shellshock/files/20*.md
	@rm -f assets/shellshock/files/shellshock
	@echo
	@sudo docker run -it --rm --cap-add=NET_ADMIN shellshock-test byexample '@shellshock'

test-matasano:
	byexample @_tests/matasano

test-z3:
	byexample @_tests/z3

test-crypto:
	byexample @_tests/crypto

test-tiburoncin:
	byexample @_tests/tiburoncin

test-debruijn:
	byexample @_tests/debruijn

test: test-shellshock test-matasano test-tiburoncin test-crypto
