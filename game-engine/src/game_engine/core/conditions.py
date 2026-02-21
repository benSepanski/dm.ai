"""
D&D condition definitions and helper utilities.

Provides mechanical effect data for all 15 standard conditions as well as
exhaustion levels, and helper functions to query a character's condition state.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from game_engine.types import Ability, CharacterSheet, Condition, DamageType

# ---------------------------------------------------------------------------
# ConditionEffect dataclass
# ---------------------------------------------------------------------------


@dataclass
class ConditionEffect:
    """Mechanical effects associated with a single D&D condition.

    Attributes:
        description: Plain-English summary of the condition.
        can_act: Whether the creature can take actions/reactions.
        attack_modifier: ``"advantage"``, ``"disadvantage"``, or ``None``.
        attack_against_modifier: Modifier on rolls *against* this creature.
        auto_fail_saves: Abilities that auto-fail saves while in this condition.
        speed_zero: Whether the condition sets movement speed to 0.
        immunity_types: Damage types the creature is immune to (condition-based).
    """

    description: str = ""
    can_act: bool = True
    attack_modifier: str | None = None
    attack_against_modifier: str | None = None
    auto_fail_saves: list[Ability] = field(default_factory=list)
    speed_zero: bool = False
    immunity_types: list[DamageType] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Condition effect data
# ---------------------------------------------------------------------------

#: Mechanical effects for each of the 15 standard D&D conditions.
CONDITION_EFFECTS: dict[Condition, ConditionEffect] = {
    Condition.BLINDED: ConditionEffect(
        description=(
            "A blinded creature can't see and automatically fails any ability "
            "check that requires sight. Attack rolls against the creature have "
            "advantage, and the creature's attack rolls have disadvantage."
        ),
        can_act=True,
        attack_modifier="disadvantage",
        attack_against_modifier="advantage",
    ),
    Condition.CHARMED: ConditionEffect(
        description=(
            "A charmed creature can't attack the charmer or target the charmer "
            "with harmful abilities or magical effects. The charmer has advantage "
            "on ability checks to interact socially with the creature."
        ),
        can_act=True,
    ),
    Condition.DEAFENED: ConditionEffect(
        description=(
            "A deafened creature can't hear and automatically fails any ability "
            "check that requires hearing."
        ),
        can_act=True,
    ),
    Condition.EXHAUSTION: ConditionEffect(
        description=(
            "Exhaustion is measured in six levels. An exhausted creature suffers "
            "cumulative penalties based on its exhaustion level."
        ),
        can_act=True,
    ),
    Condition.FRIGHTENED: ConditionEffect(
        description=(
            "A frightened creature has disadvantage on ability checks and attack "
            "rolls while the source of its fear is within line of sight. The "
            "creature can't willingly move closer to the source of its fear."
        ),
        can_act=True,
        attack_modifier="disadvantage",
    ),
    Condition.GRAPPLED: ConditionEffect(
        description=(
            "A grappled creature's speed becomes 0, and it can't benefit from "
            "any bonus to its speed. The condition ends if the grappler is "
            "incapacitated. It also ends if an effect removes the grappled "
            "creature from the reach of the grappler or grappling effect."
        ),
        can_act=True,
        speed_zero=True,
    ),
    Condition.INCAPACITATED: ConditionEffect(
        description="An incapacitated creature can't take actions or reactions.",
        can_act=False,
    ),
    Condition.INVISIBLE: ConditionEffect(
        description=(
            "An invisible creature is impossible to see without the aid of magic "
            "or a special sense. The creature's attacks have advantage, and attack "
            "rolls against the creature have disadvantage."
        ),
        can_act=True,
        attack_modifier="advantage",
        attack_against_modifier="disadvantage",
    ),
    Condition.PARALYZED: ConditionEffect(
        description=(
            "A paralyzed creature is incapacitated and can't move or speak. It "
            "automatically fails Strength and Dexterity saving throws. Attack "
            "rolls against the creature have advantage. Any attack that hits the "
            "creature is a critical hit if the attacker is within 5 feet."
        ),
        can_act=False,
        attack_against_modifier="advantage",
        auto_fail_saves=[Ability.STRENGTH, Ability.DEXTERITY],
        speed_zero=True,
    ),
    Condition.PETRIFIED: ConditionEffect(
        description=(
            "A petrified creature is transformed, along with any nonmagical object "
            "it is wearing or carrying, into a solid inanimate substance (usually "
            "stone). Its weight increases by a factor of ten, and it ceases aging. "
            "It is incapacitated, can't move or speak, and is unaware of its "
            "surroundings. Attack rolls against the creature have advantage. It "
            "automatically fails Strength and Dexterity saving throws. It has "
            "resistance to all damage."
        ),
        can_act=False,
        attack_against_modifier="advantage",
        auto_fail_saves=[Ability.STRENGTH, Ability.DEXTERITY],
        speed_zero=True,
        immunity_types=[DamageType.POISON, DamageType.PSYCHIC],
    ),
    Condition.POISONED: ConditionEffect(
        description=("A poisoned creature has disadvantage on attack rolls and ability checks."),
        can_act=True,
        attack_modifier="disadvantage",
    ),
    Condition.PRONE: ConditionEffect(
        description=(
            "A prone creature's only movement option is to crawl. An attack roll "
            "against the creature has advantage if the attacker is within 5 feet, "
            "otherwise the attack roll has disadvantage. The creature has "
            "disadvantage on attack rolls."
        ),
        can_act=True,
        attack_modifier="disadvantage",
        attack_against_modifier="advantage",  # within 5 ft; disadvantage beyond
    ),
    Condition.RESTRAINED: ConditionEffect(
        description=(
            "A restrained creature's speed becomes 0. Attack rolls against it have "
            "advantage, and its attack rolls have disadvantage. It has disadvantage "
            "on Dexterity saving throws."
        ),
        can_act=True,
        attack_modifier="disadvantage",
        attack_against_modifier="advantage",
        speed_zero=True,
    ),
    Condition.STUNNED: ConditionEffect(
        description=(
            "A stunned creature is incapacitated, can't move, and can speak only "
            "falteringly. It automatically fails Strength and Dexterity saving "
            "throws. Attack rolls against it have advantage."
        ),
        can_act=False,
        attack_against_modifier="advantage",
        auto_fail_saves=[Ability.STRENGTH, Ability.DEXTERITY],
        speed_zero=True,
    ),
    Condition.UNCONSCIOUS: ConditionEffect(
        description=(
            "An unconscious creature is incapacitated, can't move or speak, and "
            "is unaware of its surroundings. It drops whatever it's holding and "
            "falls prone. It automatically fails Strength and Dexterity saving "
            "throws. Attack rolls against the creature have advantage. Any attack "
            "that hits the creature is a critical hit if the attacker is within "
            "5 feet of the creature."
        ),
        can_act=False,
        attack_against_modifier="advantage",
        auto_fail_saves=[Ability.STRENGTH, Ability.DEXTERITY],
        speed_zero=True,
    ),
}

#: Exhaustion levels 1-6 and their mechanical penalties.
EXHAUSTION_LEVELS: list[dict] = [
    {
        "level": 1,
        "penalty": "Disadvantage on ability checks.",
        "ability_check_disadvantage": True,
        "speed_halved": False,
        "attack_save_disadvantage": False,
        "max_hp_halved": False,
        "speed_zero": False,
        "death": False,
    },
    {
        "level": 2,
        "penalty": "Speed halved.",
        "ability_check_disadvantage": True,
        "speed_halved": True,
        "attack_save_disadvantage": False,
        "max_hp_halved": False,
        "speed_zero": False,
        "death": False,
    },
    {
        "level": 3,
        "penalty": "Disadvantage on attack rolls and saving throws.",
        "ability_check_disadvantage": True,
        "speed_halved": True,
        "attack_save_disadvantage": True,
        "max_hp_halved": False,
        "speed_zero": False,
        "death": False,
    },
    {
        "level": 4,
        "penalty": "Hit point maximum halved.",
        "ability_check_disadvantage": True,
        "speed_halved": True,
        "attack_save_disadvantage": True,
        "max_hp_halved": True,
        "speed_zero": False,
        "death": False,
    },
    {
        "level": 5,
        "penalty": "Speed reduced to 0.",
        "ability_check_disadvantage": True,
        "speed_halved": True,
        "attack_save_disadvantage": True,
        "max_hp_halved": True,
        "speed_zero": True,
        "death": False,
    },
    {
        "level": 6,
        "penalty": "Death.",
        "ability_check_disadvantage": True,
        "speed_halved": True,
        "attack_save_disadvantage": True,
        "max_hp_halved": True,
        "speed_zero": True,
        "death": True,
    },
]


# ---------------------------------------------------------------------------
# Helper functions (typed)
# ---------------------------------------------------------------------------


def is_immune_to_condition(char: CharacterSheet, condition: Condition | str) -> bool:
    """Return True if *char* is immune to *condition*.

    Args:
        char: Character sheet.
        condition: The condition enum or name (case-insensitive).

    Returns:
        True if the character is immune to the condition.
    """
    if isinstance(condition, str):
        try:
            condition = Condition(condition.lower())
        except ValueError:
            return False

    return condition in char.condition_immunities


def get_active_conditions(char: CharacterSheet) -> list[Condition]:
    """Return the list of conditions currently affecting *char*.

    Args:
        char: Character sheet.

    Returns:
        List of active :class:`~game_engine.types.Condition` values.
    """
    return list(char.conditions)


def condition_prevents_action(char: CharacterSheet) -> bool:
    """Return True if any active condition prevents the character from acting.

    Args:
        char: Character sheet.

    Returns:
        True if the character cannot take actions.
    """
    return not char.can_act
