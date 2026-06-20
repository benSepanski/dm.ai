"""Combat spellcasting and rescue endpoints — wired to the engine's spell module.

Depth-first decomposition mirrors ``combat.py``: load → build-state →
resolve → persist. The engine's :func:`cast_spell` owns slot consumption,
upcasting, attack rolls, saving throws, damage/healing, rider conditions,
and concentration; this module owns the HTTP boundary and persistence.

``heal`` and ``stabilize`` are DM adjudication tools (potions, Healer's Kit,
narrative fiat) — they do not consume the actor's action economy. A spell
cast consumes the caster's action (or bonus action / reaction, per the
spell's casting time), enforced across requests via the persisted
``turn_states``.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from game_engine.rules.dnd_5_5e import cast_spell
from game_engine.rules.dnd_5_5e.data.class_features import CLASS_PROGRESSIONS
from game_engine.rules.dnd_5_5e.data.spells import SpellData, get_spell
from game_engine.rules.dnd_5_5e.engine import DnD55eEngine
from game_engine.rules.dnd_5_5e.spellcasting import SpellCastResult
from game_engine.types import (
    Ability,
    ActionType,
    CastingTime,
    CharacterSheet,
    CombatStateData,
    TurnState,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dm_api.api.auth import ClientRole, require_dm
from dm_api.api.combat_utils import broadcast_combat, dump_turn_states, load_turn_states
from dm_api.db.models.combat import (
    CastSpellRequest,
    CombatState,
    CombatStateRead,
    HealRequest,
    StabilizeRequest,
)
from dm_api.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter()

_engine = DnD55eEngine()

# Casting times resolvable inside a combat turn, mapped to the TurnState
# economy slot they consume. Anything longer (1 minute, 1 hour, rituals)
# can't be cast mid-fight.
_COMBAT_CASTING_TIMES = (CastingTime.ACTION, CastingTime.BONUS_ACTION, CastingTime.REACTION)


async def _load_active_combat(session_id: uuid.UUID, db: AsyncSession) -> CombatState:
    result = await db.execute(
        select(CombatState).where(
            CombatState.session_id == session_id,
            CombatState.ended_at.is_(None),
        )
    )
    combat = result.scalar_one_or_none()
    if combat is None:
        raise HTTPException(status_code=404, detail="No active combat for this session")
    return combat


def _require_combatant(sheets: list[CharacterSheet], char_id: str, role: str) -> CharacterSheet:
    sheet = next((s for s in sheets if s.id == char_id), None)
    if sheet is None:
        raise HTTPException(status_code=404, detail=f"{role} is not a combatant in this combat")
    return sheet


def _spellcasting_ability(caster: CharacterSheet, override: Ability | None) -> Ability:
    if override is not None:
        return override
    progression = CLASS_PROGRESSIONS.get(caster.char_class)
    if progression is None or progression.spellcasting_ability is None:
        raise HTTPException(
            status_code=422,
            detail=(
                f"{caster.name}'s class has no spellcasting ability; "
                "pass spellcasting_ability explicitly."
            ),
        )
    return progression.spellcasting_ability


def _consume_casting_economy(spell: SpellData, ts: TurnState) -> None:
    """Mark the economy slot the spell's casting time uses; 409 if spent."""
    if spell.casting_time not in _COMBAT_CASTING_TIMES:
        raise HTTPException(
            status_code=409,
            detail=f"{spell.name} takes {spell.casting_time.value} to cast — not in combat.",
        )
    if spell.casting_time is CastingTime.ACTION:
        if ts.action_used:
            raise HTTPException(status_code=409, detail="Action already used this turn.")
        ts.action_used = True
    elif spell.casting_time is CastingTime.BONUS_ACTION:
        if ts.bonus_action_used:
            raise HTTPException(status_code=409, detail="Bonus action already used.")
        ts.bonus_action_used = True
    else:
        if ts.reaction_used:
            raise HTTPException(status_code=409, detail="Reaction already used this round.")
        ts.reaction_used = True


def _cast_log_entry(combat: CombatState, actor_id: str, result: SpellCastResult) -> dict[str, Any]:
    return {
        "round": combat.round_number,
        "turn": combat.current_turn_index,
        "actor_id": actor_id,
        "action_type": ActionType.MAGIC.value,
        "event": "cast_spell",
        "spell": result.spell_name,
        "slot_level_used": result.slot_level_used,
        "concentration_started": result.concentration_started,
        "flavor": result.flavor_text,
        "outcomes": [
            {
                "target_id": o.target_id,
                "hit": o.hit,
                "attack_total": o.attack_total,
                "save_total": o.save_total,
                "save_success": o.save_success,
                "damage": o.damage,
                "healing": o.healing,
                "conditions_applied": [c.value for c in o.conditions_applied],
            }
            for o in result.outcomes
        ],
    }


