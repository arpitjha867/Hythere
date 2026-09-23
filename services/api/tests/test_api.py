from __future__ import annotations

import os
from importlib import reload

from fastapi.testclient import TestClient
from livekit.api import TokenVerifier


def build_client(**env_overrides):
    for key in list(os.environ):
        if key.startswith("HYTHERE_"):
            os.environ.pop(key)
    os.environ.update({"HYTHERE_ALLOW_LOCAL_DEV_AUTH": "true", **env_overrides})
    import hythere_api.config as config
    import hythere_api.main as main

    reload(config)
    reload(main)
    return TestClient(main.create_app())


def test_config_reports_mock_defaults() -> None:
    client = build_client()

    response = client.get("/v1/config")

    assert response.status_code == 200
    assert response.json()["mock_enabled"] is True
    assert response.json()["livekit_enabled"] is False


def test_session_creation_requires_localhost_origin() -> None:
    client = build_client()

    response = client.post(
        "/v1/session",
        json={"consent": True, "mode": "mock"},
        headers={"origin": "https://example.com"},
    )

    assert response.status_code == 403


def test_session_creation_and_mock_turn_flow() -> None:
    client = build_client()

    created = client.post(
        "/v1/session",
        json={"consent": True, "mode": "mock"},
        headers={"origin": "http://127.0.0.1:3000"},
    )
    session_id = created.json()["session_id"]

    response = client.post(
        "/v1/mock/respond",
        json={"session_id": session_id, "transcript": "Aaj ka din heavy tha"},
    )

    assert response.status_code == 200
    assert response.json()["reply_text"]


def test_session_limit_returns_429() -> None:
    client = build_client(HYTHERE_MAX_CONCURRENT_SESSIONS="1")

    first = client.post(
        "/v1/session",
        json={"consent": True, "mode": "mock"},
        headers={"origin": "http://localhost:3000"},
    )
    assert first.status_code == 200
    second = client.post(
        "/v1/session",
        json={"consent": True, "mode": "mock"},
        headers={"origin": "http://localhost:3000"},
    )
    assert second.status_code == 429


def test_livekit_response_is_disabled_without_credentials() -> None:
    client = build_client()

    response = client.post(
        "/v1/session",
        json={"consent": True, "mode": "livekit"},
        headers={"origin": "http://localhost:3000"},
    )

    assert response.status_code == 503


def test_livekit_token_is_scoped_to_generated_room() -> None:
    client = build_client(
        HYTHERE_LIVEKIT_URL="wss://example.livekit.cloud",
        HYTHERE_LIVEKIT_API_KEY="test_key",
        HYTHERE_LIVEKIT_API_SECRET="test_secret",
    )

    response = client.post(
        "/v1/session",
        json={"consent": True, "mode": "livekit"},
        headers={"origin": "http://localhost:3000"},
    )

    assert response.status_code == 200
    payload = response.json()
    claims = TokenVerifier(api_key="test_key", api_secret="test_secret").verify(payload["livekit_token"])
    assert claims.video is not None
    assert claims.video.room_join is True
    assert claims.video.room == payload["livekit_room"]
    assert claims.identity == payload["livekit_identity"]
