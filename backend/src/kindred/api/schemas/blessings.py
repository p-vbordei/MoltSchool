from pydantic import BaseModel


class AddBlessingReq(BaseModel):
    signer_pubkey: str
    sig: str
