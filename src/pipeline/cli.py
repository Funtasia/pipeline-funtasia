import asyncio
from functools import wraps
from pathlib import Path
from typing import Optional
from typing import Annotated

import httpx
import typer
from click import Parameter
from click import Context
from click.shell_completion import CompletionItem
from rich import print
from rich.console import Group
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn

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

app = typer.Typer(no_args_is_help=True, rich_markup_mode="markdown")

app.add_typer(setup_app)


@app.command("parse-data")
def parse_data(
    filename_in: Annotated[
        Path, 
        typer.Argument(exists=True)
    ],
    filename_out: Annotated[
        Path, 
        typer.Argument(writable=True)
    ] = Path("funtasia_data.json"),
    prefer_ascii: Annotated[
        bool, 
        typer.Option(help="Convert common non-ASCII characters into their ASCII equivalent")
    ] = True
):
    """
    Parse csv booth data in `filename_in` and
    output json data to `filename_out`.

    `prefer_ascii` will convert dashes to 
    the ASCII dash '-', and quotation marks 
    to their ASCII equivalent (' and ").
    """
    from .csv_parse import csv_data_to_json
    
    csv_data_to_json(filename_in, filename_out, prefer_ascii)


def find_skp(ctx: Context, param: Parameter, incomplete: str) -> list[CompletionItem]:
    # Using click CompletionItem allows spefifying type of completion ("file"),
    # which means that zsh file autocomplete will not take precedence
    # Thus we use click's shell_complete instead of typer's autocomplete
    if not incomplete:
        glob = "**/*.skp"
    else:
        glob = f"**/*{incomplete.strip('*')}*.skp"
    # click does not support generator objects
    return [
        CompletionItem(str(file), "file") 
        for file in Path().glob(glob, case_sensitive=True) 
        if file.is_file() and str(file) not in ctx.params.get('files', ())
    ]


@app.command(no_args_is_help=True)
@coro
async def model_convert(
    files: Annotated[list[Path], typer.Argument( 
        help=".skp file(s) to convert (shell completion supported)",
        exists=True, readable=True,
        shell_complete=find_skp #type: ignore
    )],
    output_folder: Annotated[Optional[Path], typer.Option(
        "--output", '-o',
        help="Output directory to save `.glb` files to",
        exists=False, writable=True
    )] = None,
    blender_path: Annotated[Optional[Path], typer.Option(
        rich_help_panel="Blender config",
        help="Path to blender executable"
    )] = None,
    blender_folder: Annotated[Optional[Path], typer.Option(
        rich_help_panel="Blender config",
        help="Directory for intermediate `.blend` files",
        writable=True
    )] = None,
    blender_script: Annotated[Optional[Path], typer.Option(
        "--blender-script", '-s',
        rich_help_panel="Blender config",
        help="Path to script to execute blender"
    )] = None,
    force: Annotated[bool, typer.Option(
        help="Override conflicting files"
    )] = True,
):
    """
    Convert files from `.skp` to `.blend` to `.glb`.

    Read the config file and cli arguments. In case of conflicts, cli arguments take precedence.
    """

    from .model_server.model_convert import ConvertSkp

    # Create progress bar for tracking all conversions
    conversion_progress = Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=120),
        TextColumn("({task.completed}/{task.total})"),
        TimeElapsedColumn(),
        expand=True
    )
    
    # Overall progress bar
    overall_progress = Progress(
        TimeElapsedColumn(),
        BarColumn(bar_width=500),
        TextColumn("{task.completed}/{task.total}"),
        TextColumn("[bold green]{task.description}"),
        expand=True
    )
    
    # Group them together
    progress_group = Group(
        Panel(conversion_progress, title="[bold]Conversions[/bold]"),
        overall_progress,
    )
        
    # Add overall task
    overall_task_id = overall_progress.add_task(
        "", 
        total=len(files)
    )

    # Add parameters not in __init__
    if blender_path:
        ConvertSkp.config.blender_exe = blender_path
    if blender_script:
        ConvertSkp.config.blender_script = blender_script

    tasks = []
    
    # Use Live context manager to display all progress bars
    with Live(progress_group, refresh_per_second=12.5) as l:

        async with httpx.AsyncClient() as client, asyncio.TaskGroup() as tg:
            for skp_file in files:
                
                # Create ConvertSkp instance and pass progress bar + task ID
                converter = await ConvertSkp( #type: ignore
                    source=skp_file,
                    client=client,
                    glb_save_folder=output_folder,
                    blend_save_folder=blender_folder,
                    override=force,
                    progress_bar=conversion_progress,
                    console=l.console
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
            description=f"[bold][green]All conversions complete![/green] [red]({no_errors} errors)[/red]"
        )
    
    return


@app.callback()
def callback():
    """
    CLI tool to process data relating to Funtasia.
    """


if __name__ == '__main__':
    app()