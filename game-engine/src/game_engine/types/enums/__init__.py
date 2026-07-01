"""
Typed string enums for the game engine.

All enums use ``str, Enum`` inheritance so values are wire-compatible
with their string equivalents and support ``Enum(value)`` construction.

Split into focused submodules; everything is re-exported here so
``from game_engine.types.enums import X`` works regardless of submodule.
"""

from game_engine.types.enums._app import (
    ChatRole,
    LocationType,
    ProposalStatus,
    ProposalType,
)
from game_engine.types.enums._character import (
    Alignment,
    Background,
    CharacterClass,
    CharacterType,
    ClassResource,
    Language,
    Species,
    SpeciesLineage,
    SpellcasterType,
)
from game_engine.types.enums._combat import (
    ActionType,
    ArmorCategory,
    CoverType,
    DeathSaveOutcome,
    RestType,
    UnarmedStrikeOption,
    WeaponCategory,
    WeaponMastery,
    WeaponProperty,
)
from game_engine.types.enums._core import (
    Ability,
    AdvantageType,
    AreaShape,
    CastingTime,
    Condition,
    CreatureSize,
    CreatureType,
    DamageType,
    LightLevel,
    Skill,
    SpellComponent,
    SpellRangeType,
    SpellSchool,
    TaskDifficulty,
)
from game_engine.types.enums._feats import Feat, FeatCategory
from game_engine.types.enums._subclasses import Subclass, subclasses_for

__all__ = [
    # _core
    "Ability",
    "AdvantageType",
    "AreaShape",
    "CastingTime",
    "Condition",
    "CreatureSize",
    "CreatureType",
    "DamageType",
    "LightLevel",
    "Skill",
    "SpellComponent",
    "SpellRangeType",
    "SpellSchool",
    "TaskDifficulty",
    # _character
    "Alignment",
    "Background",
    "CharacterClass",
    "CharacterType",
    "ClassResource",
    "Language",
    "Species",
    "SpellcasterType",
    "SpeciesLineage",
    # _subclasses
    "Subclass",
    "subclasses_for",
    # _feats
    "Feat",
    "FeatCategory",
    # _combat
    "ActionType",
    "ArmorCategory",
    "CoverType",
    "DeathSaveOutcome",
    "RestType",
    "UnarmedStrikeOption",
    "WeaponCategory",
    "WeaponMastery",
    "WeaponProperty",
    # _app
    "ChatRole",
    "LocationType",
    "ProposalStatus",
    "ProposalType",
]
