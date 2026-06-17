import sys
import shutil
from .cursor import Cursor
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