"""Combat API endpoints — wired to the DnD55eEngine rule engine.

Harness-engineering notes:
- Typed boundaries: ``CombatActionRequest`` uses ``ActionType`` enum; the engine
  receives typed ``Action`` / ``CombatStateData`` objects.
- Single source of truth: the ``CombatState.combatants`` JSON blob holds the
  full ``CharacterSheet.to_dict()`` state and is updated after every resolved
  action so HP, conditions, etc. survive between requests.
- Depth-first decomposition: ``submit_combat_action`` is split into
  load → build-state → resolve → persist stages.
- WebSocket broadcasts: every state-mutating endpoint emits a ``combat_update``
  event to all connected clients so the UI stays in sync without polling.
"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, status
from game_engine.interface import Action
from game_engine.rules.dnd_5_5e.engine import DnD55eEngine
from game_engine.types import AttackDetails, CharacterClass, CharacterSheet, CombatStateData
from game_engine.types.values import DiceNotation
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dm_api.api.ws import broadcast_to_session
from dm_api.db.models.character import Character
from dm_api.db.models.combat import (
    AttackDetailsRequest,
    CombatActionRequest,
    CombatState,
    CombatStateRead,
    StartCombatRequest,
)
from dm_api.db.models.session import GameSession
from dm_api.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter()

# Stateless engine — safe to share across requests.
_engine = DnD55eEngine()


async def _broadcast_combat(session_id: uuid.UUID, state: CombatStateRead) -> None:
    """Emit a ``combat_update`` WebSocket event after every state-mutating endpoint.

    Failures are logged but never propagate to the HTTP response — the DB
    write already succeeded so the caller gets the correct result regardless.
    """
    try:
        await broadcast_to_session(
            session_id,
            {
                "type": "combat_update",
                "session_id": str(session_id),
                "combat": state.model_dump(mode="json"),
            },
        )
    except Exception:
        logger.exception("combat broadcast failed session_id=%s", session_id)


def _character_to_sheet(character: Character) -> CharacterSheet:
    """Bridge DB Character row → typed CharacterSheet for the rule engine."""
    stats = character.stats or {}
    return CharacterSheet.from_dict(
        {
            "id": str(character.id),
            "name": character.name,
            "level": character.level,
            "class": character.char_class or CharacterClass.FIGHTER.value,
            "ability_scores": stats.get("ability_scores", {}),
            "hp_current": character.hp_current if character.hp_current is not None else 10,
            "hp_max": character.hp_max if character.hp_max is not None else 10,
            "ac": character.ac if character.ac is not None else 10,
            "speed": character.speed if character.speed is not None else 30,
            "type": character.type.value,
            "proficiencies": stats.get("proficiencies", []),
            "conditions": stats.get("conditions", []),
            "condition_durations": stats.get("condition_durations", {}),
            "damage_resistances": stats.get("damage_resistances", []),
            "damage_immunities": stats.get("damage_immunities", []),
            "damage_vulnerabilities": stats.get("damage_vulnerabilities", []),
            "condition_immunities": stats.get("condition_immunities", []),
        }
    )


def _build_attack_details(req: AttackDetailsRequest | None) -> AttackDetails | None:
    """Convert typed Pydantic request into a game-engine AttackDetails dataclass."""
    if req is None:
        return None
    return AttackDetails(
        weapon_name=req.weapon_name,
        damage_dice=DiceNotation(req.damage_dice),
        damage_type=req.damage_type,
        attack_ability=req.attack_ability,
        is_ranged=req.is_ranged,
    )


@router.post(
    "/sessions/{session_id}/combat",
    response_model=CombatStateRead,
    status_code=status.HTTP_201_CREATED,
)
async def start_combat(
    session_id: uuid.UUID,
    payload: StartCombatRequest | None = Body(default=None),
    db: AsyncSession = Depends(get_db),
) -> CombatStateRead:
    """Start a new combat encounter for the session.

    Optionally accepts a list of character IDs whose initiative is rolled
    immediately using the rule engine. Characters are sorted by initiative
    (descending) and stored in ``initiative_order``; their full
    ``CharacterSheet`` state is stored in ``combatants``.
    """
    if payload is None:
        payload = StartCombatRequest()

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

    initiative_order: list[dict] = []
    combatants: list[dict] = []

    if payload.character_ids:
        char_result = await db.execute(
            select(Character).where(Character.id.in_(payload.character_ids))
        )
        characters = list(char_result.scalars().all())

        if len(characters) != len(payload.character_ids):
            found_ids = {c.id for c in characters}
            missing = [str(cid) for cid in payload.character_ids if cid not in found_ids]
            raise HTTPException(
                status_code=404,
                detail=f"Characters not found: {missing}",
            )

        rolled: list[tuple[dict, dict]] = []
        for char in characters:
            sheet = _character_to_sheet(char)
            initiative = _engine.roll_initiative(sheet)
            rolled.append(
                (
                    {"character_id": str(char.id), "name": char.name, "initiative": initiative},
                    sheet.to_dict(),
                )
            )

        rolled.sort(key=lambda x: x[0]["initiative"], reverse=True)
        initiative_order = [r[0] for r in rolled]
        combatants = [r[1] for r in rolled]

    combat = CombatState(
        session_id=session_id,
        location_id=payload.location_id,
        initiative_order=initiative_order or None,
        combatants=combatants or None,
    )
    db.add(combat)
    await db.commit()
    await db.refresh(combat)
    result_read = CombatStateRead.model_validate(combat)
    await _broadcast_combat(session_id, result_read)
    return result_read


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
    """Resolve a combat action through the DnD55eEngine.

    Depth-first decomposition:
    1. **load** — fetch active CombatState, deserialise stored CharacterSheets.
    2. **build-state** — construct typed CombatStateData for the engine.
    3. **resolve** — run the rule engine; it mutates combatant HP / conditions
       in-place on the CharacterSheet objects inside state.
    4. **persist** — write updated sheets and the engine's log entry back to DB.
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

    # Stage 1: load — deserialise stored CharacterSheets.
    sheets: list[CharacterSheet] = [CharacterSheet.from_dict(c) for c in (combat.combatants or [])]

    # Stage 2: build-state.
    state = CombatStateData(
        combatants=sheets,
        round_number=combat.round_number,
        current_turn_index=combat.current_turn_index,
    )

    # Stage 3: resolve — engine mutates sheets in-place.
    action = Action(
        action_type=payload.action_type,
        actor_id=payload.actor_id,
        target_id=payload.target_id,
        details=_build_attack_details(payload.attack_details),
    )
    outcome = _engine.resolve_action(action, state)

    # Stage 4: persist — updated sheets + enriched log entry.
    if state.combatants:
        combat.combatants = [s.to_dict() for s in state.combatants]

    log_entry: dict = {
        "round": combat.round_number,
        "turn": combat.current_turn_index,
        "actor_id": payload.actor_id,
        "action_type": payload.action_type.value,
        **outcome.log_entry,
    }
    combat.combat_log = [*(combat.combat_log or []), log_entry]

    await db.commit()
    await db.refresh(combat)
    result_read = CombatStateRead.model_validate(combat)
    await _broadcast_combat(session_id, result_read)
    return result_read


