"""`kin save this` — placeholder for Claude Code hook (Plan 04)."""
from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel

console = Console()


def register(app: typer.Typer) -> None:
    @app.command("save")
    def save_cmd(
        what: str = typer.Argument("this", help="What to save (currently only 'this')"),
    ) -> None:
        """Stub — Claude Code hook integration lands in Plan 04."""
        console.print(
            Panel.fit(
                f"[yellow]Not yet implemented[/yellow] — hooks into Claude Code "
                f"land in Plan 04.\n(requested: {what!r})",
                title="kin save",
                border_style="yellow",
            )
        )
        raise typer.Exit(code=0)
