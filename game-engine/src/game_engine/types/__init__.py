"""
Typed enums and dataclasses for the game engine.

Sub-modules:
- :mod:`.enums`  — all ``str, Enum`` enumerations
- :mod:`.sheets` — typed dataclasses (CharacterSheet, AbilityScoreSet, etc.)
- :mod:`.values` — validated value types (DiceNotation, etc.)

Everything is re-exported here so ``from game_engine.types import X`` works
regardless of which sub-module *X* lives in.
"""

from game_engine.types.enums import (
    Ability,
    ActionType,
    AdvantageType,
    ArmorCategory,
    CharacterClass,
    CharacterType,
    ChatRole,
    Condition,
    CreatureSize,
    CreatureType,
    DamageType,
    LocationType,
    ProposalStatus,
    ProposalType,
    Skill,
    SpellSchool,
    WeaponProperty,
)
from game_engine.types.sheets import (
    AbilityScoreSet,
    AttackDetails,
    CharacterSheet,
    CombatStateData,
)
from game_engine.types.values import (
    DiceNotation,
)

__all__ = [
    # enums
    "Ability",
    "ActionType",
    "AdvantageType",
    "ArmorCategory",
    "CharacterClass",
    "CharacterType",
    "ChatRole",
    "Condition",
    "CreatureSize",
    "CreatureType",
    "DamageType",
    "LocationType",
    "ProposalStatus",
    "ProposalType",
    "Skill",
    "SpellSchool",
    "WeaponProperty",
    # dataclasses
    "AbilityScoreSet",
    "AttackDetails",
    "CharacterSheet",
    "CombatStateData",
    # value types
    "DiceNotation",
]
