"""WebSocket endpoint for real-time game session updates.

Server-push events are emitted by HTTP endpoints via :func:`broadcast_to_session`
whenever game state changes (chat messages, combat updates, proposals). The
WebSocket route also acts as a peer relay: messages from one client are
forwarded to all other clients in the same session.

Event shape (server → client):
  {"type": "chat_message", "session_id": "...", "role": "ai", "content": "..."}
  {"type": "combat_update", "session_id": "...", "combat": {...}}
  {"type": "proposal_ready", "session_id": "...", "proposal_id": "...", "proposal_type": "..."}
  {"type": "entity_update",  "session_id": "...", "entity_type": "...", "entity_id": "..."}
"""

from __future__ import annotations

import json
import logging
import uuid
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory connection registry (per session).
# Keyed by str(session_id) → list of active WebSocket connections.
# NOTE: this is process-local; a multi-process deployment needs a pub/sub
# broker (e.g. Redis) to propagate events across workers.
_connections: dict[str, list[WebSocket]] = defaultdict(list)


async def broadcast_to_session(session_id: str | uuid.UUID, event: dict[str, Any]) -> None:
    """Broadcast a server-initiated event to all WebSocket clients in a session.

    Dead connections are cleaned up silently. This is a no-op when no clients
    are currently connected to the session — safe to call unconditionally from
    HTTP endpoints after committing state changes.

    Args:
        session_id: The session whose clients should receive the event.
        event: JSON-serialisable dict; must include a ``"type"`` key identifying
            the event category (e.g. ``"chat_message"``, ``"combat_update"``).
    """
    key = str(session_id)
    connections = list(_connections.get(key, []))  # snapshot; avoid mutation during iteration
    if not connections:
        return

    payload = json.dumps(event)
    dead: list[WebSocket] = []
    for conn in connections:
        try:
            await conn.send_text(payload)
        except Exception:
            dead.append(conn)

    for conn in dead:
        try:
            _connections[key].remove(conn)
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
async def session_websocket(websocket: WebSocket, session_id: uuid.UUID) -> None:
    """WebSocket endpoint for a game session.

    Clients connect here to receive real-time server-push events (combat
    updates, chat messages, proposal notifications). Messages sent by a client
    are also relayed to all other connected clients in the same session so the
    frontend can use the socket for lightweight peer-sync (e.g. cursor moves).
    """
    await websocket.accept()
    key = str(session_id)
    _connections[key].append(websocket)
    logger.debug("ws connect  session_id=%s total=%d", key, len(_connections[key]))

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
            for conn in list(_connections[key]):
                if conn != websocket:
                    try:
                        await conn.send_text(payload)
                    except Exception:
                        pass
    except WebSocketDisconnect:
        _connections[key].remove(websocket)
        if not _connections[key]:
            del _connections[key]
        logger.debug(
            "ws disconnect  session_id=%s remaining=%d",
            key,
            len(_connections.get(key, [])),
        )
