"""
Typed enums and dataclasses for the game engine.

Sub-modules:
- :mod:`.enums`  — all ``str, Enum`` enumerations
- :mod:`.sheets` — typed dataclasses (CharacterSheet, AbilityScoreSet, etc.)

Everything is re-exported here so ``from game_engine.types import X`` works
regardless of which sub-module *X* lives in.
"""

from game_engine.types.enums import (
    Ability,
    ActionType,
    CharacterClass,
    CharacterType,
    ChatRole,
    Condition,
    DamageType,
    LocationType,
    ProposalStatus,
    ProposalType,
    Skill,
)
from game_engine.types.sheets import (
    AbilityScoreSet,
    AttackDetails,
    CharacterSheet,
    CombatStateData,
)

__all__ = [
    # enums
    "Ability",
    "ActionType",
    "CharacterClass",
    "CharacterType",
    "ChatRole",
    "Condition",
    "DamageType",
    "LocationType",
    "ProposalStatus",
    "ProposalType",
    "Skill",
    # dataclasses
    "AbilityScoreSet",
    "AttackDetails",
    "CharacterSheet",
    "CombatStateData",
]
