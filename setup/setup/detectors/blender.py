import shutil
import os
from pathlib import Path
import subprocess
import platform
import time

class BlenderDetector:
    @staticmethod
    def _version(path):
        try:
            p = subprocess.run(
                [path, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
    
            if p.returncode != 0:
                return None
    
            return p.stdout.splitlines()[0].strip()
    
        except Exception:
            return None
        
    @staticmethod
    def _windows_find_blender_all(progress=None):
        steps = 3
        found = []
    
        # 1. PATH
        path = shutil.which("blender.exe")
        if path:
            found.append(path)
        progress(1,steps)
    
        roots = [
            Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")),
            Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")),
        ]
    
        for idx,r in enumerate(roots,start=2):
            base = r / "Blender Foundation"
    
            if base.exists():    
                for exe in base.rglob("blender.exe"):
                    found.append(str(exe))
            progress(idx,steps)

        time.sleep(1)
        return list(set(found))
    
    @staticmethod
    def _linux_find_blender_all(progress=None):
        steps = 5
        found = []
    
        path = shutil.which("blender")
        if path:
            found.append(path)
        progress(1,steps)
        candidates = [
            "/usr/bin/blender",
            "/usr/local/bin/blender",
            "/opt/blender/blender",
            "/snap/bin/blender",
        ]
    
        for idx,c in enumerate(candidates,start=2):
            if Path(c).exists():
                found.append(c)
            progress(idx,steps)
    
        time.sleep(1)
        return list(set(found))
    
    @staticmethod
    def _mac_find_blender_all(progress=None):
        steps = 2
        found = []
    
        path = shutil.which("blender")
        if path:
            found.append(path)
        progress(1,2)
    
        apps = Path("/Applications")
    
        if apps.exists():
            for p in apps.glob("Blender*.app"):
                exe = p / "Contents/MacOS/Blender"
                if exe.exists():
                    found.append(str(exe))
        progress(2,2)
    
        time.sleep(0.5)
        return list(set(found))
    
    @staticmethod
    def detect_blender_all(progress=None):
        system = platform.system()
    
        if system == "Windows":
            paths = BlenderDetector._windows_find_blender_all(progress)
        elif system == "Darwin":
            paths = BlenderDetector._mac_find_blender_all(progress)
        else:
            paths = BlenderDetector._linux_find_blender_all(progress)
    
        results = []
    
        for p in paths:
            v = BlenderDetector._version(p)
            results.append({
                "path": p,
                "version": v
            })
    
        # remove duplicates (same version installs etc.)
        unique = {r["path"]: r for r in results}
    
        return list(unique.values())
