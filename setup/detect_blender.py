import subprocess
import os
from pathlib import Path
import shutil
import platform


    
def _windows_find_blender_all():
    found = []

    # 1. PATH
    path = shutil.which("blender.exe")
    if path:
        found.append(path)

    roots = [
        Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")),
        Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")),
    ]

    for root in roots:
        base = root / "Blender Foundation"

        if not base.exists():
            continue

        for exe in base.rglob("blender.exe"):
            found.append(str(exe))

    return list(set(found))

def _linux_find_blender_all():

    found = []

    path = shutil.which("blender")
    if path:
        found.append(path)

    candidates = [
        "/usr/bin/blender",
        "/usr/local/bin/blender",
        "/opt/blender/blender",
        "/snap/bin/blender",
    ]

    for c in candidates:
        if Path(c).exists():
            found.append(c)

    return list(set(found))

def _mac_find_blender_all():

    found = []

    path = shutil.which("blender")
    if path:
        found.append(path)

    apps = Path("/Applications")

    if apps.exists():
        for p in apps.glob("Blender*.app"):
            exe = p / "Contents/MacOS/Blender"
            if exe.exists():
                found.append(str(exe))

    return list(set(found))

def detect_blender_all():
    system = platform.system()

    if system == "Windows":
        paths = _windows_find_blender_all()
    elif system == "Darwin":
        paths = _mac_find_blender_all()
    else:
        paths = _linux_find_blender_all()

    results = []

    for p in paths:
        v = _version(p)
        results.append({
            "path": p,
            "version": v
        })

    # remove duplicates (same version installs etc.)
    unique = {r["path"]: r for r in results}

    return list(unique.values())



for b in detect_blender_all():
    print(b["version"], "->", b["path"])