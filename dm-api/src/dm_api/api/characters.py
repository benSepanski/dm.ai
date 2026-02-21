import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dm_api.db.models.character import (
    Character,
    CharacterCreate,
    CharacterRead,
    CharacterUpdate,
)
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
) -> CharacterRead:
    result = await db.execute(select(Character).where(Character.id == char_id))
    character = result.scalar_one_or_none()
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")
    return CharacterRead.model_validate(character)


@router.patch("/{char_id}", response_model=CharacterRead)
async def update_character(
    char_id: uuid.UUID,
    payload: CharacterUpdate,
    db: AsyncSession = Depends(get_db),
) -> CharacterRead:
    result = await db.execute(select(Character).where(Character.id == char_id))
    character = result.scalar_one_or_none()
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(character, field, value)

    await db.commit()
    await db.refresh(character)
    return CharacterRead.model_validate(character)


@router.get("/world/{world_id}", response_model=list[CharacterRead])
async def list_world_characters(
    world_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[CharacterRead]:
    result = await db.execute(
        select(Character).where(Character.world_id == world_id)
    )
    characters = result.scalars().all()
    return [CharacterRead.model_validate(c) for c in characters]
