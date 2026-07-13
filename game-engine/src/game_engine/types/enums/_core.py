"""
Core rules enums: abilities, skills, damage, conditions, creatures, magic.

Internal module — import via :mod:`game_engine.types.enums`.
"""

from __future__ import annotations

from enum import Enum


class Ability(str, Enum):
    """The six core D&D ability scores."""

    STRENGTH = "strength"
    DEXTERITY = "dexterity"
    CONSTITUTION = "constitution"
    INTELLIGENCE = "intelligence"
    WISDOM = "wisdom"
    CHARISMA = "charisma"

    def modifier(self, score: int) -> int:
        """Return the D&D modifier for the given ability score."""
        return (score - 10) // 2

    @property
    def short(self) -> str:
        """Return the three-letter abbreviation (e.g. 'str', 'dex')."""
        return self.value[:3]


class Skill(str, Enum):
    """All D&D 5e skills."""

    ACROBATICS = "acrobatics"
    ANIMAL_HANDLING = "animal handling"
    ARCANA = "arcana"
    ATHLETICS = "athletics"
    DECEPTION = "deception"
    HISTORY = "history"
    INSIGHT = "insight"
    INTIMIDATION = "intimidation"
    INVESTIGATION = "investigation"
    MEDICINE = "medicine"
    NATURE = "nature"
    PERCEPTION = "perception"
    PERFORMANCE = "performance"
    PERSUASION = "persuasion"
    RELIGION = "religion"
    SLEIGHT_OF_HAND = "sleight of hand"
    STEALTH = "stealth"
    SURVIVAL = "survival"

    @property
    def governing_ability(self) -> "Ability":
        """Return the ability score that governs this skill."""
        return _SKILL_ABILITY_MAP[self]


_SKILL_ABILITY_MAP: dict[Skill, Ability] = {
    Skill.ACROBATICS: Ability.DEXTERITY,
    Skill.ANIMAL_HANDLING: Ability.WISDOM,
    Skill.ARCANA: Ability.INTELLIGENCE,
    Skill.ATHLETICS: Ability.STRENGTH,
    Skill.DECEPTION: Ability.CHARISMA,
    Skill.HISTORY: Ability.INTELLIGENCE,
    Skill.INSIGHT: Ability.WISDOM,
    Skill.INTIMIDATION: Ability.CHARISMA,
    Skill.INVESTIGATION: Ability.INTELLIGENCE,
    Skill.MEDICINE: Ability.WISDOM,
    Skill.NATURE: Ability.INTELLIGENCE,
    Skill.PERCEPTION: Ability.WISDOM,
    Skill.PERFORMANCE: Ability.CHARISMA,
    Skill.PERSUASION: Ability.CHARISMA,
    Skill.RELIGION: Ability.INTELLIGENCE,
    Skill.SLEIGHT_OF_HAND: Ability.DEXTERITY,
    Skill.STEALTH: Ability.DEXTERITY,
    Skill.SURVIVAL: Ability.WISDOM,
}


class DamageType(str, Enum):
    """Standard D&D damage types."""

    ACID = "acid"
    BLUDGEONING = "bludgeoning"
    COLD = "cold"
    FIRE = "fire"
    FORCE = "force"
    LIGHTNING = "lightning"
    NECROTIC = "necrotic"
    PIERCING = "piercing"
    POISON = "poison"
    PSYCHIC = "psychic"
    RADIANT = "radiant"
    SLASHING = "slashing"
    THUNDER = "thunder"


class Condition(str, Enum):
    """Standard D&D conditions."""

    BLINDED = "blinded"
    CHARMED = "charmed"
    DEAFENED = "deafened"
    EXHAUSTION = "exhaustion"
    FRIGHTENED = "frightened"
    GRAPPLED = "grappled"
    INCAPACITATED = "incapacitated"
    INVISIBLE = "invisible"
    PARALYZED = "paralyzed"
    PETRIFIED = "petrified"
    POISONED = "poisoned"
    PRONE = "prone"
    RESTRAINED = "restrained"
    STUNNED = "stunned"
    UNCONSCIOUS = "unconscious"

    @classmethod
    def prevents_action(cls, condition: "Condition") -> bool:
        """Return True if *condition* prevents the character from acting."""
        return condition in _ACTION_BLOCKING_CONDITIONS

    @classmethod
    def sets_speed_to_zero(cls, condition: "Condition") -> bool:
        """Return True if *condition* reduces the creature's speed to 0."""
        return condition in _SPEED_ZERO_CONDITIONS


