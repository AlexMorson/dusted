import configparser

config = configparser.ConfigParser()

if not config.read("config.ini"):
    raise FileNotFoundError("Could not find config file `config.ini`")
