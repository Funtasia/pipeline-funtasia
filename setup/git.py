import shutil
import subprocess


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


def detect_git():
    results = []

    # 1. PATH check
    git_path = shutil.which("git")
    if git_path:
        ok, out = _run(["git", "--version"])
        if ok:
            results.append({
                "path": git_path,
                "version": out.replace("git version", "").strip()
            })

    # 2. Windows fallback (Git Bash common location)
    import platform
    if platform.system() == "Windows":
        possible = [
            r"C:\Program Files\Git\bin\git.exe",
            r"C:\Program Files (x86)\Git\bin\git.exe",
            r"C:\Program Files\Git\cmd\git.exe",
        ]

        for p in possible:
            ok, out = _run([p, "--version"])
            if ok:
                results.append({
                    "path": p,
                    "version": out.replace("git version", "").strip()
                })

    return results

print(*detect_git(),sep="\n")