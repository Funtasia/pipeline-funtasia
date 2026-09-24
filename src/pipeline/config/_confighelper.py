import tomllib
import tomlkit
from pathlib import Path

class Config:
    CONFIG_PATH = Path(__file__).parent / "config.toml"

    @staticmethod
    def load():
        with Config.CONFIG_PATH.open("rb") as f:
            return tomllib.load(f)

    @staticmethod
    def dump(data):
        with Config.CONFIG_PATH.open("w", encoding="utf-8") as f:
            tomlkit.dump(data, f)


if __name__ == "__main__":
    print(*Config.load().items(),sep="\n")
