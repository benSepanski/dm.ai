"""D&D 5.5e Sorcerer class progression (2024 rules)."""

from __future__ import annotations

from game_engine.rules.dnd_5_5e.data.class_features._base import ClassProgression
from game_engine.types import CharacterClass

SORCERER_PROGRESSION = ClassProgression(
    character_class=CharacterClass.SORCERER,
    features=[],
)
