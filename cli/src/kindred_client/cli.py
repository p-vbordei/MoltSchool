"""Typer entry point for the `kin` CLI."""
from __future__ import annotations

import typer

from kindred_client.commands import ask as ask_cmd
from kindred_client.commands import contribute as contribute_cmd
from kindred_client.commands import install as install_cmd
from kindred_client.commands import join as join_cmd
from kindred_client.commands import leave as leave_cmd
from kindred_client.commands import save as save_cmd
from kindred_client.commands import status as status_cmd

app = typer.Typer(
    name="kin",
    help="Kindred CLI — join kindreds, ask the knowledge, contribute artifacts.",
    no_args_is_help=True,
)


@app.callback()
def _callback() -> None:
    """Top-level callback (keeps Typer happy when commands are registered below)."""


# Registered lazily in each module so tests can import them in isolation.
join_cmd.register(app)
install_cmd.register(app)
ask_cmd.register(app)
contribute_cmd.register(app)
save_cmd.register(app)
status_cmd.register(app)
leave_cmd.register(app)


if __name__ == "__main__":
    app()
