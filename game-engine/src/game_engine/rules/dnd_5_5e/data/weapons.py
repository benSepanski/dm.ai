"""D&D 5.5e weapon data (2024 PHB weapon table, SRD 5.2 content)."""

from __future__ import annotations

from dataclasses import dataclass, field

from game_engine.types import (
    DamageType,
    DiceNotation,
    WeaponCategory,
    WeaponMastery,
    WeaponProperty,
)


@dataclass(frozen=True)
class WeaponData:
    """Typed weapon definition (2024 PHB, including mastery property)."""

    name: str
    category: WeaponCategory
    is_melee: bool
    damage_dice: DiceNotation
    damage_type: DamageType
    mastery: WeaponMastery
    properties: list[WeaponProperty] = field(default_factory=list)
    versatile_dice: DiceNotation | None = None
    range_normal_ft: int | None = None
    range_long_ft: int | None = None
    weight_lb: float = 0.0
    cost_gp: float = 0.0

    @property
    def two_handed(self) -> bool:
        return WeaponProperty.TWO_HANDED in self.properties


WEAPONS: list[WeaponData] = []

WEAPONS_BY_NAME: dict[str, WeaponData] = {w.name.lower(): w for w in WEAPONS}


def get_weapon(name: str) -> WeaponData | None:
    """Look up a weapon by case-insensitive name; None if unknown."""
    return WEAPONS_BY_NAME.get(name.lower())
