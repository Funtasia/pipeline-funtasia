import shlex

from rich import print as rich_print
import typer

def repl(app: typer.Typer):
    rich_print("Interactive mode. Type a command, '--help' for options, or 'exit' to quit.")
    while True:
        try:
            rich_print("nipple>>> ", end="")
            line = input().strip()
        except (EOFError, KeyboardInterrupt):
            break
        if line in ("exit", "quit"):
            break
        if not line:
            continue

        try:
            app(args=shlex.split(line), prog_name="nipple>>>", standalone_mode=False)
        except SystemExit:
            pass
        except Exception as e:
            typer.echo(f"Error: {e}")
