"""
D&D 5.5e resting rules (2024 PHB chapter 1).

Short rest: spend Hit Point Dice to heal; warlock pact slots return.
Long rest: full HP, all Hit Point Dice and spell slots return, temp HP
ends, exhaustion drops by 1.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from game_engine.core.dice import roll_dice
from game_engine.rules.dnd_5_5e._damage import _apply_healing_impl
from game_engine.types import Ability, CharacterClass, CharacterSheet, Condition


@dataclass
class RestResult:
    """Outcome of a rest."""

    hp_restored: int = 0
    hit_dice_spent: int = 0
    hit_dice_restored: int = 0
    slots_restored: bool = False
    exhaustion_reduced: bool = False
    rolls: list[int] = field(default_factory=list)


def spend_hit_die(char: CharacterSheet, die_size: int | None = None) -> int:
    """Spend one Hit Point Die and heal the rolled amount + CON modifier.

    Args:
        char: Character sheet. Modified in-place.
        die_size: Specific die size to spend (default: largest available).

    Returns:
        Hit points restored (0 if no dice remain).
    """
    pools = [p for p in char.hit_dice if p.remaining > 0]
    if die_size is not None:
        pools = [p for p in pools if p.die_size == die_size]
    if not pools:
        return 0
    pool = max(pools, key=lambda p: p.die_size)
    pool.remaining -= 1
    rolled, _ = roll_dice(1, pool.die_size)
    healed = max(1, rolled + char.ability_scores.modifier(Ability.CONSTITUTION))
    before = char.hp_current
    _apply_healing_impl(char, healed)
    return char.hp_current - before


def short_rest(char: CharacterSheet, hit_dice_to_spend: int = 0) -> RestResult:
    """Take a short rest (1+ hour), optionally spending Hit Point Dice.

    Warlock pact magic slots are fully restored on a short rest.

    Args:
        char: Character sheet. Modified in-place.
        hit_dice_to_spend: Number of Hit Point Dice to spend on healing.

    Returns:
        :class:`RestResult`.
    """
    result = RestResult()
    for _ in range(max(0, hit_dice_to_spend)):
        healed = spend_hit_die(char)
        if healed == 0 and not any(p.remaining > 0 for p in char.hit_dice):
            break
        result.hp_restored += healed
        result.hit_dice_spent += 1

    warlock_levels = char.class_level(CharacterClass.WARLOCK)
    if warlock_levels > 0:
        from game_engine.rules.dnd_5_5e.spellcasting import pact_slots_for_level

        for pact_slot in pact_slots_for_level(warlock_levels):
            slot = next(
                (s for s in char.spell_slots if s.slot_level == pact_slot.slot_level), None
            )
            if slot is not None and slot.remaining < slot.maximum:
                slot.remaining = slot.maximum
                result.slots_restored = True
    return result


def long_rest(char: CharacterSheet) -> RestResult:
    """Take a long rest (8+ hours).

    2024 rules: regain all hit points and ALL spent Hit Point Dice (a
    change from 2014's half), all spell slots, lose remaining temporary
    hit points, and reduce exhaustion by 1.

    Args:
        char: Character sheet. Modified in-place.

    Returns:
        :class:`RestResult`.
    """
    result = RestResult()
    if char.is_dead:
        return result

    before = char.hp_current
    char.hp_current = char.hp_max
    result.hp_restored = char.hp_current - before
    if before <= 0 and char.hp_current > 0:
        char.death_saves.reset()
        _rest_cleared = {Condition.UNCONSCIOUS, Condition.PRONE}
        char.conditions = [c for c in char.conditions if c not in _rest_cleared]
        char.condition_durations.pop(Condition.UNCONSCIOUS, None)
        char.condition_durations.pop(Condition.PRONE, None)
    char.temp_hp = 0

    for pool in char.hit_dice:
        result.hit_dice_restored += pool.maximum - pool.remaining
        pool.remaining = pool.maximum

    for slot in char.spell_slots:
        if slot.remaining < slot.maximum:
            result.slots_restored = True
        slot.remaining = slot.maximum

    if char.exhaustion_level > 0:
        char.exhaustion_level -= 1
        result.exhaustion_reduced = True
    return result
