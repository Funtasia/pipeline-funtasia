import asyncio
from functools import wraps
from pathlib import Path
from typing import Optional
from typing import Annotated

from click import Parameter
from click import Context
from click.shell_completion import CompletionItem
from rich import print
from rich.console import Group
from rich.live import Live
from rich.panel import Panel
from rich.progress import TimeElapsedColumn, BarColumn, TextColumn, Progress
import typer

from .csv_parse import csv_data_to_json
from .model_server.model_convert import ConvertSkp
from .setup.clone import clone
from .setup.readme import copy_readme


def coro(f):
    """
    Wrap the async function with asyncio.run for use with app.command
    
    See https://github.com/pallets/click/issues/85#issuecomment-503464628
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapper

app = typer.Typer(no_args_is_help=True, rich_markup_mode="markdown")

@app.command("parse-data")
def parse_data(
    filename_in: Annotated[Path, typer.Argument(exists=True)],
    filename_out: Annotated[Path, typer.Argument(writable=True)] = Path("funtasia_data.json"),
    prefer_ascii: Annotated[bool, typer.Option(help="Convert common non-ASCII characters into their ASCII equivalent")] = True
):
    """
    Parse csv booth data in `filename_in` and
    output json data to `filename_out`
    """
    csv_data_to_json(filename_in, filename_out, prefer_ascii)

@app.command()
def setup(
    force: Annotated[bool, typer.Option("--force/", "-f/", help="Override conflicting files.")] = False,
    ssh: Annotated[bool, typer.Option("--ssh/--https", help="Whether to use ssh or https to clone the repositories.")] = False
):
    """
    Setup the environment by cloning the 
    Funtasia repositories

    Will be called by the setup script
    """
    clone(force=force, ssh=ssh)
    copy_readme(force=force)

def find_skp(ctx: Context, param: Parameter, incomplete: str):
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
        exists=True, readable=True, 
        help=".skp file(s) to convert (shell completion supported)", 
        shell_complete=find_skp
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
    ConvertSkp.blend_path = blender_path
    ConvertSkp.script_path = blender_script

    tasks = []
    
    # Use Live context manager to display all progress bars
    with Live(progress_group, refresh_per_second=12.5) as l:

        async with asyncio.TaskGroup() as tg:
            for skp_file in files:
                
                # Create ConvertSkp instance and pass progress bar + task ID
                converter = await ConvertSkp( #type: ignore
                    source=skp_file,
                    glb_save_folder=output_folder,
                    progress_bar=conversion_progress,
                    console=l.console
                )
                
                # Create task that updates overall progress when done
                async def run_and_update(conv: ConvertSkp):
                    success = await conv.convert(suppress_errors=True)
                    # success = await conv.convert(suppress_errors=False)

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