#!/usr/bin/env python3

import tomllib
from pathlib import Path
import re

from dataclasses import dataclass, field, fields
from typing import Optional, get_origin, get_args



class Config:
    def __init__(self,config:dict[str,dict] = {}):

        dir = config.get("dir",{})

        self._root = Config.valid_path(dir.get("root",""),"Root Folder")
        self._assets = Config.valid_path(self._root / dir.get("assets",""),"Assets Folder")
        self._app = Config.valid_path(self._root / dir.get("app",""), "App Folder")
        self._pipeline = Config.valid_path(self._root / dir.get("pipeline",""),"Pipeline Folder")


        general = config.get("general",{})

        self.version = self.valid_version(general.get("version"))

        convert = config.get("convert",{})

        self._blender_exe = Config.valid_path(convert.get("blender_exe",""),"Blender Executable")
        self._blender_script = Config.valid_path(self._root / convert.get("blender_script",""),"Blender Script")
        self._glb_folder = Config.valid_path(self._root / convert.get("glb_folder",""),"GLB Folder")
        self._skp_folder = Config.valid_path(convert.get("skp_folder",""),"SKP Folder")
        self._blend_folder = Config.valid_path(convert.get("blend_folder",""),"Blend Folder")

        debug = convert.get("DEBUG","")
        self._DEBUG = debug if debug.isnumeric() else 0



    @staticmethod
    def valid_path(path:str,config_name) -> Path | bool:
        _path = Path(path)
        if isinstance(_path,Path) and _path.exists() and _path.is_absolute():
            return _path
        else:
            raise TypeError(f"Incorrect configuration for {config_name}")

    @staticmethod
    def valid_version(version):
        pattern = r"^v\.\d+\.\d+\.\d+.*$"
        if re.match(pattern,version):
            return version
        else:
            raise TypeError(f"Incorrect configuration for Version")




def load_config():
    config_exists = False
    path = Path.cwd()

    folders_to_check = ["logs", "data", "config"]

    for directory in [path, *path.parents]:
        if (directory / "config.toml").is_file():
            config_exists = True
            with open(directory/"config.toml","rb") as f:
                data = tomllib.load(f)
        if all((directory / folder).exists() for folder in folders_to_check):
            Config()

    if not config_exists:
        print("[CRITICAL] No configuration file found")
    
    

    raise FileNotFoundError("Could not find Funtasia config.toml")
