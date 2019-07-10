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

publish:
	@sudo docker stop GehnPages || true
	@sudo rm -Rf _site
	#@sudo docker run --rm -v `pwd`:/srv/jekyll ${DOCKERIMG} bundle exec jekyll build
	@sudo docker run --rm -v `pwd`:/srv/jekyll ${DOCKERIMG} jekyll build
	@[ -d _site ] || ( echo "Missing _site (source), aborting" && exit 1 )
	@[ -d _public ] || ( echo "Missing _public (destination), aborting" && exit 1 )
	@[ -d _public/.git ] || ( echo "Missing _public/.git (git repository), aborting" && exit 1 )
	rm -Rf _public/*
	cp -R _site/* _public
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

test-crypto:
	byexample @_tests/crypto

test-tiburoncin:
	byexample @_tests/tiburoncin

test: test-shellshock test-matasano test-tiburoncin test-crypto
