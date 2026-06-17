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
