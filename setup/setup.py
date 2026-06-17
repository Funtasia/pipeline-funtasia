import time
import shutil
import sys
import subprocess
import platform
from pathlib import Path
import os
import threading
import queue
import colorama
from concurrent.futures import ThreadPoolExecutor

colorama.just_fix_windows_console()

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
    ESC = "\033["
    RESET_CODE = "\033[0m"
    RESET = "0"

    # Regular
    BLACK   = "30"
    RED     = "31"
    GREEN   = "32"
    YELLOW  = "33"
    BLUE    = "34"
    MAGENTA = "35"
    CYAN    = "36"
    WHITE   = "37"

    # Bright
    BRIGHT_BLACK   = "90"
    BRIGHT_RED     = "91"
    BRIGHT_GREEN   = "92"
    BRIGHT_YELLOW  = "93"
    BRIGHT_BLUE    = "94"
    BRIGHT_MAGENTA = "95"
    BRIGHT_CYAN    = "96"
    BRIGHT_WHITE   = "97"

    # Styles
    BOLD      = "1"
    DIM       = "2"
    ITALIC    = "3"
    UNDERLINE = "4"

    # Backgrounds
    BG_RED     = "41"
    BG_GREEN   = "42"
    BG_YELLOW  = "43"
    BG_BLUE    = "44"
    BG_MAGENTA = "45"
    BG_CYAN    = "46"
    BG_WHITE   = "47"

class Symbols:
    FULL_BLOCK   = "█"
    LIGHT_SHADE = "░"
    MEDIUM_SHADE = "▒"
    DARK_SHADE = "▓"

class Spinner:
    try:
        "⠋".encode(sys.stdout.encoding or "utf-8")
        BRAILLE_SUPPORTED = True
    except UnicodeEncodeError:
        BRAILLE_SUPPORTED = False

    digits = (
        ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
        if BRAILLE_SUPPORTED
        else [".", "..", "..."]
    )
    length = len(digits)

class Cursor:
    ESC = "\033["

    # ---------- visibility ----------
    @staticmethod
    def hide():
        sys.stdout.write(Cursor.ESC + "?25l")
        sys.stdout.flush()

    @staticmethod
    def show():
        sys.stdout.write(Cursor.ESC + "?25h")
        sys.stdout.flush()

    # ---------- movement ----------
    @staticmethod
    def up(n=1):
        sys.stdout.write(f"{Cursor.ESC}{n}A")
        sys.stdout.flush()

    @staticmethod
    def down(n=1):
        sys.stdout.write(f"{Cursor.ESC}{n}B")
        sys.stdout.flush()

    @staticmethod
    def right(n=1):
        sys.stdout.write(f"{Cursor.ESC}{n}C")
        sys.stdout.flush()

    @staticmethod
    def left(n=1):
        sys.stdout.write(f"{Cursor.ESC}{n}D")
        sys.stdout.flush()

    # ---------- absolute positioning ----------
    @staticmethod
    def move(row, col):
        sys.stdout.write(f"{Cursor.ESC}{row};{col}H")
        sys.stdout.flush()

    @staticmethod
    def home():
        sys.stdout.write(Cursor.ESC + "H")
        sys.stdout.flush()

    # ---------- saving/restoring position ----------
    @staticmethod
    def save():
        sys.stdout.write(Cursor.ESC + "s")
        sys.stdout.flush()

    @staticmethod
    def restore():
        sys.stdout.write(Cursor.ESC + "u")
        sys.stdout.flush()

