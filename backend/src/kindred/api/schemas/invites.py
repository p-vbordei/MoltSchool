from pydantic import BaseModel


class IssueInviteReq(BaseModel):
    expires_in_days: int = 7
    max_uses: int = 1
    issuer_sig: str  # hex
    inv_body_b64: str


class InviteOut(BaseModel):
    token: str
    expires_at: str
    max_uses: int
    uses: int


class JoinReq(BaseModel):
    token: str
    agent_pubkey: str
    accept_sig: str
    accept_body_b64: str
