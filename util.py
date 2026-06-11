import tomllib
import re
from pathlib import Path

CONFIG_PATH = Path("config.toml")

def load_config():
    with open(CONFIG_PATH, "rb") as f:
        return tomllib.load(f)
    
def extract_url(pattern,html):
    m = re.search(pattern, html)
    return m.group(1) if m else None