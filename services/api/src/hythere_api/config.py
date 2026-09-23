from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HYTHERE_", case_sensitive=False, extra="ignore")

    app_env: Literal["development", "production", "test"] = "development"
    cors_origins: str = "http://127.0.0.1:3000,http://localhost:3000"
    allow_local_dev_auth: bool = False
    session_auth_secret: str | None = None
    livekit_url: str | None = None
    livekit_api_key: str | None = None
    livekit_api_secret: str | None = None
    session_token_ttl_seconds: int = Field(default=600, ge=60, le=3600)
    max_request_characters: int = Field(default=600, ge=32, le=4000)
    max_concurrent_sessions: int = Field(default=20, ge=1, le=200)
    session_ttl_minutes: int = Field(default=20, ge=1, le=120)
    history_turn_limit: int = Field(default=6, ge=1, le=20)
    response_timeout_seconds: int = Field(default=20, ge=2, le=60)
    mock_llm_backend: Literal["mock", "sarvam"] = "mock"
    sarvam_api_subscription_key: str | None = None
    sarvam_model: str = "sarvam-105b"
    distress_resource_name: str | None = None
    distress_resource_contact: str | None = None
    distress_resource_region: str | None = None

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def livekit_enabled(self) -> bool:
        return bool(self.livekit_url and self.livekit_api_key and self.livekit_api_secret)


@lru_cache(maxsize=1)
def get_api_settings() -> ApiSettings:
    return ApiSettings()
