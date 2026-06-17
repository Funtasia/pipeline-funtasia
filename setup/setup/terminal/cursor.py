import sys
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
