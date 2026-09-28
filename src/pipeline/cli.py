from typing import Optional
import sys
from rich import print
from click import Parameter
from click import Context
from click.shell_completion import CompletionItem
import asyncio
import typer

from typing import Annotated
from pathlib import Path

from .csv_parse import csv_data_to_json
from .setup.clone import clone
from .setup.readme import copy_readme
from .model_server.model_convert import ConvertSkp

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
def model_convert(
    files: Annotated[list[Path], typer.Argument(
        exists=True, readable=True, help=".skp file(s) to convert (shell completion supported)", shell_complete=find_skp
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
    async def convert(
        files: list[Path],
        output_folder: Optional[Path],
        blender_path: Optional[Path],
        blender_folder: Optional[Path],
        blender_script: Optional[Path],
        force: bool
    ):
        if blender_script:
            ConvertSkp.script_path = blender_script
        if blender_path:
            ConvertSkp.blender_executable = str(blender_path.absolute())

        async with asyncio.TaskGroup() as tg:
            for file in files:
                instance = await ConvertSkp( #type: ignore
                    filename=file.name, 
                    filepath=file,
                    blend_save_folder=blender_folder,
                    glb_save_folder=output_folder,
                    override=force
                ) 
                tg.create_task(instance.convert())


    output=None #TODO
    asyncio.run(convert(
        files=files, 
        output_folder=output_folder,
        blender_path=blender_path,
        blender_folder=blender_folder,
        blender_script=blender_script,
        force=force
    ))

    

@app.callback()
def callback():
    """
    CLI tool to process data relating to Funtasia.
    """

if __name__ == '__main__':
    app()