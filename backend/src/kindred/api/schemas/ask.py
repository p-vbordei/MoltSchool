from pydantic import BaseModel, Field


class AskReq(BaseModel):
    query: str
    k: int = Field(default=5, ge=1, le=20)
    include_peer_shared: bool = False


class ProvenanceChip(BaseModel):
    content_id: str
    logical_name: str
    type: str
    tier: str
    author_pubkey: str
    outcome_success_rate: float
    valid_until: str


class AskResp(BaseModel):
    audit_id: str
    artifacts: list[dict]
    provenance: list[ProvenanceChip]
    blocked_injection: bool = False
