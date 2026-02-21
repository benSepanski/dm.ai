"""D&D 5.5e (2024 Player's Handbook) rule engine."""

from game_engine.rules.dnd_5_5e.engine import DnD55eEngine
from game_engine.rules.dnd_5_5e._checks import SKILL_ABILITY_MAP, _calc_prof_bonus
from game_engine.rules.dnd_5_5e._damage import _apply_damage_impl
from game_engine.rules.dnd_5_5e._conditions import (
    _apply_condition_impl,
    _remove_condition_impl,
)
from game_engine.rules.dnd_5_5e._actions import (
    _get_available_actions_impl,
    _resolve_action_impl,
)
from game_engine.rules.dnd_5_5e._validation import _validate_character_impl

__all__ = [
    "DnD55eEngine",
    "SKILL_ABILITY_MAP",
    "_calc_prof_bonus",
    "_apply_damage_impl",
    "_apply_condition_impl",
    "_remove_condition_impl",
    "_get_available_actions_impl",
    "_resolve_action_impl",
    "_validate_character_impl",
]
