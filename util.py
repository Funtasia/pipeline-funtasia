import tomllib
import re

def load_config():
    with open("config.toml", "rb") as f:
        return tomllib.load(f)
    
def extract_url(pattern,html):
    m = re.search(pattern, html)
    return m.group(1) if m else None