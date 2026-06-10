"""D&D 5.5e species data (SRD 5.2 / 2024 PHB chapter 4)."""

from __future__ import annotations

from dataclasses import dataclass, field

from game_engine.types import CreatureSize, CreatureType, DamageType, Species


@dataclass(frozen=True)
class SpeciesTraitData:
    """A named species trait with display text."""

    name: str
    description: str


@dataclass(frozen=True)
class SpeciesData:
    """Typed species definition."""

    species: Species
    creature_type: CreatureType
    size_options: list[CreatureSize]
    speed: int
    darkvision_ft: int
    traits: list[SpeciesTraitData] = field(default_factory=list)
    damage_resistances: list[DamageType] = field(default_factory=list)
    description: str = ""


SPECIES: dict[Species, SpeciesData] = {}


def get_species(species: Species) -> SpeciesData | None:
    """Look up species data; None if not registered."""
    return SPECIES.get(species)
