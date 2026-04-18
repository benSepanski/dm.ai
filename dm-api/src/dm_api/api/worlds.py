import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dm_api.db.models.location import Location, LocationRead
from dm_api.db.models.world import World, WorldCreate, WorldRead
from dm_api.db.session import get_db

router = APIRouter()


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
    result = await db.execute(select(World).where(World.id == world_id))
    world = result.scalar_one_or_none()
    if world is None:
        raise HTTPException(status_code=404, detail="World not found")
    return WorldRead.model_validate(world)


@router.get("/{world_id}/locations", response_model=list[LocationRead])
async def get_world_locations(
    world_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[LocationRead]:
    # Verify world exists
    world_result = await db.execute(select(World).where(World.id == world_id))
    if world_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="World not found")

    result = await db.execute(select(Location).where(Location.world_id == world_id))
    locations = result.scalars().all()
    return [LocationRead.model_validate(loc) for loc in locations]


@router.delete("/{world_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_world(
    world_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(World).where(World.id == world_id))
    world = result.scalar_one_or_none()
    if world is None:
        raise HTTPException(status_code=404, detail="World not found")
    db.delete(world)
    await db.commit()
