from datetime import datetime
import tomllib
import tomlkit

def load_config(path="config.toml"):
    with open(path, "rb") as f:
        return tomllib.load(f)


def save_config(data, path="config.toml"):
    with open(path, "w") as f:
        f.write(tomlkit.dumps(data))

def bump_version(version):
    new_v = int(version[1])+1
    now = datetime.now()
    
    month = now.strftime("%m")
    day = now.strftime("%d") 
    
    new_version = f"v{new_v}-{month}-{day}"
    return new_version

def apply_bump(path="config.toml"):
    cfg = load_config(path)
    old = cfg["general"]["version"]
    cfg["general"]["version"] = bump_version(old)
    save_config(cfg, path)
    return old, cfg["general"]["version"]

if __name__ == "__main__":
    apply_bump()