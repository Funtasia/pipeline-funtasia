#!/usr/bin/env python3

import tomllib
from pathlib import Path
from dataclasses import dataclass, field, fields
from typing import Optional, get_origin, get_args


DEFAULTS = {

}


class Config:
    # general
    version: str

    # convert
    blender_exe : Path
    blender_script: Path
    glb_folder: Path
    skp_folder: Path
    blend_folder: Path
    DEBUG: int

    # dir
    root: Path
    assets: Path
    app: Path
    pipeline: Path


    def __post_init__(self):
        for f in fields(self):
            value = getattr(self, f.name)
            
            origin = get_origin(f.type)
            expected_types = get_args(f.type) if origin else (f.type,)
            
            if origin and not expected_types:
                expected_types = (origin,)

            if not isinstance(value, expected_types):
                raise TypeError(f"Expected {f.name} to be {f.type}, got {type(value).__name__}")


class Config:
    def __init__(self,config:dict[str,dict] = {}):
        general = config.get("",None)
        self.version = general.get("version")

        convert = config.get("convert",{}})
        self._blender_exe = convert.get("blender_exe")

        self._blender_script = convert.get("blender_script")

        self._glb_folder = convert.get("glb_folder")

        self._skp_folder = convert.get("skp_folder")
        self._blend_folder = convert.get("blend_folder")

        self._DEBUG = convert.get("DEBUG")

        dir = config.get("dir",{})

        self._root = dir.get("root")
        self._assets = dir.get("assets")
        self._app = dir.get("app")
        self._pipeline = dir.get("pipeline")

    @property
    def version(self):
        return self._version

    @version.setter
    def version(self,)

def load_config():
    config_exists = False
    path = Path.cwd()

    folders_to_check = ["logs", "data", "config"]

    for directory in [path, *path.parents]:
        if (directory / "config.toml").is_file():
            config_exists = True
            with open(directory/"config.toml","rb") as f:
                data = tomllib.load(f)
        if all(folder for folder in folders_to_check):
            Config()

    if not config_exists:
        print("[CRITICAL] No configuration file found")
    
    

    raise FileNotFoundError("Could not find Funtasia config.toml")
