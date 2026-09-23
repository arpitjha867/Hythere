from __future__ import annotations

import asyncio
import datetime as dt
import secrets

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from livekit.api import AccessToken, VideoGrants

from hythere_agent.config import AgentSettings
from hythere_agent.errors import ProviderError, SessionLimitError, SessionNotFoundError
from hythere_agent.pipeline import CompanionPipeline
from hythere_agent.registry import SessionRegistry

from .config import ApiSettings, get_api_settings
from .schemas import ConfigResponse, MockTurnRequest, MockTurnResponse, SessionCreateRequest, SessionCreateResponse
from .security import enforce_local_dev_auth

def create_app() -> FastAPI:
    app = FastAPI(title="Hythere API", version="0.1.0")
    settings = get_api_settings()
    agent_settings = AgentSettings.model_validate(
        {
            "mock_llm_backend": settings.mock_llm_backend,
            "sarvam_api_subscription_key": settings.sarvam_api_subscription_key,
            "sarvam_model": settings.sarvam_model,
            "distress_resource_name": settings.distress_resource_name,
            "distress_resource_contact": settings.distress_resource_contact,
            "distress_resource_region": settings.distress_resource_region,
            "response_timeout_seconds": settings.response_timeout_seconds,
            "session_ttl_minutes": settings.session_ttl_minutes,
            "max_concurrent_sessions": settings.max_concurrent_sessions,
            "history_turn_limit": settings.history_turn_limit,
        }
    )
    registry = SessionRegistry(
        max_sessions=settings.max_concurrent_sessions,
        ttl_minutes=settings.session_ttl_minutes,
        history_turn_limit=settings.history_turn_limit,
    )
    pipeline = CompanionPipeline(agent_settings, registry)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type"],
    )

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/v1/config", response_model=ConfigResponse)
    def get_public_config() -> ConfigResponse:
        return ConfigResponse(
            livekit_enabled=settings.livekit_enabled,
            local_dev_auth_enabled=settings.allow_local_dev_auth,
            max_session_minutes=settings.session_ttl_minutes,
            max_concurrent_sessions=settings.max_concurrent_sessions,
            distress_resource_configured=bool(settings.distress_resource_contact),
            mock_llm_backend=settings.mock_llm_backend,
            livekit_url=settings.livekit_url,
        )

    @app.post("/v1/session", response_model=SessionCreateResponse)
    def create_session(payload: SessionCreateRequest, request: Request, current: ApiSettings = Depends(get_api_settings)) -> SessionCreateResponse:
        if not payload.consent:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Consent is required before audio leaves the device.")

        enforce_local_dev_auth(request, current)

        try:
            if payload.mode == "livekit":
                if not current.livekit_enabled:
                    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="LiveKit mode is not configured yet.")
                room_name = f"hythere-{secrets.token_hex(6)}"
                identity = f"user-{secrets.token_hex(4)}"
                session = registry.create(mode="livekit", room_name=room_name, identity=identity)
                token = (
                    AccessToken(api_key=current.livekit_api_key, api_secret=current.livekit_api_secret)
                    .with_identity(identity)
                    .with_name(identity)
                    .with_ttl(dt.timedelta(seconds=current.session_token_ttl_seconds))
                    .with_grants(VideoGrants(room_join=True, room=room_name, can_publish=True, can_subscribe=True, can_publish_data=True))
                    .to_jwt()
                )
                return SessionCreateResponse(
                    session_id=session.session_id,
                    mode="livekit",
                    expires_in_seconds=current.session_token_ttl_seconds,
                    livekit_url=current.livekit_url,
                    livekit_room=room_name,
                    livekit_identity=identity,
                    livekit_token=token,
                )
            session = registry.create(mode="mock")
            return SessionCreateResponse(
                session_id=session.session_id,
                mode="mock",
                expires_in_seconds=current.session_ttl_minutes * 60,
            )
        except SessionLimitError as exc:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc

    @app.delete("/v1/session/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_session(session_id: str) -> None:
        registry.close(session_id)

    @app.post("/v1/mock/respond", response_model=MockTurnResponse)
    async def mock_respond(payload: MockTurnRequest, current: ApiSettings = Depends(get_api_settings)) -> MockTurnResponse:
        if len(payload.transcript) > current.max_request_characters:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Transcript is too large for this MVP.")
        try:
            reply = await asyncio.wait_for(
                pipeline.respond(session_id=payload.session_id, transcript=payload.transcript),
                timeout=current.response_timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Upstream model response timed out.") from exc
        except SessionNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except ProviderError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

        return MockTurnResponse(
            session_id=payload.session_id,
            reply_text=reply.reply_text,
            chunks=reply.chunks,
            backend=reply.backend,
            distress_notice=reply.distress_notice,
        )

    return app


app = create_app()
