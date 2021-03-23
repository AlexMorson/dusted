# Dusted

An offline editor for Dustforce replays, largely based on dustkid.com's replay composer.

## Installation

```
pip install dusted
```

For extra features, copy `plugin/tas.as` to `~dustforce/user/script_src`, compile as an in-game plugin, and enable it.

On linux, the program `unbuffer` is required, which can be installed with `sudo apt-get install expect` (or equivalent depending on your distribution).

## Usage

Run the editor with

```
python -m dusted
```

or, if the python scripts directory is on the PATH

```
dusted
```
