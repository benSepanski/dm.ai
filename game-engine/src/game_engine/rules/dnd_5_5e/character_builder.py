"""
D&D 5.5e character creation (2024 PHB chapter 2).

Builds a level-1 :class:`CharacterSheet` from class + species + background
choices, applying background ability score increases, proficiencies, hit
points, armor class, spell slots, and origin feats.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from game_engine.rules.dnd_5_5e.classes import CLASSES
from game_engine.rules.dnd_5_5e.data.armor import compute_armor_class, get_armor
from game_engine.rules.dnd_5_5e.data.backgrounds import get_background
from game_engine.rules.dnd_5_5e.data.species import get_species
from game_engine.types import (
    Ability,
    AbilityScoreSet,
    Alignment,
    Background,
    CharacterClass,
    CharacterSheet,
    CharacterType,
    ClassLevelEntry,
    ClassResource,
    Feat,
    HitDicePool,
    Language,
    Skill,
    Species,
)

#: The standard array of ability scores (2024 PHB chapter 2).
STANDARD_ARRAY: list[int] = [15, 14, 13, 12, 10, 8]

#: Point-buy cost per score (27 points total, scores 8-15).
POINT_BUY_COSTS: dict[int, int] = {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9}

POINT_BUY_BUDGET = 27

# Trait name checked during character creation to apply the HP bonus.
# Matches SpeciesTraitData.name for Dwarf's "Dwarven Toughness" entry.
_TRAIT_DWARVEN_TOUGHNESS = "Dwarven Toughness"


def point_buy_cost(scores: AbilityScoreSet) -> int:
    """Return the total point-buy cost of *scores*.

    Raises:
        ValueError: If any score is outside the 8-15 point-buy range.
    """
    total = 0
    for ability in Ability:
        score = scores.get(ability)
        if score not in POINT_BUY_COSTS:
            raise ValueError(f"{ability.value} = {score} is outside the point-buy range (8-15).")
        total += POINT_BUY_COSTS[score]
    return total


def is_valid_point_buy(scores: AbilityScoreSet) -> bool:
    """True when *scores* is a legal 27-point buy."""
    try:
        return point_buy_cost(scores) <= POINT_BUY_BUDGET
    except ValueError:
        return False


def is_standard_array(scores: AbilityScoreSet) -> bool:
    """True when *scores* is a permutation of the standard array."""
    return sorted(scores.get(a) for a in Ability) == sorted(STANDARD_ARRAY)


@dataclass
class BuildResult:
    """A built character plus any non-fatal warnings about the choices."""

    sheet: CharacterSheet
    warnings: list[str] = field(default_factory=list)


def _apply_background_increases(
    scores: AbilityScoreSet,
    allowed: list[Ability],
    allocation: dict[Ability, int] | None,
    warnings: list[str],
) -> None:
    """Apply the background's +2/+1 (or +1/+1/+1) ability increases."""
    if allocation is None:
        allocation = {allowed[0]: 2, allowed[1]: 1}
    values = sorted(allocation.values(), reverse=True)
    if values not in ([2, 1], [1, 1, 1]):
        warnings.append("Background increases must be +2/+1 or +1/+1/+1; using +2/+1 defaults.")
        allocation = {allowed[0]: 2, allowed[1]: 1}
    for ability, bonus in allocation.items():
        if ability not in allowed:
            warnings.append(f"{ability.value} is not a {len(allowed)}-option background ability.")
        scores.set(ability, min(20, scores.get(ability) + bonus))


