"""`kin leave <slug>` — call the server and drop local config entry."""
from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.panel import Panel

from kindred_client.api_client import APIError, KindredAPI
from kindred_client.config import load_config, save_config
from kindred_client.keystore import load_keypair

console = Console()


async def _run_leave(slug: str) -> tuple[bool, str | None]:
    cfg = load_config()
    entry = cfg.find_kindred(slug)
    if not entry:
        return False, f"not in config: {slug!r}"

    removed_remotely = False
    err: str | None = None
    if cfg.active_agent_id:
        _, agent_pk = load_keypair(cfg.active_agent_id)
        api = KindredAPI(entry.backend_url)
        try:
            await api.leave(slug=slug, agent_pubkey=agent_pk)
            removed_remotely = True
        except APIError as e:
            err = f"HTTP {e.status_code}: {e.message}"

    cfg.remove_kindred(slug)
    save_config(cfg)
    return removed_remotely, err


def register(app: typer.Typer) -> None:
    @app.command("leave")
    def leave_cmd(slug: str = typer.Argument(..., help="Kindred slug")) -> None:
        """Leave a kindred (remote + local)."""
        removed_remotely, err = asyncio.run(_run_leave(slug))
        if err and not removed_remotely:
            console.print(
                Panel.fit(
                    f"[yellow]Removed locally only[/yellow] — remote leave failed: {err}",
                    title="kin leave",
                    border_style="yellow",
                )
            )
            return
        if removed_remotely:
            console.print(
                Panel.fit(
                    f"[bold green]Left[/bold green] [cyan]{slug}[/cyan]",
                    title="kin leave",
                    border_style="green",
                )
            )
        else:
            console.print(
                Panel.fit(
                    "[yellow]Removed locally only[/yellow] (no active agent).",
                    title="kin leave",
                    border_style="yellow",
                )
            )
