"""
Typed dataclasses for the game engine.

These structured objects represent characters, combat state, and attack
details in a fully typed, enum-keyed format for use by the rule engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from game_engine.types.enums import (
    Ability,
    CharacterClass,
    CharacterType,
    Condition,
    DamageType,
    Skill,
)
from game_engine.types.values import DiceNotation


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
        return int(getattr(self, ability.value))

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

        def _safe_enum(enum_cls: type, value: str) -> bool:
            try:
                enum_cls(value)
                return True
            except ValueError:
                return False

        def _conditions(key: str) -> list[Condition]:
            return [
                Condition(c.lower()) for c in d.get(key, []) if _safe_enum(Condition, c.lower())
            ]

        def _damage_types(key: str) -> list[DamageType]:
            return [
                DamageType(t.lower()) for t in d.get(key, []) if _safe_enum(DamageType, t.lower())
            ]

        profs = d.get("proficiencies", [])
        skills = [Skill(p.lower()) for p in profs if _safe_enum(Skill, p.lower())]
        abilities = [Ability(p.lower()) for p in profs if _safe_enum(Ability, p.lower())]

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
    damage_dice: DiceNotation = DiceNotation("1d4")
    damage_type: DamageType = DamageType.BLUDGEONING
    attack_ability: Ability = Ability.STRENGTH
    is_ranged: bool = False
