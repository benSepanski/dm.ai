"""
D&D 5.5e spellcasting engine: slot progression, save DCs, and result types.

This module owns slot bookkeeping, save DC / attack-bonus helpers, the
casting-time action-economy gate (SPL-03, SPL-06), and the typed
:class:`SpellCastResult` / :class:`SpellTargetOutcome` dataclasses. Spell
effect resolution (damage, conditions, healing) lives in
:mod:`._spell_resolution`, which calls :func:`check_casting_economy` /
:func:`commit_casting_economy` so the gate is enforced in exactly one place
regardless of caller (dm-api's cast-spell endpoint, or any future caller).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from game_engine.rules.dnd_5_5e._checks import _calc_prof_bonus
from game_engine.rules.dnd_5_5e.data.spells import SpellData
from game_engine.types import (
    Ability,
    CastingTime,
    CharacterSheet,
    ClassLevelEntry,
    Condition,
    DiceNotation,
    SpellcasterType,
    SpellSlotState,
    TurnState,
)

# Casting times resolvable inside a combat turn, mapped to the TurnState
# economy slot they consume. Anything longer (1 minute, 1 hour, rituals)
# can't be cast mid-fight.
_COMBAT_CASTING_TIMES = (CastingTime.ACTION, CastingTime.BONUS_ACTION, CastingTime.REACTION)

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
    return [SpellSlotState(slot_level=slot_level, maximum=count, remaining=count)]


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
        merged into the same list (the warlock's slots sit at their pact
        slot level).
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
    for pact_slot in pact:
        existing = next((s for s in slots if s.slot_level == pact_slot.slot_level), None)
        if existing is None:
            slots.append(pact_slot)
        else:
            existing.maximum += pact_slot.maximum
            existing.remaining += pact_slot.remaining
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


def _scale_dice(dice: DiceNotation, multiplier: int = 1, extra_dice: int = 0) -> DiceNotation:
    """Return *dice* with the die count multiplied and extra dice added."""
    count, sides, mod = dice.parsed()
    new_count = count * multiplier + extra_dice
    suffix = f"{mod:+d}" if mod else ""
    return DiceNotation(f"{new_count}d{sides}{suffix}")


def duration_rounds(duration: str) -> int | None:
    """Best-effort conversion of a duration string to combat rounds."""
    text = duration.lower()
    if "1 round" in text:
        return 1
    if "1 minute" in text:
        return 10
    if "10 minutes" in text:
        return 100
    if "1 hour" in text:
        return 600
    return None


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


def check_casting_economy(
    spell: SpellData, ts: TurnState, *, expends_slot: bool
) -> tuple[str, str] | None:
    """Read-only check: would casting *spell* right now violate the turn economy?

    Returns ``(error_code, flavor_text)`` if the cast should be rejected, or
    ``None`` if it's clear to proceed. Mutates nothing — callers validate
    with this *before* touching a spell slot (ACT-05-style validate-before-
    consume), then call :func:`commit_casting_economy` only once the cast
    has actually succeeded.

    Covers two 2024 PHB rules that apply only to the three casting times the
    turn-based action economy defines (action/bonus action/reaction): a
    spell is cast using the specific slot its ``casting_time`` names
    (SPL-03), and a creature can expend only one spell slot per turn to
    cast a spell — cantrips and ritual casts, which don't expend a slot, are
    unrestricted (SPL-06). Longer casting times (10 minutes, 1 hour, ...)
    are downtime rituals outside any single turn, so they're exempt from
    both checks here; a caller representing an active combat turn (e.g. the
    dm-api combat-cast-spell endpoint) is responsible for rejecting those
    separately as inappropriate for its context.
    """
    if spell.casting_time not in _COMBAT_CASTING_TIMES:
        return None
    if spell.casting_time is CastingTime.ACTION and ts.action_used:
        return ("action_used", "Action already used this turn.")
    if spell.casting_time is CastingTime.BONUS_ACTION and ts.bonus_action_used:
        return ("bonus_action_used", "Bonus action already used.")
    if spell.casting_time is CastingTime.REACTION and ts.reaction_used:
        return ("reaction_used", "Reaction already used this round.")
    if expends_slot and ts.spell_slot_expended_this_turn:
        return (
            "spell_slot_already_used",
            "Only one spell can be cast using a spell slot per turn.",
        )
    return None


def commit_casting_economy(spell: SpellData, ts: TurnState, *, expends_slot: bool) -> None:
    """Mark the casting-time economy slot spent. Call only after the cast succeeds.

    No-op for casting times outside the turn economy (see
    :func:`check_casting_economy`) — there's no TurnState slot for them to
    consume.
    """
    if spell.casting_time not in _COMBAT_CASTING_TIMES:
        return
    if spell.casting_time is CastingTime.ACTION:
        ts.action_used = True
    elif spell.casting_time is CastingTime.BONUS_ACTION:
        ts.bonus_action_used = True
    else:
        ts.reaction_used = True
    if expends_slot:
        ts.spell_slot_expended_this_turn = True
