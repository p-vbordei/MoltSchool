from pydantic import BaseModel


class RegisterUserReq(BaseModel):
    email: str
    display_name: str
    pubkey: str  # ed25519:hex


class UserOut(BaseModel):
    id: str
    email: str
    display_name: str
    pubkey: str  # ed25519:hex
