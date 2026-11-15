import shlex

from rich import print as rich_print
import typer
import typer.main

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import NestedCompleter
    PROMPT_TOOLKIT = True

except ImportError:
    PROMPT_TOOLKIT = False

if PROMPT_TOOLKIT:

    def build_completer(app: typer.Typer) -> NestedCompleter:
        click_cmd = typer.main.get_command(app)
        tree = {}
        for name, sub in click_cmd.commands.items():
            tree[name] = {opt: None for p in sub.params for opt in p.opts}
        tree["exit"] = None
        tree["quit"] = None
        return NestedCompleter.from_nested_dict(tree)

def repl(app: typer.Typer):
    rich_print("Interactive mode. Type a command, '--help' for options, or 'exit' to quit.")
    if PROMPT_TOOLKIT:
        session = PromptSession(message="nipple>>> ", completer=build_completer(app))
    while True:
        try:
            if PROMPT_TOOLKIT:
                line = session.prompt()
            else:
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
