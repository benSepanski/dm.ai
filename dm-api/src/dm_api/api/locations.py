import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dm_api.db.models.location import (
    Location,
    LocationCreate,
    LocationRead,
    LocationUpdate,
)
from dm_api.db.session import get_db

router = APIRouter()


@router.post("/", response_model=LocationRead, status_code=status.HTTP_201_CREATED)
async def create_location(
    payload: LocationCreate,
    db: AsyncSession = Depends(get_db),
) -> LocationRead:
    location = Location(**payload.model_dump())
    db.add(location)
    await db.commit()
    await db.refresh(location)
    return LocationRead.model_validate(location)


@router.get("/{loc_id}", response_model=LocationRead)
async def get_location(
    loc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> LocationRead:
    result = await db.execute(select(Location).where(Location.id == loc_id))
    location = result.scalar_one_or_none()
    if location is None:
        raise HTTPException(status_code=404, detail="Location not found")
    return LocationRead.model_validate(location)


@router.patch("/{loc_id}", response_model=LocationRead)
async def update_location(
    loc_id: uuid.UUID,
    payload: LocationUpdate,
    db: AsyncSession = Depends(get_db),
) -> LocationRead:
    result = await db.execute(select(Location).where(Location.id == loc_id))
    location = result.scalar_one_or_none()
    if location is None:
        raise HTTPException(status_code=404, detail="Location not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(location, field, value)

    await db.commit()
    await db.refresh(location)
    return LocationRead.model_validate(location)


@router.delete("/{loc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_location(
    loc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(Location).where(Location.id == loc_id))
    location = result.scalar_one_or_none()
    if location is None:
        raise HTTPException(status_code=404, detail="Location not found")
    await db.delete(location)
    await db.commit()
