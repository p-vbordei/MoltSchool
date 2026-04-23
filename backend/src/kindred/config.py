from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KINDRED_", env_file=".env")

    database_url: str

    @field_validator("database_url", mode="after")
    @classmethod
    def _ensure_asyncpg_driver(cls, v: str) -> str:
        # Railway / Heroku / etc. export the sync scheme; SQLAlchemy async needs +asyncpg.
        if v.startswith("postgresql://"):
            return "postgresql+asyncpg://" + v[len("postgresql://"):]
        if v.startswith("postgres://"):
            return "postgresql+asyncpg://" + v[len("postgres://"):]
        return v

    object_store_endpoint: str
    object_store_access_key: str
    object_store_secret_key: SecretStr
    object_store_bucket: str
    facilitator_signing_key_hex: SecretStr = Field(min_length=64, max_length=64)
    env: str = "dev"
    rate_limit_ask_per_min: int = 30
    rate_limit_contribute_per_hour: int = 10
    rate_limit_install_per_hour: int = 20
    embedding_provider: str = "fake"
    openai_api_key: SecretStr | None = None

    @property
    def facilitator_signing_key(self) -> bytes:
        return bytes.fromhex(self.facilitator_signing_key_hex.get_secret_value())
