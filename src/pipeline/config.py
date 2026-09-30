#!/usr/bin/env python3

import tomllib
from pathlib import Path
import re

from dataclasses import dataclass, field, fields
from typing import Optional, get_origin, get_args


DEFAULT_CONFIG = {
    "app": Path("app-funtasia"),
    "assets": Path("app-funtasia") / "assets-funtasia",
    "blender_exe": "", #TODO Replace with auto detect function
    "blender_script": Path("3dfiles-funtasia") / "misc" / "scripts" / "blender_script.py",
    "glb_folder": Path("app-funtasia") / "assets-funtasia" / "model",
    "skp_folder":Path("3dfiles-funtasia") / ".skp",
    "glb_folder":Path("3dfiles-funtasia") / ".glb",
    "DEBUG": 0,
}

class Config:
    def __init__(self,config:dict[str,dict] = {},default_root: Path = Path('')):
        self.default_root = default_root

        general = config.get("general",{})

        self._version = general.get("version")

        dir = config.get("dir",{})

        self._root = dir.get("root")
        self._assets = dir.get("assets")
        self._app = dir.get("app")


        convert = config.get("convert",{})

        self._blender_exe = convert.get("blender_exe")
        self._blender_script = convert.get("blender_script")
        self._glb_folder = convert.get("glb_folder")
        self._skp_folder = convert.get("skp_folder")
        self._blend_folder = convert.get("blend_folder")

        self._DEBUG = convert.get("DEBUG")


    @property
    def version(self):
        return self._version
    @property
    def root(self):
        return self._root
    @property
    def assets(self):
        return self._assets
    @property
    def app(self):
        return self._app
    @property
    def blender_exe(self):
        return self._blender_exe
    @property
    def blender_script(self):
        return self._blender_script
    @property
    def glb_folder(self):
        return self._glb_folder
    @property
    def skp_folder(self):
        return self.skp_folder
    @property
    def blend_folder(self):
        return self._blend_folder
    @property
    def DEBUG(self):
        return self._DEBUG

    @version.setter
    def version(self,version):
        pattern = r"^v\.\d+\.\d+\.\d+.*$"
        if re.match(pattern,version):
            self._version = version
        else:
            raise TypeError("Configuration for Version is invalid")


    @root.setter
    def root(self,root):
        if path := self.validate_path(root):
            self._root = path
        elif path := self.validate_path(self.default_root):
            self._root = path
        else:
            raise TypeError("Configuration for Root Folder is invalid")

    @assets.setter
    def assets(self,assets):
        if path := self.validate_path(assets):
            self._assets = path
        elif path := self.validate_path(self.root / DEFAULT_CONFIG["assets"]):
            self._assets = path
        else:
            raise TypeError("Configuration for Assets Folder is invalid") 

    @app.setter
    def app(self,app):
        if path := self.validate_path(app):
            self._app = path
        elif path := self.validate_path(self.root / DEFAULT_CONFIG["app"]):
            self._app = path
        else:
            raise TypeError("Configuration for Root Folder is invalid") 

    @blender_exe.setter
    def blender_exe(self,blender_exe):
        if path := self.validate_path(blender_exe):
            self._blender_exe = path
        elif path := self.validate_path(DEFAULT_CONFIG["blender_exe"]):
            self._blender_exe = path
        else:
            raise TypeError("Configuration for Blender Executable is invalid") 

    @blender_script.setter
    def blender_script(self,blender_script):
        if path := self.validate_path(blender_script):
            self._blender_script = path
        elif path := self.validate_path(self.root / DEFAULT_CONFIG["blender_script"]):
            self._blender_script = path
        else:
            raise TypeError("Configuration for Blender Script is invalid")
        
    @glb_folder.setter
    def glb_folder(self,glb_folder):
        if path := self.validate_path(glb_folder):
            self._glb_folder = path
        elif path := self.validate_path(self.root / DEFAULT_CONFIG["glb_folder"]):
            self._glb_folder = path
        else:
            raise TypeError("Configuration for GLB Folder is invalid") 
        
    @skp_folder.setter
    def skp_folder(self,skp_folder):
        if path := self.validate_path(skp_folder):
            self._skp_folder = path
        elif path := self.validate_path(self.root / DEFAULT_CONFIG["skp_folder"]):
            self._skp_folder = path
        else:
            raise TypeError("Configuration for SKP Folder is invalid") 
        
    @blend_folder.setter
    def blend_folder(self,blend_folder):
        if path := self.validate_path(blend_folder):
            self._blend_folder = path
        elif path := self.validate_path(self.root / DEFAULT_CONFIG["blend_folder"]):
            self._blend_folder = path
        else:
            raise TypeError("Configuration for Blend Folder is invalid") 
        
    @DEBUG.setter
    def DEBUG(self,DEBUG):
        if DEBUG.isnumeric():
            self._DEBUG = int(DEBUG)
        else:
            self._DEBUG = 0
            print("[WARNING] Configuration for DEBUG is invalid.  A default of 0 will be used")


    @staticmethod
    def validate_path(path: Path | str) -> Path | bool:
        if not isinstance(path,Path):
            path = Path(path)

        if path.is_absolute() and path.exists():
            return path

        return False
    
    @staticmethod
    def validate_version(version):
        pattern = r"^v\.\d+\.\d+\.\d+.*$"
        if re.match(pattern,version):
            return version
        else:
            raise TypeError("Configuration for Version is inalid.")




def load_config():
    config_exists = False
    path = Path.cwd()

    for directory in [path, *path.parents]:
        if (directory / "config.toml").is_file():
            config_exists = True
            with open(directory/"config.toml","rb") as f:
                data = tomllib.load(f)

            return Config(
                config=data,
                default_root=directory
            )

    if not config_exists:
        print("[CRITICAL] No configuration file found")
    

    raise FileNotFoundError("Could not find Funtasia config.toml")
