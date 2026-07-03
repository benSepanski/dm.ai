"""
Typed character dataclasses for the game engine.

``AbilityScoreSet`` and ``CharacterSheet`` — a character's persistent state,
in a fully typed, enum-keyed format for use by the rule engine.
Per-encounter combat state (``TurnState``, ``CombatStateData``,
``AttackDetails``) lives in :mod:`game_engine.types.combat_state`.
Serialisation lives in :mod:`game_engine.types._sheet_serde`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from game_engine.types.character_state import (
    ClassLevelEntry,
    Currency,
    DeathSaveState,
    HitDicePool,
    InventoryItem,
    SpellSlotState,
)
from game_engine.types.enums import (
    Ability,
    Alignment,
    ArmorCategory,
    Background,
    CharacterClass,
    CharacterType,
    Condition,
    DamageType,
    Feat,
    Language,
    Skill,
    Species,
    SpeciesLineage,
    Subclass,
    WeaponCategory,
)


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

    def set(self, ability: Ability, score: int) -> None:
        """Set the score for *ability*."""
        setattr(self, ability.value, score)

    def modifier(self, ability: Ability) -> int:
        """Return the D&D modifier for *ability*."""
        return ability.modifier(self.get(ability))

    def to_dict(self) -> dict[str, int]:
        """Return a JSON-serialisable dict of all six scores."""
        return {a.value: self.get(a) for a in Ability}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "AbilityScoreSet":
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
    # Origin & build (2024 PHB chapters 2-5)
    species: Species | None = None
    species_lineage: SpeciesLineage | None = None
    background: Background | None = None
    alignment: Alignment | None = None
    subclass: Subclass | None = None
    class_levels: list[ClassLevelEntry] = field(default_factory=list)
    xp: int = 0
    feats: list[Feat] = field(default_factory=list)
    languages: list[Language] = field(default_factory=list)
    # Combat state
    temp_hp: int = 0
    hit_dice: list[HitDicePool] = field(default_factory=list)
    death_saves: DeathSaveState = field(default_factory=DeathSaveState)
    exhaustion_level: int = 0
    # Spellcasting state
    spell_slots: list[SpellSlotState] = field(default_factory=list)
    concentrating_on: str | None = None
    known_spells: list[str] = field(default_factory=list)
    prepared_spells: list[str] = field(default_factory=list)
    # Proficiencies & equipment
    expertise_skills: list[Skill] = field(default_factory=list)
    armor_training: list[ArmorCategory] = field(default_factory=list)
    weapon_category_training: list[WeaponCategory] = field(default_factory=list)
    weapon_training: list[str] = field(default_factory=list)
    tool_proficiencies: list[str] = field(default_factory=list)
    weapon_masteries: list[str] = field(default_factory=list)
    inventory: list[InventoryItem] = field(default_factory=list)
    currency: Currency = field(default_factory=Currency)
    darkvision_ft: int = 0

    @property
    def is_dead(self) -> bool:
        """Return True if the character has died (3 failed death saves, etc.)."""
        return self.death_saves.is_dead or self.exhaustion_level >= 6

    @property
    def is_alive(self) -> bool:
        """Return True if the character has more than 0 hit points."""
        return self.hp_current > 0 and not self.is_dead

    @property
    def is_dying(self) -> bool:
        """Return True if the character is at 0 HP, unstable, and not dead."""
        return self.hp_current <= 0 and not self.is_dead and not self.death_saves.is_stable

    @property
    def can_act(self) -> bool:
        """Return True if the character can take actions this turn."""
        if not self.is_alive:
            return False
        return not any(Condition.prevents_action(c) for c in self.conditions)

    @property
    def effective_speed(self) -> int:
        """Walking speed after exhaustion (−5 ft/level) and speed-zero conditions."""
        if any(Condition.sets_speed_to_zero(c) for c in self.conditions):
            return 0
        return max(0, self.speed - 5 * self.exhaustion_level)

    @property
    def d20_modifier(self) -> int:
        """Flat penalty applied to every d20 test (2024 exhaustion: −2/level)."""
        return -2 * self.exhaustion_level

    def class_level(self, character_class: CharacterClass) -> int:
        """Return this character's level in *character_class* (0 if none)."""
        if not self.class_levels:
            return self.level if character_class == self.char_class else 0
        return sum(e.level for e in self.class_levels if e.character_class == character_class)

    def is_proficient(self, skill_or_ability: Skill | Ability) -> bool:
        """Return True if the character is proficient in *skill_or_ability*."""
        if isinstance(skill_or_ability, Skill):
            return skill_or_ability in self.proficient_skills
        return skill_or_ability in self.proficient_abilities

    def has_expertise(self, skill: Skill) -> bool:
        """Return True if the character has expertise (double proficiency)."""
        return skill in self.expertise_skills

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable dict representation of this character."""
        from game_engine.types._sheet_serde import sheet_to_dict

        return sheet_to_dict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "CharacterSheet":
        """Create a :class:`CharacterSheet` from a dict.

        Tolerant of missing keys — uses sensible defaults for everything.
        """
        from game_engine.types._sheet_serde import sheet_from_dict

        return sheet_from_dict(d)
