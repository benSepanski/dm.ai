"""
Typed enums and dataclasses for the game engine.

All enums use ``str, Enum`` inheritance so values are wire-compatible
with their string equivalents and support ``Enum(value)`` construction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CharacterClass(str, Enum):
    """Valid D&D 5.5e character classes."""

    ARTIFICER = "Artificer"
    BARBARIAN = "Barbarian"
    BARD = "Bard"
    CLERIC = "Cleric"
    DRUID = "Druid"
    FIGHTER = "Fighter"
    MONK = "Monk"
    PALADIN = "Paladin"
    RANGER = "Ranger"
    ROGUE = "Rogue"
    SORCERER = "Sorcerer"
    WARLOCK = "Warlock"
    WIZARD = "Wizard"

    @classmethod
    def all(cls) -> list["CharacterClass"]:
        return list(cls)


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
        _MAP: dict[Skill, Ability] = {
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
        return _MAP[self]


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
        return condition in {
            cls.INCAPACITATED,
            cls.PARALYZED,
            cls.PETRIFIED,
            cls.STUNNED,
            cls.UNCONSCIOUS,
        }


class ActionType(str, Enum):
    """Combat action types available in D&D 5.5e."""

    ATTACK = "Attack"
    CAST_SPELL = "CastSpell"
    DASH = "Dash"
    DISENGAGE = "Disengage"
    DODGE = "Dodge"
    HELP = "Help"
    HIDE = "Hide"
    READY = "Ready"
    SEARCH = "Search"
    USE_OBJECT = "Use Object"


class CharacterType(str, Enum):
    """Broad classification for a character's role in the game."""

    PC = "PC"
    NPC = "NPC"
    MONSTER = "MONSTER"


class LocationType(str, Enum):
    """Classification for a location in the game world."""

    REALM = "realm"
    COUNTRY = "country"
    REGION = "region"
    TOWN = "town"
    DISTRICT = "district"
    BUILDING = "building"
    ROOM = "room"
    DUNGEON = "dungeon"
    WILDERNESS = "wilderness"


class ProposalType(str, Enum):
    """Type of AI-generated proposal for the DM to review."""

    LOCATION = "location"
    CHARACTER = "character"
    DUNGEON = "dungeon"
    DIALOGUE = "dialogue"
    COMBAT_ACTION = "combat_action"


