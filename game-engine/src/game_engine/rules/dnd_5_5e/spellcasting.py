"""
D&D 5.5e spellcasting engine: slot progression, save DCs, and result types.

Action economy for the Magic action is enforced by :mod:`._actions`;
this module owns slot bookkeeping, save DC / attack-bonus helpers, and the
typed :class:`SpellCastResult` / :class:`SpellTargetOutcome` dataclasses.
Spell effect resolution (damage, conditions, healing) lives in
:mod:`._spell_resolution`.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from game_engine.rules.dnd_5_5e._checks import _calc_prof_bonus
from game_engine.types import (
    Ability,
    CharacterSheet,
    ClassLevelEntry,
    Condition,
    DiceNotation,
    SpellcasterType,
    SpellSlotState,
)

# Shared full-caster slot table: SLOT_TABLE[caster_level][slot_level - 1].
_FULL_CASTER_SLOTS: dict[int, list[int]] = {
    1: [2],
    2: [3],
    3: [4, 2],
    4: [4, 3],
    5: [4, 3, 2],
    6: [4, 3, 3],
    7: [4, 3, 3, 1],
    8: [4, 3, 3, 2],
    9: [4, 3, 3, 3, 1],
    10: [4, 3, 3, 3, 2],
    11: [4, 3, 3, 3, 2, 1],
    12: [4, 3, 3, 3, 2, 1],
    13: [4, 3, 3, 3, 2, 1, 1],
    14: [4, 3, 3, 3, 2, 1, 1],
    15: [4, 3, 3, 3, 2, 1, 1, 1],
    16: [4, 3, 3, 3, 2, 1, 1, 1],
    17: [4, 3, 3, 3, 2, 1, 1, 1, 1],
    18: [4, 3, 3, 3, 3, 1, 1, 1, 1],
    19: [4, 3, 3, 3, 3, 2, 1, 1, 1],
    20: [4, 3, 3, 3, 3, 2, 2, 1, 1],
}

# Pact magic: (slot count, slot level) by warlock level (2024 PHB).
_PACT_SLOTS: dict[int, tuple[int, int]] = {
    1: (1, 1),
    2: (2, 1),
    3: (2, 2),
    4: (2, 2),
    5: (2, 3),
    6: (2, 3),
    7: (2, 4),
    8: (2, 4),
    9: (2, 5),
    10: (2, 5),
    11: (3, 5),
    12: (3, 5),
    13: (3, 5),
    14: (3, 5),
    15: (3, 5),
    16: (3, 5),
    17: (4, 5),
    18: (4, 5),
    19: (4, 5),
    20: (4, 5),
}


def caster_level_contribution(caster_type: SpellcasterType, class_level: int) -> int:
    """Return the effective caster levels a class contributes (2024 rules)."""
    if class_level <= 0:
        return 0
    if caster_type is SpellcasterType.FULL:
        return class_level
    if caster_type is SpellcasterType.HALF:
        return math.ceil(class_level / 2)
    if caster_type is SpellcasterType.THIRD:
        return math.ceil(class_level / 3)
    return 0


def slots_for_caster_level(caster_level: int) -> list[SpellSlotState]:
    """Return fresh spell slots for an effective caster level (0 → none)."""
    if caster_level <= 0:
        return []
    table = _FULL_CASTER_SLOTS[min(20, caster_level)]
    return [
        SpellSlotState(slot_level=i + 1, maximum=count, remaining=count)
        for i, count in enumerate(table)
        if count > 0
    ]


def pact_slots_for_level(warlock_level: int) -> list[SpellSlotState]:
    """Return fresh pact magic slots for a warlock level (0 → none)."""
    if warlock_level <= 0:
        return []
    count, slot_level = _PACT_SLOTS[min(20, warlock_level)]
    return [SpellSlotState(slot_level=slot_level, maximum=count, remaining=count, is_pact=True)]


def compute_spell_slots(
    class_levels: list[ClassLevelEntry],
    caster_types: dict[ClassLevelEntry, SpellcasterType] | None = None,
) -> list[SpellSlotState]:
    """Compute combined spell slots (standard + pact) for a class mix.

    Args:
        class_levels: The character's class level entries.
        caster_types: Optional override of each entry's caster type; when
            omitted, the class progression registry is consulted.

    Returns:
        Fresh (fully restored) :class:`SpellSlotState` list. Pact slots are
        kept as their own entries — even at a slot level a standard slot
        also occupies — rather than merged into the standard pool, since
        only pact slots are restored by a short rest (SPL-15); see
        :func:`SpellSlotState.is_pact`.
    """
    from game_engine.rules.dnd_5_5e.data.class_features import CLASS_PROGRESSIONS

    total_caster_level = 0
    pact: list[SpellSlotState] = []
    for entry in class_levels:
        if caster_types is not None and entry in caster_types:
            ctype = caster_types[entry]
        else:
            progression = CLASS_PROGRESSIONS.get(entry.character_class)
            ctype = progression.spellcaster_type if progression else SpellcasterType.NONE
        if ctype is SpellcasterType.PACT:
            pact = pact_slots_for_level(entry.level)
        else:
            total_caster_level += caster_level_contribution(ctype, entry.level)

    slots = slots_for_caster_level(total_caster_level)
    slots.extend(pact)
    return sorted(slots, key=lambda s: s.slot_level)


def spell_save_dc(char: CharacterSheet, ability: Ability) -> int:
    """Return 8 + proficiency bonus + spellcasting ability modifier."""
    return 8 + _calc_prof_bonus(char.level) + char.ability_scores.modifier(ability)


def spell_attack_bonus(char: CharacterSheet, ability: Ability) -> int:
    """Return proficiency bonus + spellcasting ability modifier."""
    return _calc_prof_bonus(char.level) + char.ability_scores.modifier(ability)


def cantrip_dice_multiplier(character_level: int) -> int:
    """Cantrip damage dice multiplier: ×2 at level 5, ×3 at 11, ×4 at 17."""
    if character_level >= 17:
        return 4
    if character_level >= 11:
        return 3
    if character_level >= 5:
        return 2
    return 1


def _scale_dice(
    dice: DiceNotation, multiplier: int = 1, extra_dice: int = 0, extra_flat: int = 0
) -> DiceNotation:
    """Return *dice* with the die count multiplied, extra dice, and extra flat modifier added."""
    count, sides, mod = dice.parsed()
    new_count = count * multiplier + extra_dice
    new_mod = mod + extra_flat
    suffix = f"{new_mod:+d}" if new_mod else ""
    return DiceNotation(f"{new_count}d{sides}{suffix}")


_DURATION_RE = re.compile(r"(\d+)\s*(round|minute|hour)")
_ROUNDS_PER_UNIT = {"round": 1, "minute": 10, "hour": 600}


def duration_rounds(duration: str) -> int | None:
    """Best-effort conversion of a duration string to combat rounds.

    Matches any ``N round(s)``/``N minute(s)``/``N hour(s)`` substring (e.g.
    "8 hours", "Concentration, up to 10 minutes") rather than a fixed set of
    literal phrases (SPL-23), so durations outside the handful originally
    special-cased don't silently fall through to ``None``. Returns ``None``
    for genuinely unbounded/unparseable durations (e.g. "Until dispelled",
    "Instantaneous").
    """
    match = _DURATION_RE.search(duration.lower())
    if match is None:
        return None
    count = int(match.group(1))
    return count * _ROUNDS_PER_UNIT[match.group(2)]


@dataclass
class SpellTargetOutcome:
    """Per-target result of a spell cast."""

    target_id: str
    hit: bool = True
    attack_total: int | None = None
    save_total: int | None = None
    save_success: bool | None = None
    damage: int = 0
    healing: int = 0
    revived: bool = False
    conditions_applied: list[Condition] = field(default_factory=list)
    concentration_save_dc: int | None = None
    concentration_save_total: int | None = None
    concentration_broken: str | None = None


@dataclass
class SpellCastResult:
    """Typed outcome of casting a spell."""

    success: bool
    spell_name: str
    slot_level_used: int | None
    outcomes: list[SpellTargetOutcome]
    flavor_text: str
    concentration_started: bool = False
    error: str | None = None


def _consume_slot(caster: CharacterSheet, slot_level: int) -> bool:
    """Consume one slot of exactly *slot_level*; False if none remain."""
    slot = next(
        (s for s in caster.spell_slots if s.slot_level == slot_level and s.remaining > 0),
        None,
    )
    if slot is None:
        return False
    slot.remaining -= 1
    return True
