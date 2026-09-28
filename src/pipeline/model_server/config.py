#!/usr/bin/env python3

import tomllib
from pathlib import Path

def load_config():
    path = Path.cwd()

    for directory in [path, *path.parents]:
        if (directory / "config.toml").is_file():
            with open(directory/"config.toml","rb") as f:
                data = tomllib.load(f)
            return data

    raise FileNotFoundError("Could not find Funtasia config.toml")
