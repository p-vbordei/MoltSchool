"""`kin report <audit_id> <result>` — report how useful an /ask was."""
from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.panel import Panel

from kindred_client.api_client import APIError, KindredAPI
from kindred_client.config import load_config

console = Console()


async def _run_report(
    audit_id: str, result: str, *, chosen: str | None, notes: str,
) -> dict:
    cfg = load_config()
    api = KindredAPI(cfg.backend_url)
    return await api.report_outcome(
        audit_id=audit_id, result=result,
        notes=notes, chosen_content_id=chosen,
    )


def register(app: typer.Typer) -> None:
    @app.command("report")
    def report_cmd(
        audit_id: str = typer.Argument(..., help="Audit ID from a prior `kin ask`"),
        result: str = typer.Argument(
            ..., help="One of: success | partial | fail | overridden"
        ),
        chose: str | None = typer.Option(
            None, "--chose", help="content_id of the artifact the agent actually used"
        ),
        notes: str = typer.Option("", "--notes", help="Free-text note"),
    ) -> None:
        """Report how useful the artifacts returned by a previous ask were."""
        try:
            asyncio.run(_run_report(audit_id, result, chosen=chose, notes=notes))
        except APIError as e:
            console.print(Panel.fit(
                f"[red]Backend error[/red]: {e.message}",
                title=f"HTTP {e.status_code}", border_style="red",
            ))
            raise typer.Exit(code=1) from e
        console.print(Panel.fit(
            f"[green]Outcome reported[/green]: {result}"
            + (f" (chose {chose})" if chose else ""),
            border_style="green",
        ))
