from shlex import quote

import typer
import typer.main
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion, ThreadedCompleter
from prompt_toolkit.document import Document
from rich import print as rich_print
from typer._completion_classes import BashComplete, click_split_arg_string

PROG_NAME = "nipple>>>"


class TyperAppCompleter(Completer):
    def __init__(
        self, 
        typer_app: typer.Typer, 
        prog_name: str = "nipple", 
        extra_cmds: list[str | tuple[str, str]] | None = None
    ):
        """
        `typer_app` is an instance of typer.Typer() to get completions from.
        
        `extra_cmds` gives extra commands not inside `typer_app`, such as 
        'exit' or 'quit'. Is a list of either the command name or a 
        2-element str tuple of the command name with its help text.
        """
        if extra_cmds is None:
            extra_cmds = []
        self.cli = typer.main.get_command(typer_app)
        self.prog_name = prog_name
        self.extra_cmds = extra_cmds

    def get_completions(self, document: Document, complete_event):
        # we show completion regardless whether tab or normal typing, so complete_event unused
        text = document.text_before_cursor

        # Separate the text into completed arguments and the word being typed.
        if text and text[-1].isspace():
            args = click_split_arg_string(text)
            incomplete = ""
        else:
            parts = click_split_arg_string(text)
            args = parts[:-1]
            incomplete = parts[-1] if parts else ""

        completer = BashComplete(
            cli=self.cli,
            ctx_args={},
            prog_name=self.prog_name,
            complete_var=f"_{self.prog_name.upper()}_COMPLETE",
        )

        # completions in typer_app
        for item in completer.get_completions(args, incomplete):
            res = quote(item.value) if ' ' in item.value else item.value
            yield Completion(
                res,
                start_position=-len(incomplete),
                display_meta=item.help or "",
            )

        # completions in extra_cmds
        for extra_cmd in self.extra_cmds:
            if isinstance(extra_cmd, str):
                cmd, help_text = extra_cmd, ''
            else:
                cmd, help_text = extra_cmd

            if cmd.startswith(text):
                yield Completion(
                    cmd,
                    start_position=-len(incomplete),
                    display_meta=help_text
                )


def repl(
    app: typer.Typer,
    extra_cmds: list[str | tuple[str, str]] | None = None
):
    rich_print("Interactive mode. Type a command, 'help' for help, or 'exit' to quit.")

    if extra_cmds is None:
        extra_cmds = [
            ("help", "Show a help message"), 
            ("exit", "Exit this REPL")
        ]

    # '**/' globs can take long time, so run in background thread to not block
    completer = ThreadedCompleter(TyperAppCompleter(
        app,
        extra_cmds=extra_cmds,
        prog_name=PROG_NAME))
    session = PromptSession(message=f"{PROG_NAME} ", completer=completer)

    while True:
        try:
            line = session.prompt()
        except (EOFError, KeyboardInterrupt):
            break

        if not line:
            continue
        elif line in ("exit",):
            break
        elif line in ("help",):
            args = ["--help"]
        else:
            args = click_split_arg_string(line)

        # `standalone_mode=True` for consistent formatted output.
        # However, this means app() raises SystemExit, which we also exit
        # the REPL instead of just the command, so we swallow the SystemExit.
        try:
            app(args=args, prog_name=PROG_NAME, standalone_mode=True)
        except SystemExit:
            pass
