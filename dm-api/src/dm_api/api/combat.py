"""
Combat API endpoints.

These endpoints manage combat encounters for a session:
- Start/end combat with initiative rolling via the rule engine.
- Submit actions that are resolved by the DnD55eEngine, mutating combatant
  HP/conditions in the stored JSON and appending results to the combat log.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from game_engine.interface import Action
from game_engine.rules.dnd_5_5e.engine import DnD55eEngine
from game_engine.types import ActionType, AttackDetails, CharacterSheet, CombatStateData
from game_engine.types.values import DiceNotation
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dm_api.db.models.combat import (
    ActionResultSchema,
    CombatActionRequest,
    CombatActionResponse,
    CombatStartRequest,
    CombatState,
    CombatStateRead,
)
from dm_api.db.models.session import GameSession
from dm_api.db.session import get_db

router = APIRouter()

_engine = DnD55eEngine()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_combat_state(combat: CombatState) -> CombatStateData:
    """Reconstruct a :class:`CombatStateData` from the JSON stored in *combat*."""
    raw_combatants: list[dict[str, Any]] = combat.combatants or []
    combatants = [CharacterSheet.from_dict(c) for c in raw_combatants]
    return CombatStateData(
        combatants=combatants,
        round_number=combat.round_number,
        current_turn_index=combat.current_turn_index,
    )


def _save_combat_state(combat: CombatState, state: CombatStateData) -> None:
    """Serialise *state* back into the JSON columns of *combat*."""
    combat.combatants = [c.to_dict() for c in state.combatants]
    combat.round_number = state.round_number
    combat.current_turn_index = state.current_turn_index


def _advance_turn(combat: CombatState, state: CombatStateData) -> None:
    """Advance to the next living (non-dead) combatant.

    Wraps around the initiative order and increments *round_number* when
    the full order has been cycled through.  Dead characters (3 death save
    failures) are skipped; dying characters still get a turn to roll saves.
    """
    order: list[dict[str, Any]] = combat.initiative_order or []
    if not order:
        return

    chars_by_id = {c.id: c for c in state.combatants}
    n = len(order)

    for _ in range(n):
        combat.current_turn_index = (combat.current_turn_index + 1) % n
        if combat.current_turn_index == 0:
            combat.round_number += 1
        char_id = order[combat.current_turn_index]["char_id"]
        char = chars_by_id.get(char_id)
        if char is None or not char.is_dead:
            break


# ---------------------------------------------------------------------------
# Start combat
# ---------------------------------------------------------------------------


@router.post(
    "/sessions/{session_id}/combat",
    response_model=CombatStateRead,
    status_code=status.HTTP_201_CREATED,
)
async def start_combat(
    session_id: uuid.UUID,
    payload: CombatStartRequest,
    db: AsyncSession = Depends(get_db),
) -> CombatStateRead:
    """Start a new combat encounter.

    Rolls initiative for every combatant in *payload.combatants* using the
    rule engine and stores the sorted order.  Combatants are provided as
    ``CharacterSheet.to_dict()`` payloads.
    """
    session_result = await db.execute(select(GameSession).where(GameSession.id == session_id))
    if session_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Session not found")

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

    # Build CharacterSheet objects and roll initiative
    sheets = [CharacterSheet.from_dict(c) for c in payload.combatants]
    initiative_rolls: list[tuple[CharacterSheet, int]] = [
        (sheet, _engine.roll_initiative(sheet)) for sheet in sheets
    ]
    # Highest initiative goes first
    initiative_rolls.sort(key=lambda t: t[1], reverse=True)

    initiative_order = [
        {"char_id": sheet.id, "initiative": roll} for sheet, roll in initiative_rolls
    ]
    combatants_json = [sheet.to_dict() for sheet, _ in initiative_rolls]

    combat = CombatState(
        session_id=session_id,
        location_id=payload.location_id,
        initiative_order=initiative_order,
        combatants=combatants_json,
        round_number=1,
        current_turn_index=0,
    )
    db.add(combat)
    await db.commit()
    await db.refresh(combat)
    return CombatStateRead.model_validate(combat)


# ---------------------------------------------------------------------------
# Get active combat
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Submit action
# ---------------------------------------------------------------------------


@router.post(
    "/sessions/{session_id}/combat/action",
    response_model=CombatActionResponse,
)
async def submit_combat_action(
    session_id: uuid.UUID,
    payload: CombatActionRequest,
    db: AsyncSession = Depends(get_db),
) -> CombatActionResponse:
    """Resolve a combat action via the rule engine.

    The engine mutates the combatant JSON in-place (updating HP, conditions,
    death saves, etc.) and appends the structured result to *combat_log*.
    """
    result = await db.execute(
        select(CombatState).where(
            CombatState.session_id == session_id,
            CombatState.ended_at.is_(None),
        )
    )
    combat = result.scalar_one_or_none()
    if combat is None:
        raise HTTPException(status_code=404, detail="No active combat for this session")

    # Reconstruct engine state from stored JSON
    combat_state = _build_combat_state(combat)

    # Parse action type
    try:
        action_type = ActionType(payload.action_type)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Unknown action_type '{payload.action_type}'. "
                f"Valid values: {[a.value for a in ActionType]}"
            ),
        )

    # Build AttackDetails from the request 'extra' dict when provided
    details: AttackDetails | None = None
    if action_type == ActionType.ATTACK and payload.extra:
        extra = payload.extra
        details = AttackDetails(
            weapon_name=extra.get("weapon_name", "Unarmed Strike"),
            damage_dice=DiceNotation(extra.get("damage_dice", "1d4")),
            damage_type=_parse_damage_type(extra.get("damage_type", "bludgeoning")),
        )

    action = Action(
        action_type=action_type,
        actor_id=payload.actor_id,
        target_id=payload.target_id,
        details=details,
    )

    # Resolve via the rule engine (mutates combatant sheets in combat_state)
    action_result = _engine.resolve_action(action, combat_state)

    # Persist updated combatant state and append log entry
    _save_combat_state(combat, combat_state)
    new_log_entry = {
        "round": combat.round_number,
        "turn": combat.current_turn_index,
        **action_result.log_entry,
        "flavor_text": action_result.flavor_text,
    }
    combat.combat_log = [*(combat.combat_log or []), new_log_entry]

    # Advance to the next combatant's turn
    _advance_turn(combat, combat_state)

    await db.commit()
    await db.refresh(combat)

    return CombatActionResponse(
        combat=CombatStateRead.model_validate(combat),
        result=ActionResultSchema(
            success=action_result.success,
            damage=action_result.damage,
            damage_type=action_result.damage_type.value,
            conditions_applied=[c.value for c in action_result.conditions_applied],
            flavor_text=action_result.flavor_text,
            log_entry=action_result.log_entry,
        ),
    )


# ---------------------------------------------------------------------------
# End combat
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _parse_damage_type(value: str) -> Any:
    """Parse a string into a :class:`DamageType`, defaulting to BLUDGEONING."""
    from game_engine.types import DamageType

    try:
        return DamageType(value.lower())
    except ValueError:
        return DamageType.BLUDGEONING
