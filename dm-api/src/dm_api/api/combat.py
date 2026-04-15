import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dm_api.db.models.combat import CombatActionRequest, CombatState, CombatStateRead
from dm_api.db.models.session import GameSession
from dm_api.db.session import get_db

router = APIRouter()


@router.post(
    "/sessions/{session_id}/combat",
    response_model=CombatStateRead,
    status_code=status.HTTP_201_CREATED,
)
async def start_combat(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> CombatStateRead:
    # Verify session exists
    session_result = await db.execute(select(GameSession).where(GameSession.id == session_id))
    if session_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Check for existing active combat
    existing = await db.execute(
        select(CombatState).where(
            CombatState.session_id == session_id,
            CombatState.ended_at.is_(None),
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=409, detail="Active combat already exists for this session"
        )

    combat = CombatState(session_id=session_id)
    db.add(combat)
    await db.commit()
    await db.refresh(combat)
    return CombatStateRead.model_validate(combat)


@router.get(
    "/sessions/{session_id}/combat",
    response_model=CombatStateRead,
)
async def get_combat(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> CombatStateRead:
    result = await db.execute(
        select(CombatState).where(
            CombatState.session_id == session_id,
            CombatState.ended_at.is_(None),
        )
    )
    combat = result.scalar_one_or_none()
    if combat is None:
        raise HTTPException(status_code=404, detail="No active combat for this session")
    return CombatStateRead.model_validate(combat)


@router.post(
    "/sessions/{session_id}/combat/action",
    response_model=CombatStateRead,
)
async def submit_combat_action(
    session_id: uuid.UUID,
    payload: CombatActionRequest,
    db: AsyncSession = Depends(get_db),
) -> CombatStateRead:
    result = await db.execute(
        select(CombatState).where(
            CombatState.session_id == session_id,
            CombatState.ended_at.is_(None),
        )
    )
    combat = result.scalar_one_or_none()
    if combat is None:
        raise HTTPException(status_code=404, detail="No active combat for this session")

    # Append action to combat log (always create new list for SQLAlchemy change detection)
    new_entry = {
        "round": combat.round_number,
        "turn": combat.current_turn_index,
        "actor_id": payload.actor_id,
        "action_type": payload.action_type,
        "target_id": payload.target_id,
    }
    combat.combat_log = [*(combat.combat_log or []), new_entry]

    await db.commit()
    await db.refresh(combat)
    return CombatStateRead.model_validate(combat)


@router.put(
    "/sessions/{session_id}/combat/end",
    response_model=CombatStateRead,
)
async def end_combat(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> CombatStateRead:
    result = await db.execute(
        select(CombatState).where(
            CombatState.session_id == session_id,
            CombatState.ended_at.is_(None),
        )
    )
    combat = result.scalar_one_or_none()
    if combat is None:
        raise HTTPException(status_code=404, detail="No active combat for this session")

    combat.ended_at = datetime.now(tz=timezone.utc)
    await db.commit()
    await db.refresh(combat)
    return CombatStateRead.model_validate(combat)
