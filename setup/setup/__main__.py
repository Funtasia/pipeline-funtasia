from phase import Detector, Clone
from terminal import Cursor

if __name__ == "__main__":
    try:
        import colorama
        colorama.just_fix_windows_console()
    except ImportError:
        pass
    Detector.detection_component()
    print('\n' * 15, flush=True) # Allow next section to be 15 lines lower as previous section is 15 lines
    Clone.clone_component()
    Cursor.show()