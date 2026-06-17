from pathlib import Path
import os
import platform

class SketchupDetector:
    @staticmethod
    def _windows_find_sketchup_all(progress=None):
        steps = 2
        found = []
    
        roots = [
            Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")),
            Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")),
        ]
    
        for idx,r in enumerate(roots,start=1):
            base = r / "SketchUp"
            

            if base.exists():
    
                for version_folder in base.glob("SketchUp*"):
                    exe = version_folder / "SketchUp.exe"
        
                    if exe.exists():
                        found.append(str(exe))
        
                    # fallback deep scan (rare edge cases)
                    for deep in version_folder.rglob("SketchUp.exe"):
                        found.append(str(deep))

            progress(idx,steps)
    
        return list(set(found))

    @staticmethod
    def _mac_find_sketchup_all(progress=None):
        steps = 1
        found = []
    
        apps = Path("/Applications")
    
        if apps.exists():
            for app in apps.glob("SketchUp*.app"):
                exe = app / "Contents/MacOS/SketchUp"
                if exe.exists():
                    found.append(str(exe))

        progress(1,steps)

        return list(set(found))
    
    @staticmethod
    def _linux_find_sketchup_all(progress=None):
        steps = 2
        found = []
    
        wine_paths = [
            Path.home() / ".wine/drive_c/Program Files/SketchUp",
            Path.home() / ".wine/drive_c/Program Files (x86)/SketchUp",
        ]
    
        for idx,p in enumerate(wine_paths,start=1):
            if p.exists():
                for exe in p.rglob("SketchUp.exe"):
                    found.append(str(exe))

            progress(idx,steps)
    
        return list(set(found))
    
    @staticmethod
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
    
    @staticmethod
    def detect_sketchup_all(progress=None):
        system = platform.system()
    
        if system == "Windows":
            paths = SketchupDetector._windows_find_sketchup_all(progress)
        elif system == "Darwin":
            paths = SketchupDetector._mac_find_sketchup_all(progress)
        else:
            paths = SketchupDetector._linux_find_sketchup_all(progress)
    
        results = []
    
        for p in paths:
            results.append({
                "path": p,
                "version": SketchupDetector._infer_version(p)
            })
    
        return results
