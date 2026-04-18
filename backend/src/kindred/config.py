from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KINDRED_", env_file=".env")

    database_url: str
    object_store_endpoint: str
    object_store_access_key: str
    object_store_secret_key: SecretStr
    object_store_bucket: str
    facilitator_signing_key_hex: SecretStr = Field(min_length=64, max_length=64)
    env: str = "dev"
    rate_limit_ask_per_min: int = 30
    rate_limit_contribute_per_hour: int = 10

    @property
    def facilitator_signing_key(self) -> bytes:
        return bytes.fromhex(self.facilitator_signing_key_hex.get_secret_value())
