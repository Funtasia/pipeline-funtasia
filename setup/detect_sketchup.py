import os
import platform
import shutil
from pathlib import Path


# ----------------------------
# Windows
# ----------------------------

def _windows_find_sketchup_all():
    found = []

    roots = [
        Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")),
        Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")),
    ]

    for root in roots:
        base = root / "SketchUp"

        if not base.exists():
            continue

        # Structure:
        # SketchUp / SketchUp 2024 / SketchUp.exe
        for version_folder in base.glob("SketchUp*"):
            exe = version_folder / "SketchUp.exe"

            if exe.exists():
                found.append(str(exe))

            # fallback deep scan (rare edge cases)
            for deep in version_folder.rglob("SketchUp.exe"):
                found.append(str(deep))

    return list(set(found))


# ----------------------------
# macOS
# ----------------------------

def _mac_find_sketchup_all():
    found = []

    apps = Path("/Applications")

    if apps.exists():
        for app in apps.glob("SketchUp*.app"):
            exe = app / "Contents/MacOS/SketchUp"
            if exe.exists():
                found.append(str(exe))

    return list(set(found))


# ----------------------------
# Linux (usually Wine only)
# ----------------------------

def _linux_find_sketchup_all():
    found = []

    wine_paths = [
        Path.home() / ".wine/drive_c/Program Files/SketchUp",
        Path.home() / ".wine/drive_c/Program Files (x86)/SketchUp",
    ]

    for base in wine_paths:
        if base.exists():
            for exe in base.rglob("SketchUp.exe"):
                found.append(str(exe))

    return list(set(found))


# ----------------------------
# Version inference (NO EXECUTION)
# ----------------------------

def _infer_version(path):
    """
    SketchUp usually encodes version in folder name:
    e.g. SketchUp 2023, SketchUp 2024
    """

    parts = Path(path).parts

    for part in parts:
        if "SketchUp" in part:
            # try extract year/version number
            tokens = part.replace("SketchUp", "").strip()
            if tokens:
                return tokens.strip()

    return None


# ----------------------------
# Public API
# ----------------------------

def detect_sketchup_all():
    system = platform.system()

    if system == "Windows":
        paths = _windows_find_sketchup_all()
    elif system == "Darwin":
        paths = _mac_find_sketchup_all()
    else:
        paths = _linux_find_sketchup_all()

    results = []

    for p in paths:
        results.append({
            "path": p,
            "version": _infer_version(p)
        })

    return results


# ----------------------------
# Example usage
# ----------------------------

if __name__ == "__main__":
    for app in detect_sketchup_all():
        print(app["version"], "->", app["path"])