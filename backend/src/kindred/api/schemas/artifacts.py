from typing import Any

from pydantic import BaseModel


class UploadArtifactReq(BaseModel):
    metadata: dict[str, Any]
    body_b64: str
    author_pubkey: str
    author_sig: str


class ArtifactOut(BaseModel):
    content_id: str
    type: str
    logical_name: str
    tier: str
    valid_from: str
    valid_until: str
    outcome_uses: int
    outcome_successes: int
    blessings_count: int
    bless_threshold: int
