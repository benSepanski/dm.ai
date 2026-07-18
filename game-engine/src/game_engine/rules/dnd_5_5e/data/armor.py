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


ARMOR: list[ArmorData] = [
    # --- Light armor ---
    ArmorData(
        name="Padded Armor",
        armor_type=ArmorCategory.LIGHT,
        base_ac=11,
        dex_bonus=True,
        dex_cap=None,
        min_strength=0,
        stealth_disadvantage=True,
        weight_lb=8.0,
        cost_gp=5.0,
    ),
    ArmorData(
        name="Leather Armor",
        armor_type=ArmorCategory.LIGHT,
        base_ac=11,
        dex_bonus=True,
        dex_cap=None,
        min_strength=0,
        stealth_disadvantage=False,
        weight_lb=10.0,
        cost_gp=10.0,
    ),
    ArmorData(
        name="Studded Leather Armor",
        armor_type=ArmorCategory.LIGHT,
        base_ac=12,
        dex_bonus=True,
        dex_cap=None,
        min_strength=0,
        stealth_disadvantage=False,
        weight_lb=13.0,
        cost_gp=45.0,
    ),
    # --- Medium armor ---
    ArmorData(
        name="Hide Armor",
        armor_type=ArmorCategory.MEDIUM,
        base_ac=12,
        dex_bonus=True,
        dex_cap=2,
        min_strength=0,
        stealth_disadvantage=False,
        weight_lb=12.0,
        cost_gp=10.0,
    ),
    ArmorData(
        name="Chain Shirt",
        armor_type=ArmorCategory.MEDIUM,
        base_ac=13,
        dex_bonus=True,
        dex_cap=2,
        min_strength=0,
        stealth_disadvantage=False,
        weight_lb=20.0,
        cost_gp=50.0,
    ),
    ArmorData(
        name="Scale Mail",
        armor_type=ArmorCategory.MEDIUM,
        base_ac=14,
        dex_bonus=True,
        dex_cap=2,
        min_strength=0,
        stealth_disadvantage=True,
        weight_lb=45.0,
        cost_gp=50.0,
    ),
    ArmorData(
        name="Breastplate",
        armor_type=ArmorCategory.MEDIUM,
        base_ac=14,
        dex_bonus=True,
        dex_cap=2,
        min_strength=0,
        stealth_disadvantage=False,
        weight_lb=20.0,
        cost_gp=400.0,
    ),
    ArmorData(
        name="Half Plate Armor",
        armor_type=ArmorCategory.MEDIUM,
        base_ac=15,
        dex_bonus=True,
        dex_cap=2,
        min_strength=0,
        stealth_disadvantage=True,
        weight_lb=40.0,
        cost_gp=750.0,
    ),
    # --- Heavy armor ---
    ArmorData(
        name="Ring Mail",
        armor_type=ArmorCategory.HEAVY,
        base_ac=14,
        dex_bonus=False,
        dex_cap=0,
        min_strength=0,
        stealth_disadvantage=True,
        weight_lb=40.0,
        cost_gp=30.0,
    ),
    ArmorData(
        name="Chain Mail",
        armor_type=ArmorCategory.HEAVY,
        base_ac=16,
        dex_bonus=False,
        dex_cap=0,
        min_strength=13,
        stealth_disadvantage=True,
        weight_lb=55.0,
        cost_gp=75.0,
    ),
    ArmorData(
        name="Splint Armor",
        armor_type=ArmorCategory.HEAVY,
        base_ac=17,
        dex_bonus=False,
        dex_cap=0,
        min_strength=15,
        stealth_disadvantage=True,
        weight_lb=60.0,
        cost_gp=200.0,
    ),
    ArmorData(
        name="Plate Armor",
        armor_type=ArmorCategory.HEAVY,
        base_ac=18,
        dex_bonus=False,
        dex_cap=0,
        min_strength=15,
        stealth_disadvantage=True,
        weight_lb=65.0,
        cost_gp=1500.0,
    ),
    # --- Shield ---
    ArmorData(
        name="Shield",
        armor_type=ArmorCategory.SHIELD,
        base_ac=2,
        dex_bonus=False,
        dex_cap=0,
        min_strength=0,
        stealth_disadvantage=False,
        weight_lb=6.0,
        cost_gp=10.0,
    ),
]

ARMOR_BY_NAME: dict[str, ArmorData] = {a.name.lower(): a for a in ARMOR}


def get_armor(name: str) -> ArmorData | None:
    """Look up armor by case-insensitive name; None if unknown."""
    return ARMOR_BY_NAME.get(name.lower())


def compute_armor_class(armor: ArmorData | None, dex_modifier: int, shield: bool = False) -> int:
    """Return AC for *armor* worn with *dex_modifier* (no class features).

    Unarmored AC is ``10 + dex``. Shields add +2.

    Raises:
        ValueError: If *armor* is a shield (``ArmorCategory.SHIELD``). A shield
            is worn *in addition to* body armor via the ``shield`` flag, not
            passed as the body armor itself (EQP-06) — doing so previously
            yielded a nonsensical AC of 2.
    """
    if armor is not None and armor.armor_type is ArmorCategory.SHIELD:
        raise ValueError(
            f"{armor.name!r} is a shield, not body armor; pass shield=True instead "
            "of supplying it as the worn armor."
        )
    if armor is None:
        ac = 10 + dex_modifier
    elif armor.dex_bonus:
        dex = dex_modifier if armor.dex_cap is None else min(dex_modifier, armor.dex_cap)
        ac = armor.base_ac + dex
    else:
        ac = armor.base_ac
    return ac + (2 if shield else 0)
