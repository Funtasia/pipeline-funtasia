#!/usr/bin/env python3

import tomllib
import re
from pathlib import Path

CONFIG_PATH = Path("config.toml")

def load_config():
    with open(CONFIG_PATH, "rb") as f:
        return tomllib.load(f)
    
