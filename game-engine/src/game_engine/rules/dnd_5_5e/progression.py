"""
D&D 5.5e character advancement: XP thresholds, leveling, multiclassing.
"""

from __future__ import annotations

from dataclasses import dataclass

from game_engine.rules.dnd_5_5e.classes import CLASSES
from game_engine.types import (
    Ability,
    CharacterClass,
    CharacterSheet,
    ClassLevelEntry,
    HitDicePool,
    Subclass,
)

#: XP required to reach each character level (2024 PHB chapter 2).
XP_THRESHOLDS: dict[int, int] = {
    1: 0,
    2: 300,
    3: 900,
    4: 2_700,
    5: 6_500,
    6: 14_000,
    7: 23_000,
    8: 34_000,
    9: 48_000,
    10: 64_000,
    11: 85_000,
    12: 100_000,
    13: 120_000,
    14: 140_000,
    15: 165_000,
    16: 195_000,
    17: 225_000,
    18: 265_000,
    19: 305_000,
    20: 355_000,
}

#: Minimum ability score required to multiclass into/out of a class.
MULTICLASS_MINIMUM_SCORE = 13


def level_for_xp(xp: int) -> int:
    """Return the character level earned by *xp* (1-20)."""
    level = 1
    for lvl, threshold in XP_THRESHOLDS.items():
        if xp >= threshold:
            level = lvl
    return level


def xp_for_level(level: int) -> int:
    """Return the XP threshold for *level*.

    Raises:
        ValueError: If *level* is outside 1-20.
    """
    if level not in XP_THRESHOLDS:
        raise ValueError(f"Level must be between 1 and 20, got {level}.")
    return XP_THRESHOLDS[level]


def average_hit_points_gain(hit_die: int, con_modifier: int) -> int:
    """HP gained on level-up using the fixed (average) roll: die/2 + 1 + CON."""
    return max(1, hit_die // 2 + 1 + con_modifier)


@dataclass
class MulticlassCheck:
    """Result of a multiclass prerequisite check."""

    allowed: bool
    reason: str | None = None


def can_multiclass(sheet: CharacterSheet, new_class: CharacterClass) -> MulticlassCheck:
    """Check the 2024 multiclassing prerequisites.

    A character needs a score of 13+ in the primary ability of both the
    current class(es) and the new class.

    Args:
        sheet: Character sheet.
        new_class: The class being added.

    Returns:
        :class:`MulticlassCheck` with an explanatory reason on failure.
    """
    classes_to_check = {e.character_class for e in sheet.class_levels} or {sheet.char_class}
    classes_to_check.add(new_class)
    for cls in classes_to_check:
        data = CLASSES[cls]
        if not any(
            sheet.ability_scores.get(ability) >= MULTICLASS_MINIMUM_SCORE
            for ability in data.primary_abilities
        ):
            names = " or ".join(a.value for a in data.primary_abilities)
            return MulticlassCheck(
                allowed=False,
                reason=f"Requires {names} {MULTICLASS_MINIMUM_SCORE}+ for {cls.value}.",
            )
    return MulticlassCheck(allowed=True)


def level_up(
    sheet: CharacterSheet,
    character_class: CharacterClass | None = None,
    subclass: Subclass | None = None,
    rolled_hp: int | None = None,
) -> CharacterSheet:
    """Advance *sheet* one level in *character_class* (default: primary class).

    Applies hit point gain (average unless *rolled_hp* is given), extends
    the hit dice pool, refreshes maximum spell slots, and records the
    class level entry. Feature/ASI choices are the caller's responsibility
    (consult the class progression registry for what was gained).

    Args:
        sheet: Character sheet. Modified in-place and returned.
        character_class: Class gaining the level.
        subclass: Subclass choice, if this level grants one.
        rolled_hp: Rolled hit die result to use instead of the average.

    Returns:
        Updated character sheet.

    Raises:
        ValueError: If the character is already level 20 or multiclass
            prerequisites are not met.
    """
    from game_engine.rules.dnd_5_5e.spellcasting import compute_spell_slots

    if sheet.level >= 20:
        raise ValueError("Already at maximum level (20).")
    target_class = character_class or sheet.char_class

    if not sheet.class_levels:
        sheet.class_levels = [ClassLevelEntry(sheet.char_class, sheet.level, sheet.subclass)]
    entry = next(
        (e for e in sheet.class_levels if e.character_class == target_class),
        None,
    )
    if entry is None:
        check = can_multiclass(sheet, target_class)
        if not check.allowed:
            raise ValueError(check.reason or "Multiclass prerequisites not met.")
        entry = ClassLevelEntry(target_class, 0, None)
        sheet.class_levels.append(entry)
    entry.level += 1
    if subclass is not None:
        entry.subclass = subclass
        if target_class == sheet.char_class:
            sheet.subclass = subclass
    sheet.level += 1

    hit_die = CLASSES[target_class].hit_die
    con_modifier = sheet.ability_scores.modifier(Ability.CONSTITUTION)
    gained = (
        max(1, rolled_hp + con_modifier)
        if rolled_hp is not None
        else average_hit_points_gain(hit_die, con_modifier)
    )
    sheet.hp_max += gained
    sheet.hp_current += gained

    pool = next((p for p in sheet.hit_dice if p.die_size == hit_die), None)
    if pool is None:
        sheet.hit_dice.append(HitDicePool(die_size=hit_die, maximum=1, remaining=1))
    else:
        pool.maximum += 1
        pool.remaining += 1

    # Refresh maximum spell slots, preserving how many were already spent.
    spent = {s.slot_level: s.maximum - s.remaining for s in sheet.spell_slots}
    sheet.spell_slots = compute_spell_slots(sheet.class_levels)
    for slot in sheet.spell_slots:
        slot.remaining = max(0, slot.maximum - spent.get(slot.slot_level, 0))
    return sheet
