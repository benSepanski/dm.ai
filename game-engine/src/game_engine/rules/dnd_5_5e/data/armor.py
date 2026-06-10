"""D&D 5.5e armor data (2024 PHB armor table, SRD 5.2 content)."""

from __future__ import annotations

from dataclasses import dataclass

from game_engine.types import ArmorCategory


@dataclass(frozen=True)
class ArmorData:
    """Typed armor definition."""

    name: str
    armor_type: ArmorCategory
    base_ac: int
    dex_bonus: bool
    dex_cap: int | None
    min_strength: int
    stealth_disadvantage: bool
    weight_lb: float
    cost_gp: float


ARMOR: list[ArmorData] = []

ARMOR_BY_NAME: dict[str, ArmorData] = {a.name.lower(): a for a in ARMOR}


def get_armor(name: str) -> ArmorData | None:
    """Look up armor by case-insensitive name; None if unknown."""
    return ARMOR_BY_NAME.get(name.lower())


def compute_armor_class(armor: ArmorData | None, dex_modifier: int, shield: bool = False) -> int:
    """Return AC for *armor* worn with *dex_modifier* (no class features).

    Unarmored AC is ``10 + dex``. Shields add +2.
    """
    if armor is None:
        ac = 10 + dex_modifier
    elif armor.dex_bonus:
        dex = dex_modifier if armor.dex_cap is None else min(dex_modifier, armor.dex_cap)
        ac = armor.base_ac + dex
    else:
        ac = armor.base_ac
    return ac + (2 if shield else 0)
