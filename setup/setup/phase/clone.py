import subprocess
import queue
from terminal import Console, Screen

class Clone:

    progress_state = {}
    results = {}
    components = {}
    status_queue = queue.Queue()
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

    percent_re = re.compile(r"(\d+)%")

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