def build_character(
    char_id: str,
    name: str,
    character_class: CharacterClass,
    species: Species,
    background: Background,
    ability_scores: AbilityScoreSet,
    skill_choices: list[Skill],
    background_ability_allocation: dict[Ability, int] | None = None,
    languages: list[Language] | None = None,
    armor_name: str | None = None,
    shield: bool = False,
    alignment: Alignment | None = None,
    char_type: CharacterType = CharacterType.PC,
) -> BuildResult:
    """Build a level-1 character (2024 PHB creation steps).

    Args:
        char_id: Unique id for the sheet.
        name: Display name.
        character_class: The chosen class.
        species: The chosen species.
        background: The chosen background.
        ability_scores: Base scores BEFORE background increases (standard
            array, point buy, or rolled).
        skill_choices: Skill proficiencies chosen from the class list.
        background_ability_allocation: Optional map of ability → +1/+2
            among the background's three abilities (default: +2/+1 to the
            first two).
        languages: Known languages (default: Common).
        armor_name: Starting armor worn (looked up in the armor registry).
        shield: Whether a shield is equipped.
        alignment: Optional alignment.
        char_type: PC/NPC/MONSTER classification.

    Returns:
        :class:`BuildResult` with the sheet and any warnings.

    Raises:
        KeyError: If species or background data is not registered.
    """
    from game_engine.rules.dnd_5_5e.data.class_features import CLASS_PROGRESSIONS
    from game_engine.rules.dnd_5_5e.spellcasting import compute_spell_slots

    warnings: list[str] = []
    class_data = CLASSES[character_class]
    species_data = get_species(species)
    background_data = get_background(background)
    if species_data is None:
        raise KeyError(f"Species {species.value} is not registered.")
    if background_data is None:
        raise KeyError(f"Background {background.value} is not registered.")

    scores = AbilityScoreSet(**ability_scores.to_dict())
    _apply_background_increases(
        scores, background_data.ability_scores, background_ability_allocation, warnings
    )

    # Skills: class choices (validated) + background skills.
    chosen: list[Skill] = []
    for skill in skill_choices:
        if skill not in class_data.skill_choices:
            warnings.append(f"{skill.value} is not a {character_class.value} skill option.")
        elif skill not in chosen:
            chosen.append(skill)
    if len(chosen) != class_data.num_skill_choices:
        warnings.append(
            f"{character_class.value} expects {class_data.num_skill_choices} skill choices, "
            f"got {len(chosen)}."
        )
    for skill in background_data.skill_proficiencies:
        if skill not in chosen:
            chosen.append(skill)

    con_mod = scores.modifier(Ability.CONSTITUTION)
    hp_max = class_data.hit_die + con_mod
    # Species/feat HP riders.
    if any(t.name == _TRAIT_DWARVEN_TOUGHNESS for t in species_data.traits):
        hp_max += 1
    feats = [background_data.origin_feat]
    if background_data.origin_feat is Feat.TOUGH:
        hp_max += 2
    hp_max = max(1, hp_max)

    dex_mod = scores.modifier(Ability.DEXTERITY)
    armor = get_armor(armor_name) if armor_name else None
    if armor_name and armor is None:
        warnings.append(f"Unknown armor {armor_name!r}; using unarmored AC.")
    if armor is not None and armor.armor_type not in class_data.armor_training:
        warnings.append(f"{character_class.value} lacks {armor.armor_type.value} armor training.")
    ac = compute_armor_class(armor, dex_mod, shield=shield)
    if armor is None:
        # Unarmored Defense (2024): barbarian 10+DEX+CON, monk 10+DEX+WIS.
        if character_class is CharacterClass.BARBARIAN:
            ac = max(ac, 10 + dex_mod + con_mod + (2 if shield else 0))
        elif character_class is CharacterClass.MONK and not shield:
            ac = max(ac, 10 + dex_mod + scores.modifier(Ability.WISDOM))

    class_levels = [ClassLevelEntry(character_class=character_class, level=1, subclass=None)]
    progression = CLASS_PROGRESSIONS.get(character_class)
    spell_slots = compute_spell_slots(class_levels) if class_data.spellcasting else []

    masteries: list[str] = []
    if progression is not None:
        mastery_count = progression.resource_at_level(ClassResource.WEAPON_MASTERY, 1)
        if mastery_count:
            weapon_word = "weapon mastery" if mastery_count == 1 else "weapon masteries"
            warnings.append(
                f"Your class can choose {mastery_count} {weapon_word} — "
                "set them later via character edit."
            )

    sheet = CharacterSheet(
        id=char_id,
        name=name,
        level=1,
        char_class=character_class,
        ability_scores=scores,
        hp_current=hp_max,
        hp_max=hp_max,
        ac=ac,
        speed=species_data.speed,
        proficient_skills=chosen,
        proficient_abilities=list(class_data.saving_throw_proficiencies),
        char_type=char_type,
        species=species,
        background=background,
        alignment=alignment,
        class_levels=class_levels,
        feats=feats,
        languages=languages or [Language.COMMON],
        hit_dice=[HitDicePool(die_size=class_data.hit_die, maximum=1, remaining=1)],
        spell_slots=spell_slots,
        armor_training=list(class_data.armor_training),
        weapon_category_training=list(class_data.weapon_category_training),
        weapon_training=list(class_data.weapon_training_notes),
        tool_proficiencies=[background_data.tool_proficiency],
        weapon_masteries=masteries,
        darkvision_ft=species_data.darkvision_ft,
        damage_resistances=list(species_data.damage_resistances),
    )
    return BuildResult(sheet=sheet, warnings=warnings)
