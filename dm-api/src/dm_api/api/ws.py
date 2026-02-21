"""WebSocket endpoint for real-time game session updates."""

import json
import uuid
from collections import defaultdict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

# In-memory connection registry (per session)
_connections: dict[str, list[WebSocket]] = defaultdict(list)


@router.websocket("/ws/sessions/{session_id}")
async def session_websocket(websocket: WebSocket, session_id: uuid.UUID) -> None:
    """WebSocket endpoint for a game session.

    Clients connect here to receive real-time updates about combat,
    chat messages, and proposal notifications.
    """
    await websocket.accept()
    key = str(session_id)
    _connections[key].append(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            # Broadcast received messages to all connected clients
            message = json.loads(data)
            message["session_id"] = key
            for conn in _connections[key]:
                if conn != websocket:
                    await conn.send_text(json.dumps(message))
    except WebSocketDisconnect:
        _connections[key].remove(websocket)
        if not _connections[key]:
            del _connections[key]
