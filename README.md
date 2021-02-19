# Dustforce TAS Editor
An offline replay editor for dustforce based heavily on dustkid.com's Replay Composer.

## Setup
- `pip install requests dustmaker`
- On linux, `sudo apt-get install expect` (or equivalent, for the program `unbuffer`)
- `git clone https://github.com/AlexMorson/dustforce-tas-editor`
- Set the path to your dustforce installation in `config.ini`
- Copy `plugin/tas.as` to `~dustforce/user/script_src`, compile as an in-game plugin, and enable it
- Run the app with `python gui.py`
