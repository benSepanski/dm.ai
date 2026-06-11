from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dm_api.db.models.game_config import (
    GameConfig,
    GameConfigRead,
    GameConfigUpdate,
    build_game_config_read,
)
from dm_api.db.models.location import Location, LocationRead
from dm_api.db.models.world import World, WorldCreate, WorldRead
from dm_api.db.session import get_db

router = APIRouter()


async def _fetch_world_or_404(db: AsyncSession, world_id: uuid.UUID) -> World:
    result = await db.execute(select(World).where(World.id == world_id))
    world = result.scalar_one_or_none()
    if world is None:
        raise HTTPException(status_code=404, detail="World not found")
    return world


@router.post("/", response_model=WorldRead, status_code=status.HTTP_201_CREATED)
async def create_world(
    payload: WorldCreate,
    db: AsyncSession = Depends(get_db),
) -> WorldRead:
    world = World(
        name=payload.name,
        setting_description=payload.setting_description,
        themes=payload.themes,
        lore_summary=payload.lore_summary,
    )
    db.add(world)
    await db.commit()
    await db.refresh(world)
    return WorldRead.model_validate(world)


@router.get("/{world_id}", response_model=WorldRead)
async def get_world(
    world_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> WorldRead:
    world = await _fetch_world_or_404(db, world_id)
    return WorldRead.model_validate(world)


@router.get("/{world_id}/locations", response_model=list[LocationRead])
async def get_world_locations(
    world_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[LocationRead]:
    await _fetch_world_or_404(db, world_id)

    result = await db.execute(select(Location).where(Location.world_id == world_id))
    locations = result.scalars().all()
    return [LocationRead.model_validate(loc) for loc in locations]


@router.get("/{world_id}/config", response_model=GameConfigRead)
async def get_game_config(
    world_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> GameConfigRead:
    """Return the game's config: stored overrides plus the effective values.

    A game with no stored config returns all-null overrides with the
    deployment defaults as the effective settings.
    """
    await _fetch_world_or_404(db, world_id)
    result = await db.execute(select(GameConfig).where(GameConfig.world_id == world_id))
    return build_game_config_read(world_id, result.scalar_one_or_none())


@router.put("/{world_id}/config", response_model=GameConfigRead)
async def put_game_config(
    world_id: uuid.UUID,
    payload: GameConfigUpdate,
    db: AsyncSession = Depends(get_db),
) -> GameConfigRead:
    """Replace the game's config overrides.

    Full-replace semantics: a null/omitted field clears that override and the
    setting reverts to the deployment default. Takes effect on the next AI
    call for this game — no restart needed.
    """
    await _fetch_world_or_404(db, world_id)
    result = await db.execute(select(GameConfig).where(GameConfig.world_id == world_id))
    config = result.scalar_one_or_none()
    if config is None:
        config = GameConfig(world_id=world_id)
        db.add(config)

    config.ai_provider = payload.ai_provider
    config.orchestrator_model = payload.orchestrator_model
    config.generation_model = payload.generation_model
    config.context_token_limit = payload.context_token_limit
    config.context_preserve_last_n = payload.context_preserve_last_n
    config.database_url = payload.database_url
    config.redis_url = payload.redis_url

    await db.commit()
    await db.refresh(config)
    return build_game_config_read(world_id, config)


@router.delete("/{world_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_world(
    world_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    world = await _fetch_world_or_404(db, world_id)
    await db.delete(world)
    await db.commit()