@router.post(
    "/sessions/{session_id}/combat/next-turn",
    response_model=CombatStateRead,
)
async def next_turn(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> CombatStateRead:
    """Advance to the next combatant's turn, incrementing the round when the
    turn index wraps past the last combatant in the initiative order."""
    result = await db.execute(
        select(CombatState).where(
            CombatState.session_id == session_id,
            CombatState.ended_at.is_(None),
        )
    )
    combat = result.scalar_one_or_none()
    if combat is None:
        raise HTTPException(status_code=404, detail="No active combat for this session")

    order_len = len(combat.initiative_order or [])
    if order_len == 0:
        raise HTTPException(
            status_code=409,
            detail="No combatants registered; add combatants before advancing turns",
        )

    # Tick condition durations for the combatant whose turn is ending.
    # Indices in combatants[] are aligned with initiative_order[] (both sorted
    # by initiative in start_combat and never reordered after that).
    current_idx = combat.current_turn_index
    combatants = list(combat.combatants or [])
    if current_idx < len(combatants):
        sheet = CharacterSheet.from_dict(combatants[current_idx])
        _engine.tick_condition_durations(sheet)
        combatants[current_idx] = sheet.to_dict()
        combat.combatants = combatants

    next_index = current_idx + 1
    if next_index >= order_len:
        combat.round_number += 1
        next_index = 0
    combat.current_turn_index = next_index

    await db.commit()
    await db.refresh(combat)
    result_read = CombatStateRead.model_validate(combat)
    await _broadcast_combat(session_id, result_read)
    return result_read


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
    result_read = CombatStateRead.model_validate(combat)
    await _broadcast_combat(session_id, result_read)
    return result_read
