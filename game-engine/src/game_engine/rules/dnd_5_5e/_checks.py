"""
D&D 5.5e skill/ability check and initiative implementations.

Internal module — import via :class:`DnD55eEngine`.
"""

from __future__ import annotations

from game_engine.core.dice import roll_dice, roll_with_advantage, roll_with_disadvantage
from game_engine.interface import CheckResult
from game_engine.types import Ability, CharacterSheet, Skill

# ---------------------------------------------------------------------------
# Skill → ability map (includes raw ability checks)
# ---------------------------------------------------------------------------

# Built from the canonical Skill enum so a new skill added to enums.py is
# automatically picked up here — no second place to update.
SKILL_ABILITY_MAP: dict[str, Ability] = {
    skill.value: skill.governing_ability for skill in Skill
}
# Raw ability name lookups (full and 3-letter short form).
SKILL_ABILITY_MAP.update({ability.value: ability for ability in Ability})
SKILL_ABILITY_MAP.update({ability.short: ability for ability in Ability})


def _calc_prof_bonus(level: int) -> int:
    """Return the proficiency bonus for *level* (1-20).

    Args:
        level: Character level.

    Returns:
        Proficiency bonus: +2 (1-4), +3 (5-8), +4 (9-12), +5 (13-16), +6 (17-20).

    Raises:
        ValueError: If *level* is outside 1-20.
    """
    if not 1 <= level <= 20:
        raise ValueError(f"Level must be between 1 and 20, got {level}.")
    return 2 + (level - 1) // 4


def _roll_initiative_impl(char: CharacterSheet) -> int:
    """Roll the raw d20 for initiative.

    The caller (``DnD55eEngine.roll_initiative``) adds the DEX modifier to
    produce the final total; this function returns only the raw roll so the
    engine can expose both values if needed (e.g., for tie-breaking storage).

    Args:
        char: Character sheet (unused here; retained for interface symmetry).

    Returns:
        Raw d20 roll (1-20), without any modifier applied.
    """
    raw, _ = roll_dice(1, 20)
    return raw


def _roll_check_impl(
    char: CharacterSheet,
    skill: Skill | Ability | str,
    dc: int,
    advantage: bool = False,
    disadvantage: bool = False,
) -> CheckResult:
    """Roll a skill or ability check against *dc*.

    Args:
        char: Character sheet.
        skill: Skill or ability enum, or a name string (case-insensitive).
        dc: Difficulty class (integer).
        advantage: Roll twice and take the higher result.
        disadvantage: Roll twice and take the lower result.

    Returns:
        :class:`~game_engine.interface.CheckResult`.

    Raises:
        ValueError: If *skill* is not recognised.
    """
    # Resolve skill/ability key
    if isinstance(skill, Skill):
        ability = skill.governing_ability
        skill_key = skill.value
    elif isinstance(skill, Ability):
        ability = skill
        skill_key = skill.value
    else:
        skill_key = skill.lower()
        resolved = SKILL_ABILITY_MAP.get(skill_key)
        if resolved is None:
            raise ValueError(
                f"Unknown skill or ability {skill!r}.  "
                f"Valid skills: {sorted(SKILL_ABILITY_MAP.keys())}"
            )
        ability = resolved

    ability_mod = char.ability_scores.modifier(ability)
    prof_bonus = _calc_prof_bonus(char.level)

    # Proficiency check: match against skill name or ability name
    try:
        proficiency_key: Skill | Ability = Skill(skill_key)
    except ValueError:
        proficiency_key = ability
    is_proficient = char.is_proficient(proficiency_key)
    total_mod = ability_mod + (prof_bonus if is_proficient else 0)

    # Roll d20
    if advantage and not disadvantage:
        raw_roll, _ = roll_with_advantage(20)
    elif disadvantage and not advantage:
        raw_roll, _ = roll_with_disadvantage(20)
    else:
        raw_roll, _ = roll_dice(1, 20)

    total = raw_roll + total_mod
    return CheckResult(
        success=total >= dc,
        roll=raw_roll,
        total=total,
        dc=dc,
        margin=total - dc,
    )
