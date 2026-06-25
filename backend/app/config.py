"""Application settings, loaded from environment / .env."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


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
    # Accept either a comma-separated string ("a,b") or a JSON array ('["a","b"]')
    # from the environment. NoDecode stops pydantic-settings from JSON-decoding the
    # raw value before our validator runs, so a plain string like
    # "http://localhost:3000" doesn't crash settings loading.
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: object) -> object:
        if value is None:
            return []
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return []
            if text.startswith("["):
                return json.loads(text)
            return [item.strip() for item in text.split(",") if item.strip()]
        return value

    @property
    def kite_configured(self) -> bool:
        return bool(self.kite_api_key and self.kite_api_secret)


@lru_cache
def get_settings() -> Settings:
    return Settings()
