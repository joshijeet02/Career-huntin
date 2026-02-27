from __future__ import annotations

import hmac
import os
from typing import Final

from fastapi import HTTPException, Request

_ALLOWED_PATH_PREFIXES: Final[tuple[str, ...]] = (
    "/healthz",
    "/docs",
    "/openapi.json",
    "/redoc",
)
_ALLOWED_EXACT_PATHS: Final[set[str]] = {"/"}


def _extract_bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        return None
    token = authorization[len(prefix) :].strip()
    return token or None


def validate_request_auth(request: Request) -> None:
    expected = os.getenv("BACKEND_API_KEY", "").strip()
    if not expected:
        return

    path = request.url.path
    if path in _ALLOWED_EXACT_PATHS or any(path.startswith(prefix) for prefix in _ALLOWED_PATH_PREFIXES):
        return

    provided = request.headers.get("X-API-Key") or _extract_bearer(request.headers.get("Authorization"))
    if not provided or not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")
