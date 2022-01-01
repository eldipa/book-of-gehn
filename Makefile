
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
	@cd out/site ; python3 -m http.server 4000
