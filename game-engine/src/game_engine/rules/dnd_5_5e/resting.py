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
from game_engine.types import Ability, CharacterSheet, Condition


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

    # SPL-15: pact slots are their own pool (SpellSlotState.is_pact), never
    # merged with standard slots at the same level, so restoring by that flag
    # can't also refill a standard slot that happens to share a slot level.
    for slot in char.spell_slots:
        if slot.is_pact and slot.remaining < slot.maximum:
            slot.remaining = slot.maximum
            result.slots_restored = True
    return result


def long_rest(char: CharacterSheet) -> RestResult:
    """Take a long rest (8+ hours).

    2024 rules: regain all hit points and ALL spent Hit Point Dice (a
    change from 2014's half), all spell slots, lose remaining temporary
    hit points, and reduce exhaustion by 1.

    Note on EFF-08's sibling finding (EFF-16, "long rest grants full
    benefits to a character at 0 HP"): strict 2024 RAW requires at least 1
    HP *at the start* of a rest to gain its benefits, but this engine
    deliberately keeps the "stable character wakes up on a long rest"
    behavior — see the regression tests
    ``test_long_rest_clears_death_saves_and_unconscious_for_stable_character``
    / ``test_long_rest_clears_prone_from_unconscious_fall`` in
    ``tests/test_resting_exploration.py``, which exist specifically to guard
    it. Gating this on ``hp_current >= 1`` would strand a stabilized
    0-HP character forever absent the natural-recovery rule (1 HP after
    1d4 hours), which this engine doesn't model. Left as-is; flagged in
    ``docs/engine-correctness-remediation.md`` as a design decision rather
    than silently "fixed".

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
        if char.exhaustion_level == 0:
            # Keep the bare Condition.EXHAUSTION tag (see
            # _conditions.gain_exhaustion) in sync now that the level is 0.
            char.conditions = [c for c in char.conditions if c != Condition.EXHAUSTION]
            char.condition_durations.pop(Condition.EXHAUSTION, None)
    return result
