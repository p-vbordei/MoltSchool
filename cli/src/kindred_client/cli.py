"""Typer entry point for the `kin` CLI."""
from __future__ import annotations

import typer

app = typer.Typer(
    name="kin",
    help="Kindred CLI — join kindreds, ask the knowledge, contribute artifacts.",
    no_args_is_help=True,
)


@app.callback()
def _callback() -> None:
    """Top-level callback (keeps Typer happy when commands are registered below)."""


if __name__ == "__main__":
    app()
