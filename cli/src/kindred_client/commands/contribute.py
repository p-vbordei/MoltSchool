"""`kin contribute <slug> --type <kind> --file <path>` — upload an artifact."""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from kindred_client import crypto
from kindred_client.api_client import APIError, KindredAPI
from kindred_client.config import load_config
from kindred_client.keystore import load_keypair

console = Console()

ALLOWED_TYPES = ("claude_md", "routine", "skill_ref")


def build_metadata(
    *,
    type_: str,
    logical_name: str,
    kindred_id: str,
    body: bytes,
    tags: list[str] | None = None,
    valid_days: int = 180,
) -> dict:
    now = datetime.now(UTC)
    return {
        "kaf_version": "0.1",
        "type": type_,
        "logical_name": logical_name,
        "kindred_id": kindred_id,
        "valid_from": now.isoformat(),
        "valid_until": (now + timedelta(days=valid_days)).isoformat(),
        "tags": tags or [],
        "body_sha256": crypto.compute_content_id(body),
    }


async def _run_contribute(
    slug: str,
    *,
    type_: str,
    file_path: Path,
    logical_name: str | None,
    tags: list[str],
) -> dict:
    cfg = load_config()
    if not cfg.active_agent_id:
        raise RuntimeError("no active agent — run `kin join <invite_url>` first")
    entry = cfg.find_kindred(slug)
    if not entry:
        raise RuntimeError(f"not joined to kindred {slug!r} (run `kin join` first)")
    backend = entry.backend_url
    agent_sk, agent_pk = load_keypair(cfg.active_agent_id)

    body = file_path.read_bytes()

    api = KindredAPI(backend)
    kindred = await api.get_kindred_by_slug(slug)
    metadata = build_metadata(
        type_=type_,
        logical_name=logical_name or file_path.stem,
        kindred_id=kindred["id"],
        body=body,
        tags=tags,
    )
    cid = crypto.compute_content_id(metadata)
    author_sig = crypto.sign(agent_sk, cid.encode())

    return await api.upload_artifact(
        slug=slug,
        metadata=metadata,
        body=body,
        author_pubkey=agent_pk,
        author_sig=author_sig,
    )


def register(app: typer.Typer) -> None:
    @app.command("contribute")
    def contribute_cmd(
        slug: str = typer.Argument(..., help="Kindred slug"),
        type_: str = typer.Option(
            ..., "--type", help=f"Artifact type: {' | '.join(ALLOWED_TYPES)}"
        ),
        file: Path = typer.Option(..., "--file", exists=True, readable=True),
        name: str = typer.Option(None, "--name", help="Logical name (defaults to filename stem)"),
        tag: list[str] = typer.Option(None, "--tag", help="Tag (repeatable)"),
    ) -> None:
        """Upload an artifact to a kindred."""
        if type_ not in ALLOWED_TYPES:
            console.print(
                Panel.fit(
                    f"[red]Invalid --type[/red] {type_!r}. "
                    f"Must be one of: {', '.join(ALLOWED_TYPES)}",
                    border_style="red",
                )
            )
            raise typer.Exit(code=2)
        try:
            art = asyncio.run(
                _run_contribute(
                    slug,
                    type_=type_,
                    file_path=file,
                    logical_name=name,
                    tags=tag or [],
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
        except (RuntimeError, FileNotFoundError) as e:
            console.print(Panel.fit(f"[red]{e}[/red]", border_style="red"))
            raise typer.Exit(code=2) from e

        console.print(
            Panel.fit(
                f"[bold green]Contributed[/bold green]\n"
                f"tier: [yellow]{art.get('tier', '?')}[/yellow]\n"
                f"content_id: [cyan]{art.get('content_id', '?')}[/cyan]",
                title="kin contribute",
                border_style="green",
            )
        )
