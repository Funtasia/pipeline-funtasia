#!/usr/bin/env python3

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








    
    







if __name__ == "__main__":
    Detector.detection_component()
    print("\033[0m]")