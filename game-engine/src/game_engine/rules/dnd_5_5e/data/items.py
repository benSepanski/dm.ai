"""D&D 5.5e SRD item data — weapons and armor."""

from __future__ import annotations

from dataclasses import dataclass, field

from game_engine.types import DamageType


@dataclass
class WeaponData:
    name: str
    damage_dice: str
    damage_type: DamageType
    properties: list[str]       # ["finesse", "light", "thrown", etc.]
    range_normal_ft: int | None
    range_long_ft: int | None
    weight_lb: float
    cost_gp: float
    two_handed: bool


@dataclass
class ArmorData:
    name: str
    armor_type: str             # "light", "medium", "heavy", "shield"
    base_ac: int
    dex_bonus: bool
    dex_cap: int | None         # None = no cap
    min_strength: int
    stealth_disadvantage: bool
    weight_lb: float
    cost_gp: float


# ── Weapons ───────────────────────────────────────────────────────────────────

WEAPONS: list[WeaponData] = [
    # Simple Melee
    WeaponData(
        name="Club", damage_dice="1d4", damage_type=DamageType.BLUDGEONING,
        properties=["light"], range_normal_ft=None, range_long_ft=None,
        weight_lb=2.0, cost_gp=0.1, two_handed=False,
    ),
    WeaponData(
        name="Dagger", damage_dice="1d4", damage_type=DamageType.PIERCING,
        properties=["finesse", "light", "thrown"],
        range_normal_ft=20, range_long_ft=60,
        weight_lb=1.0, cost_gp=2.0, two_handed=False,
    ),
    WeaponData(
        name="Quarterstaff", damage_dice="1d6", damage_type=DamageType.BLUDGEONING,
        properties=["versatile"],
        range_normal_ft=None, range_long_ft=None,
        weight_lb=4.0, cost_gp=0.2, two_handed=False,
    ),
    WeaponData(
        name="Spear", damage_dice="1d6", damage_type=DamageType.PIERCING,
        properties=["thrown", "versatile"],
        range_normal_ft=20, range_long_ft=60,
        weight_lb=3.0, cost_gp=1.0, two_handed=False,
    ),
    WeaponData(
        name="Javelin", damage_dice="1d6", damage_type=DamageType.PIERCING,
        properties=["thrown"],
        range_normal_ft=30, range_long_ft=120,
        weight_lb=2.0, cost_gp=0.5, two_handed=False,
    ),
    WeaponData(
        name="Mace", damage_dice="1d6", damage_type=DamageType.BLUDGEONING,
        properties=[],
        range_normal_ft=None, range_long_ft=None,
        weight_lb=4.0, cost_gp=5.0, two_handed=False,
    ),
    # Simple Ranged
    WeaponData(
        name="Shortbow", damage_dice="1d6", damage_type=DamageType.PIERCING,
        properties=["ammunition", "two-handed"],
        range_normal_ft=80, range_long_ft=320,
        weight_lb=2.0, cost_gp=25.0, two_handed=True,
    ),
    WeaponData(
        name="Light Crossbow", damage_dice="1d8", damage_type=DamageType.PIERCING,
        properties=["ammunition", "loading", "two-handed"],
        range_normal_ft=80, range_long_ft=320,
        weight_lb=5.0, cost_gp=25.0, two_handed=True,
    ),
    # Martial Melee
    WeaponData(
        name="Shortsword", damage_dice="1d6", damage_type=DamageType.PIERCING,
        properties=["finesse", "light"],
        range_normal_ft=None, range_long_ft=None,
        weight_lb=2.0, cost_gp=10.0, two_handed=False,
    ),
    WeaponData(
        name="Rapier", damage_dice="1d8", damage_type=DamageType.PIERCING,
        properties=["finesse"],
        range_normal_ft=None, range_long_ft=None,
        weight_lb=2.0, cost_gp=25.0, two_handed=False,
    ),
    WeaponData(
        name="Scimitar", damage_dice="1d6", damage_type=DamageType.SLASHING,
        properties=["finesse", "light"],
        range_normal_ft=None, range_long_ft=None,
        weight_lb=3.0, cost_gp=25.0, two_handed=False,
    ),
    WeaponData(
        name="Longsword", damage_dice="1d8", damage_type=DamageType.SLASHING,
        properties=["versatile"],
        range_normal_ft=None, range_long_ft=None,
        weight_lb=3.0, cost_gp=15.0, two_handed=False,
    ),
    WeaponData(
        name="Battleaxe", damage_dice="1d8", damage_type=DamageType.SLASHING,
        properties=["versatile"],
        range_normal_ft=None, range_long_ft=None,
        weight_lb=4.0, cost_gp=10.0, two_handed=False,
    ),
    WeaponData(
        name="Warhammer", damage_dice="1d8", damage_type=DamageType.BLUDGEONING,
        properties=["versatile"],
        range_normal_ft=None, range_long_ft=None,
        weight_lb=2.0, cost_gp=15.0, two_handed=False,
    ),
    WeaponData(
        name="Flail", damage_dice="1d8", damage_type=DamageType.BLUDGEONING,
        properties=[],
        range_normal_ft=None, range_long_ft=None,
        weight_lb=2.0, cost_gp=10.0, two_handed=False,
    ),
    WeaponData(
        name="Whip", damage_dice="1d4", damage_type=DamageType.SLASHING,
        properties=["finesse", "reach"],
        range_normal_ft=None, range_long_ft=None,
        weight_lb=3.0, cost_gp=2.0, two_handed=False,
    ),
    WeaponData(
        name="Trident", damage_dice="1d6", damage_type=DamageType.PIERCING,
        properties=["thrown", "versatile"],
        range_normal_ft=20, range_long_ft=60,
        weight_lb=4.0, cost_gp=5.0, two_handed=False,
    ),
    WeaponData(
        name="Handaxe", damage_dice="1d6", damage_type=DamageType.SLASHING,
        properties=["light", "thrown"],
        range_normal_ft=20, range_long_ft=60,
        weight_lb=2.0, cost_gp=5.0, two_handed=False,
    ),
    WeaponData(
        name="Lance", damage_dice="1d12", damage_type=DamageType.PIERCING,
        properties=["reach", "special"],
        range_normal_ft=None, range_long_ft=None,
        weight_lb=6.0, cost_gp=10.0, two_handed=False,
    ),
    WeaponData(
        name="Glaive", damage_dice="1d10", damage_type=DamageType.SLASHING,
        properties=["heavy", "reach", "two-handed"],
        range_normal_ft=None, range_long_ft=None,
        weight_lb=6.0, cost_gp=20.0, two_handed=True,
    ),
    WeaponData(
        name="Greatsword", damage_dice="2d6", damage_type=DamageType.SLASHING,
        properties=["heavy", "two-handed"],
        range_normal_ft=None, range_long_ft=None,
        weight_lb=6.0, cost_gp=50.0, two_handed=True,
    ),
    WeaponData(
        name="Greataxe", damage_dice="1d12", damage_type=DamageType.SLASHING,
        properties=["heavy", "two-handed"],
        range_normal_ft=None, range_long_ft=None,
        weight_lb=7.0, cost_gp=30.0, two_handed=True,
    ),
    # Martial Ranged
    WeaponData(
        name="Longbow", damage_dice="1d8", damage_type=DamageType.PIERCING,
        properties=["ammunition", "heavy", "two-handed"],
        range_normal_ft=150, range_long_ft=600,
        weight_lb=2.0, cost_gp=50.0, two_handed=True,
    ),
    WeaponData(
        name="Hand Crossbow", damage_dice="1d6", damage_type=DamageType.PIERCING,
        properties=["ammunition", "light", "loading"],
        range_normal_ft=30, range_long_ft=120,
        weight_lb=3.0, cost_gp=75.0, two_handed=False,
    ),
    WeaponData(
        name="Heavy Crossbow", damage_dice="1d10", damage_type=DamageType.PIERCING,
        properties=["ammunition", "heavy", "loading", "two-handed"],
        range_normal_ft=100, range_long_ft=400,
        weight_lb=18.0, cost_gp=50.0, two_handed=True,
    ),
]

