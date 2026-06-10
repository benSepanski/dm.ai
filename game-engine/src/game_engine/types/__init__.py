"""
Typed enums and dataclasses for the game engine.

Sub-modules:
- :mod:`.enums`  — all ``str, Enum`` enumerations (package)
- :mod:`.sheets` — typed dataclasses (CharacterSheet, AbilityScoreSet, etc.)
- :mod:`.character_state` — sheet sub-structures (hit dice, slots, currency)
- :mod:`.values` — validated value types (DiceNotation, etc.)

Everything is re-exported here so ``from game_engine.types import X`` works
regardless of which sub-module *X* lives in.
"""

from game_engine.types.character_state import (
    ClassLevelEntry,
    Currency,
    DeathSaveState,
    HitDicePool,
    InventoryItem,
    SpellSlotState,
)
from game_engine.types.enums import (
    Ability,
    ActionType,
    AdvantageType,
    Alignment,
    AreaShape,
    ArmorCategory,
    Background,
    CastingTime,
    CharacterClass,
    CharacterType,
    ChatRole,
    ClassResource,
    Condition,
    CoverType,
    CreatureSize,
    CreatureType,
    DamageType,
    DeathSaveOutcome,
    Feat,
    FeatCategory,
    Language,
    LightLevel,
    LocationType,
    ProposalStatus,
    ProposalType,
    RestType,
    Skill,
    Species,
    SpellcasterType,
    SpellComponent,
    SpellRangeType,
    SpellSchool,
    Subclass,
    TaskDifficulty,
    UnarmedStrikeOption,
    WeaponCategory,
    WeaponMastery,
    WeaponProperty,
    subclasses_for,
)
from game_engine.types.sheets import (
    AbilityScoreSet,
    AttackDetails,
    CharacterSheet,
    CombatStateData,
    TurnState,
)
from game_engine.types.values import (
    DiceNotation,
)

__all__ = [
    # enums
    "Ability",
    "ActionType",
    "AdvantageType",
    "Alignment",
    "AreaShape",
    "ArmorCategory",
    "Background",
    "CharacterClass",
    "CastingTime",
    "CharacterType",
    "ChatRole",
    "ClassResource",
    "Condition",
    "CoverType",
    "CreatureSize",
    "CreatureType",
    "DamageType",
    "DeathSaveOutcome",
    "Feat",
    "FeatCategory",
    "Language",
    "LightLevel",
    "LocationType",
    "ProposalStatus",
    "ProposalType",
    "RestType",
    "Skill",
    "Species",
    "SpellcasterType",
    "SpellComponent",
    "SpellRangeType",
    "SpellSchool",
    "TaskDifficulty",
    "Subclass",
    "UnarmedStrikeOption",
    "WeaponCategory",
    "WeaponMastery",
    "WeaponProperty",
    "subclasses_for",
    # dataclasses
    "AbilityScoreSet",
    "AttackDetails",
    "CharacterSheet",
    "CombatStateData",
    "TurnState",
    # character state
    "ClassLevelEntry",
    "Currency",
    "DeathSaveState",
    "HitDicePool",
    "InventoryItem",
    "SpellSlotState",
    # value types
    "DiceNotation",
]
