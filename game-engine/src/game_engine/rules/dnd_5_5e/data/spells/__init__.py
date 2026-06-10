"""
D&D 5.5e spell registry (SRD 5.2 content), organised by spell level.
"""

from game_engine.rules.dnd_5_5e.data.spells._base import SpellData
from game_engine.rules.dnd_5_5e.data.spells.cantrips import CANTRIPS
from game_engine.rules.dnd_5_5e.data.spells.level1 import LEVEL_1_SPELLS
from game_engine.rules.dnd_5_5e.data.spells.level2 import LEVEL_2_SPELLS
from game_engine.rules.dnd_5_5e.data.spells.level3 import LEVEL_3_SPELLS
from game_engine.rules.dnd_5_5e.data.spells.level4 import LEVEL_4_SPELLS
from game_engine.rules.dnd_5_5e.data.spells.level5 import LEVEL_5_SPELLS
from game_engine.rules.dnd_5_5e.data.spells.level6 import LEVEL_6_SPELLS
from game_engine.rules.dnd_5_5e.data.spells.level7 import LEVEL_7_SPELLS
from game_engine.rules.dnd_5_5e.data.spells.level8 import LEVEL_8_SPELLS
from game_engine.rules.dnd_5_5e.data.spells.level9 import LEVEL_9_SPELLS

SPELLS: list[SpellData] = (
    CANTRIPS
    + LEVEL_1_SPELLS
    + LEVEL_2_SPELLS
    + LEVEL_3_SPELLS
    + LEVEL_4_SPELLS
    + LEVEL_5_SPELLS
    + LEVEL_6_SPELLS
    + LEVEL_7_SPELLS
    + LEVEL_8_SPELLS
    + LEVEL_9_SPELLS
)

SPELLS_BY_NAME: dict[str, SpellData] = {s.name.lower(): s for s in SPELLS}


def get_spell(name: str) -> SpellData | None:
    """Look up a spell by case-insensitive name; None if unknown."""
    return SPELLS_BY_NAME.get(name.lower())


__all__ = [
    "SpellData",
    "SPELLS",
    "SPELLS_BY_NAME",
    "get_spell",
]
