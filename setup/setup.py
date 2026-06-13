import time
class Box:
    H = "─"
    V = "│"
    TL = "┌"
    TR = "┐"
    BL = "└"
    BR = "┘"

    DH = "═"
    DV = "║"
    DTL = "╔"
    DTR = "╗"
    DBL = "╚"
    DBR = "╝"

    DL = "╠"
    DR = "╣"
    DT = "╦"
    DB = "╩"
    CROSS = "╬"

class Colour:
    RESET = "\033[0m"

    # Regular
    BLACK   = "\033[30m"
    RED     = "\033[31m"
    GREEN   = "\033[32m"
    YELLOW  = "\033[33m"
    BLUE    = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN    = "\033[36m"
    WHITE   = "\033[37m"

    # Bright
    BRIGHT_BLACK   = "\033[90m"
    BRIGHT_RED     = "\033[91m"
    BRIGHT_GREEN   = "\033[92m"
    BRIGHT_YELLOW  = "\033[93m"
    BRIGHT_BLUE    = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN    = "\033[96m"
    BRIGHT_WHITE   = "\033[97m"

    # Styles
    BOLD      = "\033[1m"
    DIM       = "\033[2m"
    ITALIC    = "\033[3m"
    UNDERLINE = "\033[4m"

    # Backgrounds
    BG_RED     = "\033[41m"
    BG_GREEN   = "\033[42m"
    BG_YELLOW  = "\033[43m"
    BG_BLUE    = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN    = "\033[46m"
    BG_WHITE   = "\033[47m"

class Symbols:
    FULL_BLOCK   = "█"
    LIGHT_SHADE = "░"
    MEDIUM_SHADE = "▒"
    DARK_SHADE = "▓"

class console:

    @staticmethod
    def doublebox(msg,colour='\033[0m'):
        tbl_lst = []
        total_length = len(msg)+10
        centre = total_length-2
        tbl_lst.append(Box.DTL + Box.DH*centre + Box.DTR)
        tbl_lst.append(f"{Box.DV}{msg:^{centre}}{Box.DV}")
        tbl_lst.append(Box.DBL + Box.DH*centre + Box.DBR)
        output = Colour.BRIGHT_GREEN + "\n".join(tbl_lst) + Colour.RESET
        print(output)

    @staticmethod
    def singlebox(msg,colour='\033[0m'):
        tbl_lst = []
        total_length = len(msg)+10
        centre = total_length-2
        tbl_lst.append(Box.TL + Box.H*centre + Box.TR)
        tbl_lst.append(f"{Box.V}{msg:^{centre}}{Box.V}")
        tbl_lst.append(Box.BL + Box.H*centre + Box.BR)
        output = colour + "\n".join(tbl_lst) + Colour.RESET
        print(output)

   

console.doublebox("Hello gng",colour=Colour.BRIGHT_GREEN)
console.singlebox(Symbols.FULL_BLOCK*10,colour=Colour.BRIGHT_MAGENTA)

print("\u2588")  # █
print("\u2591")  # ░

import sys

def progress(current, total, task="Installing"):
    width = 32

    percent = current / total
    filled = int(width * percent)

    bar = "█" * filled + " " * (width - filled)

    sys.stdout.write(
        f"\r{task:<18} │{bar}│ {percent:>6.1%}"
    )

    sys.stdout.flush()

    if current == total:
        print()

def progress_percent(percent, task="Working"):
    width = 32

    filled = int(width * percent / 100)

    bar = "█" * filled + "─" * (width - filled)

    print(
        f"\r{task:<18} │{bar}│ {percent:6.1f}%",
        end="",
        flush=True
    )

    if percent >= 100:
        print()


import shutil
import subprocess
from pathlib import Path

def detect_git():
    if not shutil.which('git'):
        return False
    try:
        result = subprocess.run(
            ["git","--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False
    
import os
import platform
import subprocess
import shutil
from pathlib import Path


# ----------------------------
# Helpers
# ----------------------------

def _run(cmd):
    try:
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=5
        )
        return p.returncode == 0, p.stdout + p.stderr
    except Exception:
        return False, ""


def _version(blender_path):
    ok, out = _run([blender_path, "--version"])
    if not ok:
        return None
    return out.splitlines()[0].strip()


# ----------------------------
# Linux detection
# ----------------------------

def _linux_find_blender():
    # 1. PATH
    path = shutil.which("blender")
    if path:
        return path

    # 2. common locations
    candidates = [
        "/usr/bin/blender",
        "/usr/local/bin/blender",
        "/opt/blender/blender",
        "/snap/bin/blender",
    ]

    for c in candidates:
        if Path(c).exists():
            return c

    # 3. Flatpak
    try:
        ok, out = _run(["flatpak", "list"])
        if ok and "Blender" in out:
            return "flatpak run org.blender.Blender"
    except Exception:
        pass

    return None


# ----------------------------
# Windows detection
# ----------------------------

def _windows_find_blender():
    # 1. PATH first (best case)
    path = shutil.which("blender.exe")
    if path:
        return path

    # 2. Standard install locations
    roots = [
        Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")),
        Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")),
    ]

    for root in roots:
        base = root / "Blender Foundation"

        if not base.exists():
            continue

        # THIS is the missing part: version subfolders
        for version_folder in base.glob("Blender*"):
            exe = version_folder / "blender.exe"

            if exe.exists():
                return str(exe)

            # sometimes nested installs (rare but happens)
            for deeper in version_folder.rglob("blender.exe"):
                return str(deeper)

# ----------------------------
# macOS detection
# ----------------------------

def _mac_find_blender():
    # 1. PATH
    path = shutil.which("blender")
    if path:
        return path

    # 2. Applications folder
    apps = Path("/Applications")
    if apps.exists():
        for p in apps.glob("Blender*.app"):
            exe = p / "Contents" / "MacOS" / "Blender"
            if exe.exists():
                return str(exe)

    return None


# ----------------------------
# Public API
# ----------------------------

def detect_blender():
    system = platform.system()

    if system == "Windows":
        path = _windows_find_blender()
    elif system == "Darwin":
        path = _mac_find_blender()
    else:
        path = _linux_find_blender()

    if not path:
        return False, None, None

    version = _version(path)
    return True, path, version


print(detect_blender())