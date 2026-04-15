"""
D&D 5.5e SRD data modules.

Re-exports the main data lists and dataclasses for convenience.
"""

from game_engine.rules.dnd_5_5e.data.items import ARMOR, WEAPONS, ArmorData, WeaponData
from game_engine.rules.dnd_5_5e.data.monsters import MONSTERS, MonsterAction, MonsterData
from game_engine.rules.dnd_5_5e.data.spells import SPELLS, SpellData

__all__ = [
    "SPELLS",
    "SpellData",
    "MONSTERS",
    "MonsterData",
    "MonsterAction",
    "WEAPONS",
    "ARMOR",
    "WeaponData",
    "ArmorData",
]
