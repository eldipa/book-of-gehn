.PHONY: Tupfile

all: Tupfile
	@tup

# List all the directories in posts/ and drafts/ folders and
# create a Tupfile with the rules to build the blog site
#
# With this we can make a Tupfile with dynamic rules just
# playing with the template engine Jinja (j2)
Tupfile: scripts/Tupfile.tup
	@j2 --customize scripts/j2helpers.py $^ > $@

serve:
	@cd out/site ; python3 -m http.server 4000
