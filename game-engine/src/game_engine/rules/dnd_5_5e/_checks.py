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

#: Maps every D&D 5e skill to its governing ability score.
SKILL_ABILITY_MAP: dict[str, Ability] = {
    # Skills
    "acrobatics": Ability.DEXTERITY,
    "animal handling": Ability.WISDOM,
    "arcana": Ability.INTELLIGENCE,
    "athletics": Ability.STRENGTH,
    "deception": Ability.CHARISMA,
    "history": Ability.INTELLIGENCE,
    "insight": Ability.WISDOM,
    "intimidation": Ability.CHARISMA,
    "investigation": Ability.INTELLIGENCE,
    "medicine": Ability.WISDOM,
    "nature": Ability.INTELLIGENCE,
    "perception": Ability.WISDOM,
    "performance": Ability.CHARISMA,
    "persuasion": Ability.CHARISMA,
    "religion": Ability.INTELLIGENCE,
    "sleight of hand": Ability.DEXTERITY,
    "stealth": Ability.DEXTERITY,
    "survival": Ability.WISDOM,
    # Raw ability checks
    "strength": Ability.STRENGTH,
    "dexterity": Ability.DEXTERITY,
    "constitution": Ability.CONSTITUTION,
    "intelligence": Ability.INTELLIGENCE,
    "wisdom": Ability.WISDOM,
    "charisma": Ability.CHARISMA,
    # Short-form ability names
    "str": Ability.STRENGTH,
    "dex": Ability.DEXTERITY,
    "con": Ability.CONSTITUTION,
    "int": Ability.INTELLIGENCE,
    "wis": Ability.WISDOM,
    "cha": Ability.CHARISMA,
}


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
    """Roll initiative: d20 + Dexterity modifier.

    Args:
        char: Character sheet.

    Returns:
        Integer initiative total.
    """
    dex_mod = char.ability_scores.modifier(Ability.DEXTERITY)
    raw, _ = roll_dice(1, 20)
    return raw + dex_mod


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
    is_proficient = char.is_proficient(
        Skill(skill_key) if skill_key in Skill._value2member_map_ else ability
    )
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
