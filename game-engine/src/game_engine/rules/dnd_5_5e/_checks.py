"""
D&D 5.5e skill/ability check and initiative implementations.

Internal module — import via :class:`DnD55eEngine`.
"""

from __future__ import annotations

from game_engine.core.dice import roll_dice, roll_with_advantage, roll_with_disadvantage
from game_engine.interface import CheckResult
from game_engine.types import Ability, CharacterSheet, Condition, Skill, TurnState

# Conditions that impose disadvantage on ability checks (2024 PHB).
# Frightened technically requires line of sight to the fear source; the
# engine has no positional model, so it is applied unconditionally.
_CHECK_DISADVANTAGE_CONDITIONS: frozenset[Condition] = frozenset(
    {Condition.POISONED, Condition.FRIGHTENED}
)

# ---------------------------------------------------------------------------
# Skill → ability map (includes raw ability checks)
# ---------------------------------------------------------------------------

# Built from the canonical Skill enum so a new skill added to enums.py is
# automatically picked up here — no second place to update.
SKILL_ABILITY_MAP: dict[str, Ability] = {skill.value: skill.governing_ability for skill in Skill}
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


def _passive_score_impl(char: CharacterSheet, skill: Skill) -> int:
    """Return the passive score for *skill*: 10 + all check modifiers.

    Args:
        char: Character sheet.
        skill: The skill (e.g. ``Skill.PERCEPTION`` for Passive Perception).

    Returns:
        Integer passive score.
    """
    total = 10 + char.ability_scores.modifier(skill.governing_ability)
    prof_bonus = _calc_prof_bonus(char.level)
    if char.is_proficient(skill):
        total += prof_bonus
    if char.has_expertise(skill):
        total += prof_bonus
    return total + char.d20_modifier


def _roll_initiative_impl(char: CharacterSheet) -> int:
    """Roll the raw d20 for initiative, honoring check-disadvantage conditions.

    The caller (``DnD55eEngine.roll_initiative``) adds the DEX modifier and
    the exhaustion ``d20_modifier``, and returns the final total.
    Tie-breaking in combat uses the raw DEX score directly, not a separate
    raw-roll value.

    Args:
        char: Character sheet — consulted for Poisoned/Frightened
            disadvantage (initiative is a Dexterity check).

    Returns:
        Raw d20 roll (1-20), without any modifier applied.
    """
    if any(c in _CHECK_DISADVANTAGE_CONDITIONS for c in char.conditions):
        raw, _ = roll_with_disadvantage(20)
    else:
        raw, _ = roll_dice(1, 20)
    return raw


def _roll_check_impl(
    char: CharacterSheet,
    skill: Skill | Ability | str,
    dc: int,
    advantage: bool = False,
    disadvantage: bool = False,
    turn_state: TurnState | None = None,
) -> CheckResult:
    """Roll a skill or ability check against *dc*.

    Args:
        char: Character sheet.
        skill: Skill or ability enum, or a name string (case-insensitive).
        dc: Difficulty class (integer).
        advantage: Roll twice and take the higher result.
        disadvantage: Roll twice and take the lower result.
        turn_state: The roller's :class:`TurnState`, if this check happens in
            combat. When ``turn_state.helped`` is set (2024 Help action —
            "advantage on their next roll"), it grants advantage here and is
            consumed, mirroring the attack-roll path in ``_attacks.py``.

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

    # Proficiency check: only *skill* proficiency grants a bonus on a check.
    # `CharacterSheet.proficient_abilities` records saving-throw proficiency
    # (see `_saves.py`) and must never leak into a raw ability check.
    try:
        skill_key_enum = Skill(skill_key)
    except ValueError:
        skill_key_enum = None
    is_proficient = skill_key_enum is not None and char.is_proficient(skill_key_enum)
    total_mod = ability_mod + (prof_bonus if is_proficient else 0)
    # Expertise doubles the proficiency bonus.
    if skill_key_enum is not None and char.has_expertise(skill_key_enum):
        total_mod += prof_bonus
    # Exhaustion: flat -2 per level on every d20 test (2024 rules).
    total_mod += char.d20_modifier

    # Poisoned/frightened impose disadvantage on ability checks.
    if any(c in _CHECK_DISADVANTAGE_CONDITIONS for c in char.conditions):
        disadvantage = True

    # Help (2024 PHB): advantage on the helped character's next roll, of
    # any kind — consumed here just as the attack path consumes it.
    if turn_state is not None and turn_state.helped:
        advantage = True
        turn_state.helped = False

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
