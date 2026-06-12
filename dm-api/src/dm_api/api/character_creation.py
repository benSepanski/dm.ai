"""Character-creation endpoints backed by the 2024 PHB rule engine.

``GET /options`` serves the engine's data registries (classes, species,
backgrounds, armor, …) so the UI never hard-codes game data, and
``POST /build`` runs :func:`build_character` and persists the resulting
sheet — the engine is the single source of truth for creation rules.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from game_engine.rules.dnd_5_5e import (
    CLASSES,
    POINT_BUY_BUDGET,
    POINT_BUY_COSTS,
    STANDARD_ARRAY,
    build_character,
)
from game_engine.rules.dnd_5_5e.data.armor import ARMOR
from game_engine.rules.dnd_5_5e.data.backgrounds import BACKGROUNDS
from game_engine.rules.dnd_5_5e.data.species import SPECIES
from game_engine.types import Alignment, ArmorCategory, CharacterType, Language, Skill
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dm_api.api.character_creation_schemas import (
    ArmorOptionRead,
    BackgroundOptionRead,
    CharacterBuildRead,
    CharacterBuildRequest,
    ClassOptionRead,
    CreationOptionsRead,
    SkillOptionRead,
    SpeciesOptionRead,
    SpeciesTraitRead,
)
from dm_api.db.models.character import Character, CharacterRead
from dm_api.db.models.world import World
from dm_api.db.session import get_db

router = APIRouter()


def _creation_options() -> CreationOptionsRead:
    """Assemble the full options payload from the engine registries."""
    return CreationOptionsRead(
        classes=[
            ClassOptionRead(
                character_class=data.character_class,
                hit_die=data.hit_die,
                primary_abilities=data.primary_abilities,
                saving_throw_proficiencies=data.saving_throw_proficiencies,
                armor_training=data.armor_training,
                weapon_category_training=data.weapon_category_training,
                skill_choices=data.skill_choices,
                num_skill_choices=data.num_skill_choices,
                spellcasting=data.spellcasting,
            )
            for data in CLASSES.values()
        ],
        species=[
            SpeciesOptionRead(
                species=data.species,
                creature_type=data.creature_type,
                size_options=data.size_options,
                speed=data.speed,
                darkvision_ft=data.darkvision_ft,
                traits=[
                    SpeciesTraitRead(name=t.name, description=t.description) for t in data.traits
                ],
                damage_resistances=data.damage_resistances,
                description=data.description,
            )
            for data in SPECIES.values()
        ],
        backgrounds=[
            BackgroundOptionRead(
                background=data.background,
                ability_scores=data.ability_scores,
                skill_proficiencies=data.skill_proficiencies,
                tool_proficiency=data.tool_proficiency,
                origin_feat=data.origin_feat,
                equipment=data.equipment,
                description=data.description,
            )
            for data in BACKGROUNDS.values()
        ],
        armor=[
            ArmorOptionRead(
                name=a.name,
                armor_type=a.armor_type,
                base_ac=a.base_ac,
                dex_bonus=a.dex_bonus,
                dex_cap=a.dex_cap,
                stealth_disadvantage=a.stealth_disadvantage,
            )
            for a in ARMOR
            if a.armor_type is not ArmorCategory.SHIELD  # shield is the `shield` flag
        ],
        skills=[SkillOptionRead(skill=s, governing_ability=s.governing_ability) for s in Skill],
        languages=list(Language),
        alignments=list(Alignment),
        standard_array=STANDARD_ARRAY,
        point_buy_budget=POINT_BUY_BUDGET,
        point_buy_costs=POINT_BUY_COSTS,
    )


@router.get("/options", response_model=CreationOptionsRead)
async def get_creation_options() -> CreationOptionsRead:
    """Reference data for the character-creation UI (engine registries)."""
    return _creation_options()


@router.post("/build", response_model=CharacterBuildRead, status_code=status.HTTP_201_CREATED)
async def build_player_character(
    payload: CharacterBuildRequest,
    db: AsyncSession = Depends(get_db),
) -> CharacterBuildRead:
    """Build a level-1 PC with the rule engine and persist it.

    The engine applies background ability increases, proficiencies, HP, AC,
    and spell slots; rule-bending choices (off-list skills, untrained armor)
    come back as non-fatal ``warnings`` rather than errors.
    """
    world_result = await db.execute(select(World).where(World.id == payload.world_id))
    if world_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="World not found")

    char_id = uuid.uuid4()
    result = build_character(
        char_id=str(char_id),
        name=payload.name,
        character_class=payload.character_class,
        species=payload.species,
        background=payload.background,
        ability_scores=payload.ability_scores.to_engine(),
        skill_choices=payload.skill_choices,
        background_ability_allocation=payload.background_ability_allocation,
        languages=payload.languages,
        armor_name=payload.armor_name,
        shield=payload.shield,
        alignment=payload.alignment,
        char_type=CharacterType.PC,
    )
    sheet = result.sheet

    equipment = list(BACKGROUNDS[payload.background].equipment)
    if payload.armor_name:
        equipment.append(payload.armor_name)
    if payload.shield:
        equipment.append("Shield")

    character = Character(
        id=char_id,
        world_id=payload.world_id,
        type=CharacterType.PC,
        name=payload.name,
        race=payload.species.value,
        char_class=payload.character_class.value,
        level=1,
        alignment=payload.alignment.value if payload.alignment else None,
        stats=sheet.to_dict(),
        hp_current=sheet.hp_current,
        hp_max=sheet.hp_max,
        ac=sheet.ac,
        speed=sheet.speed,
        equipment=equipment,
    )
    db.add(character)
    await db.commit()
    await db.refresh(character)
    return CharacterBuildRead(
        character=CharacterRead.model_validate(character),
        warnings=result.warnings,
    )
