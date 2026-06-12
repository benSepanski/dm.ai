"""Helpers shared by the combat route handlers.

Split out of ``combat.py`` to keep the route module under the repo's 400-LoC
guideline. Pure bridging/serialisation logic lives here; HTTP concerns stay
in ``combat.py``.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from game_engine.rules.dnd_5_5e.classes import CLASSES
from game_engine.rules.dnd_5_5e.spellcasting import compute_spell_slots
from game_engine.types import (
    AttackDetails,
    CharacterClass,
    CharacterSheet,
    ClassLevelEntry,
    HitDicePool,
    TurnState,
)
from game_engine.types.values import DiceNotation
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dm_api.api.ws import broadcast_to_session
from dm_api.db.models.character import Character
from dm_api.db.models.combat import AttackDetailsRequest, CombatState, CombatStateRead

# CharacterSheet fields written back to the Character.stats blob when combat
# ends (or when a sheet is persisted after a rest). Everything the engine can
# mutate during a fight must be listed here or it is silently lost.
SHEET_STATE_FIELDS = (
    "conditions",
    "condition_durations",
    "death_saves",
    "spell_slots",
    "concentrating_on",
    "temp_hp",
    "exhaustion_level",
    "hit_dice",
)

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
        for stat_field in SHEET_STATE_FIELDS:
            if stat_field in combatant:
                stats[stat_field] = combatant[stat_field]
        character.stats = stats


def missing_combat_stats(characters: list[Character]) -> list[str]:
    """Names of characters that cannot meaningfully enter combat.

    AI character proposals carry roleplay fields only, so accepting one
    creates a row with NULL hp/ac. Enrolling such a character used to
    silently fabricate a 10 HP / AC 10 placeholder — loud failure beats a
    fake combatant the DM never asked for.
    """
    return [c.name for c in characters if c.hp_max is None or c.ac is None]


def _normalize_char_class(raw: str | None) -> str:
    """Map a free-form class string onto the canonical CharacterClass value.

    The characters API accepts any string for ``char_class`` (raw user/AI
    input), but the sheet serde is case-sensitive — ``"wizard"`` used to
    silently coerce to Fighter inside combat. Unknown strings are passed
    through unchanged (the engine's own fallback remains a known issue).
    """
    if raw is None:
        return CharacterClass.FIGHTER.value
    for cls in CharacterClass:
        if cls.value.lower() == raw.strip().lower():
            return cls.value
    return raw


def character_to_sheet(character: Character) -> CharacterSheet:
    """Bridge DB Character row → typed CharacterSheet for the rule engine.

    The whole ``stats`` blob is passed through the sheet serde (which is
    tolerant of unknown/missing keys), so spell slots, hit dice, known
    spells, exhaustion, etc. all round-trip; explicit DB columns override.
    Spell slots and hit dice are derived from class/level on first use when
    the stats blob doesn't carry them yet.
    """
    stats = character.stats or {}
    hp_max = character.hp_max if character.hp_max is not None else _DEFAULT_HP
    sheet_dict: dict[str, Any] = {
        **stats,
        "id": str(character.id),
        "name": character.name,
        "level": character.level,
        "class": _normalize_char_class(character.char_class),
        "hp_current": character.hp_current if character.hp_current is not None else hp_max,
        "hp_max": hp_max,
        "ac": character.ac if character.ac is not None else _DEFAULT_AC,
        "speed": character.speed if character.speed is not None else _DEFAULT_SPEED,
        "type": character.type.value,
    }
    if not sheet_dict.get("known_spells") and character.spells:
        sheet_dict["known_spells"] = [str(s) for s in character.spells]
    sheet = CharacterSheet.from_dict(sheet_dict)

    class_levels = sheet.class_levels or [
        ClassLevelEntry(character_class=sheet.char_class, level=sheet.level)
    ]
    if "spell_slots" not in stats:
        sheet.spell_slots = compute_spell_slots(class_levels)
    if not sheet.hit_dice:
        sheet.hit_dice = [
            HitDicePool(
                die_size=CLASSES[entry.character_class].hit_die,
                maximum=entry.level,
                remaining=entry.level,
            )
            for entry in class_levels
        ]
    return sheet


def advance_turn_index(
    current_idx: int,
    order_len: int,
    combatants: list[dict[str, Any]],
) -> tuple[int, int]:
    """Return ``(next_index, rounds_advanced)`` for a turn advance.

    Skips combatants who can never act again: the dead, and the stable
    unconscious (who don't roll death saves). Dying creatures are NOT
    skipped — their turn is when their death save rolls. Bounded loop so
    an all-dead roster can't spin forever.
    """
    next_index = current_idx + 1
    rounds_advanced = 0
    if next_index >= order_len:
        next_index = 0
        rounds_advanced = 1

    for _ in range(order_len - 1):
        if next_index >= len(combatants):
            break
        sheet = CharacterSheet.from_dict(combatants[next_index])
        if not (sheet.is_dead or (sheet.hp_current <= 0 and sheet.death_saves.is_stable)):
            break
        next_index += 1
        if next_index >= order_len:
            next_index = 0
            rounds_advanced += 1

    return next_index, rounds_advanced


def load_turn_states(combat: CombatState) -> dict[str, TurnState]:
    """Deserialise the persisted per-combatant TurnStates for the engine."""
    return {char_id: TurnState.from_dict(ts) for char_id, ts in (combat.turn_states or {}).items()}


def dump_turn_states(turn_states: dict[str, TurnState]) -> dict[str, Any]:
    """Serialise engine TurnStates back into the CombatState JSON column."""
    return {char_id: ts.to_dict() for char_id, ts in turn_states.items()}


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


def combat_summary_text(round_number: int, combatants: list[dict[str, Any]]) -> str:
    """Render a mechanical end-of-combat summary for the chat history.

    Persisted as a SYSTEM chat message so the AI DM (which never sees the
    combat log) knows what actually happened when narration resumes —
    without this it confabulates an outcome.
    """
    lines = [f"Combat ended after {round_number} round(s). Final state:"]
    for combatant in combatants:
        name = combatant.get("name", "Unknown")
        hp = combatant.get("hp_current")
        hp_max = combatant.get("hp_max")
        downed = isinstance(hp, int) and hp <= 0
        saves = combatant.get("death_saves") or {}
        conditions = [c for c in combatant.get("conditions", []) if c]
        if saves.get("is_dead"):
            suffix = " — DEAD"
        elif downed and saves.get("is_stable"):
            suffix = " — DOWN, stable"
        elif downed:
            suffix = " — DOWN"
            successes = saves.get("successes", 0)
            failures = saves.get("failures", 0)
            if successes or failures:
                suffix += f", death saves {successes} success / {failures} failure"
        else:
            suffix = ""
        if conditions:
            suffix += f" ({', '.join(str(c) for c in conditions)})"
        lines.append(f"- {name}: {hp}/{hp_max} HP{suffix}")
    return "\n".join(lines)
