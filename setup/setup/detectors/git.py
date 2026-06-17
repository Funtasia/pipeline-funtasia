import platform
import shutil
import subprocess

class GitDetector:
    @staticmethod
    def _runcmd(cmd):
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
        
    @staticmethod
    def detect_git(progress=None):
        steps = 2
        if platform.system() == "Windows":
            steps =  5
        results = []
    
        # 1. PATH check
        git_path = shutil.which("git")
        progress(1,steps)
        if git_path:
            ok, out = GitDetector._runcmd(["git", "--version"])
            if ok:
                results.append({
                    "path": git_path,
                    "version": out.replace("git version", "").strip()
                })
                progress(2,steps)
    
        # 2. Windows fallback (Git Bash common location)
        if platform.system() == "Windows":
            possible = [
                r"C:\Program Files\Git\bin\git.exe",
                r"C:\Program Files (x86)\Git\bin\git.exe",
                r"C:\Program Files\Git\cmd\git.exe",
            ]
    
            for idx,p in enumerate(possible,start=3):
                ok, out = GitDetector._runcmd([p, "--version"])
                if ok:
                    results.append({
                        "path": p,
                        "version": out.replace("git version", "").strip()
                    })
                progress(idx,steps)
    
        return results
