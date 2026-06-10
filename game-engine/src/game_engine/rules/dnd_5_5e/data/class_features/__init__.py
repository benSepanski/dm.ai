"""
Per-class progression tables (2024 PHB chapter 3).
"""

from game_engine.rules.dnd_5_5e.data.class_features._base import (
    ClassFeatureData,
    ClassProgression,
)
from game_engine.rules.dnd_5_5e.data.class_features.artificer import ARTIFICER_PROGRESSION
from game_engine.rules.dnd_5_5e.data.class_features.barbarian import BARBARIAN_PROGRESSION
from game_engine.rules.dnd_5_5e.data.class_features.bard import BARD_PROGRESSION
from game_engine.rules.dnd_5_5e.data.class_features.cleric import CLERIC_PROGRESSION
from game_engine.rules.dnd_5_5e.data.class_features.druid import DRUID_PROGRESSION
from game_engine.rules.dnd_5_5e.data.class_features.fighter import FIGHTER_PROGRESSION
from game_engine.rules.dnd_5_5e.data.class_features.monk import MONK_PROGRESSION
from game_engine.rules.dnd_5_5e.data.class_features.paladin import PALADIN_PROGRESSION
from game_engine.rules.dnd_5_5e.data.class_features.ranger import RANGER_PROGRESSION
from game_engine.rules.dnd_5_5e.data.class_features.rogue import ROGUE_PROGRESSION
from game_engine.rules.dnd_5_5e.data.class_features.sorcerer import SORCERER_PROGRESSION
from game_engine.rules.dnd_5_5e.data.class_features.warlock import WARLOCK_PROGRESSION
from game_engine.rules.dnd_5_5e.data.class_features.wizard import WIZARD_PROGRESSION
from game_engine.types import CharacterClass

CLASS_PROGRESSIONS: dict[CharacterClass, ClassProgression] = {
    p.character_class: p
    for p in [
        ARTIFICER_PROGRESSION,
        BARBARIAN_PROGRESSION,
        BARD_PROGRESSION,
        CLERIC_PROGRESSION,
        DRUID_PROGRESSION,
        FIGHTER_PROGRESSION,
        MONK_PROGRESSION,
        PALADIN_PROGRESSION,
        RANGER_PROGRESSION,
        ROGUE_PROGRESSION,
        SORCERER_PROGRESSION,
        WARLOCK_PROGRESSION,
        WIZARD_PROGRESSION,
    ]
}


def get_progression(character_class: CharacterClass) -> ClassProgression:
    """Return the progression table for *character_class*."""
    return CLASS_PROGRESSIONS[character_class]


__all__ = [
    "ClassFeatureData",
    "ClassProgression",
    "CLASS_PROGRESSIONS",
    "get_progression",
]
