"""D&D 5.5e (2024 Player's Handbook) rule engine."""

from game_engine.rules.dnd_5_5e._spell_resolution import cast_spell
from game_engine.rules.dnd_5_5e.character_builder import (
    STANDARD_ARRAY,
    BuildResult,
    build_character,
    is_standard_array,
    is_valid_point_buy,
    point_buy_cost,
)
from game_engine.rules.dnd_5_5e.classes import CLASSES, ClassData
from game_engine.rules.dnd_5_5e.engine import DnD55eEngine
from game_engine.rules.dnd_5_5e.progression import (
    XP_THRESHOLDS,
    can_multiclass,
    level_for_xp,
    level_up,
    xp_for_level,
)
from game_engine.rules.dnd_5_5e.resting import RestResult, long_rest, short_rest, spend_hit_die
from game_engine.rules.dnd_5_5e.spellcasting import (
    SpellCastResult,
    SpellTargetOutcome,
    compute_spell_slots,
    spell_attack_bonus,
    spell_save_dc,
)

__all__ = [
    "DnD55eEngine",
    # class data
    "CLASSES",
    "ClassData",
    # creation & advancement
    "STANDARD_ARRAY",
    "BuildResult",
    "build_character",
    "is_standard_array",
    "is_valid_point_buy",
    "point_buy_cost",
    "XP_THRESHOLDS",
    "can_multiclass",
    "level_for_xp",
    "level_up",
    "xp_for_level",
    # spellcasting
    "cast_spell",
    "SpellCastResult",
    "SpellTargetOutcome",
    "compute_spell_slots",
    "spell_attack_bonus",
    "spell_save_dc",
    # resting
    "RestResult",
    "long_rest",
    "short_rest",
    "spend_hit_die",
]
