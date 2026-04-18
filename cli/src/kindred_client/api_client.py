"""httpx-based async client for the Kindred backend API."""
from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any

import httpx

from kindred_client import crypto


class APIError(RuntimeError):
    """Raised when the backend returns a non-2xx status."""

    def __init__(self, status_code: int, message: str, body: Any | None = None):
        super().__init__(f"HTTP {status_code}: {message}")
        self.status_code = status_code
        self.message = message
        self.body = body


@dataclass
class KindredAPI:
    backend_url: str
    timeout: float = 15.0

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self.backend_url, timeout=self.timeout)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any | None = None,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        async with self._client() as c:
            resp = await c.request(method, path, json=json, headers=headers, params=params)
        if resp.status_code >= 400:
            try:
                body = resp.json()
                msg = body.get("message") or body.get("detail") or resp.text
            except Exception:
                body = resp.text
                msg = resp.text
            raise APIError(resp.status_code, str(msg), body=body)
        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    # --- Users / agents ---------------------------------------------------

    async def create_user(self, email: str, display_name: str, pubkey: bytes) -> dict:
        return await self._request(
            "POST",
            "/v1/users",
            json={
                "email": email,
                "display_name": display_name,
                "pubkey": crypto.pubkey_to_str(pubkey),
            },
        )

    async def get_user_by_pubkey(self, pubkey: bytes) -> dict:
        return await self._request(
            "GET", f"/v1/users/by-pubkey/{crypto.pubkey_to_str(pubkey)}"
        )

    async def create_agent(
        self,
        *,
        owner_id: str,
        owner_sk: bytes,
        agent_pubkey: bytes,
        display_name: str,
        scope: dict,
        expires_at_iso: str,
    ) -> dict:
        """Owner signs canonical_json({agent_pubkey, scope, expires_at}) and attests the agent."""
        payload = crypto.canonical_json(
            {
                "agent_pubkey": crypto.pubkey_to_str(agent_pubkey),
                "scope": scope,
                "expires_at": expires_at_iso,
            }
        )
        sig = crypto.sign(owner_sk, payload)
        return await self._request(
            "POST",
            f"/v1/users/{owner_id}/agents",
            json={
                "agent_pubkey": crypto.pubkey_to_str(agent_pubkey),
                "display_name": display_name,
                "scope": scope,
                "expires_at": expires_at_iso,
                "sig": sig.hex(),
            },
        )

    # --- Kindreds / invites / join ---------------------------------------

    async def get_kindred_by_slug(self, slug: str) -> dict:
        return await self._request("GET", f"/v1/kindreds/{slug}")

    async def create_kindred(
        self,
        *,
        owner_pubkey: bytes,
        slug: str,
        display_name: str,
        description: str = "",
        bless_threshold: int = 2,
    ) -> dict:
        return await self._request(
            "POST",
            "/v1/kindreds",
            json={
                "slug": slug,
                "display_name": display_name,
                "description": description,
                "bless_threshold": bless_threshold,
            },
            headers={"x-owner-pubkey": crypto.pubkey_to_str(owner_pubkey)},
        )

    async def issue_invite(
        self,
        *,
        slug: str,
        owner_pubkey: bytes,
        owner_sk: bytes,
        kindred_id: str,
        token: str,
        expires_at_iso: str,
        expires_in_days: int = 7,
        max_uses: int = 1,
    ) -> dict:
        inv_body = crypto.canonical_json(
            {"kindred_id": kindred_id, "token": token, "expires_at": expires_at_iso}
        )
        issuer_sig = crypto.sign(owner_sk, inv_body)
        return await self._request(
            "POST",
            f"/v1/kindreds/{slug}/invites",
            json={
                "expires_in_days": expires_in_days,
                "max_uses": max_uses,
                "issuer_sig": issuer_sig.hex(),
                "inv_body_b64": base64.b64encode(inv_body).decode(),
            },
            headers={"x-owner-pubkey": crypto.pubkey_to_str(owner_pubkey)},
        )

    async def join(
        self,
        *,
        token: str,
        agent_pubkey: bytes,
        agent_sk: bytes,
    ) -> dict:
        accept_body = crypto.canonical_json(
            {"token": token, "agent_pubkey": crypto.pubkey_to_str(agent_pubkey)}
        )
        accept_sig = crypto.sign(agent_sk, accept_body)
        return await self._request(
            "POST",
            "/v1/join",
            json={
                "token": token,
                "agent_pubkey": crypto.pubkey_to_str(agent_pubkey),
                "accept_sig": accept_sig.hex(),
                "accept_body_b64": base64.b64encode(accept_body).decode(),
            },
        )

    async def leave(self, *, slug: str, agent_pubkey: bytes) -> dict | None:
        return await self._request(
            "POST",
            f"/v1/kindreds/{slug}/leave",
            headers={"x-agent-pubkey": crypto.pubkey_to_str(agent_pubkey)},
        )

    # --- Artifacts --------------------------------------------------------

    async def upload_artifact(
        self,
        *,
        slug: str,
        metadata: dict,
        body: bytes,
        author_pubkey: bytes,
        author_sig: bytes,
    ) -> dict:
        return await self._request(
            "POST",
            f"/v1/kindreds/{slug}/artifacts",
            json={
                "metadata": metadata,
                "body_b64": base64.b64encode(body).decode(),
                "author_pubkey": crypto.pubkey_to_str(author_pubkey),
                "author_sig": author_sig.hex(),
            },
        )

    async def list_artifacts(self, slug: str) -> list[dict]:
        return await self._request("GET", f"/v1/kindreds/{slug}/artifacts")

    async def bless_artifact(
        self,
        *,
        slug: str,
        content_id: str,
        signer_pubkey: bytes,
        sig: bytes,
    ) -> dict:
        return await self._request(
            "POST",
            f"/v1/kindreds/{slug}/artifacts/{content_id}/bless",
            json={
                "signer_pubkey": crypto.pubkey_to_str(signer_pubkey),
                "sig": sig.hex(),
            },
        )

    # --- Ask / outcomes --------------------------------------------------

    async def ask(
        self,
        *,
        slug: str,
        agent_pubkey: bytes,
        query: str,
        k: int = 5,
        include_peer_shared: bool = False,
    ) -> dict:
        return await self._request(
            "POST",
            f"/v1/kindreds/{slug}/ask",
            json={"query": query, "k": k, "include_peer_shared": include_peer_shared},
            headers={"x-agent-pubkey": crypto.pubkey_to_str(agent_pubkey)},
        )

    async def report_outcome(self, *, audit_id: str, result: str, notes: str = "") -> dict:
        return await self._request(
            "POST",
            "/v1/ask/outcome",
            json={"audit_id": audit_id, "result": result, "notes": notes},
        )
