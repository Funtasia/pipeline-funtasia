#!/usr/bin/env python3

import tomllib
from pprint import pprint
from pathlib import Path

with open("config.toml","rb") as f:
    config = tomllib.load(f)

pprint(config)
print(Path(config["repos"]["MAINDIR"]))
print(Path(config["repos"]["app"]))
print(Path(config["repos"]["MAINDIR"]) / Path(config["repos"]["app"]))