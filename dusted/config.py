import configparser
import os

path = os.path.join(os.path.dirname(__file__), "config.ini")

config = configparser.ConfigParser()

if not config.read(path):
    raise FileNotFoundError("Could not find config file `config.ini`")

def write():
    with open(path, "w") as file:
        config.write(file)
