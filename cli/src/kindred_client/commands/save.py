"""`kin save this` — scan ~/.kin/history for the latest unconsumed success
entry and report it as outcome=success."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from kindred_client.api_client import APIError, KindredAPI
from kindred_client.config import load_config

console = Console()


def _history_dir() -> Path:
    return Path.home() / ".kin" / "history"


def _latest_unconsumed(hist: Path) -> Path | None:
    if not hist.exists():
        return None
    candidates = sorted(
        [p for p in hist.iterdir() if p.suffix == ".json"],
        key=lambda p: p.name,
        reverse=True,
    )
    return candidates[0] if candidates else None


async def _run_save() -> str | None:
    entry = _latest_unconsumed(_history_dir())
    if entry is None:
        return None
    data = json.loads(entry.read_text())
    audit_id = data.get("audit_id")
    if not audit_id:
        entry.rename(entry.with_suffix(".json.consumed"))
        return "no-audit"

    cfg = load_config()
    api = KindredAPI(cfg.backend_url)
    await api.report_outcome(
        audit_id=audit_id, result="success",
        notes=data.get("output_snippet", "")[:200],
    )
    entry.rename(entry.with_suffix(".json.consumed"))
    return audit_id


def register(app: typer.Typer) -> None:
    @app.command("save")
    def save_cmd(
        what: str = typer.Argument("this", help="Currently only 'this'"),
    ) -> None:
        """Report the latest PostToolUse success as a Kindred outcome."""
        try:
            reported = asyncio.run(_run_save())
        except APIError as e:
            console.print(Panel.fit(
                f"[red]Backend error[/red]: {e.message}",
                title=f"HTTP {e.status_code}", border_style="red",
            ))
            raise typer.Exit(code=1) from e
        if reported is None:
            console.print("[yellow]No history to save.[/yellow]")
            return
        if reported == "no-audit":
            console.print("[yellow]History entry has no audit_id (not from Kindred ask).[/yellow]")
            return
        console.print(f"[green]Reported outcome=success for audit {reported}[/green]")
