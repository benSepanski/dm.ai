"""Bridges between the characters API and live combat snapshots.

Combatants are snapshotted into ``CombatState.combatants`` when combat
starts. Without write-through, a PATCH to a character mid-combat never
reached the live fight — and ``end_combat`` then wrote the stale snapshot
back over the patch. These helpers mirror character updates into every
active combat the character is enrolled in.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dm_api.db.models.character import Character
from dm_api.db.models.combat import CombatState

# Character columns whose PATCH values map 1:1 onto combatant-sheet keys.
_COLUMN_SHEET_KEYS = ("name", "level", "hp_current", "hp_max", "ac", "speed")


async def active_combats_with_character(db: AsyncSession, char_id: uuid.UUID) -> list[CombatState]:
    """Return every active (not ended) combat that has *char_id* enrolled."""
    result = await db.execute(select(CombatState).where(CombatState.ended_at.is_(None)))
    char_key = str(char_id)
    return [
        combat
        for combat in result.scalars().all()
        if any(c.get("id") == char_key for c in (combat.combatants or []))
    ]


def _patched_combatant(
    combatant: dict[str, Any],
    column_updates: dict[str, Any],
    stats_updates: dict[str, Any],
) -> dict[str, Any]:
    """Apply the PATCHed fields onto one combatant-sheet dict.

    Only the keys the PATCH actually touched are mirrored, so mid-fight
    state the DB row doesn't track (spent spell slots, temp HP,
    concentration) survives.
    """
    patched = dict(combatant)
    for column in _COLUMN_SHEET_KEYS:
        if column in column_updates and column_updates[column] is not None:
            patched[column] = column_updates[column]
    for key, value in stats_updates.items():
        if value is not None:
            patched[key] = value
    return patched


async def write_through_character_update(
    db: AsyncSession,
    character: Character,
    column_updates: dict[str, Any],
    stats_updates: dict[str, Any],
) -> list[CombatState]:
    """Mirror a character PATCH into active combat snapshots.

    Returns the combats that changed so the caller can broadcast their
    updated state after commit. The ``stats`` blob and the combatant sheet
    share serde keys (``ability_scores``, ``conditions``, ...), so stats
    updates apply directly.
    """
    updated: list[CombatState] = []
    for combat in await active_combats_with_character(db, character.id):
        char_key = str(character.id)
        combat.combatants = [
            (
                _patched_combatant(c, column_updates, stats_updates)
                if c.get("id") == char_key
                else c
            )
            for c in (combat.combatants or [])
        ]
        updated.append(combat)
    return updated
