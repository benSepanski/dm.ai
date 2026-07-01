"""Pydantic schemas for the character-creation API.

Typed boundary between the HTTP layer and the game-engine character
builder: every option list mirrors an engine registry dataclass, and the
build request maps 1:1 onto :func:`game_engine.rules.dnd_5_5e.build_character`
parameters. No raw-string domain fields — everything with a finite value
set is the engine enum itself.
"""

from __future__ import annotations

import uuid

from game_engine.types import (
    Ability,
    AbilityScoreSet,
    Alignment,
    ArmorCategory,
    Background,
    CharacterClass,
    CreatureSize,
    CreatureType,
    DamageType,
    Feat,
    Language,
    Skill,
    Species,
    SpeciesLineage,
    SpellSchool,
    WeaponCategory,
    WeaponProperty,
)
from pydantic import BaseModel, Field

from dm_api.db.models.character import CharacterRead


class ClassOptionRead(BaseModel):
    """Creation-relevant view of an engine ``ClassData`` entry."""

    character_class: CharacterClass
    hit_die: int
    primary_abilities: list[Ability]
    saving_throw_proficiencies: list[Ability]
    armor_training: list[ArmorCategory]
    weapon_category_training: list[WeaponCategory]
    skill_choices: list[Skill]
    num_skill_choices: int
    spellcasting: bool
    weapon_mastery_count: int
    cantrips_known: int
    prepared_spells_known: int


class WeaponMasteryOption(BaseModel):
    """A choosable weapon for mastery selection during character creation."""

    name: str
    category: WeaponCategory
    mastery_property: str
    is_melee: bool
    properties: list[WeaponProperty]


class SpeciesTraitChoiceRead(BaseModel):
    """Closed option set for a species trait requiring a player pick."""

    skill_options: list[Skill] = Field(default_factory=list)
    lineage_options: list[SpeciesLineage] = Field(default_factory=list)


class SpeciesTraitRead(BaseModel):
    name: str
    description: str
    choice: SpeciesTraitChoiceRead | None = None


class SpeciesOptionRead(BaseModel):
    """Creation-relevant view of an engine ``SpeciesData`` entry."""

    species: Species
    creature_type: CreatureType
    size_options: list[CreatureSize]
    speed: int
    darkvision_ft: int
    traits: list[SpeciesTraitRead]
    damage_resistances: list[DamageType]
    description: str


class SpellOptionRead(BaseModel):
    """Creation-relevant view of an engine ``SpellData`` entry."""

    name: str
    level: int
    school: SpellSchool
    classes: list[CharacterClass]
    description: str


class BackgroundOptionRead(BaseModel):
    """Creation-relevant view of an engine ``BackgroundData`` entry."""

    background: Background
    ability_scores: list[Ability]
    skill_proficiencies: list[Skill]
    tool_proficiency: str
    origin_feat: Feat
    equipment: list[str]
    description: str


class ArmorOptionRead(BaseModel):
    """Creation-relevant view of an engine ``ArmorData`` entry."""

    name: str
    armor_type: ArmorCategory
    base_ac: int
    dex_bonus: bool
    dex_cap: int | None
    stealth_disadvantage: bool


class SkillOptionRead(BaseModel):
    skill: Skill
    governing_ability: Ability


class CreationOptionsRead(BaseModel):
    """Everything the creation UI needs, sourced from the engine registries."""

    classes: list[ClassOptionRead]
    species: list[SpeciesOptionRead]
    backgrounds: list[BackgroundOptionRead]
    armor: list[ArmorOptionRead]
    skills: list[SkillOptionRead]
    languages: list[Language]
    alignments: list[Alignment]
    standard_array: list[int]
    point_buy_budget: int
    point_buy_costs: dict[int, int]
    weapon_mastery_options: list[WeaponMasteryOption]
    spells: list[SpellOptionRead]


class AbilityScoresWrite(BaseModel):
    """The six base scores BEFORE background increases (3-20 each)."""

    strength: int = Field(ge=3, le=20)
    dexterity: int = Field(ge=3, le=20)
    constitution: int = Field(ge=3, le=20)
    intelligence: int = Field(ge=3, le=20)
    wisdom: int = Field(ge=3, le=20)
    charisma: int = Field(ge=3, le=20)

    def to_engine(self) -> AbilityScoreSet:
        return AbilityScoreSet(**self.model_dump())


class CharacterBuildRequest(BaseModel):
    """Request body for building a level-1 PC via the rule engine."""

    world_id: uuid.UUID
    # When the PC is created from inside a live session, the session id lets the
    # server broadcast a roster update so other connected clients (players) see
    # the new character without a manual refresh.
    session_id: uuid.UUID | None = None
    name: str = Field(min_length=1, max_length=255)
    character_class: CharacterClass
    species: Species
    background: Background
    ability_scores: AbilityScoresWrite
    skill_choices: list[Skill]
    background_ability_allocation: dict[Ability, int] | None = None
    languages: list[Language] | None = None
    armor_name: str | None = None
    shield: bool = False
    alignment: Alignment | None = None
    weapon_masteries: list[str] | None = None
    species_trait_choices: dict[str, str] | None = None
    starting_cantrips: list[str] | None = None
    starting_spells: list[str] | None = None


class CharacterBuildRead(BaseModel):
    """The persisted character plus non-fatal warnings from the engine."""

    character: CharacterRead
    warnings: list[str]
