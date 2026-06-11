from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from game_engine.rules.dnd_5_5e import long_rest, short_rest
from game_engine.types import RestType
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dm_api.api.auth import ClientRole, client_role, require_dm
from dm_api.api.character_combat import (
    active_combats_with_character,
    write_through_character_update,
)
from dm_api.api.combat_utils import (
    SHEET_STATE_FIELDS,
    broadcast_combat,
    character_to_sheet,
)
from dm_api.api.visibility import character_read_for
from dm_api.db.models.character import (
    Character,
    CharacterCreate,
    CharacterRead,
    CharacterUpdate,
    RestRead,
    RestRequest,
)
from dm_api.db.models.combat import CombatStateRead
from dm_api.db.models.world import World
from dm_api.db.session import get_db

router = APIRouter()


@router.post("/", response_model=CharacterRead, status_code=status.HTTP_201_CREATED)
async def create_character(
    payload: CharacterCreate,
    db: AsyncSession = Depends(get_db),
) -> CharacterRead:
    character = Character(**payload.model_dump())
    db.add(character)
    await db.commit()
    await db.refresh(character)
    return CharacterRead.model_validate(character)


@router.get("/{char_id}", response_model=CharacterRead)
async def get_character(
    char_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    role: ClientRole = Depends(client_role),
) -> CharacterRead:
    result = await db.execute(select(Character).where(Character.id == char_id))
    character = result.scalar_one_or_none()
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")
    return character_read_for(character, role)


@router.patch("/{char_id}", response_model=CharacterRead)
async def update_character(
    char_id: uuid.UUID,
    payload: CharacterUpdate,
    db: AsyncSession = Depends(get_db),
    _role: ClientRole = Depends(require_dm),
) -> CharacterRead:
    """Partially update a character.

    ``stats`` is merged key-by-key into the existing blob (a key set to
    null removes it) — re-sending the whole blob is not required. Updates
    are also written through into any active combat the character is
    enrolled in, so a mid-fight PATCH affects the live fight and is not
    overwritten when combat ends.
    """
    result = await db.execute(select(Character).where(Character.id == char_id))
    character = result.scalar_one_or_none()
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")

    update_data = payload.model_dump(exclude_unset=True)
    stats_update: dict = update_data.pop("stats", None) or {}
    if stats_update:
        merged = {**(character.stats or {}), **stats_update}
        character.stats = {k: v for k, v in merged.items() if v is not None}
    for field, value in update_data.items():
        setattr(character, field, value)

    updated_combats = await write_through_character_update(
        db, character, update_data, stats_update
    )

    await db.commit()
    await db.refresh(character)
    for combat in updated_combats:
        await db.refresh(combat)
        await broadcast_combat(combat.session_id, CombatStateRead.model_validate(combat))
    return CharacterRead.model_validate(character)


@router.post("/{char_id}/rest", response_model=RestRead)
async def rest_character(
    char_id: uuid.UUID,
    payload: RestRequest,
    db: AsyncSession = Depends(get_db),
    _role: ClientRole = Depends(require_dm),
) -> RestRead:
    """Take a short or long rest, resolved by the rule engine (2024 PHB).

    Short rest: spend Hit Point Dice to heal (``hit_dice_to_spend``);
    warlock pact slots return. Long rest: full HP, all Hit Point Dice and
    spell slots return, temp HP ends, exhaustion drops by 1. Spell slots
    and hit dice are derived from class/level the first time a character
    rests; thereafter the spent/remaining state persists in ``stats``.
    """
    result = await db.execute(select(Character).where(Character.id == char_id))
    character = result.scalar_one_or_none()
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")

    if await active_combats_with_character(db, char_id):
        raise HTTPException(status_code=409, detail="Cannot rest during an active combat")

    sheet = character_to_sheet(character)
    if sheet.is_dead:
        raise HTTPException(status_code=409, detail=f"{sheet.name} is dead and cannot rest")

    if payload.rest_type is RestType.LONG:
        rest_result = long_rest(sheet)
    else:
        rest_result = short_rest(sheet, hit_dice_to_spend=payload.hit_dice_to_spend)

    sheet_dict = sheet.to_dict()
    character.hp_current = sheet.hp_current
    stats = dict(character.stats or {})
    for field in SHEET_STATE_FIELDS:
        stats[field] = sheet_dict[field]
    character.stats = stats

    await db.commit()
    await db.refresh(character)
    return RestRead(
        rest_type=payload.rest_type,
        hp_restored=rest_result.hp_restored,
        hit_dice_spent=rest_result.hit_dice_spent,
        hit_dice_restored=rest_result.hit_dice_restored,
        slots_restored=rest_result.slots_restored,
        exhaustion_reduced=rest_result.exhaustion_reduced,
        character=CharacterRead.model_validate(character),
    )


@router.get("/world/{world_id}", response_model=list[CharacterRead])
async def list_world_characters(
    world_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    role: ClientRole = Depends(client_role),
) -> list[CharacterRead]:
    world_result = await db.execute(select(World).where(World.id == world_id))
    if world_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="World not found")
    result = await db.execute(select(Character).where(Character.world_id == world_id))
    characters = result.scalars().all()
    return [character_read_for(c, role) for c in characters]
