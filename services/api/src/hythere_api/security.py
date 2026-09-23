from __future__ import annotations

from fastapi import HTTPException, Request, status

from .config import ApiSettings


def enforce_local_dev_auth(request: Request, settings: ApiSettings) -> None:
    if settings.allow_local_dev_auth:
        origin = request.headers.get("origin") or ""
        if origin.startswith("http://127.0.0.1") or origin.startswith("http://localhost"):
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Local dev auth is enabled only for localhost origins.",
        )

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Session creation is closed until secure auth and configuration are enabled.",
    )
