"""Application settings, loaded from environment / .env."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Zerodha Kite Connect
    kite_api_key: str = ""
    kite_api_secret: str = ""
    kite_redirect_url: str = "http://localhost:8000/auth/kite/callback"

    # Anthropic
    anthropic_api_key: str = ""

    # Infra
    database_url: str = "postgresql+psycopg://trader:trader@localhost:5432/trading"
    redis_url: str = "redis://localhost:6379/0"

    # App behavior
    use_mock_market_data: bool = True
    token_encryption_key: str = "change-me-32-bytes-minimum-secret"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    @property
    def kite_configured(self) -> bool:
        return bool(self.kite_api_key and self.kite_api_secret)


@lru_cache
def get_settings() -> Settings:
    return Settings()
