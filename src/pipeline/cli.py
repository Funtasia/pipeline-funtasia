import asyncio
import logging
from functools import wraps
from pathlib import Path
from typing import Annotated

import typer
from typer._click import Context, Parameter
from typer._click.shell_completion import CompletionItem

from .setup import app as setup_app


def coro(f):
    """
    Wrap the async function with asyncio.run for use with app.command

    See https://github.com/pallets/click/issues/85#issuecomment-503464628

    E.g.

    >>> @coro
    >>> async def foo():
    >>>     ...
    >>>
    >>> foo()

    is equivalent to:

    >>> async def foo()
    >>>     ...
    >>>
    >>> asyncio.run(foo())
    """

    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapper


app = typer.Typer(
    no_args_is_help=True,
    rich_markup_mode="markdown",
    context_settings={"help_option_names": ["-h", "--help"]},
)

app.add_typer(setup_app)


def find(ext: str):
    """
    Return a shell completion function that finds a file with the extension `ext`.
    `ext` includes the leading period ('.')
    """

    def find_file(
        ctx: Context, param: Parameter, incomplete: str
    ) -> list[CompletionItem]:
        # Using click CompletionItem allows specifying type of
        # completion ("file"), which means that zsh file
        # autocomplete will not take precedence. Thus we use
        # click's shell_complete instead of typer's autocomplete

        # TODO: Switch to typer once they implement click
        # feature of typed completion

        # files with names that match `incomplete`
        matches = set(Path().rglob(f"*{incomplete}*{ext}"))

        # files with filepath starting with `incomplete`
        for match in Path().glob(f"{incomplete}*"):
            if match.is_file() and match.suffix == ext:
                matches.update((match,))
            elif match.is_dir():
                matches.update(match.rglob(f"*{ext}"))

        # click does not support generator objects
        return [
            CompletionItem(str(file), "file")
            for file in sorted(matches, key=lambda p: len(str(p)))
            if file.is_file() and str(file) not in (ctx.params.get("files") or [])
        ]

    return find_file


@app.command("parse-data", no_args_is_help=True)
def parse_data(
    filename_in: Annotated[
        Path,
        typer.Argument(
            help="Filename of the csv dataset",
            exists=True,
            shell_complete=find(".csv"),
        ),
    ],
    filename_out: Annotated[
        Path,
        typer.Argument(
            writable=True,
        ),
    ] = Path("funtasia_data.json"),
    prefer_ascii: Annotated[
        bool,
        typer.Option(
            help=(
                "Convert common non-ASCII characters (dashes and quotation marks) "
                "into their ASCII equivalent"
            ),
        ),
    ] = True,
):
    """
    Parse csv booth data in `filename_in` and
    output json data to `filename_out`.
    """
    from .csv_parse import csv_data_to_json

    csv_data_to_json(filename_in, filename_out, prefer_ascii)


@app.command(no_args_is_help=True)
@coro
async def model_convert(
    files: Annotated[
        list[Path],
        typer.Argument(
            help=".skp file(s) to convert (shell completion supported)",
            exists=True,
            readable=True,
            shell_complete=find(".skp"),
        ),
    ],
    output_folder: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Output directory to save `.glb` files to",
            exists=False,
            writable=True,
        ),
    ] = None,
    blender_path: Annotated[
        Path | None,
        typer.Option(
            rich_help_panel="Blender config",
            help="Path to blender executable",
        ),
    ] = None,
    blender_folder: Annotated[
        Path | None,
        typer.Option(
            rich_help_panel="Blender config",
            help="Directory for intermediate `.blend` files",
            writable=True,
        ),
    ] = None,
    blender_script: Annotated[
        Path | None,
        typer.Option(
            "--blender-script",
            "-s",
            rich_help_panel="Blender config",
            help="Path to script to execute blender",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            help="Override conflicting files",
        ),
    ] = True,
):
    """
    Convert files from `.skp` to `.blend` to `.glb`.

    Read the config file and cli arguments.
    In case of conflicts, cli arguments take precedence.
    """

    import httpx
    from rich.console import Group
    from rich.live import Live
    from rich.panel import Panel
    from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn

    from .model_server.model_convert import ConvertSkp

    # Create progress bar for tracking all conversions
    conversion_progress = Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=120),
        TextColumn("({task.completed}/{task.total})"),
        TimeElapsedColumn(),
        expand=True,
    )

    # Overall progress bar
    overall_progress = Progress(
        TimeElapsedColumn(),
        BarColumn(bar_width=500),
        TextColumn("{task.completed}/{task.total}"),
        TextColumn("[bold green]{task.description}"),
        expand=True,
    )

    # Group them together
    progress_group = Group(
        Panel(conversion_progress, title="[bold]Conversions[/bold]"),
        overall_progress,
    )

    # Add overall task
    overall_task_id = overall_progress.add_task("", total=len(files))

    # Add parameters not in __init__
    if blender_path:
        ConvertSkp.config.blender_exe = blender_path
    if blender_script:
        ConvertSkp.config.blender_script = blender_script

    tasks = []

    # Use Live context manager to display all progress bars
    with Live(progress_group, refresh_per_second=12.5) as live:
        async with httpx.AsyncClient() as client, asyncio.TaskGroup() as tg:
            for skp_file in files:
                # Create ConvertSkp instance and pass progress bar + task ID
                converter = await ConvertSkp(
                    source=skp_file,
                    client=client,
                    glb_save_folder=output_folder,
                    blend_save_folder=blender_folder,
                    override=force,
                    progress_bar=conversion_progress,
                    console=live.console,
                )

                # Create task that updates overall progress when done
                async def run_and_update(conv: ConvertSkp):
                    success = await conv.convert(suppress_errors=True)

                    overall_progress.update(overall_task_id, advance=1)

                    return success

                tasks.append(tg.create_task(run_and_update(converter)))

        no_errors = sum(1 if task.result() is False else 0 for task in tasks)

        # Final message
        overall_progress.update(
            overall_task_id,
            description=(
                "[bold][green]All conversions complete![/green] "
                f"[red]({no_errors} errors)[/red]"
            ),
        )


@app.command(name="repl", hidden=True)
def app_repl():
    """
    Hidden command to activate the repl
    """
    from .repl import repl

    repl(app)


@app.callback()
def callback(
    verbose: Annotated[
        int,
        typer.Option(
            "-v",
            "--verbose",
            count=True,
        ),
    ] = 0,
):
    """
    CLI tool to process data relating to Funtasia.
    """

    from rich.logging import RichHandler

    verbosity = max(0, 30 - (10 * verbose))

    logging.basicConfig(
        level=verbosity, format="%(message)s", datefmt="[%X]", handlers=[RichHandler()]
    )

    logging.getLogger(__name__).info(
        f"Verbosity level set to {min(3, verbose)} (python log level {verbosity})"
    )


def launched_by_double_click() -> bool:
    import ctypes
    import os
    import sys

    if os.name == "nt":
        buf = (ctypes.c_uint * 2)()
        count = ctypes.windll.kernel32.GetConsoleProcessList(buf, 2)
        return count <= 2  # launched from GUI will have 2, from terminal will have 3

    # On *NIX, GUI will not make tty to run.
    return not sys.stdin.isatty()


def main():
    if launched_by_double_click():
        from .repl import repl

        repl(app)
    else:
        app()


if __name__ == "__main__":
    main()
