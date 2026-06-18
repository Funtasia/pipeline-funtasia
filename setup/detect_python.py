import sys
import shutil
import subprocess
from pathlib import Path


def _run(cmd):
    try:
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=5
        )
        return p.returncode == 0, p.stdout.strip()
    except Exception:
        return False, ""


def _python_version(exe):
    ok, out = _run([exe, "--version"])
    if not ok:
        return None

    # Python 3.12.1 -> clean parsing
    if "Python" in out:
        return out.replace("Python", "").strip()

    return None


def detect_python_all():
    found = {}

    # 1. current interpreter (always valid)
    found[sys.executable] = _python_version(sys.executable)

    # 2. PATH-based detection
    candidates = ["python", "python3", "py", "python.exe"]

    for c in candidates:
        path = shutil.which(c)
        if path:
            found[path] = _python_version(path)

    # 3. Windows launcher (py.exe) extra check
    if sys.platform == "win32":
        for v in ["-0p", "-3", "-3.12", "-3.11", "-3.10"]:
            ok, out = _run(["py", v, "--version"])
            if ok:
                found[f"py {v}"] = out

    # remove None versions cleanly
    return [
        {"path": k, "version": v}
        for k, v in found.items()
        if v is not None
    ]

print(*detect_python_all(),sep="\n")