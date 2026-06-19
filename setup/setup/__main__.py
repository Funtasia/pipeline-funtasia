from phase import Detector, Clone
from terminal import Cursor

import colorama

if __name__ == "__main__":
    colorama.just_fix_windows_console()
    Detector.detection_component()
    Clone.clone_component()
    Cursor.show()