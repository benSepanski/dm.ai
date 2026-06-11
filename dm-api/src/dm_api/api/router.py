from __future__ import annotations

from fastapi import APIRouter

from dm_api.api import (
    ai,
    auth,
    character_creation,
    characters,
    combat,
    combat_spells,
    locations,
    sessions,
    worlds,
    ws,
)

router = APIRouter()
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(worlds.router, prefix="/worlds", tags=["worlds"])
router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
router.include_router(
    character_creation.router, prefix="/characters/creation", tags=["characters"]
)
router.include_router(characters.router, prefix="/characters", tags=["characters"])
router.include_router(locations.router, prefix="/locations", tags=["locations"])
router.include_router(combat.router, tags=["combat"])
router.include_router(combat_spells.router, tags=["combat"])
router.include_router(ai.router, prefix="/ai", tags=["ai"])
router.include_router(ws.router, tags=["websocket"])
