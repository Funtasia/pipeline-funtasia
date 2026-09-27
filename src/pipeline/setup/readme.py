import sys
from pathlib import Path

if sys.version_info >= (3, 14):
    from shutil import copy

def copy_readme(force: bool = False):
    readme = Path(__file__).parent / "README.md"
    destination = Path() / "README.md"

    if not force and destination.exists():
        raise FileExistsError

    if sys.version_info >= (3, 14):
        readme.copy(destination)
    else:
        copy(readme, destination)