class Screen:
    ESC = "\033["

    # ---------- screen control ----------
    @staticmethod
    def clear():
        sys.stdout.write(Screen.ESC + "2J")
        sys.stdout.write(Screen.ESC + "H")
        sys.stdout.flush()

    @staticmethod
    def clear_line():
        sys.stdout.write(Screen.ESC + "2K")
        sys.stdout.flush()

    @staticmethod
    def reset():
        sys.stdout.write(Screen.ESC + "0m")
        sys.stdout.flush()

    # ---------- terminal state ----------
    @staticmethod
    def hide_cursor():
        sys.stdout.write(Screen.ESC + "?25l")
        sys.stdout.flush()

    @staticmethod
    def show_cursor():
        sys.stdout.write(Screen.ESC + "?25h")
        sys.stdout.flush()

    # ---------- screen size ----------
    @staticmethod
    def size():
        try:
            return shutil.get_terminal_size()
        except Exception:
            return shutil.terminal_size((80, 24))

    # ---------- drawing helpers ----------
    @staticmethod
    def write(x, y, text):
        sys.stdout.write(f"{Screen.ESC}{y};{x}H{text}")
        sys.stdout.flush()

    @staticmethod
    def write_center(text, y=None):
        size = Screen.size()
        if y is None:
            y = size.lines // 2
        x = max(1, (size.columns - len(text)) // 2)
        Screen.write(x, y, text)

    @staticmethod
    def refresh():
        sys.stdout.flush()

    # ---------- scrolling ----------
    @staticmethod
    def scroll_up(n=1):
        sys.stdout.write(f"{Cursor.ESC}{n}S")
        sys.stdout.flush()

    @staticmethod
    def scroll_down(n=1):
        sys.stdout.write(f"{Cursor.ESC}{n}T")
        sys.stdout.flush()

    # ---------- buffering mode ----------
    @staticmethod
    def enable_alt_buffer():
        sys.stdout.write(Screen.ESC + "?1049h")
        sys.stdout.flush()

    @staticmethod
    def disable_alt_buffer():
        sys.stdout.write(Screen.ESC + "?1049l")
        sys.stdout.flush()



class Detector:
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
        

    progress_state = {}
    results = {}
    components = {}
    status_queue = queue.Queue()

    @staticmethod
    def _make_progress(name):
        return lambda c, t: Detector.status_queue.put(
            ("progress", name, c, t)
        )

    @staticmethod
    def _detectionrender():
        Screen.clear()

        console.section("Detecting Software")

        for name, (cur, total) in Detector.progress_state.items():
            bar_len = 20
            filled = int((cur / total) * bar_len)
            bar = "#" * filled + " " * (bar_len - filled)

            print(
                f"Searching for {name:<10} [{bar}] {cur}/{total}"
            )

        sys.stdout.flush()

    @staticmethod
    def _detection_run():

        with ThreadPoolExecutor(max_workers=3) as pool:

            futures = {
                pool.submit(
                    func,
                    Detector._make_progress(name)
                ): name
                for name, func in Detector.components.items()
            }

            running = True

            while running:

                while True:
                    try:
                        msg = Detector.status_queue.get_nowait()
                    except queue.Empty:
                        break

                    if msg[0] == "progress":
                        _, name, cur, total = msg
                        Detector.progress_state[name] = (
                            min(cur, total),
                            total,
                        )

                Detector._detectionrender()

                running = not all(
                    f.done() for f in futures
                )

                time.sleep(0.05)

            while True:
                try:
                    msg = Detector.status_queue.get_nowait()
                except queue.Empty:
                    break

                if msg[0] == "progress":
                    _, name, cur, total = msg
                    Detector.progress_state[name] = (
                        min(cur, total),
                        total,
                    )

            Detector._detectionrender()

            for f in futures:
                name = futures[f]
                Detector.results[name] = f.result()

        print(
            "\n\nDONE:",
            *Detector.results.items(),
            sep="\n"
        )

    @staticmethod
    def detection_component():

        Screen.clear()
        Screen.hide_cursor()

        Detector.progress_state = {
            "Git": (0, 1),
            "Blender": (0, 1),
            "SketchUp": (0, 1),
        }

        Detector.results = {}

        Detector.components = {
            "Git": lambda p: GitDetector.detect_git(progress=p),
            "Blender": lambda p: BlenderDetector.detect_blender_all(progress=p),
            "SketchUp": lambda p: SketchupDetector.detect_sketchup_all(progress=p),
        }

        Detector.status_queue = queue.Queue()

        Detector._detection_run()


class GitDetector:
    @staticmethod
    def detect_git(progress=None):
        steps = 5
        results = []
    
        # 1. PATH check
        git_path = shutil.which("git")
        progress(1,steps)
        if git_path:
            ok, out = Detector._runcmd(["git", "--version"])
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
                ok, out = Detector._runcmd([p, "--version"])
                if ok:
                    results.append({
                        "path": p,
                        "version": out.replace("git version", "").strip()
                    })
                progress(idx,steps)
    
        time.sleep(1)
        return results
    
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
    
        time.sleep(1)
        return list(unique.values())
    
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

class console:
    @staticmethod
    def parse_escapecodes(escapecodes):
        return "\033[" + ";".join(escapecodes) + "m"

    @staticmethod
    def doublebox(text,escapecodes=[Colour.RESET],mode='PRINT'):
        
        tbl_lst = []
        total_length = len(text)+10
        centre = total_length-2
        tbl_lst.append(Box.DTL + Box.DH*centre + Box.DTR)
        tbl_lst.append(f"{Box.DV}{text:^{centre}}{Box.DV}")
        tbl_lst.append(Box.DBL + Box.DH*centre + Box.DBR)
        output = console.parse_escapecodes(escapecodes) + "\n".join(tbl_lst) + Colour.RESET_CODE
        if mode == "RETURN":
            return output
        else:
            print(output)

    @staticmethod
    def singlebox(text,buffer=10,escapecodes=[Colour.RESET],mode='PRINT'):
        
        tbl_lst = []
        total_length = len(text)+buffer
        centre = total_length-2
        tbl_lst.append(Box.TL + Box.H*centre + Box.TR)
        tbl_lst.append(f"{Box.V}{text:^{centre}}{Box.V}")
        tbl_lst.append(Box.BL + Box.H*centre + Box.BR)
        output = console.parse_escapecodes(escapecodes) + "\n".join(tbl_lst) + Colour.RESET_CODE
        if mode == "RETURN":
            return [console.parse_escapecodes(escapecodes)] + tbl_lst + [Colour.RESET_CODE]
        else:
            print(output)


    @staticmethod
    def section(title):
        title_texts = console.singlebox(title,buffer=30,escapecodes=[Colour.BLUE],mode='RETURN')
        width = shutil.get_terminal_size().columns
        print("\n".join(line.center(width) for line in title_texts))





if __name__ == "__main__":
    Detector.detection_component()