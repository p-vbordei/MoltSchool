"""`kin ask <slug> "<query>"` — ask your team's shared notebook and print the most relevant pages."""
from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.panel import Panel

from kindred_client.api_client import APIError, KindredAPI
from kindred_client.config import load_config
from kindred_client.keystore import load_keypair

console = Console()


async def _run_ask(
    slug: str, query: str, *, k: int, peer_shared: bool
) -> dict:
    cfg = load_config()
    if not cfg.active_agent_id:
        raise RuntimeError("no active agent — run `kin join <invite_url>` first")
    entry = cfg.find_kindred(slug)
    backend = entry.backend_url if entry else cfg.backend_url
    _, agent_pk = load_keypair(cfg.active_agent_id)
    api = KindredAPI(backend)
    return await api.ask(
        slug=slug,
        agent_pubkey=agent_pk,
        query=query,
        k=k,
        include_peer_shared=peer_shared,
    )


def _render_response(resp: dict) -> None:
    artifacts = resp.get("artifacts") or []
    provenance = resp.get("provenance") or []
    if not artifacts:
        console.print(
            Panel.fit("[yellow]No artifacts matched.[/yellow]", title="kin ask")
        )
    for art, chip in zip(artifacts, provenance, strict=False):
        framed = art.get("framed") or ""
        tier = art.get("tier") or "unproven"
        console.print(
            Panel(
                framed,
                title=f"[cyan]{chip.get('logical_name', art['content_id'])}[/cyan]",
                subtitle=(
                    f"tier={tier} | author={chip.get('author_pubkey', '?')[:20]}… | "
                    f"success={chip.get('outcome_success_rate', 0.0):.0%}"
                ),
                border_style="green" if tier == "blessed" else "yellow",
            )
        )
    console.print(f"[dim]audit_id:[/dim] {resp.get('audit_id', '?')}")


def register(app: typer.Typer) -> None:
    @app.command("ask")
    def ask_cmd(
        slug: str = typer.Argument(..., help="Kindred slug"),
        query: str = typer.Argument(..., help="Natural-language query"),
        k: int = typer.Option(5, "--k", help="Max artifacts to return"),
        peer_shared: bool = typer.Option(
            False, "--peer-shared", help="Include peer-shared (unsigned) artifacts"
        ),
    ) -> None:
        """Ask your team's shared notebook and print the most relevant pages with provenance."""
        try:
            resp = asyncio.run(_run_ask(slug, query, k=k, peer_shared=peer_shared))
        except APIError as e:
            console.print(
                Panel.fit(
                    f"[red]Backend error[/red]: {e.message}",
                    title=f"HTTP {e.status_code}",
                    border_style="red",
                )
            )
            raise typer.Exit(code=1) from e
        except RuntimeError as e:
            console.print(Panel.fit(f"[red]{e}[/red]", border_style="red"))
            raise typer.Exit(code=2) from e
        except FileNotFoundError as e:
            console.print(
                Panel.fit(f"[red]Missing keypair[/red]: {e}", border_style="red")
            )
            raise typer.Exit(code=2) from e

        _render_response(resp)
