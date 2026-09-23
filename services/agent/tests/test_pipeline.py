from __future__ import annotations

import asyncio

import pytest

from hythere_agent.config import AgentSettings
from hythere_agent.errors import ProviderError, SessionLimitError
from hythere_agent.pipeline import CompanionPipeline
from hythere_agent.registry import SessionRegistry


def build_registry(max_sessions: int = 2) -> SessionRegistry:
    return SessionRegistry(max_sessions=max_sessions, ttl_minutes=20, history_turn_limit=6)


def build_settings(**overrides) -> AgentSettings:
    base = {
        "mock_llm_backend": "mock",
        "response_timeout_seconds": 5,
        "session_ttl_minutes": 20,
        "max_concurrent_sessions": 2,
        "history_turn_limit": 6,
    }
    base.update(overrides)
    return AgentSettings.model_validate(base)


def test_pipeline_returns_deterministic_mock_reply() -> None:
    registry = build_registry()
    session = registry.create(mode="mock")
    pipeline = CompanionPipeline(build_settings(), registry)

    reply = asyncio.run(pipeline.respond(session_id=session.session_id, transcript="Aaj mood off hai"))

    assert reply.reply_text
    assert reply.backend == "mock"
    assert reply.chunks


def test_pipeline_prepends_distress_notice_when_needed() -> None:
    registry = build_registry()
    session = registry.create(mode="mock")
    pipeline = CompanionPipeline(
        build_settings(
            distress_resource_name="Example Helpline",
            distress_resource_contact="12345",
            distress_resource_region="Test Region",
        ),
        registry,
    )

    reply = asyncio.run(pipeline.respond(session_id=session.session_id, transcript="I want to kill myself"))

    assert reply.distress_notice is not None
    assert "Example Helpline" in reply.reply_text


def test_session_isolation_keeps_histories_separate() -> None:
    registry = build_registry(max_sessions=3)
    session_a = registry.create(mode="mock")
    session_b = registry.create(mode="mock")
    pipeline = CompanionPipeline(build_settings(max_concurrent_sessions=3), registry)

    asyncio.run(pipeline.respond(session_id=session_a.session_id, transcript="Session A"))
    asyncio.run(pipeline.respond(session_id=session_b.session_id, transcript="Session B"))

    assert registry.get(session_a.session_id).turns[0].text == "Session A"
    assert registry.get(session_b.session_id).turns[0].text == "Session B"


def test_registry_enforces_session_limit() -> None:
    registry = build_registry(max_sessions=1)
    registry.create(mode="mock")
    with pytest.raises(SessionLimitError):
        registry.create(mode="mock")


def test_new_turn_marks_previous_generation_stale() -> None:
    registry = build_registry()
    session = registry.create(mode="mock")

    _, first_generation = registry.begin_turn(session.session_id, "pehla turn")
    _, second_generation = registry.begin_turn(session.session_id, "doosra turn")

    assert registry.is_current_generation(session.session_id, first_generation) is False
    assert registry.is_current_generation(session.session_id, second_generation) is True


def test_sarvam_backend_requires_api_key() -> None:
    registry = build_registry()
    with pytest.raises(ProviderError):
        CompanionPipeline(build_settings(mock_llm_backend="sarvam", sarvam_api_subscription_key=None), registry)
