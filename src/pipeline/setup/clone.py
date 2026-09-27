from pathlib import Path
import shutil
import subprocess
import subprocess
import sys
from typing import Optional
from urllib.parse import urlsplit

from rich import print
from rich.live import Live

def get_target_dir(url):
    _, _, path, _, _ = urlsplit(url)
    target_dir = Path(path).stem


def clone_repo(url: str):
    proc = subprocess.Popen(
        [
            "git",
            "clone",
            "--progress",
            "--recursive",
            url,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    prev_line = ""

    with Live() as live:

        for line in proc.stderr:
            if prev_line.endswith('.'):
                live.console.print(prev_line)
            
            line = line.strip()

            live.update(line)
            prev_line = line


            # m = percent_re.search(line)
            # if m and progress:
            #     pct = int(m.group(1))
            #     progress(pct, 100)


    returncode = proc.wait()

    return returncode

def clone(force: bool = False, ssh = False):
    """
    Clone the Funtasia repos onto the machine.

    If force is True, remove the contents of any conflicting directories

    If ssh is True, use the ssh links instead of https
    """

    if ssh:
        repo_urls = [
            "git@github.com:Funtasia/app-funtasia.git",
            "git@github.com:Funtasia/data-funtasia.git"
        ]
    else:
        repo_urls = [
            "https://github.com/Funtasia/app-funtasia.git",
            "https://github.com/Funtasia/data-funtasia.git",
        ]

    for repo in repo_urls:

        if force:
            path = Path(get_target_dir(repo))
            if path.exists():
                shutil.rmtree(path, ignore_errors=True)

        exit_code = clone_repo(repo)
        
        if exit_code:
            print("Aborting...")
            sys.exit(exit_code)
        
if __name__ == "__main__":
    clone()
        