from typing import Any

from pydantic import BaseModel


class RegisterAgentReq(BaseModel):
    agent_pubkey: str  # ed25519:hex
    display_name: str
    scope: dict[str, Any]
    expires_at: str  # ISO format
    sig: str  # hex


class AgentOut(BaseModel):
    id: str
    owner_id: str
    pubkey: str
    display_name: str
