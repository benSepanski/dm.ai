"""
D&D 5.5e saving throw implementation.

Internal module — import via :class:`DnD55eEngine`.
"""

from __future__ import annotations

from game_engine.core.conditions import CONDITION_EFFECTS
from game_engine.core.dice import roll_dice, roll_with_advantage, roll_with_disadvantage
from game_engine.interface import SaveResult
from game_engine.rules.dnd_5_5e._checks import _calc_prof_bonus
from game_engine.rules.dnd_5_5e._equipment import is_armor_untrained
from game_engine.types import Ability, CharacterSheet, Condition


def _auto_fails_save(char: CharacterSheet, ability: Ability) -> bool:
    """True when a current condition forces automatic failure of this save."""
    for cond in char.conditions:
        effect = CONDITION_EFFECTS.get(cond)
        if effect is not None and ability in effect.auto_fail_saves:
            return True
    return False


def _roll_saving_throw_impl(
    char: CharacterSheet,
    ability: Ability,
    dc: int,
    advantage: bool = False,
    disadvantage: bool = False,
) -> SaveResult:
    """Roll a saving throw against *dc*.

    Applies (2024 rules):
    - automatic failure of STR/DEX saves while paralyzed, petrified,
      stunned, or unconscious;
    - disadvantage on DEX saves while restrained;
    - disadvantage on STR/DEX saves while wearing untrained armor (D2);
    - save proficiency (proficiency bonus);
    - exhaustion's flat −2/level penalty on all d20 tests.

    Args:
        char: Character sheet.
        ability: Ability being saved with.
        dc: Difficulty class.
        advantage: Roll twice, take higher.
        disadvantage: Roll twice, take lower.

    Returns:
        :class:`~game_engine.interface.SaveResult`.
    """
    if _auto_fails_save(char, ability):
        return SaveResult(success=False, roll=0, total=0, dc=dc, margin=-dc, auto_failed=True)

    if ability is Ability.DEXTERITY and Condition.RESTRAINED in char.conditions:
        disadvantage = True

    # D2/EQP-03: untrained armor imposes disadvantage on STR/DEX saves.
    if ability in (Ability.STRENGTH, Ability.DEXTERITY) and is_armor_untrained(char):
        disadvantage = True

    modifier = char.ability_scores.modifier(ability)
    if char.is_proficient(ability):
        modifier += _calc_prof_bonus(char.level)
    modifier += char.d20_modifier

    if advantage and not disadvantage:
        raw_roll, _ = roll_with_advantage(20)
    elif disadvantage and not advantage:
        raw_roll, _ = roll_with_disadvantage(20)
    else:
        raw_roll, _ = roll_dice(1, 20)

    total = raw_roll + modifier
    return SaveResult(
        success=total >= dc,
        roll=raw_roll,
        total=total,
        dc=dc,
        margin=total - dc,
        auto_failed=False,
    )
