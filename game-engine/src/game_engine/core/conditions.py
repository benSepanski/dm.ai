"""
D&D condition definitions and helper utilities.

Provides mechanical effect data for all 15 standard conditions as well as
exhaustion levels, and helper functions to query a character's condition state.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Condition data
# ---------------------------------------------------------------------------

#: Mechanical effects for each of the 15 standard D&D conditions.
#:
#: Keys per condition:
#:   description          – plain-English summary of the condition
#:   immunity_types       – damage types the creature is immune to while in
#:                          this condition (rarely used, but e.g. petrified →
#:                          poison is not an immunity here; kept for completeness)
#:   auto_fail_saves      – ability score names that automatically fail saves
#:   attack_modifier      – "advantage", "disadvantage", or "none" on attack rolls
#:   attack_against_modifier – modifier applied to attack rolls *against* this creature
#:   speed_zero           – whether the condition sets movement speed to 0
#:   can_act              – whether the creature can take actions / reactions
CONDITION_EFFECTS: dict[str, dict] = {
    "blinded": {
        "description": (
            "A blinded creature can't see and automatically fails any ability "
            "check that requires sight. Attack rolls against the creature have "
            "advantage, and the creature's attack rolls have disadvantage."
        ),
        "immunity_types": [],
        "auto_fail_saves": [],
        "attack_modifier": "disadvantage",
        "attack_against_modifier": "advantage",
        "speed_zero": False,
        "can_act": True,
    },
    "charmed": {
        "description": (
            "A charmed creature can't attack the charmer or target the charmer "
            "with harmful abilities or magical effects. The charmer has advantage "
            "on ability checks to interact socially with the creature."
        ),
        "immunity_types": [],
        "auto_fail_saves": [],
        "attack_modifier": "none",
        "attack_against_modifier": "none",
        "speed_zero": False,
        "can_act": True,
    },
    "deafened": {
        "description": (
            "A deafened creature can't hear and automatically fails any ability "
            "check that requires hearing."
        ),
        "immunity_types": [],
        "auto_fail_saves": [],
        "attack_modifier": "none",
        "attack_against_modifier": "none",
        "speed_zero": False,
        "can_act": True,
    },
    "exhaustion": {
        "description": (
            "Exhaustion is measured in six levels. An exhausted creature suffers "
            "cumulative penalties based on its exhaustion level."
        ),
        "immunity_types": [],
        "auto_fail_saves": [],
        "attack_modifier": "none",
        "attack_against_modifier": "none",
        "speed_zero": False,  # speed halved at level 2; zero at level 5
        "can_act": True,
    },
    "frightened": {
        "description": (
            "A frightened creature has disadvantage on ability checks and attack "
            "rolls while the source of its fear is within line of sight. The "
            "creature can't willingly move closer to the source of its fear."
        ),
        "immunity_types": [],
        "auto_fail_saves": [],
        "attack_modifier": "disadvantage",
        "attack_against_modifier": "none",
        "speed_zero": False,
        "can_act": True,
    },
    "grappled": {
        "description": (
            "A grappled creature's speed becomes 0, and it can't benefit from "
            "any bonus to its speed. The condition ends if the grappler is "
            "incapacitated. It also ends if an effect removes the grappled "
            "creature from the reach of the grappler or grappling effect."
        ),
        "immunity_types": [],
        "auto_fail_saves": [],
        "attack_modifier": "none",
        "attack_against_modifier": "none",
        "speed_zero": True,
        "can_act": True,
    },
    "incapacitated": {
        "description": (
            "An incapacitated creature can't take actions or reactions."
        ),
        "immunity_types": [],
        "auto_fail_saves": [],
        "attack_modifier": "none",
        "attack_against_modifier": "none",
        "speed_zero": False,
        "can_act": False,
    },
    "invisible": {
        "description": (
            "An invisible creature is impossible to see without the aid of magic "
            "or a special sense. The creature's attacks have advantage, and attack "
            "rolls against the creature have disadvantage."
        ),
        "immunity_types": [],
        "auto_fail_saves": [],
        "attack_modifier": "advantage",
        "attack_against_modifier": "disadvantage",
        "speed_zero": False,
        "can_act": True,
    },
    "paralyzed": {
        "description": (
            "A paralyzed creature is incapacitated and can't move or speak. It "
            "automatically fails Strength and Dexterity saving throws. Attack "
            "rolls against the creature have advantage. Any attack that hits the "
            "creature is a critical hit if the attacker is within 5 feet."
        ),
        "immunity_types": [],
        "auto_fail_saves": ["strength", "dexterity"],
        "attack_modifier": "none",
        "attack_against_modifier": "advantage",
        "speed_zero": True,
        "can_act": False,
    },
    "petrified": {
        "description": (
            "A petrified creature is transformed, along with any nonmagical object "
            "it is wearing or carrying, into a solid inanimate substance (usually "
            "stone). Its weight increases by a factor of ten, and it ceases aging. "
            "It is incapacitated, can't move or speak, and is unaware of its "
            "surroundings. Attack rolls against the creature have advantage. It "
            "automatically fails Strength and Dexterity saving throws. It has "
            "resistance to all damage."
        ),
        "immunity_types": ["poison", "psychic"],
        "auto_fail_saves": ["strength", "dexterity"],
        "attack_modifier": "none",
        "attack_against_modifier": "advantage",
        "speed_zero": True,
        "can_act": False,
    },
    "poisoned": {
        "description": (
            "A poisoned creature has disadvantage on attack rolls and ability checks."
        ),
        "immunity_types": [],
        "auto_fail_saves": [],
        "attack_modifier": "disadvantage",
        "attack_against_modifier": "none",
        "speed_zero": False,
        "can_act": True,
    },
    "prone": {
        "description": (
            "A prone creature's only movement option is to crawl. An attack roll "
            "against the creature has advantage if the attacker is within 5 feet, "
            "otherwise the attack roll has disadvantage. The creature has "
            "disadvantage on attack rolls."
        ),
        "immunity_types": [],
        "auto_fail_saves": [],
        "attack_modifier": "disadvantage",
        "attack_against_modifier": "advantage",  # within 5 ft; disadvantage beyond
        "speed_zero": False,
        "can_act": True,
    },
    "restrained": {
        "description": (
            "A restrained creature's speed becomes 0. Attack rolls against it have "
            "advantage, and its attack rolls have disadvantage. It has disadvantage "
            "on Dexterity saving throws."
        ),
        "immunity_types": [],
        "auto_fail_saves": [],
        "attack_modifier": "disadvantage",
        "attack_against_modifier": "advantage",
        "speed_zero": True,
        "can_act": True,
    },
    "stunned": {
        "description": (
            "A stunned creature is incapacitated, can't move, and can speak only "
            "falteringly. It automatically fails Strength and Dexterity saving "
            "throws. Attack rolls against it have advantage."
        ),
        "immunity_types": [],
        "auto_fail_saves": ["strength", "dexterity"],
        "attack_modifier": "none",
        "attack_against_modifier": "advantage",
        "speed_zero": True,
        "can_act": False,
    },
    "unconscious": {
        "description": (
            "An unconscious creature is incapacitated, can't move or speak, and "
            "is unaware of its surroundings. It drops whatever it's holding and "
            "falls prone. It automatically fails Strength and Dexterity saving "
            "throws. Attack rolls against the creature have advantage. Any attack "
            "that hits the creature is a critical hit if the attacker is within "
            "5 feet of the creature."
        ),
        "immunity_types": [],
        "auto_fail_saves": ["strength", "dexterity"],
        "attack_modifier": "none",
        "attack_against_modifier": "advantage",
        "speed_zero": True,
        "can_act": False,
    },
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
# Helper functions
# ---------------------------------------------------------------------------

#: Conditions that prevent a creature from taking actions.
_INCAPACITATING_CONDITIONS: frozenset[str] = frozenset(
    {
        "incapacitated",
        "paralyzed",
        "petrified",
        "stunned",
        "unconscious",
    }
)


def is_immune_to_condition(char: dict, condition: str) -> bool:
    """Return True if *char* is immune to *condition*.

    Checks the ``condition_immunities`` list on the character sheet dict.

    Args:
        char: Character sheet dict.  May contain ``condition_immunities: list[str]``.
        condition: The condition name to check (case-insensitive).

    Returns:
        True if the character is immune to the condition.
    """
    immunities: list[str] = char.get("condition_immunities", [])
    return condition.lower() in {c.lower() for c in immunities}


def get_active_conditions(char: dict) -> list[str]:
    """Return the list of conditions currently affecting *char*.

    Args:
        char: Character sheet dict.  May contain ``conditions: list[str]``.

    Returns:
        List of active condition name strings (may be empty).
    """
    return list(char.get("conditions", []))


def condition_prevents_action(char: dict) -> bool:
    """Return True if any active condition prevents the character from acting.

    A character cannot act if they have any of the incapacitating conditions:
    incapacitated, paralyzed, petrified, stunned, or unconscious.

    Args:
        char: Character sheet dict.

    Returns:
        True if the character cannot take actions.
    """
    active = {c.lower() for c in get_active_conditions(char)}
    return bool(active & _INCAPACITATING_CONDITIONS)
