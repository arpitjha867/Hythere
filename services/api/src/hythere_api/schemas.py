from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SessionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    consent: bool
    mode: Literal["mock", "livekit"] = "mock"


class SessionCreateResponse(BaseModel):
    session_id: str
    mode: Literal["mock", "livekit"]
    expires_in_seconds: int
    livekit_url: str | None = None
    livekit_room: str | None = None
    livekit_identity: str | None = None
    livekit_token: str | None = None


class MockTurnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(min_length=8, max_length=80)
    transcript: str = Field(min_length=1, max_length=600)


class MockTurnResponse(BaseModel):
    session_id: str
    reply_text: str
    chunks: list[str]
    backend: str
    distress_notice: str | None = None


class ConfigResponse(BaseModel):
    mock_enabled: bool = True
    livekit_enabled: bool
    local_dev_auth_enabled: bool
    max_session_minutes: int
    max_concurrent_sessions: int
    distress_resource_configured: bool
    mock_llm_backend: str
    livekit_url: str | None = None
