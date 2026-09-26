from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HYTHERE_", case_sensitive=False, extra="ignore")

    livekit_url: str | None = None
    livekit_api_key: str | None = None
    livekit_api_secret: str | None = None
    mock_llm_backend: Literal["mock", "sarvam"] = "mock"
    sarvam_api_subscription_key: str | None = None
    sarvam_model: str = "sarvam-105b"
    sarvam_stt_model: str = "saaras:v4"
    sarvam_stt_mode: str = "codemix"
    sarvam_stt_language: str = "hi-IN"
    sarvam_tts_model: str = "bulbul:v3"
    sarvam_tts_speaker: str = "shubh"
    sarvam_tts_language: str = "hi-IN"
    distress_resource_name: str | None = None
    distress_resource_contact: str | None = None
    distress_resource_region: str | None = None
    history_turn_limit: int = Field(default=6, ge=1, le=20)
    response_timeout_seconds: int = Field(default=20, ge=2, le=60)
    session_ttl_minutes: int = Field(default=20, ge=1, le=120)
    max_concurrent_sessions: int = Field(default=20, ge=1, le=200)


@lru_cache(maxsize=1)
def get_agent_settings() -> AgentSettings:
    return AgentSettings()
