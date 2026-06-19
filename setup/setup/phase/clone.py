import subprocess
import queue
from terminal import Console, Screen, Cursor
import subprocess
import re
from concurrent.futures import ThreadPoolExecutor
from vars import Colour
import time
import sys

class Clone:

    progress_state = {}
    components = {}
    status_queue = queue.Queue()

    repo_lnks = {
        "app-funtasia":"https://github.com/Funtasia/app-funtasia.git",
        "3dfiles-funtasia":"https://github.com/Funtasia/3dfiles-funtasia.git",
        "pipeline-funtasia":"https://github.com/Funtasia/pipeline-funtasia.git",
    }

    @staticmethod
    def _make_progress(name):
        return lambda c, t: Clone.status_queue.put(
            ("progress", name, c, t)
        )


    @staticmethod
    def clone_repo(url, name, progress=None):
        proc = subprocess.Popen(
            ["git", "clone", "--progress", url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=0
        )

        while True:
            line = proc.stderr.readline()

            if line:
                line = line.strip()

                if "Receiving objects" in line:
                    m = re.search(r"(\d+)/(\d+)", line)
                    if m and progress:
                        cur = int(m.group(1))
                        total = int(m.group(2))
                        progress(int(cur * 100 / total), 100)

            if proc.poll() is not None:
                break

        proc.wait()

        if progress:
            progress(100, 100)
            
    @staticmethod
    def _clonerender():
        Cursor.move(15,0)

        Console.section("Cloning Repositories")

        for name, (cur,total) in Clone.progress_state.items():
            bar_len = 20
            filled = int((cur/total) * bar_len)
            bar = "#" * filled + " " * (bar_len - filled)

            print(
                f"Cloning {name:<20} [{bar}] {cur:6.1f}%"
            )

        sys.stdout.flush()

    @staticmethod
    def _clone_run():

        with ThreadPoolExecutor(max_workers=3) as pool:
        
            futures = {
                pool.submit(
                    Clone.clone_repo,
                    url,
                    name,
                    Clone._make_progress(name)
                ): name
                for name, url in Clone.repo_lnks.items()
            }

            running = True

            while running:

                while True:
                    try:
                        msg = Clone.status_queue.get_nowait()
                    except queue.Empty:
                        break

                    if msg[0] == "progress":
                        _, name, cur, total = msg
                        Clone.progress_state[name] = (
                            min(cur, total),
                            total,
                        )

                Clone._clonerender()

                running = not all(
                    f.done() for f in futures
                )

                time.sleep(0.05)

            while True:
                try:
                    msg = Clone.status_queue.get_nowait()
                except queue.Empty:
                    break

                if msg[0] == "progress":
                    _, name, cur, total = msg
                    Clone.progress_state[name] = (
                        min(cur, total),
                        total,
                    )

            Clone._clonerender()

        output = [f"{repo}: {Console.colour_string(url,[Colour.BLUE])}" for repo,url in Clone.repo_lnks.items()]
        print(Console.colour_string("4 Repositories Cloned",[Colour.GREEN]),*output,sep="\n" )

    @staticmethod
    def clone_component():


        Clone.progress_state = {
            "app-funtasia":(0,100),
            "3dfiles-funtasia":(0,100),
            "pipeline-funtasia":(0,100),
        }

        Clone.components = {
            "app-funtasia": lambda p: Clone.clone_repo(url = Clone.repo_lnks["app-funtasia"],name="app-funtasia",progress = p),
            "3dfiles-funtasia": lambda p: Clone.clone_repo(url = Clone.repo_lnks["3dfiles-funtasia"],name="3dfiles-funtasia",progress = p),
            "pipeline-funtasia": lambda p: Clone.clone_repo(url = Clone.repo_lnks["pipeline-funtasia"],name="pipeline-funtasia",progress = p)
        }

        Clone.status_queue = queue.Queue()

        Clone._clone_run()