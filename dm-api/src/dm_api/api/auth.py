"""DM/player role authentication.

A single shared DM token splits connected clients into two roles:

- ``DM`` — presents the token in the ``X-DM-Token`` header (REST) or the
  ``dm_token`` query parameter (WebSocket). Full read/write access.
- ``PLAYER`` — everyone else. DM-only endpoints respond 403, and sensitive
  fields are redacted from read endpoints (see ``visibility.py``).

The token comes from ``settings.dm_token`` (``DM_TOKEN`` in .env). When
unset, one is generated per process and logged at startup so the DM can
copy it from the API logs.
"""

from __future__ import annotations

import logging
import secrets
from enum import Enum

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel

from dm_api.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


class ClientRole(str, Enum):
    """Access level of a connected client, derived from the DM token."""

    DM = "dm"
    PLAYER = "player"


# Fallback token generated once per process when DM_TOKEN is not configured.
_generated_token: str | None = None


def get_dm_token() -> str:
    """Return the active DM token (configured, or auto-generated once)."""
    global _generated_token
    if settings.dm_token:
        return settings.dm_token
    if _generated_token is None:
        _generated_token = secrets.token_urlsafe(16)
    return _generated_token


def log_dm_token_source() -> None:
    """Tell the operator (the DM) where their token comes from. Called at startup."""
    if settings.dm_token:
        logger.info("DM token loaded from DM_TOKEN")
    else:
        logger.warning(
            "DM_TOKEN is not set — generated a DM token for this run: %s  "
            "Enter it in the UI to unlock DM controls; set DM_TOKEN in .env "
            "to keep it stable across restarts.",
            get_dm_token(),
        )


def _role_for_token(token: str | None) -> ClientRole:
    if token is not None and secrets.compare_digest(token, get_dm_token()):
        return ClientRole.DM
    return ClientRole.PLAYER


def client_role(x_dm_token: str | None = Header(default=None)) -> ClientRole:
    """FastAPI dependency: resolve the caller's role from the X-DM-Token header."""
    return _role_for_token(x_dm_token)


def require_dm(role: ClientRole = Depends(client_role)) -> ClientRole:
    """FastAPI dependency: reject non-DM callers with 403."""
    if role is not ClientRole.DM:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="DM token required",
        )
    return role


def ws_client_role(dm_token: str | None = Query(default=None)) -> ClientRole:
    """WebSocket dependency: resolve the role from the dm_token query parameter.

    WebSocket clients can't set custom headers from the browser, so the
    token rides in the query string instead.
    """
    return _role_for_token(dm_token)


class RoleRead(BaseModel):
    role: ClientRole


@router.get("/role", response_model=RoleRead)
async def get_role(role: ClientRole = Depends(client_role)) -> RoleRead:
    """Report the caller's role — lets the UI validate a DM token."""
    return RoleRead(role=role)
