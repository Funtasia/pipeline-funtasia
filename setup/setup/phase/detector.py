import queue
from detectors import GitDetector, BlenderDetector, SketchupDetector
from terminal import Console, Screen, Cursor
from concurrent.futures import ThreadPoolExecutor
import sys
import time

class Detector:     
    progress_state = {}
    results = {}
    components = {}
    status_queue = queue.Queue()

    @staticmethod
    def _make_progress(name):
        return lambda c, t: Detector.status_queue.put(
            ("progress", name, c, t)
        )

    @staticmethod
    def _detectionrender():
        Cursor.home()

        Console.section("Detecting Software")

        for name, (cur, total) in Detector.progress_state.items():
            bar_len = 20
            filled = int((cur / total) * bar_len)
            bar = "#" * filled + " " * (bar_len - filled)

            print(
                f"Searching for {name:<10} [{bar}] {cur}/{total}"
            )

        sys.stdout.flush()

    @staticmethod
    def _detection_run():

        with ThreadPoolExecutor(max_workers=3) as pool:

            futures = {
                pool.submit(
                    func,
                    Detector._make_progress(name)
                ): name
                for name, func in Detector.components.items()
            }

            running = True

            while running:

                while True:
                    try:
                        msg = Detector.status_queue.get_nowait()
                    except queue.Empty:
                        break

                    if msg[0] == "progress":
                        _, name, cur, total = msg
                        Detector.progress_state[name] = (
                            min(cur, total),
                            total,
                        )

                Detector._detectionrender()

                running = not all(
                    f.done() for f in futures
                )

                time.sleep(0.05)

            while True:
                try:
                    msg = Detector.status_queue.get_nowait()
                except queue.Empty:
                    break

                if msg[0] == "progress":
                    _, name, cur, total = msg
                    Detector.progress_state[name] = (
                        min(cur, total),
                        total,
                    )

            Detector._detectionrender()

            for f in futures:
                name = futures[f]
                Detector.results[name] = f.result()

        print(
            "\n\nDONE:",
            *Detector.results.items(),
            sep="\n"
        )

    @staticmethod
    def detection_component():

        Screen.clear()
        Screen.hide_cursor()

        Detector.progress_state = {
            "Git": (0, 1),
            "Blender": (0, 1),
            "SketchUp": (0, 1),
        }

        Detector.results = {}

        Detector.components = {
            "Git": lambda p: GitDetector.detect_git(progress=p),
            "Blender": lambda p: BlenderDetector.detect_blender_all(progress=p),
            "SketchUp": lambda p: SketchupDetector.detect_sketchup_all(progress=p),
        }

        Detector.status_queue = queue.Queue()

        Detector._detection_run()