class ProposalStatus(str, Enum):
    """Current status of an AI proposal."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    MODIFIED = "modified"


class ChatRole(str, Enum):
    """Role of the sender in a chat message."""

    DM = "dm"
    AI = "ai"
    SYSTEM = "system"


# ---------------------------------------------------------------------------
# Typed dataclasses
# ---------------------------------------------------------------------------


@dataclass
class AbilityScoreSet:
    """Typed container for the six D&D ability scores."""

    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10

    def get(self, ability: Ability) -> int:
        """Return the score for *ability*."""
        return getattr(self, ability.value)

    def modifier(self, ability: Ability) -> int:
        """Return the D&D modifier for *ability*."""
        return ability.modifier(self.get(ability))

    def to_dict(self) -> dict[str, int]:
        """Return a JSON-serialisable dict of all six scores."""
        return {a.value: self.get(a) for a in Ability}

    @classmethod
    def from_dict(cls, d: dict) -> "AbilityScoreSet":
        """Create an :class:`AbilityScoreSet` from a dict.

        Accepts both full names (``"strength"``) and short forms (``"str"``).
        """

        def _get(ability: Ability) -> int:
            return int(d.get(ability.value, d.get(ability.short, 10)))

        return cls(**{a.value: _get(a) for a in Ability})


@dataclass
class CharacterSheet:
    """Typed representation of a character for use by the rule engine."""

    id: str
    name: str
    level: int
    char_class: CharacterClass
    ability_scores: AbilityScoreSet = field(default_factory=AbilityScoreSet)
    hp_current: int = 10
    hp_max: int = 10
    ac: int = 10
    speed: int = 30
    proficient_skills: list[Skill] = field(default_factory=list)
    proficient_abilities: list[Ability] = field(default_factory=list)
    conditions: list[Condition] = field(default_factory=list)
    condition_durations: dict[Condition, int] = field(default_factory=dict)
    damage_resistances: list[DamageType] = field(default_factory=list)
    damage_immunities: list[DamageType] = field(default_factory=list)
    damage_vulnerabilities: list[DamageType] = field(default_factory=list)
    condition_immunities: list[Condition] = field(default_factory=list)
    char_type: CharacterType = CharacterType.PC

    @property
    def is_alive(self) -> bool:
        """Return True if the character has more than 0 hit points."""
        return self.hp_current > 0

    @property
    def can_act(self) -> bool:
        """Return True if the character can take actions this turn."""
        if not self.is_alive:
            return False
        return not any(Condition.prevents_action(c) for c in self.conditions)

    def is_proficient(self, skill_or_ability: Skill | Ability) -> bool:
        """Return True if the character is proficient in *skill_or_ability*."""
        if isinstance(skill_or_ability, Skill):
            return skill_or_ability in self.proficient_skills
        return skill_or_ability in self.proficient_abilities

    def to_dict(self) -> dict:
        """Return a JSON-serialisable dict representation of this character."""
        return {
            "id": self.id,
            "name": self.name,
            "level": self.level,
            "class": self.char_class.value,
            "ability_scores": self.ability_scores.to_dict(),
            "hp_current": self.hp_current,
            "hp_max": self.hp_max,
            "ac": self.ac,
            "speed": self.speed,
            "proficiencies": (
                [s.value for s in self.proficient_skills]
                + [a.value for a in self.proficient_abilities]
            ),
            "conditions": [c.value for c in self.conditions],
            "damage_resistances": [d.value for d in self.damage_resistances],
            "damage_immunities": [d.value for d in self.damage_immunities],
            "damage_vulnerabilities": [d.value for d in self.damage_vulnerabilities],
            "condition_immunities": [c.value for c in self.condition_immunities],
            "type": self.char_type.value,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CharacterSheet":
        """Create a :class:`CharacterSheet` from a dict.

        Tolerant of missing keys — uses sensible defaults for everything.
        """

        def _conditions(key: str) -> list[Condition]:
            return [
                Condition(c.lower())
                for c in d.get(key, [])
                if c.lower() in Condition._value2member_map_
            ]

        def _damage_types(key: str) -> list[DamageType]:
            return [
                DamageType(t.lower())
                for t in d.get(key, [])
                if t.lower() in DamageType._value2member_map_
            ]

        profs = d.get("proficiencies", [])
        skills = [
            Skill(p.lower())
            for p in profs
            if p.lower() in Skill._value2member_map_
        ]
        abilities = [
            Ability(p.lower())
            for p in profs
            if p.lower() in Ability._value2member_map_
        ]

        raw_class = d.get("class", "Fighter")
        try:
            char_class = CharacterClass(raw_class)
        except ValueError:
            char_class = CharacterClass.FIGHTER

        raw_type = d.get("type", CharacterType.PC.value)
        try:
            char_type = CharacterType(raw_type)
        except ValueError:
            char_type = CharacterType.PC

        return cls(
            id=d.get("id", ""),
            name=d.get("name", ""),
            level=int(d.get("level", 1)),
            char_class=char_class,
            ability_scores=AbilityScoreSet.from_dict(d.get("ability_scores", {})),
            hp_current=int(d.get("hp_current", 10)),
            hp_max=int(d.get("hp_max", 10)),
            ac=int(d.get("ac", 10)),
            speed=int(d.get("speed", 30)),
            proficient_skills=skills,
            proficient_abilities=abilities,
            conditions=_conditions("conditions"),
            damage_resistances=_damage_types("damage_resistances"),
            damage_immunities=_damage_types("damage_immunities"),
            damage_vulnerabilities=_damage_types("damage_vulnerabilities"),
            condition_immunities=_conditions("condition_immunities"),
            char_type=char_type,
        )


@dataclass
class CombatStateData:
    """Typed combat state for use by the rule engine."""

    combatants: list[CharacterSheet] = field(default_factory=list)
    round_number: int = 1
    current_turn_index: int = 0

    def get_combatant(self, char_id: str) -> CharacterSheet | None:
        """Return the combatant with *char_id*, or None."""
        return next((c for c in self.combatants if c.id == char_id), None)


@dataclass
class AttackDetails:
    """Details for an Attack action."""

    weapon_name: str = "Unarmed Strike"
    damage_dice: str = "1d4"
    damage_type: DamageType = DamageType.BLUDGEONING
    attack_ability: Ability = Ability.STRENGTH
    is_ranged: bool = False
