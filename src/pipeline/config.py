#!/usr/bin/env python3

# run `python -m pipeline.config`` to dump config

import platform
import tomllib
import re
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

FILENAME = "nipple_config.toml"


class Config:
    # General
    version: str # required in __init__
    
    # Dir
    root: Path # required in __init__
    assets: Path = Path("app-funtasia/assets")
    app: Path = Path("app-funtasia")

    # Convert
    blender_exe: Path # default value set later in __init__, may raise
    blender_script: Path = Path("3dfiles-funtasia/misc/scripts/blender_script.py")
    skp_folder: Path = Path("3dfiles-funtasia/.skp")
    glb_folder: Path = Path("3dfiles-funtasia/.glb")
    blend_folder: Path = Path("3dfiles-funtasua/.blend")

    attempts: int = 2
    DEBUG: int = 0


    def __init__(self, config:dict[str, dict[str, Any]] = {}):
        # set required values first
        # WILL raise exception if values are missing / wrong type
        self.root = config.get("dir", {}).get("root") # type: ignore
        self.version = config.get("general", {}).get("version") # type: ignore

        for subsection in config.values():
            for k, v in subsection.items():
                if k in ("root", "version"):
                    continue
                setattr(self, k, v)

        # set defaults which may raise Error
        if not getattr(self, "blender_exe"):
            self.blender_exe = Path(get_blender_exe()).absolute()

    def absoulte_validate_path(self, path: Path | str, root: Path | None) -> tuple[bool, Path]:
        if not isinstance(path, Path | str):
            raise TypeError(f"Expected path-like object (Path | str), got {type(path)}")
        
        path = Path(path)

        if not path.is_absolute():
            if root:
                path = root / path
            else:
                path = path.absolute()

        if path.exists():
            return True, path

        return False, path

    def __setattr__(self, name: str, value: Any, /) -> None:
        hints: dict[str, type] = self.__class__.__annotations__
        if name not in hints:
            raise TypeError(f"No attribute '{name}' in {self.__class__.__name__}")

        if hints[name] is Path:
            exists, value = self.absoulte_validate_path(value, root = self.root if name != "root" else None)
            if not exists:
                raise FileNotFoundError(f"Cannot find directory {value}")
        
        if not isinstance(value, hints[name]):
            raise TypeError(f"Type mismatch for '{name}': expected {hints[name].__name__}, got {type(value).__name__}")

        elif name == "version":
            # see: https://semver.org/#is-there-a-suggested-regular-expression-regex-to-check-a-semver-string
            # added optional 'v' at front
            pattern = r"^v?(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
            if not re.match(pattern, value):
                raise TypeError("Configuration for Version is invalid")

        super().__setattr__(name, value)

    def __rich_repr__(self):
        for attr in self.__class__.__annotations__:
            yield attr, getattr(self, attr)


def load_config(force_default=False) -> Config:
    path = Path.cwd()

    for directory in [path, *path.parents]:
        if (directory / FILENAME).is_file():
            with open(directory / FILENAME, "rb") as f:
                data = tomllib.load(f)

            return Config(
                config={"dir": {"root": directory}} | data,
            )
    
    print("[CRITICAL] No configuration file found")
    
    if force_default:
        return Config(
            config={"general": {"version": "v67.69.420"}, "dir": {"root": str(Path())}}
        )
    
    raise FileNotFoundError(f"Could not find {FILENAME}")


def get_blender_exe(force_default=False) -> str:
    if platform.system() == "Windows":
        # version agnostic
        matches = list(Path().glob("C:/Program Files/Blender Foundation/Blender*/blender.exe"))
        if not matches:
            if force_default:
                return "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
            raise NotImplementedError(f"Cannot detect blender, please make sure it is installed and put its path in {FILENAME}.")
        elif len(matches) > 1:
            print(f"Multiple blender found. Specify correct version in {FILENAME}")
        return str(matches[0])
    
    elif platform.system() == "Linux":
        blender_exe = "/usr/bin/blender" # wow such nice path
    elif platform.system() == "Darwin":
        blender_exe = "/Applications/Blender.app/Contents/MacOS/Blender"
    else:
        raise NotImplementedError(f"bro wtf why are you on {platform.system()}")

    if not force_default and not Path(blender_exe).exists():
        raise NotImplementedError(f"Cannot detect blender, please make sure it is installed and put its path in {FILENAME}.")

    return blender_exe

    
def write_config(overwrite=False):
    """
    Set root to cwd and write default config to root.

    Should be run only once to setup.
    """

    # Use Jinja instead of writing default_config to toml
    # because writing toml requires external library, 
    # but Jinja is already a requirement for Quart.
    
    root = Path()
    config_path = root / FILENAME

    if not overwrite and config_path.exists():
        raise FileExistsError("Config file `nipple_config.toml` already exists.")


    jinja_env = Environment(loader=FileSystemLoader(Path(__file__).parent))
    template = jinja_env.get_template("nipple_config.toml.jinja")
    config_file = template.render(
        blender = get_blender_exe(force_default=True),
        root = str(root.absolute()),
    )

    with open(config_path, 'w') as f:
        f.write(config_file)

if __name__ == "__main__":
    from rich.pretty import pprint
    pprint(load_config())

