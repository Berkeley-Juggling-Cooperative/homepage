# This is the homepage for the Berkeley Juggling club.

It includes all files to create the static webpage using (Nikola)[https://getnikola.com].

## How to build the static webpage

Using (UV)[https://docs.astral.sh/uv/] is an easy way to get python installed on any system.
The installationi instruction for UV can be found (here)[https://docs.astral.sh/uv/getting-started/installation/]. 

Once install, you need to `cd` into this github repo (cloning it first) and then run `uv sync`.

This will update a uv-managed virtual environment (and create it if needed) inside .venv.

After this you can eiher run `nikola` by using `uv run nikola` or by activating the venv and running `nikola` directly.

## Developing

### Adding new packages

To add a new package, use `uv add <package name>' and after it comit the `uv.lock` file and pyproject.toml to git.

## TODO

- add juggling patterns and organize them
- see if we can add automated diagrams from ascii descriptions, use either
   https://github.com/helbling/passist/ or https://www.jugglingedge.com/help/causaldiagrams.php
- use the browser built-in error checker (F12 in firefox) and fix any issues
- reorganize webpage
- import all images and videos and host them locally
- change deployment commands to be able to store images/videos directly on dreamhost (currenlty they would be deleted)
