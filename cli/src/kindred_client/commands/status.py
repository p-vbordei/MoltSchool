"""`kin status` — list joined kindreds with artifact counts."""
from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.table import Table

from kindred_client.api_client import APIError, KindredAPI
from kindred_client.config import load_config

console = Console()


async def _gather_rows() -> list[dict]:
    cfg = load_config()
    rows: list[dict] = []
    for entry in cfg.kindreds:
        api = KindredAPI(entry.backend_url)
        row: dict = {
            "slug": entry.slug,
            "backend_url": entry.backend_url,
            "name": "-",
            "description": "",
            "artifact_count": 0,
            "error": None,
        }
        try:
            k = await api.get_kindred_by_slug(entry.slug)
            row["name"] = k.get("display_name", "-")
            row["description"] = k.get("description", "")
            arts = await api.list_artifacts(entry.slug)
            row["artifact_count"] = len(arts or [])
        except APIError as e:
            row["error"] = f"HTTP {e.status_code}"
        rows.append(row)
    return rows


def register(app: typer.Typer) -> None:
    @app.command("status")
    def status_cmd() -> None:
        """Print a table of all joined kindreds."""
        cfg = load_config()
        if not cfg.kindreds:
            console.print("[yellow]No kindreds joined yet.[/yellow] Run `kin join <url>`.")
            raise typer.Exit(code=0)

        rows = asyncio.run(_gather_rows())
        table = Table(title="kindreds")
        table.add_column("slug", style="cyan")
        table.add_column("name")
        table.add_column("artifacts", justify="right")
        table.add_column("backend")
        for r in rows:
            name_col = r["name"] if not r["error"] else f"[red]{r['error']}[/red]"
            table.add_row(
                r["slug"], name_col, str(r["artifact_count"]), r["backend_url"]
            )
        console.print(table)
