"""Core rule-agnostic building blocks for the game engine."""

from game_engine.core.character import (
    AbstractCharacter,
    AbilityScores,
    CharacterType,
    get_modifier,
)
from game_engine.core.combat import AbstractCombat, CombatPhase
from game_engine.core.conditions import (
    CONDITION_EFFECTS,
    EXHAUSTION_LEVELS,
    condition_prevents_action,
    get_active_conditions,
    is_immune_to_condition,
)
from game_engine.core.dice import (
    d4,
    d6,
    d8,
    d10,
    d12,
    d20,
    d100,
    parse_notation,
    roll,
    roll_dice,
    roll_with_advantage,
    roll_with_disadvantage,
)
from game_engine.core.initiative import InitiativeEntry, InitiativeTracker

__all__ = [
    # character
    "AbstractCharacter",
    "AbilityScores",
    "CharacterType",
    "get_modifier",
    # combat
    "AbstractCombat",
    "CombatPhase",
    # conditions
    "CONDITION_EFFECTS",
    "EXHAUSTION_LEVELS",
    "condition_prevents_action",
    "get_active_conditions",
    "is_immune_to_condition",
    # dice
    "d4",
    "d6",
    "d8",
    "d10",
    "d12",
    "d20",
    "d100",
    "parse_notation",
    "roll",
    "roll_dice",
    "roll_with_advantage",
    "roll_with_disadvantage",
    # initiative
    "InitiativeEntry",
    "InitiativeTracker",
]
