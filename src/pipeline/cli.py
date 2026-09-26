import typer

from typing import Annotated

from .csv_parse import csv_data_to_json

app = typer.Typer(no_args_is_help=True)

@app.command("parse-data")
def parse_data(
    filename_in: str, 
    filename_out: str = typer.Argument("funtasia_data.json"),
    prefer_ascii: bool = True
):
    """
    Parse csv booth data in filename_in and
    output json data to filename_out
    """
    csv_data_to_json(filename_in, filename_out, prefer_ascii)

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