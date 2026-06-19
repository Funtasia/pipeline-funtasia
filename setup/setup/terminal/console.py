from vars import Colour, Box
import shutil
from enum import StrEnum, auto

class Mode(StrEnum):
    def _generate_next_value_(name, start, count, last_values):
        return name.capitalize() # auto() return capitalised string of attribute name

    PRINT = auto()
    RETURN = auto()

class Console:
    @staticmethod
    def parse_escapecodes(escapecodes):
        return "\033[" + ";".join(escapecodes) + "m"
    
    @staticmethod
    def colour_string(txt,colour):
        return Console.parse_escapecodes(colour) + txt + Colour.RESET_CODE

    @staticmethod
    def doublebox(text,escapecodes=[Colour.RESET],mode:Mode=Mode.PRINT):
        
        tbl_lst = []
        total_length = len(text)+10
        centre = total_length-2
        tbl_lst.append(Box.DTL + Box.DH*centre + Box.DTR)
        tbl_lst.append(f"{Box.DV}{text:^{centre}}{Box.DV}")
        tbl_lst.append(Box.DBL + Box.DH*centre + Box.DBR)
        output = Console.parse_escapecodes(escapecodes) + "\n".join(tbl_lst) + Colour.RESET_CODE
        if mode == mode.RETURN:
            return output
        else:
            print(output)

    @staticmethod
    def singlebox(text,buffer=10,escapecodes=[Colour.RESET],mode:Mode=Mode.PRINT):
        
        tbl_lst = []
        total_length = len(text)+buffer
        centre = total_length-2
        tbl_lst.append(Box.TL + Box.H*centre + Box.TR)
        tbl_lst.append(f"{Box.V}{text:^{centre}}{Box.V}")
        tbl_lst.append(Box.BL + Box.H*centre + Box.BR)
        output = Console.parse_escapecodes(escapecodes) + "\n".join(tbl_lst) + Colour.RESET_CODE
        if mode == Mode.RETURN:
            return [Console.parse_escapecodes(escapecodes)] + tbl_lst + [Colour.RESET_CODE]
        else:
            print(output)


    @staticmethod
    def section(title):
        title_texts = Console.singlebox(title,buffer=30,escapecodes=[Colour.BLUE],mode=Mode.RETURN)
        width = shutil.get_terminal_size().columns
        print("\n".join(line.center(width) for line in title_texts))