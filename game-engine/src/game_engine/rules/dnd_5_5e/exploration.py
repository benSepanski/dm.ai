"""
D&D 5.5e exploration and environment rules (2024 PHB chapters 1 & 6):
encumbrance, jumping, falling, suffocation, travel pace, light.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from game_engine.core.dice import roll_dice
from game_engine.types import (
    Ability,
    CharacterSheet,
    Condition,
    CreatureSize,
    DamageType,
    LightLevel,
)

_SIZE_CAPACITY_MULTIPLIER: dict[CreatureSize, int] = {
    CreatureSize.TINY: 1,  # tiny creatures halve capacity; see carrying_capacity
    CreatureSize.SMALL: 1,
    CreatureSize.MEDIUM: 1,
    CreatureSize.LARGE: 2,
    CreatureSize.HUGE: 4,
    CreatureSize.GARGANTUAN: 8,
}


def carrying_capacity(strength_score: int, size: CreatureSize = CreatureSize.MEDIUM) -> int:
    """Maximum carried weight in pounds: STR × 15, scaled by size."""
    base = strength_score * 15
    if size is CreatureSize.TINY:
        return base // 2
    return base * _SIZE_CAPACITY_MULTIPLIER[size]


def push_drag_lift(strength_score: int, size: CreatureSize = CreatureSize.MEDIUM) -> int:
    """Maximum push/drag/lift weight in pounds: STR × 30, scaled by size."""
    return carrying_capacity(strength_score, size) * 2


def is_encumbered(char: CharacterSheet, size: CreatureSize = CreatureSize.MEDIUM) -> bool:
    """True when carried inventory weight exceeds carrying capacity."""
    total = sum(item.weight_lb * item.quantity for item in char.inventory)
    return total > carrying_capacity(char.ability_scores.get(Ability.STRENGTH), size)


def long_jump_distance(strength_score: int, running_start: bool = True) -> int:
    """Long jump distance in feet: STR score (halved without a running start)."""
    return strength_score if running_start else strength_score // 2


def high_jump_height(strength_modifier: int, running_start: bool = True) -> int:
    """High jump height in feet: 3 + STR modifier (halved without a run-up)."""
    height = max(0, 3 + strength_modifier)
    return height if running_start else height // 2


def fall_damage(char: CharacterSheet, distance_ft: int) -> int:
    """Apply falling damage: 1d6 bludgeoning per 10 feet (max 20d6), land prone.

    Args:
        char: The falling character. Modified in-place.
        distance_ft: Distance fallen in feet.

    Returns:
        Damage dealt (after resistances).
    """
    from game_engine.rules.dnd_5_5e._damage import _apply_damage_impl

    dice = min(20, distance_ft // 10)
    if dice <= 0:
        return 0
    total, _ = roll_dice(dice, 6)
    before = char.hp_current + char.temp_hp
    _apply_damage_impl(char, total, DamageType.BLUDGEONING)
    if Condition.PRONE not in char.conditions:
        char.conditions.append(Condition.PRONE)
    return before - (char.hp_current + char.temp_hp)


def breath_holding_minutes(constitution_modifier: int) -> int:
    """Minutes a creature can hold its breath: 1 + CON modifier (min 30 s → 1)."""
    return max(1, 1 + constitution_modifier)


class TravelPace(str, Enum):
    """Overland travel paces (2024 PHB chapter 1)."""

    FAST = "fast"
    NORMAL = "normal"
    SLOW = "slow"


@dataclass(frozen=True)
class TravelPaceData:
    """Distances covered at a travel pace, plus its trade-off."""

    pace: TravelPace
    feet_per_minute: int
    miles_per_hour: int
    miles_per_day: int
    note: str


TRAVEL_PACES: dict[TravelPace, TravelPaceData] = {
    TravelPace.FAST: TravelPaceData(
        pace=TravelPace.FAST,
        feet_per_minute=400,
        miles_per_hour=4,
        miles_per_day=30,
        note="−5 penalty to passive Wisdom (Perception) scores.",
    ),
    TravelPace.NORMAL: TravelPaceData(
        pace=TravelPace.NORMAL,
        feet_per_minute=300,
        miles_per_hour=3,
        miles_per_day=24,
        note="No modifier.",
    ),
    TravelPace.SLOW: TravelPaceData(
        pace=TravelPace.SLOW,
        feet_per_minute=200,
        miles_per_hour=2,
        miles_per_day=18,
        note="Able to use Stealth while traveling.",
    ),
}


def perception_disadvantage_in(light: LightLevel) -> bool:
    """True when sight-based Perception checks have disadvantage in *light*."""
    return light is LightLevel.DIM


def effectively_blinded_in(light: LightLevel, darkvision_ft: int = 0) -> bool:
    """True when a creature can't see in *light* (no/insufficient darkvision).

    Darkvision lets a creature treat darkness within range as dim light.
    """
    return light is LightLevel.DARKNESS and darkvision_ft <= 0