# ── Armor ─────────────────────────────────────────────────────────────────────

ARMOR: list[ArmorData] = [
    # Light
    ArmorData(
        name="Leather",
        armor_type="light", base_ac=11, dex_bonus=True, dex_cap=None,
        min_strength=0, stealth_disadvantage=False,
        weight_lb=10.0, cost_gp=10.0,
    ),
    ArmorData(
        name="Studded Leather",
        armor_type="light", base_ac=12, dex_bonus=True, dex_cap=None,
        min_strength=0, stealth_disadvantage=False,
        weight_lb=13.0, cost_gp=45.0,
    ),
    # Medium
    ArmorData(
        name="Hide",
        armor_type="medium", base_ac=12, dex_bonus=True, dex_cap=2,
        min_strength=0, stealth_disadvantage=False,
        weight_lb=12.0, cost_gp=10.0,
    ),
    ArmorData(
        name="Chain Shirt",
        armor_type="medium", base_ac=13, dex_bonus=True, dex_cap=2,
        min_strength=0, stealth_disadvantage=False,
        weight_lb=20.0, cost_gp=50.0,
    ),
    ArmorData(
        name="Scale Mail",
        armor_type="medium", base_ac=14, dex_bonus=True, dex_cap=2,
        min_strength=0, stealth_disadvantage=True,
        weight_lb=45.0, cost_gp=50.0,
    ),
    ArmorData(
        name="Breastplate",
        armor_type="medium", base_ac=14, dex_bonus=True, dex_cap=2,
        min_strength=0, stealth_disadvantage=False,
        weight_lb=20.0, cost_gp=400.0,
    ),
    ArmorData(
        name="Half Plate",
        armor_type="medium", base_ac=15, dex_bonus=True, dex_cap=2,
        min_strength=0, stealth_disadvantage=True,
        weight_lb=40.0, cost_gp=750.0,
    ),
    # Heavy
    ArmorData(
        name="Ring Mail",
        armor_type="heavy", base_ac=14, dex_bonus=False, dex_cap=0,
        min_strength=0, stealth_disadvantage=True,
        weight_lb=40.0, cost_gp=30.0,
    ),
    ArmorData(
        name="Chain Mail",
        armor_type="heavy", base_ac=16, dex_bonus=False, dex_cap=0,
        min_strength=13, stealth_disadvantage=True,
        weight_lb=55.0, cost_gp=75.0,
    ),
    ArmorData(
        name="Splint",
        armor_type="heavy", base_ac=17, dex_bonus=False, dex_cap=0,
        min_strength=15, stealth_disadvantage=True,
        weight_lb=60.0, cost_gp=200.0,
    ),
    ArmorData(
        name="Plate",
        armor_type="heavy", base_ac=18, dex_bonus=False, dex_cap=0,
        min_strength=15, stealth_disadvantage=True,
        weight_lb=65.0, cost_gp=1500.0,
    ),
    # Shield
    ArmorData(
        name="Shield",
        armor_type="shield", base_ac=2, dex_bonus=False, dex_cap=None,
        min_strength=0, stealth_disadvantage=False,
        weight_lb=6.0, cost_gp=10.0,
    ),
]
