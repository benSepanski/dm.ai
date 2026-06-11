"""WebSocket endpoint for real-time game session updates.

Server-push events are emitted by HTTP endpoints via :func:`broadcast_to_session`
whenever game state changes (chat messages, combat updates, proposals). The
WebSocket route also acts as a peer relay: messages from one client are
forwarded to all other clients in the same session.

Connections carry a :class:`~dm_api.api.auth.ClientRole` resolved from the
``dm_token`` query parameter at connect time. Events broadcast with
``dm_only=True`` (e.g. ``proposal_ready``) are delivered only to DM
connections so player browsers never receive unreviewed AI content.

Event shape (server → client):
  {"type": "chat_message", "session_id": "...", "role": "ai", "content": "..."}
  {"type": "combat_update", "session_id": "...", "combat": {...}}
  {"type": "proposal_ready", "session_id": "...", "proposal_id": "...", "proposal_type": "...", "status": "..."}  (DM only)
  {"type": "entity_update",  "session_id": "...", "entity_type": "...", "entity_id": "..."}
"""

from __future__ import annotations

import json
import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from dm_api.api.auth import ClientRole, ws_client_role

logger = logging.getLogger(__name__)
router = APIRouter()


@dataclass
class SessionClient:
    """A connected WebSocket client and the role it authenticated as."""

    socket: WebSocket
    role: ClientRole


# In-memory connection registry (per session).
# Keyed by str(session_id) → list of connected clients.
# NOTE: this is process-local; a multi-process deployment needs a pub/sub
# broker (e.g. Redis) to propagate events across workers.
_connections: dict[str, list[SessionClient]] = defaultdict(list)


async def broadcast_to_session(
    session_id: str | uuid.UUID,
    event: dict[str, Any],
    *,
    dm_only: bool = False,
) -> None:
    """Broadcast a server-initiated event to WebSocket clients in a session.

    Dead connections are cleaned up silently. This is a no-op when no clients
    are currently connected to the session — safe to call unconditionally from
    HTTP endpoints after committing state changes.

    Args:
        session_id: The session whose clients should receive the event.
        event: JSON-serialisable dict; must include a ``"type"`` key identifying
            the event category (e.g. ``"chat_message"``, ``"combat_update"``).
        dm_only: When True, deliver only to clients that authenticated with
            the DM token (used for proposal events the players must not see).
    """
    key = str(session_id)
    clients = list(_connections.get(key, []))  # snapshot; avoid mutation during iteration
    if not clients:
        return

    payload = json.dumps(event)
    dead: list[SessionClient] = []
    for client in clients:
        if dm_only and client.role is not ClientRole.DM:
            continue
        try:
            await client.socket.send_text(payload)
        except Exception:
            dead.append(client)

    for client in dead:
        try:
            _connections[key].remove(client)
        except ValueError:
            pass
    if key in _connections and not _connections[key]:
        del _connections[key]

    if dead:
        logger.debug(
            "broadcast_to_session: removed %d dead connection(s) session_id=%s",
            len(dead),
            key,
        )


@router.websocket("/ws/sessions/{session_id}")
async def session_websocket(
    websocket: WebSocket,
    session_id: uuid.UUID,
    role: ClientRole = Depends(ws_client_role),
) -> None:
    """WebSocket endpoint for a game session.

    Clients connect here to receive real-time server-push events (combat
    updates, chat messages, and — for DM connections — proposal
    notifications). Messages sent by a client are also relayed to all other
    connected clients in the same session so the frontend can use the socket
    for lightweight peer-sync (e.g. battle-map token moves).
    """
    await websocket.accept()
    key = str(session_id)
    client = SessionClient(socket=websocket, role=role)
    _connections[key].append(client)
    logger.info(
        "ws connect  session_id=%s role=%s total=%d", key, role.value, len(_connections[key])
    )

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"error": "invalid JSON"}))
                continue
            # Relay to other clients in the same session.
            # Per-connection errors are swallowed: a dead relay target must not
            # terminate the sending client's connection. Stale entries are pruned
            # by broadcast_to_session on the next server-push event.
            message["session_id"] = key
            payload = json.dumps(message)
            for other in list(_connections[key]):
                if other is not client:
                    try:
                        await other.socket.send_text(payload)
                    except Exception:
                        pass
    except WebSocketDisconnect:
        # broadcast_to_session may have already pruned this connection if it
        # failed a send_text while receive_text was suspended — guard defensively.
        try:
            _connections[key].remove(client)
        except ValueError:
            pass
        if not _connections.get(key):
            _connections.pop(key, None)
        logger.info(
            "ws disconnect  session_id=%s remaining=%d",
            key,
            len(_connections.get(key, [])),
        )
