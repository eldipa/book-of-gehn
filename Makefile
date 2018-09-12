all:
	@echo ":´("

create:
	# if fails, rm Gemfile.lock
	docker run --name GehnPages -v `pwd`:/srv/jekyll -p 127.0.0.1:4000:4000 personal-jekyll

start:
	@docker stop GehnPages || true
	@rm -Rf _site
	docker start GehnPages

stop:
	docker stop GehnPages

publish:
	@docker stop GehnPages || true
	@rm -Rf _site
	docker run --rm -v `pwd`:/srv/jekyll personal-jekyll bundle exec jekyll build
	@[ -d _site ] || ( echo "Missing _site (source), aborting" && exit 1 )
	@[ -d _public ] || ( echo "Missing _public (destination), aborting" && exit 1 )
	@[ -d _public/.git ] || ( echo "Missing _public/.git (git repository), aborting" && exit 1 )
	rm -Rf _public/*
	cp -R _site/* _public
	grep -q -v -R 'OI/tb2g5khoRa5v3srldjQiPFqlbcFlnYpk99k0wEwE=' _public/ || ( echo "Draft are beign published, aborting" && exit 1 )
	( cd _public && git status )

test:
	byexample @_tests/matasano
