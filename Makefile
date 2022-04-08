# Pass this environment variable to compile (tup) only a subset
# of the targets. Leave it undefined to compile everything.
PAGETARGET ?=

all: Tupfile
	tup ${PAGETARGET}

force: Tupfile
	tup -k ${PAGETARGET}

# List all the directories in posts/ and drafts/ folders and
# create a Tupfile with the rules to build the blog site
#
# With this we can make a Tupfile with dynamic rules just
# playing with the template engine Jinja (j2)
Tupfile: scripts/j2helpers.py z/Tupfile.tup recreate-tupfile

recreate-tupfile:
	@echo "Recreating Tupfile..."
	@j2 --customize scripts/j2helpers.py z/Tupfile.tup > Tupfile

serve:
	# Serve (locally) the site on port 4000 watching for requests
	# to out/site/articles/**/*.html. If such request is received,
	# the server will call 'make' before serving it triggering a
	# recomputation of the site behind the scenes
	@./scripts/server.py -c make -d out/site -t 'out/site/articles/**/*.html' -t 'out/site/pages/**/*.html'  -t 'out/site/pages/'  -t 'out/site/' 4000

publish:
	# Make the public site. Note that the DRAFT folders
	# are *not* copied however this impl is not perfect
	# and it leaks thinks like the drafts' date
	# (article/<date>/)
	@rsync --human-readable --partial --progress --recursive \
	       --times --delete --links \
	       --exclude ".git" 	\
	       --exclude "**DRAFT**" 	\
               out/site/ public-site/
	@# This is not necessary; just in case
	@find public-site/ -name '**DRAFT**' -delete
	# Point to the correct public web site
	@grep -Rl 'http://127.0.0.1:4000' public-site/ | xargs -I{} sed -i 's%http://127.0.0.1:4000%https://book-of-gehn.github.io%g' {}
