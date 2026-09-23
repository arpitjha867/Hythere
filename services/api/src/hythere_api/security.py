from __future__ import annotations

from urllib.parse import urlparse

from fastapi import HTTPException, Request, status

from .config import ApiSettings


def enforce_local_dev_auth(request: Request, settings: ApiSettings) -> None:
    if settings.allow_local_dev_auth:
        origin = request.headers.get("origin") or ""
        parsed = urlparse(origin)
        if parsed.hostname in {"127.0.0.1", "localhost"} and parsed.scheme in {"http", "https"}:
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Local dev auth is enabled only for localhost origins.",
        )

    expected_secret = settings.session_auth_secret
    if expected_secret:
        provided_secret = request.headers.get("x-hythere-session-auth")
        if provided_secret == expected_secret:
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing or invalid trusted session auth header.",
        )

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Session creation is closed until secure auth and configuration are enabled.",
    )
