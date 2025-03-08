# This is the homepage for the Berkeley Juggling club.

It includes all files to create the static webpage using (Nikola)[https://getnikola.com].

## How to build the static webpage

Using (UV)[https://docs.astral.sh/uv/] is an easy way to get python
installed on any system.  The installationi instruction for UV can be
found (here)[https://docs.astral.sh/uv/getting-started/installation/].

Once install, you need to `cd` into this github repo (cloning it
first) and then run:

    uv sync

This will update a uv-managed virtual environment (and create it if
needed) inside .venv.

After this you can eiher run `nikola` by using `uv run nikola` or by
activating the venv and running `nikola` directly.

## How to add a new pattern

Create a new page using, say for a 3-count pattern

	uv run nikola new_page pages/patterns/3-count.md

Nikola will ask you for a page name, for this example, you would add
"3 Count".

Then open the new file in an editor and add tags, e.g. "2-person,
3-count" and for the category add "patterns", add a short description
"A simple 3 count pattern".

Delete the "Write your page here" text and add the pattern. See
existing patterns on what should be on a pattern page.

Save the file and run

    uv run nikola build
	uv run nikola serve

Which will open a web server on your computer, so that you can look at
the results.

Also make sure that if you add a new tag, that the new tag is listed
on the `page/patterns.md` page.

## Adding new python packages

To add a new package, use `uv add <package name>' and after it comit
the `uv.lock` file and pyproject.toml to git.

## TODO

- add juggling patterns and organize them using tags
- modify tag page to not say "Posts about 3-count", but "Patterns
  involving 3-count"
- remove categories from tag overview and don't generate the category
  pages (or delete them before deploying?)
- add 3d animation of patterns (see https://github.com/helbling/passist/)
- add option to add position of jugglers
- add option to plot passes at a certain time in position diagram
  (think the different beat in torture chamber)
- can we do 3d animation of moving patterns?
- use the browser built-in error checker (F12 in firefox) and fix any issues
- reorganize webpage
- handle images and videos: Figure out how to do this using git
  without committing all the images to git. Probably an rsync command
  to download them into a different folder, a script that
  creates very small previews of them that can be committed into git, and a
  modified deploy script that upload the original ones back (in case
  new ones got added) and also making sure that we don't delete images
  on the server during deployment.
