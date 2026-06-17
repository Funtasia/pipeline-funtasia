import os
import sys
import platform
import shutil
import subprocess
from pathlib import Path


# =========================================================
# ANSI UI
# =========================================================

class Colour:
    RESET = "\033[0m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"


class Box:
    H = "─"
    V = "│"
    TL = "┌"
    TR = "┐"
    BL = "└"
    BR = "┘"


# =========================================================
# Helpers
# =========================================================

def _run(cmd):
    try:
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=5
        )
        return p.returncode == 0, (p.stdout + p.stderr).strip()
    except Exception:
        return False, ""


def _bar(current, total, width=30):
    percent = current / total
    filled = int(width * percent)
    return "█" * filled + "░" * (width - filled), percent


def _print_progress(i, total, label):
    bar, pct = _bar(i, total)
    sys.stdout.write(
        f"\r{label:<15} │{bar}│ {pct*100:6.1f}%"
    )
    sys.stdout.flush()
    if i == total:
        print()


# =========================================================
# Python detector
# =========================================================

def detect_python():
    results = {}

    def version(exe):
        ok, out = _run([exe, "--version"])
        return out.replace("Python", "").strip() if ok else None

    results[sys.executable] = version(sys.executable)

    for c in ["python", "python3", "py"]:
        p = shutil.which(c)
        if p:
            results[p] = version(p)

    return [
        {"name": "Python", "path": k, "version": v}
        for k, v in results.items()
        if v
    ]


# =========================================================
# Git detector
# =========================================================

def detect_git():
    results = []

    git = shutil.which("git")
    if git:
        ok, out = _run(["git", "--version"])
        if ok:
            results.append({
                "name": "Git",
                "path": git,
                "version": out.replace("git version", "").strip()
            })

    return results


# =========================================================
# Blender detector
# =========================================================

def detect_blender():
    found = []

    def version(p):
        ok, out = _run([p, "--version"])
        if ok and "Blender" in out:
            return out.splitlines()[0].strip()
        return None

    # PATH
    p = shutil.which("blender")
    if p:
        found.append(p)

    # Windows / Linux / Mac common search
    roots = []

    if platform.system() == "Windows":
        roots = [
            Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")),
            Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")),
        ]
    elif platform.system() == "Darwin":
        roots = [Path("/Applications")]
    else:
        roots = [Path("/usr"), Path("/opt"), Path.home()]

    for root in roots:
        if not root.exists():
            continue
        for exe in root.rglob("blender*"):
            if exe.is_file() and "blender" in exe.name.lower():
                found.append(str(exe))

    unique = list(set(found))

    return [
        {
            "name": "Blender",
            "path": p,
            "version": version(p)
        }
        for p in unique
        if version(p)
    ]


# =========================================================
# SketchUp detector (no execution)
# =========================================================

def detect_sketchup():
    found = []

    if platform.system() == "Windows":
        roots = [
            Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")),
            Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")),
        ]

        for root in roots:
            base = root / "SketchUp"
            if not base.exists():
                continue

            for exe in base.rglob("SketchUp.exe"):
                found.append(exe)

    elif platform.system() == "Darwin":
        apps = Path("/Applications")
        if apps.exists():
            for app in apps.glob("SketchUp*.app"):
                exe = app / "Contents/MacOS/SketchUp"
                if exe.exists():
                    found.append(exe)

    else:
        wine = Path.home() / ".wine"
        if wine.exists():
            for exe in wine.rglob("SketchUp.exe"):
                found.append(exe)

    def infer_version(p):
        parts = Path(p).parts
        for part in parts:
            if "SketchUp" in part:
                return part.replace("SketchUp", "").strip()
        return None

    return [
        {
            "name": "SketchUp",
            "path": str(p),
            "version": infer_version(p)
        }
        for p in set(found)
    ]


# =========================================================
# Audit engine
# =========================================================

def run_audit():
    checks = [
        ("Python", detect_python),
        ("Git", detect_git),
        ("Blender", detect_blender),
        ("SketchUp", detect_sketchup),
    ]

    total = len(checks)
    all_results = []

    print(Colour.BOLD + "\nSYSTEM AUDIT\n" + Colour.RESET)

    for i, (name, fn) in enumerate(checks, start=1):
        _print_progress(i, total, "Checking")

        results = fn()
        all_results.extend(results)

    print("\n")

    # =====================================================
    # Output table
    # =====================================================

    print(Box.TL + "─" * 70 + Box.TR)
    print(f"{Box.V} {'SOFTWARE':<10} {'VERSION':<20} {'PATH'}")
    print(Box.V + "─" * 70 + Box.V)

    for r in all_results:
        ver = r["version"] or "unknown"
        path = r["path"]

        print(f"{Box.V} {r['name']:<10} {ver:<20} {path}")

    print(Box.BL + "─" * 70 + Box.BR)


# =========================================================
# Run
# =========================================================

if __name__ == "__main__":
    run_audit()