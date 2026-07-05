"""
Schema for per-class progression tables (2024 PHB chapter 3).

Internal module — import via
:mod:`game_engine.rules.dnd_5_5e.data.class_features`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from game_engine.types import Ability, CharacterClass, ClassResource, SpellcasterType, Subclass


@dataclass(frozen=True)
class ClassFeatureData:
    """A single class (or subclass) feature gained at a given level."""

    name: str
    level: int
    description: str
    subclass: Subclass | None = None  # None = base-class feature
    attacks_granted: int | None = None  # Extra Attack: attacks per Attack action


@dataclass(frozen=True)
class ClassProgression:
    """Full level 1-20 progression for one class.

    Resource tables are 20-entry lists indexed by ``level - 1``.
    ``cantrips_known`` / ``prepared_spells`` are None for non-casters.
    """

    character_class: CharacterClass
    features: list[ClassFeatureData]
    resources: dict[ClassResource, list[int]] = field(default_factory=dict)
    spellcaster_type: SpellcasterType = SpellcasterType.NONE
    spellcasting_ability: Ability | None = None
    cantrips_known: list[int] | None = None
    prepared_spells: list[int] | None = None

    def features_at_level(
        self, level: int, subclass: Subclass | None = None
    ) -> list[ClassFeatureData]:
        """Return features gained at exactly *level* (base + chosen subclass)."""
        return [
            f
            for f in self.features
            if f.level == level and (f.subclass is None or f.subclass == subclass)
        ]

    def features_through_level(
        self, level: int, subclass: Subclass | None = None
    ) -> list[ClassFeatureData]:
        """Return all features available at *level* (base + chosen subclass)."""
        return [
            f
            for f in self.features
            if f.level <= level and (f.subclass is None or f.subclass == subclass)
        ]

    def resource_at_level(self, resource: ClassResource, level: int) -> int:
        """Return the value of *resource* at *level* (0 if untracked)."""
        table = self.resources.get(resource)
        if table is None or not 1 <= level <= 20:
            return 0
        return table[level - 1]
