import typer

from typing import Annotated

from .csv_parse import csv_data_to_json
from .setup.clone import clone
from .setup.readme import copy_readme

app = typer.Typer(no_args_is_help=True)

@app.command("parse-data")
def parse_data(
    filename_in: str, 
    filename_out: Annotated[str, typer.Argument()] = "funtasia_data.json",
    prefer_ascii: Annotated[bool | None, typer.Option(help="Convert common non-ASCII characters into their ASCII equivalent")] = True
):
    """
    Parse csv booth data in filename_in and
    output json data to filename_out
    """
    csv_data_to_json(filename_in, filename_out, prefer_ascii or False)

@app.command("")
def setup(
    force: Annotated[bool | None, typer.Option("--force", help="Clear conflicting files.")] = False,
    ssh: Annotated[bool | None, typer.Option("--ssh", help="Use ssh to clone the repositories.")] = False
):
    """
    Setup the environment by cloning the 
    Funtasia repositories

    Will be called by the setup script
    """
    clone(force=force, ssh=ssh)
    copy_readme(force=force)

@app.command()
def model():
    """
    Convert the model from .skp to .blend
    """
    ... #TODO

@app.callback()
def callback():
    """
    CLI tool to process data relating to Funtasia.
    """

if __name__ == '__main__':
    app()