import time
import queue
import random
import sys
from concurrent.futures import ThreadPoolExecutor

status_queue = queue.Queue()

# ----------------------------
# Fake detector (simulated work)
# ----------------------------
def fake_detector(name, steps=10, delay=0.15, progress=None):
    for i in range(1, steps + 1):
        time.sleep(delay + random.uniform(0, 0.05))

        if progress:
            progress(i, steps)

    return f"{name} done"


# ----------------------------
# Progress callback factory
# ----------------------------
def make_progress(name):
    return lambda c, t: status_queue.put(("progress", name, c, t))


# ----------------------------
# UI state
# ----------------------------
components = {
    "Blender": lambda p: fake_detector("Blender", steps=20, progress=p),
    "Git": lambda p: fake_detector("Git", steps=12, progress=p),
    "SketchUp": lambda p: fake_detector("SketchUp", steps=16, progress=p),
}

progress_state = {name: (0, 1) for name in components}
results = {}


# ----------------------------
# UI renderer
# ----------------------------
def render():
    sys.stdout.write("\033[H")

    sys.stdout.write("SYSTEM SCAN\n")

    for name, (cur, total) in progress_state.items():
        bar_len = 20
        filled = int((cur / total) * bar_len)
        bar = "#" * filled + " " * (bar_len - filled)

        sys.stdout.write(f"{name:<10} [{bar}] {cur}/{total}\n")

    sys.stdout.flush()  

# ----------------------------
# Runner
# ----------------------------
def run():
    global progress_state

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(func, make_progress(name)): name
            for name, func in components.items()
        }

        running = True

        while running:

            # 1. process ALL queue messages first
            while True:
                try:
                    msg = status_queue.get_nowait()
                except queue.Empty:
                    break

                if msg[0] == "progress":
                    _, name, cur, total = msg
                    progress_state[name] = (min(cur, total), total)

            # 2. render UI
            render()

            # 3. check completion AFTER processing queue
            running = not all(f.done() for f in futures)

            time.sleep(0.05)

        # 4. FORCE final drain (THIS is what you were missing)
        while True:
            try:
                msg = status_queue.get_nowait()
            except queue.Empty:
                break

            if msg[0] == "progress":
                _, name, cur, total = msg
                progress_state[name] = (min(cur, total), total)

        # 5. final render
        render()

        # 6. collect results
        for f in futures:
            name = futures[f]
            results[name] = f.result()

    print("\nDONE:", results)


if __name__ == "__main__":
    print("\033[2J\033[0m")  # clear screen
    run()