from phase import Detector, Clone
from terminal import Cursor

if __name__ == "__main__":
    try:
        import colorama
        colorama.just_fix_windows_console()
    except ImportError:
        pass
    Detector.detection_component()
    Clone.clone_component()
    Cursor.show()