print("\033[41mHello\033[0m")
print(
    f"{Colour.BG_BLUE}{Colour.BRIGHT_WHITE}"
    f"{Box.DTL}{Box.DH*20}{Box.DTR}"
    f"{Colour.RESET}"
)

colour = Colour.BRIGHT_WHITE + Colour.BG_BLUE

print(
    f"{colour}"
    f"{Box.DTL}{Box.DH*20}{Box.DTR}\n"
    f"{Box.DV}{'Hello':^20}{Box.DV}\n"
    f"{Box.DBL}{Box.DH*20}{Box.DBR}"
    f"{Colour.RESET}"
)

SUCCESS = Colour.BLACK + Colour.BG_GREEN
WARNING = Colour.BLACK + Colour.BG_YELLOW
ERROR   = Colour.WHITE + Colour.BG_RED
INFO    = Colour.WHITE + Colour.BG_BLUE

print(f"{SUCCESS} SUCCESS {Colour.RESET}")
print(f"{WARNING} WARNING {Colour.RESET}")
print(f"{ERROR} ERROR {Colour.RESET}")