"""
D&D 5.5e SRD data modules.

Re-exports the main data registries and dataclasses for convenience.
"""

from game_engine.rules.dnd_5_5e.data.armor import (
    ARMOR,
    ARMOR_BY_NAME,
    ArmorData,
    compute_armor_class,
    get_armor,
)
from game_engine.rules.dnd_5_5e.data.backgrounds import (
    BACKGROUNDS,
    BackgroundData,
    get_background,
)
from game_engine.rules.dnd_5_5e.data.class_features import (
    CLASS_PROGRESSIONS,
    ClassFeatureData,
    ClassProgression,
    get_progression,
)
from game_engine.rules.dnd_5_5e.data.feats import FEATS, FeatData, get_feat
from game_engine.rules.dnd_5_5e.data.gear import (
    GEAR,
    PACKS,
    TOOLS,
    GearData,
    PackData,
    ToolData,
    get_gear,
    get_tool,
)
from game_engine.rules.dnd_5_5e.data.monsters import MONSTERS, MonsterAction, MonsterData
from game_engine.rules.dnd_5_5e.data.species import (
    SPECIES,
    SpeciesData,
    SpeciesTraitData,
    get_species,
)
from game_engine.rules.dnd_5_5e.data.spells import (
    SPELLS,
    SPELLS_BY_NAME,
    SpellData,
    get_spell,
)
from game_engine.rules.dnd_5_5e.data.weapons import (
    WEAPONS,
    WEAPONS_BY_NAME,
    WeaponData,
    get_weapon,
)

__all__ = [
    # spells
    "SPELLS",
    "SPELLS_BY_NAME",
    "SpellData",
    "get_spell",
    # monsters
    "MONSTERS",
    "MonsterData",
    "MonsterAction",
    # weapons & armor
    "WEAPONS",
    "WEAPONS_BY_NAME",
    "WeaponData",
    "get_weapon",
    "ARMOR",
    "ARMOR_BY_NAME",
    "ArmorData",
    "get_armor",
    "compute_armor_class",
    # gear
    "GEAR",
    "TOOLS",
    "PACKS",
    "GearData",
    "ToolData",
    "PackData",
    "get_gear",
    "get_tool",
    # origins
    "SPECIES",
    "SpeciesData",
    "SpeciesTraitData",
    "get_species",
    "BACKGROUNDS",
    "BackgroundData",
    "get_background",
    # feats
    "FEATS",
    "FeatData",
    "get_feat",
    # class progressions
    "CLASS_PROGRESSIONS",
    "ClassFeatureData",
    "ClassProgression",
    "get_progression",
]
