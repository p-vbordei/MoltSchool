"""`kin install <slug-or-url>` — one-line onboarding.

If the argument already looks like an invite URL, it's handed off to the
`join` flow unchanged. If it's a bare slug, the CLI asks the configured
backend to mint a one-time install invite (public kindreds only) and
then proceeds with the normal join.
"""
from __future__ import annotations

import asyncio
import os

import httpx
import typer
from rich.console import Console
from rich.panel import Panel

from kindred_client.api_client import APIError
from kindred_client.commands.join import _run_join, _safe_load_config

console = Console()


def _looks_like_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://")


async def _fetch_public_invite(backend_url: str, slug: str) -> str:
    """Call the backend's install endpoint; return the invite URL."""
    async with httpx.AsyncClient(base_url=backend_url, timeout=15.0) as client:
        resp = await client.post(f"/v1/kindreds/{slug}/install")
    if resp.status_code == 404:
        raise APIError(404, f"kindred not found: {slug}", body=None)
    if resp.status_code == 403:
        raise APIError(
            403,
            f"kindred '{slug}' is not public — ask its owner for an invite URL",
            body=None,
        )
    if resp.status_code >= 400:
        raise APIError(resp.status_code, resp.text, body=None)
    return resp.json()["invite_url"]


def register(app: typer.Typer) -> None:
    @app.command("install")
    def install_cmd(
        target: str = typer.Argument(
            ...,
            help="Invite URL, or a bare slug of a public kindred.",
        ),
        backend: str = typer.Option(
            None,
            "--backend",
            help=(
                "Backend URL (defaults to $KINDRED_BACKEND_URL or the saved "
                "backend_url from a previous join)."
            ),
        ),
        email: str = typer.Option(None, "--email", help="Email (prompted if missing)"),
        display_name: str = typer.Option(
            None, "--name", help="Display name (prompted if missing)"
        ),
    ) -> None:
        """Install a kindred by slug (public) or invite URL (any)."""
        cfg = _safe_load_config()

        if _looks_like_url(target):
            invite_url = target
        else:
            resolved_backend = (
                backend
                or os.environ.get("KINDRED_BACKEND_URL")
                or cfg.backend_url
            )
            try:
                invite_url = asyncio.run(
                    _fetch_public_invite(resolved_backend, target)
                )
            except APIError as e:
                console.print(
                    Panel.fit(
                        f"[red]Install failed[/red]: {e.message}",
                        title=f"HTTP {e.status_code}",
                        border_style="red",
                    )
                )
                raise typer.Exit(code=1) from e

        need_email = cfg.active_owner_id is None and not email
        need_name = cfg.active_owner_id is None and not display_name
        if need_email:
            email = typer.prompt("Email")
        if need_name:
            display_name = typer.prompt("Display name")

        try:
            result = asyncio.run(
                _run_join(
                    invite_url,
                    email=email or "",
                    display_name=display_name or "",
                )
            )
        except APIError as e:
            console.print(
                Panel.fit(
                    f"[red]Backend error[/red]: {e.message}",
                    title=f"HTTP {e.status_code}",
                    border_style="red",
                )
            )
            raise typer.Exit(code=1) from e
        except ValueError as e:
            console.print(Panel.fit(f"[red]{e}[/red]", border_style="red"))
            raise typer.Exit(code=2) from e

        console.print(
            Panel.fit(
                f"[bold green]Installed[/bold green] [cyan]{result['slug']}[/cyan]\n"
                f"agent: [magenta]{result['agent_id']}[/magenta]\n"
                f"try: [dim]kin ask {result['slug']} \"<your question>\"[/dim]",
                title="kin install",
                border_style="green",
            )
        )
