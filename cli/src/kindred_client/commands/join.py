"""`kin join <invite_url>` — onboard a new agent into a kindred."""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import typer
from rich.console import Console
from rich.panel import Panel

from kindred_client import crypto
from kindred_client.api_client import APIError, KindredAPI
from kindred_client.config import Config, KindredEntry, load_config, save_config
from kindred_client.keystore import load_keypair, store_keypair

console = Console()


def parse_invite_url(url: str) -> tuple[str, str, str]:
    """Return (backend_url, slug, token) from `https://<host>/k/<slug>?inv=<token>`."""
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"invalid invite URL: {url!r}")
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2 or parts[0] != "k":
        raise ValueError(f"invite URL must contain /k/<slug>, got path={parsed.path!r}")
    slug = parts[1]
    qs = parse_qs(parsed.query)
    tokens = qs.get("inv") or qs.get("token")
    if not tokens:
        raise ValueError("invite URL missing ?inv=<token>")
    backend = f"{parsed.scheme}://{parsed.netloc}"
    return backend, slug, tokens[0]


def _agent_id_for(pubkey: bytes) -> str:
    return f"agent-{pubkey.hex()[:8]}"


async def _run_join(
    invite_url: str,
    *,
    email: str,
    display_name: str,
    prompt_create_agent: bool = True,
) -> dict:
    backend_url, slug, token = parse_invite_url(invite_url)
    api = KindredAPI(backend_url)
    cfg = load_config()

    # --- Owner: reuse if present, else register ---
    if cfg.active_owner_id:
        owner_sk, owner_pk = load_keypair(cfg.active_owner_id)
        user = await api.get_user_by_pubkey(owner_pk)
    else:
        owner_sk, owner_pk = crypto.generate_keypair()
        user = await api.create_user(email, display_name, owner_pk)
        store_keypair("owner", owner_sk, owner_pk)
        cfg.active_owner_id = "owner"
        cfg.backend_url = backend_url

    # --- Agent: always create fresh for this join (pattern matches spec §6) ---
    agent_sk, agent_pk = crypto.generate_keypair()
    scope = {"kindreds": ["*"], "actions": ["read", "contribute"]}
    expires_at = (datetime.now(UTC) + timedelta(days=180)).isoformat()
    await api.create_agent(
        owner_id=user["id"],
        owner_sk=owner_sk,
        agent_pubkey=agent_pk,
        display_name=display_name,
        scope=scope,
        expires_at_iso=expires_at,
    )
    agent_id = _agent_id_for(agent_pk)
    store_keypair(agent_id, agent_sk, agent_pk)
    cfg.active_agent_id = agent_id

    # --- Accept the invite ---
    await api.join(token=token, agent_pubkey=agent_pk, agent_sk=agent_sk)

    cfg.upsert_kindred(
        KindredEntry(slug=slug, backend_url=backend_url, user_id=user["id"])
    )
    save_config(cfg)

    return {
        "slug": slug,
        "backend_url": backend_url,
        "user_id": user["id"],
        "agent_id": agent_id,
        "agent_pubkey": crypto.pubkey_to_str(agent_pk),
    }


def register(app: typer.Typer) -> None:
    @app.command("join")
    def join_cmd(
        invite_url: str = typer.Argument(..., help="Invite URL (https://host/k/<slug>?inv=...)"),
        email: str = typer.Option(None, "--email", help="Email (prompted if missing)"),
        display_name: str = typer.Option(
            None, "--name", help="Display name (prompted if missing)"
        ),
    ) -> None:
        """Join a kindred via an invite URL."""
        cfg = _safe_load_config()
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
                f"[bold green]Joined[/bold green] [cyan]{result['slug']}[/cyan]\n"
                f"agent: [magenta]{result['agent_id']}[/magenta]",
                title="kin join",
                border_style="green",
            )
        )


def _safe_load_config() -> Config:
    """Load config, returning a fresh default if the file is missing."""
    try:
        return load_config()
    except FileNotFoundError:
        return Config()