@router.post("/sessions/{session_id}/combat/cast-spell", response_model=CombatStateRead)
async def cast_combat_spell(
    session_id: uuid.UUID,
    payload: CastSpellRequest,
    db: AsyncSession = Depends(get_db),
    _role: ClientRole = Depends(require_dm),
) -> CombatStateRead:
    """Cast a spell through the rule engine's spellcasting module.

    Resolves slot consumption (with upcasting), spell attack rolls, saving
    throws against the caster's spell save DC, damage/healing (cantrip
    scaling included), rider conditions, and concentration. Rule rejections
    (no slot, economy spent, incapacitated) are 409s and never touch the
    combat log.
    """
    combat = await _load_active_combat(session_id, db)
    sheets = [CharacterSheet.from_dict(c) for c in (combat.combatants or [])]

    caster = _require_combatant(sheets, payload.actor_id, "Actor")
    for target_id in payload.target_ids:
        _require_combatant(sheets, target_id, "Target")

    spell = get_spell(payload.spell_name)
    if spell is None:
        raise HTTPException(status_code=404, detail=f"Unknown spell: {payload.spell_name}")

    if not caster.can_act:
        raise HTTPException(status_code=409, detail=f"{caster.name} can't act.")

    state = CombatStateData(
        combatants=sheets,
        round_number=combat.round_number,
        current_turn_index=combat.current_turn_index,
        turn_states=load_turn_states(combat),
    )
    _consume_casting_economy(spell, state.turn_state_for(caster.id))

    ability = _spellcasting_ability(caster, payload.spellcasting_ability)
    result = cast_spell(
        caster=caster,
        spell=spell,
        spellcasting_ability=ability,
        combat_state=state,
        target_ids=payload.target_ids,
        slot_level=payload.slot_level,
    )
    if not result.success:
        # Slot validation failed — nothing was consumed; keep the log clean.
        raise HTTPException(status_code=409, detail=result.flavor_text)

    combat.combatants = [s.to_dict() for s in state.combatants]
    combat.turn_states = dump_turn_states(state.turn_states)
    combat.combat_log = [
        *(combat.combat_log or []),
        _cast_log_entry(combat, payload.actor_id, result),
    ]

    await db.commit()
    await db.refresh(combat)
    result_read = CombatStateRead.model_validate(combat)
    await broadcast_combat(session_id, result_read)
    return result_read


@router.post("/sessions/{session_id}/combat/heal", response_model=CombatStateRead)
async def heal_combatant(
    session_id: uuid.UUID,
    payload: HealRequest,
    db: AsyncSession = Depends(get_db),
    _role: ClientRole = Depends(require_dm),
) -> CombatStateRead:
    """Apply healing to a combatant mid-fight (potion, Lay on Hands, DM fiat).

    Healing a dying creature brings it back up and clears its death saves.
    For spell-based healing prefer ``cast-spell`` (it also handles slots).
    """
    combat = await _load_active_combat(session_id, db)
    sheets = [CharacterSheet.from_dict(c) for c in (combat.combatants or [])]
    target = _require_combatant(sheets, payload.target_id, "Target")

    if target.is_dead:
        raise HTTPException(status_code=409, detail=f"{target.name} is dead and can't be healed.")

    _engine.apply_healing(target, payload.amount)

    combat.combatants = [s.to_dict() for s in sheets]
    combat.combat_log = [
        *(combat.combat_log or []),
        {
            "round": combat.round_number,
            "turn": combat.current_turn_index,
            "actor_id": payload.target_id,
            "event": "heal",
            "amount": payload.amount,
            "hp_after": target.hp_current,
        },
    ]

    await db.commit()
    await db.refresh(combat)
    result_read = CombatStateRead.model_validate(combat)
    await broadcast_combat(session_id, result_read)
    return result_read


@router.post("/sessions/{session_id}/combat/stabilize", response_model=CombatStateRead)
async def stabilize_combatant(
    session_id: uuid.UUID,
    payload: StabilizeRequest,
    db: AsyncSession = Depends(get_db),
    _role: ClientRole = Depends(require_dm),
) -> CombatStateRead:
    """Stabilize a dying combatant (successful DC 10 Medicine check, Healer's Kit).

    A stable creature stays unconscious at 0 HP but stops rolling death saves.
    """
    combat = await _load_active_combat(session_id, db)
    sheets = [CharacterSheet.from_dict(c) for c in (combat.combatants or [])]
    target = _require_combatant(sheets, payload.target_id, "Target")

    if target.is_dead:
        raise HTTPException(status_code=409, detail=f"{target.name} is dead.")
    if target.hp_current > 0:
        raise HTTPException(status_code=409, detail=f"{target.name} is not dying.")
    if target.death_saves.is_stable:
        raise HTTPException(status_code=409, detail=f"{target.name} is already stable.")

    _engine.stabilize(target)

    combat.combatants = [s.to_dict() for s in sheets]
    combat.combat_log = [
        *(combat.combat_log or []),
        {
            "round": combat.round_number,
            "turn": combat.current_turn_index,
            "actor_id": payload.target_id,
            "event": "stabilize",
        },
    ]

    await db.commit()
    await db.refresh(combat)
    result_read = CombatStateRead.model_validate(combat)
    await broadcast_combat(session_id, result_read)
    return result_read
