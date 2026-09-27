from pathlib import Path
import shutil
import subprocess
import subprocess
import sys
from urllib.parse import urlsplit

from rich import print
from rich.live import Live
from rich.text import Text

def get_target_dir(url):
    _, _, path, _, _ = urlsplit(url)
    target_dir = Path(path).stem
    return target_dir


def format_line(line: str) -> Text:
    """Format git output with custom highlighting."""
    text = Text(line)
    
    text.highlight_regex(r'fatal:', style="bold red")
    text.highlight_regex(r'Cloning into.*', style="bold blue")
    text.highlight_regex(r'done.', style="green")

    # highlight strings and numbers
    text.highlight_regex(r"'.+'", style="green")
    text.highlight_regex(r'[\d%]+', style="cyan")
    
    return text


def clone_repo(url: str):
    proc = subprocess.Popen(
        [
            "git",
            "clone",
            "--progress",
            "--recursive",
            url,
        ],
        env={"GIT_TERMINAL_PROMPT":"0"},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    prev_line = ""

    with Live() as live:
        for line in proc.stderr:
            if prev_line.endswith('.'):
                live.console.print(format_line(prev_line))
            
            line = line.strip()

            live.update(format_line(line))
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
            "git@github.com:Funtasia/3dfiles-funtasia.git"
        ]
    else:
        repo_urls = [
            "https://github.com/Funtasia/app-funtasia.git",
            "https://github.com/Funtasia/3dfiles-funtasia.git",
        ]

    for repo in repo_urls:

        path = Path(get_target_dir(repo))
        if path.exists():
            if force:
                shutil.rmtree(path, ignore_errors=True)
            else:
                print(f"[red]Directory '{path.name}' exists, aborting...")

        exit_code = clone_repo(repo)
        
        if exit_code:
            print("[red]Aborting...")
            if not ssh:
                print("[yellow]hint: [/][bright_black]If facing authentication issues with https, try using ssh authenticaation with 'nipple setup --ssh' instead[/]")
            sys.exit(exit_code)
        
if __name__ == "__main__":
    clone()
        