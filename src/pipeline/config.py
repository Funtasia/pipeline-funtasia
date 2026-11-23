# run `python -m pipeline.config`` to dump config

import logging
import platform
from configparser import ConfigParser
from pathlib import Path

from .__about__ import version

FILENAME = "nipple_config.ini"

logger = logging.getLogger(__name__)


def get_blender_exe(force_default=False) -> str:
    if platform.system() == "Windows":
        # version agnostic
        matches = list(
            Path("C:/Program Files").glob("Blender Foundation/Blender*/blender.exe")
        )
        if not matches:
            if force_default:
                return "blender.exe"
            raise NotImplementedError(
                f"Cannot detect blender, please make sure it is "
                f"installed and put its path in {FILENAME}."
            )
        elif len(matches) > 1:
            print(f"Multiple blender found. Specify correct version in {FILENAME}")
        return str(matches[0])

    elif platform.system() == "Linux":
        blender_exe = "/usr/bin/blender"  # wow such nice path
    elif platform.system() == "Darwin":
        blender_exe = "/Applications/Blender.app/Contents/MacOS/Blender"
    else:
        raise NotImplementedError(f"bro wtf why are you on {platform.system()}")

    if not force_default and not Path(blender_exe).exists():
        raise NotImplementedError(
            f"Cannot detect blender, please make sure it is "
            f"installed and put its path in {FILENAME}."
        )

    return blender_exe


DEFAULT_CONFIG_OVERRIDES = {
    "general": {
        "version": version,
    },
    "dir": {
        "root": str(Path().absolute()),
    },
    "model_convert": {
        "blender_exe": get_blender_exe(force_default=True),
    },
}


def get_default_config(comments=False) -> ConfigParser:
    """
    Get the default config and apply the host-specific overrides.

    `comments` for whether to include comments inside the configuration
    as keys with no values.
    """
    # See https://stackoverflow.com/a/52306763
    # set comment_prefixes to a string which you will not use in the config file
    if comments:
        config = ConfigParser(comment_prefixes="/", allow_no_value=True)
    else:
        config = ConfigParser()

    config_file_path = Path(__file__).parent / FILENAME
    with open(config_file_path) as f:
        config.read_file(f)

    config.read_dict(DEFAULT_CONFIG_OVERRIDES)

    return config


def load_config(force_default=False) -> ConfigParser:
    path = Path.cwd()

    for directory in (path, *path.parents):
        if (directory / FILENAME).is_file():
            with open(directory / FILENAME) as f:
                cfg = ConfigParser()
                cfg.read_file(f)

            return cfg

    if force_default:
        logger.warn("No configuration file found, using default configuration")
        return get_default_config()

    else:
        raise FileNotFoundError(
            "Cannot find config file in current directory or parents."
        )


def write_default_config(overwrite=False):
    """
    Set root to cwd and write default config to root.

    Should be run only once to setup.
    """
    destination = Path(FILENAME)
    if destination.exists():
        if not overwrite:
            raise FileExistsError(f"'{destination.absolute()}' already exists")
        else:
            logger.info(f"Overwriting existing file '{destination.absolute()}'")

    with open(FILENAME, "w") as f:
        get_default_config(comments=True).write(f)


if __name__ == "__main__":
    from rich.pretty import pprint
    config = load_config()
    pprint(dict((section, dict(body)) for section, body in config.items()))
