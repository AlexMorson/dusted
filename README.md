# Dusted

An offline editor for Dustforce replays, largely based on dustkid.com's replay composer.

## Installation

### With uv

Using [uv](https://docs.astral.sh/uv/) will handle installing a compatible Python version, and will install and run the latest version of Dusted.

```shell
uvx dusted
```

For extra features, copy `plugin/tas.as` to `~dustforce/user/script_src`, compile as an in-game plugin, and enable it.

On linux, the program `unbuffer` is required, which can be installed with `sudo apt-get install expect` (or equivalent depending on your distribution).

### Manual

Alternatively, Dusted can be installed manually using pip.

```shell
pip install dusted
```

Then run with:

```shell
python -m dusted
```

or, if the Python scripts directory is on the PATH:

```shell
dusted
```
