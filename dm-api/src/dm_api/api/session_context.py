"""Builders for the typed :class:`WorldContext` injected into the DM prompt.

Runtime-layer module: queries the worlds/sessions/locations/characters/combat
tables and condenses the rows into the frozen brief dataclasses defined in
``dm_api.ai.prompts.system_prompt``, so the orchestrator is grounded in the
accepted canon (and the live combat tracker) instead of contradicting it.
Split out of ``sessions.py`` to keep the route module under the repo's
400-LoC guideline.
"""

from __future__ import annotations

import uuid
from typing import Any

from game_engine.types import CharacterSheet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dm_api.ai.prompts.system_prompt import (
    CharacterBrief,
    CombatantBrief,
    CombatSnapshot,
    LocationBrief,
    WorldContext,
)
from dm_api.db.models.character import Character
from dm_api.db.models.combat import CombatState
from dm_api.db.models.location import Location
from dm_api.db.models.session import GameSession
from dm_api.db.models.world import World

# Most recent ended sessions whose summaries are injected into the system
# prompt for cross-session continuity. Summaries are 2-3 sentences each, so
# the token cost stays negligible.
_PRIOR_SESSION_LIMIT = 10

# Canon entities injected per kind. When a world has more, the most recently
# created rows win so the briefs track the current arc of the campaign.
_KNOWN_ENTITY_LIMIT = 20

# Free-text brief fields are truncated to keep the per-entity token cost
# bounded regardless of how verbose the stored description is.
_BRIEF_TEXT_LIMIT = 280
_KNOWN_FACTS_LIMIT = 8


def _truncate(text: str | None, limit: int = _BRIEF_TEXT_LIMIT) -> str | None:
    if text is None:
        return None
    collapsed = " ".join(text.split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[:limit].rstrip() + "…"


def _location_brief(row: Location) -> LocationBrief:
    return LocationBrief(
        name=row.name,
        type=row.type,
        description=_truncate(row.description),
    )


def _character_brief(row: Character) -> CharacterBrief:
    facts = tuple(
        fact
        for raw in (row.known_facts or [])[:_KNOWN_FACTS_LIMIT]
        if (fact := _truncate(str(raw)))
    )
    return CharacterBrief(
        name=row.name,
        type=row.type,
        race=row.race,
        char_class=row.char_class,
        level=row.level,
        personality_traits=_truncate(row.personality_traits),
        ideals=_truncate(row.ideals),
        bonds=_truncate(row.bonds),
        flaws=_truncate(row.flaws),
        known_facts=facts,
    )


def _combat_snapshot(combat: CombatState | None) -> CombatSnapshot | None:
    """Condense a live CombatState row into the prompt's typed snapshot.

    Combatants are stored as sheet dicts (untrusted JSON column); each one is
    parsed through the engine serde so HP, death state, and conditions come
    out typed rather than as raw dict lookups.
    """
    if combat is None:
        return None
    order: list[dict[str, Any]] = combat.initiative_order or []
    active: str | None = None
    if 0 <= combat.current_turn_index < len(order):
        raw_name = order[combat.current_turn_index].get("name")
        active = str(raw_name) if raw_name else None
    briefs = tuple(
        CombatantBrief(
            name=sheet.name,
            hp_current=sheet.hp_current,
            hp_max=sheet.hp_max,
            is_dead=sheet.is_dead,
            conditions=tuple(sheet.conditions),
        )
        for sheet in (CharacterSheet.from_dict(raw) for raw in combat.combatants or [])
    )
    return CombatSnapshot(
        round_number=combat.round_number,
        active_combatant=active,
        combatants=briefs,
    )


async def fetch_world_context(
    db: AsyncSession,
    world_id: uuid.UUID,
    current_session_id: uuid.UUID,
) -> WorldContext:
    """Build the typed grounding context for the orchestrator's system prompt.

    Combines the world's setting/lore, summaries of the most recently ended
    sessions (chronological order, oldest first), the accepted canon entities
    (locations and characters, capped and truncated to bound token cost), and
    the session's live combat state when a fight is in progress.
    """
    world = (await db.execute(select(World).where(World.id == world_id))).scalar_one_or_none()

    sessions_result = await db.execute(
        select(GameSession)
        .where(
            GameSession.world_id == world_id,
            GameSession.id != current_session_id,
            GameSession.session_summary.is_not(None),
        )
        .order_by(GameSession.started_at.desc())
        .limit(_PRIOR_SESSION_LIMIT)
    )
    prior_sessions = list(reversed(sessions_result.scalars().all()))

    locations_result = await db.execute(
        select(Location)
        .where(Location.world_id == world_id)
        .order_by(Location.created_at.desc())
        .limit(_KNOWN_ENTITY_LIMIT)
    )
    locations = list(reversed(locations_result.scalars().all()))

    characters_result = await db.execute(
        select(Character)
        .where(Character.world_id == world_id)
        .order_by(Character.created_at.desc())
        .limit(_KNOWN_ENTITY_LIMIT)
    )
    characters = list(reversed(characters_result.scalars().all()))

    combat_result = await db.execute(
        select(CombatState)
        .where(
            CombatState.session_id == current_session_id,
            CombatState.ended_at.is_(None),
        )
        .order_by(CombatState.started_at.desc())
    )
    combat = combat_result.scalars().first()

    return WorldContext(
        setting_description=world.setting_description if world else None,
        lore_summary=world.lore_summary if world else None,
        prior_session_summaries=tuple(f"{s.name}: {s.session_summary}" for s in prior_sessions),
        known_locations=tuple(_location_brief(row) for row in locations),
        known_characters=tuple(_character_brief(row) for row in characters),
        active_combat=_combat_snapshot(combat),
    )
