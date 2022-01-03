
all: Tupfile
	@tup

# List all the directories in posts/ and drafts/ folders and
# create a Tupfile with the rules to build the blog site
#
# With this we can make a Tupfile with dynamic rules just
# playing with the template engine Jinja (j2)
Tupfile: scripts/j2helpers.py z/Tupfile.tup
	@echo "Recreating Tupfile..."
	@j2 --customize scripts/j2helpers.py z/Tupfile.tup > $@

serve:
	# Serve (locally) the site on port 4000 watching for requests
	# to out/site/articles/**/*.html. If such request is received,
	# the server will call 'make' before serving it triggering a
	# recomputation of the site behind the scenes
	@./scripts/server.py -c make -d out/site -t 'out/site/articles/**/*.html' -t 'out/site/pages/**/*.html'  -t 'out/site/pages/'  -t 'out/site/' 4000
