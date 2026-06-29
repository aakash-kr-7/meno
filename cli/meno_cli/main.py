# ==============================================================================
# (a) What this file is: MENO CLI entry point.
# (b) What it does: Registers subcommands: init, ingest, capture, hooks (with install sub), status. hook-capture is a hidden subcommand used by the git hook.
# (c) How it fits into the MENO system: Main entry point for command executions in terminal.
# ==============================================================================

import typer

from meno_cli.commands.init import init_cmd
from meno_cli.commands.ingest import ingest_cmd
from meno_cli.commands.capture import capture_cmd
from meno_cli.commands.hooks import hooks_app, hook_capture_cmd
from meno_cli.commands.status import status_cmd

app = typer.Typer(
    help="MENO CLI — persistent intelligence platform manager",
    pretty_exceptions_enable=False
)

# Register subcommands
app.command(name="init")(init_cmd)
app.command(name="ingest")(ingest_cmd)
app.command(name="capture")(capture_cmd)
app.add_typer(hooks_app, name="hooks")
app.command(name="hook-capture", hidden=True)(hook_capture_cmd)
app.command(name="status")(status_cmd)

if __name__ == "__main__":
    app()