_ACTION_BLOCKING_CONDITIONS: frozenset[Condition] = frozenset(
    {
        Condition.INCAPACITATED,
        Condition.PARALYZED,
        Condition.PETRIFIED,
        Condition.STUNNED,
        Condition.UNCONSCIOUS,
    }
)

_SPEED_ZERO_CONDITIONS: frozenset[Condition] = frozenset(
    {
        Condition.GRAPPLED,
        Condition.PARALYZED,
        Condition.PETRIFIED,
        Condition.RESTRAINED,
        Condition.UNCONSCIOUS,
    }
)


class AdvantageType(str, Enum):
    """Whether a roll has advantage or disadvantage."""

    ADVANTAGE = "advantage"
    DISADVANTAGE = "disadvantage"


class CreatureSize(str, Enum):
    """Standard D&D creature sizes."""

    TINY = "Tiny"
    SMALL = "Small"
    MEDIUM = "Medium"
    LARGE = "Large"
    HUGE = "Huge"
    GARGANTUAN = "Gargantuan"


class CreatureType(str, Enum):
    """Standard D&D creature types."""

    ABERRATION = "aberration"
    BEAST = "beast"
    CELESTIAL = "celestial"
    CONSTRUCT = "construct"
    DRAGON = "dragon"
    ELEMENTAL = "elemental"
    FEY = "fey"
    FIEND = "fiend"
    GIANT = "giant"
    HUMANOID = "humanoid"
    MONSTROSITY = "monstrosity"
    OOZE = "ooze"
    PLANT = "plant"
    UNDEAD = "undead"


class SpellSchool(str, Enum):
    """Schools of magic in D&D 5.5e."""

    ABJURATION = "abjuration"
    CONJURATION = "conjuration"
    DIVINATION = "divination"
    ENCHANTMENT = "enchantment"
    EVOCATION = "evocation"
    ILLUSION = "illusion"
    NECROMANCY = "necromancy"
    TRANSMUTATION = "transmutation"


class SpellComponent(str, Enum):
    """Spell components: verbal, somatic, material."""

    VERBAL = "V"
    SOMATIC = "S"
    MATERIAL = "M"


class AreaShape(str, Enum):
    """Areas of effect for spells and abilities (2024 PHB)."""

    CONE = "cone"
    CUBE = "cube"
    CYLINDER = "cylinder"
    EMANATION = "emanation"
    LINE = "line"
    SPHERE = "sphere"


class CastingTime(str, Enum):
    """Standard spell casting times."""

    ACTION = "1 action"
    BONUS_ACTION = "1 bonus action"
    REACTION = "1 reaction"
    ONE_MINUTE = "1 minute"
    TEN_MINUTES = "10 minutes"
    ONE_HOUR = "1 hour"
    EIGHT_HOURS = "8 hours"
    TWELVE_HOURS = "12 hours"
    TWENTY_FOUR_HOURS = "24 hours"


class TaskDifficulty(str, Enum):
    """Typical difficulty classes for d20 tests (2024 PHB chapter 1)."""

    VERY_EASY = "very easy"
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    VERY_HARD = "very hard"
    NEARLY_IMPOSSIBLE = "nearly impossible"

    @property
    def dc(self) -> int:
        """Return the typical DC for this difficulty."""
        return _TASK_DIFFICULTY_DCS[self]


class LightLevel(str, Enum):
    """Illumination levels (2024 PHB chapter 1)."""

    BRIGHT = "bright"
    DIM = "dim"  # lightly obscured: disadvantage on sight-based Perception
    DARKNESS = "darkness"  # heavily obscured: effectively blinded


class SpellRangeType(str, Enum):
    """How a spell's range is expressed."""

    SELF = "self"
    TOUCH = "touch"
    RANGED = "ranged"  # numeric range in feet
    SIGHT = "sight"
    UNLIMITED = "unlimited"


_TASK_DIFFICULTY_DCS: dict[TaskDifficulty, int] = {
    TaskDifficulty.VERY_EASY: 5,
    TaskDifficulty.EASY: 10,
    TaskDifficulty.MEDIUM: 15,
    TaskDifficulty.HARD: 20,
    TaskDifficulty.VERY_HARD: 25,
    TaskDifficulty.NEARLY_IMPOSSIBLE: 30,
}
