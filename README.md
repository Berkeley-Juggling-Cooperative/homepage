# The repo for the homepage of the Berkeley Juggling club.

It includes all files to create the static webpage using (Nikola)[https://getnikola.com].

The homepage can be found at https://test.berkeleyjuggling.org.

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

We run all html through (tidy)[https://www.html-tidy.org], which needs
to be installed. If `tidy` is not available, you can turn this off by
commenting out the filter section in the `conf.py` file.

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

If you like the results, add it to git and push it to github.

## Updating the homepage

To update the homepage at berkeleyjuggling.org you need ssh access to
the server. Contact Arun, if you need to have access or ask him to
deploy the changes.  If you have access, you can do the following to
build the web page:

    uv run nikola deploy download
	uv run nikola build

This will download all the images and videos used on the web page and
then build the webpage including thumbnails for all these galleries
and links.

To then upload the web page, you can use

    uv run nikola deploy

Eventually we should set up an automatic deploy from github.

## Adding new python packages

To add a new package, use `uv add <package name>' and after it comit
the `uv.lock` file and pyproject.toml to git.

## TODO

- add juggling patterns and organize them using tags
- add old patterns from original web page
- Causal diagrams:
  - Try adding Havanna and Scrambled Ivy to test new system
  - add option to plot passes at a certain time in position diagram
    (think the different beat in torture chamber), instead or additional to animation
- page layout:
  - modify tag page to not say "Posts about 3-count", but "Patterns
	involving 3-count"
  - remove categories from tag overview and don't generate the category
	pages (or delete them before deploying?)
- 3d Animations:
  - add 3d animation of patterns (see https://github.com/helbling/passist/blob/main/src/lib/animation.mjs)
  - can we do 3d animation of moving patterns?
- use the browser built-in error checker (F12 in firefox) and fix any issues
- handle images and videos: Figure out how to do this using git
  without committing all the images to git. Probably:
  * we might commit certain files there though, e.g. subtitles or other yaml files that nikola uses
