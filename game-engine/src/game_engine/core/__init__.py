"""Core rule-agnostic building blocks for the game engine."""

from game_engine.core.conditions import (
    CONDITION_EFFECTS,
    ConditionEffect,
    is_immune_to_condition,
)
from game_engine.core.dice import (
    parse_notation,
    roll,
    roll_dice,
    roll_with_advantage,
    roll_with_disadvantage,
)
from game_engine.core.initiative import InitiativeEntry, InitiativeTracker

__all__ = [
    # conditions
    "CONDITION_EFFECTS",
    "ConditionEffect",
    "is_immune_to_condition",
    # dice
    "parse_notation",
    "roll",
    "roll_dice",
    "roll_with_advantage",
    "roll_with_disadvantage",
    # initiative
    "InitiativeEntry",
    "InitiativeTracker",
]
