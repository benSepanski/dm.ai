"""Shared helpers for the combat API endpoints.

Extracted from combat.py to keep endpoint handlers thin per the 400-LoC limit.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from game_engine.types import AttackDetails, CharacterClass, CharacterSheet
from game_engine.types.values import DiceNotation
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dm_api.api.ws import broadcast_to_session
from dm_api.db.models.character import Character
from dm_api.db.models.combat import AttackDetailsRequest, CombatStateRead

logger = logging.getLogger(__name__)

# CharacterSheet defaults applied when the DB column is NULL.
# These match the CharacterSheet dataclass defaults so engine output
# is consistent whether or not the character was given explicit values.
_DEFAULT_HP = 10
_DEFAULT_AC = 10
_DEFAULT_SPEED = 30


async def broadcast_combat(session_id: uuid.UUID, state: CombatStateRead) -> None:
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


async def sync_combatants_to_db(
    db: AsyncSession,
    combatants: list[dict[str, Any]],
) -> None:
    """Write updated HP and conditions from combat state back to Character DB rows.

    Called by ``end_combat`` to make combat damage and condition changes
    persistent.  Combatants whose ``id`` does not resolve to a ``Character``
    row (e.g. ad-hoc monsters not stored in DB) are skipped silently.
    """
    for combatant in combatants:
        char_id_str = combatant.get("id", "")
        try:
            char_uuid = uuid.UUID(char_id_str)
        except (ValueError, AttributeError):
            continue

        result = await db.execute(select(Character).where(Character.id == char_uuid))
        character = result.scalar_one_or_none()
        if character is None:
            continue

        hp_current = combatant.get("hp_current")
        if hp_current is not None:
            character.hp_current = int(hp_current)

        stats: dict[str, Any] = dict(character.stats or {})
        for field in ("conditions", "condition_durations"):
            if field in combatant:
                stats[field] = combatant[field]
        character.stats = stats


def character_to_sheet(character: Character) -> CharacterSheet:
    """Bridge DB Character row → typed CharacterSheet for the rule engine."""
    stats = character.stats or {}
    return CharacterSheet.from_dict(
        {
            "id": str(character.id),
            "name": character.name,
            "level": character.level,
            "class": character.char_class or CharacterClass.FIGHTER.value,
            "ability_scores": stats.get("ability_scores", {}),
            "hp_current": (
                character.hp_current if character.hp_current is not None else _DEFAULT_HP
            ),
            "hp_max": character.hp_max if character.hp_max is not None else _DEFAULT_HP,
            "ac": character.ac if character.ac is not None else _DEFAULT_AC,
            "speed": character.speed if character.speed is not None else _DEFAULT_SPEED,
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


def build_attack_details(req: AttackDetailsRequest | None) -> AttackDetails | None:
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
