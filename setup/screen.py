import sys
import os

class Screen:
    ESC = "\x1b["

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
            return os.get_terminal_size()
        except OSError:
            return os.terminal_size((80, 24))

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

    # ---------- buffering mode ----------
    @staticmethod
    def enable_alt_buffer():
        sys.stdout.write(Screen.ESC + "?1049h")
        sys.stdout.flush()

    @staticmethod
    def disable_alt_buffer():
        sys.stdout.write(Screen.ESC + "?1049l")
        sys.stdout.flush()




import time
import sys

box = "⣿"
spinner = [
    "⠋","⠙","⠹","⠸","⠼",
    "⠴","⠦","⠧","⠇","⠏"
]
print("\033[2J\033[H", end="")
Screen.hide_cursor()


print(f"  [1/3] Detecting Git")
print(f"  [2/3] Detecting Blender")
print(f"  [3/3] Detecting Sketchup")
print()

width = 32
for i in range(1000):

    filled = int(width * (i/10) / 100)

    bar = "█" * filled + "─" * (width - filled)
    frame = spinner[i % len(spinner)]

    progress = min(i // 2, 20)
    Screen.write(1,1,frame)
    Screen.write(1,5,f"\r{"Detecting Git":<18} │{bar}│ {i/10:6.1f}%")

    sys.stdout.flush()
    time.sleep(0.1)
