import subprocess
import queue
from terminal import Console, Screen, Cursor

class Clone:

    repo_urls = [
        "https://github.com/Funtasia/app-funtasia.git",
        "https://github.com/Funtasia/3dfiles-funtasia.git",
        "https://github.com/Funtasia/pipeline-funtasia.git"
    ]
    progress_state = {}
    results = {}
    components = {}
    status_queue = queue.Queue()

    @staticmethod
    def _make_progress(name):
        return lambda c, t: Clone.status_queue.put(
            ("progress", name, c, t)
        )
    
    @staticmethod
    def _clonerender():
        Cursor.move(7,0)

        Console.section("Cloning Repositories")

        for name, (cur,total) in Clone.progress_state.items():
            
    
    def _clone_repo(url):        
    
        subprocess.run(
            ["git", "clone", url],
            check=True
        )



import subprocess
import re

def clone_repo(url, target_dir, progress=None):
    proc = subprocess.Popen(
        [
            "git",
            "clone",
            "--progress",
            url,
            target_dir,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )


    for line in proc.stderr:
        line = line.strip()

        m = percent_re.search(line)
        if m and progress:
            pct = int(m.group(1))
            progress(pct, 100)

        # Optional debug output
        print(line)

    returncode = proc.wait()

    if returncode != 0:
        raise RuntimeError(f"git clone failed ({returncode})")

    if progress:
        progress(100, 100)

    return target_dir