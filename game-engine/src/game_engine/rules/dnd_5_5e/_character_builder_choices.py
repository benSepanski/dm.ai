"""Choice-resolution helpers for :mod:`character_builder`.

Split out of ``character_builder.py`` (file-length guideline) — owns
validating a player's species-trait picks (Elven Lineage, Keen Senses,
Skillful, Versatile) and starting cantrip/spell picks against each entity's
closed option set.
"""

from __future__ import annotations

from game_engine.rules.dnd_5_5e.data.species import SpeciesData
from game_engine.rules.dnd_5_5e.data.spells import get_spells_for_class
from game_engine.types import CharacterClass, Feat, Skill, SpeciesLineage


def resolve_species_trait_choices(
    species_data: SpeciesData,
    species_trait_choices: dict[str, str],
    warnings: list[str],
) -> tuple[SpeciesLineage | None, Skill | None, Feat | None]:
    """Validate and resolve every choice-bearing trait on *species_data*.

    Returns ``(species_lineage, bonus_skill, bonus_origin_feat)`` — the
    three choice-bearing trait shapes in the registry: a lineage pick (Elf's
    Elven Lineage), a skill pick (Elf's Keen Senses, Human's Skillful), and a
    feat pick (Human's Versatile). A species only ever has one skill-choice
    trait and one feat-choice trait, so ``bonus_skill``/``bonus_origin_feat``
    are single values. Raises :class:`ValueError` if a submitted choice isn't
    in that trait's closed option set; emits a warning (not an error) if a
    choice-bearing trait was left unanswered.
    """
    species_lineage: SpeciesLineage | None = None
    bonus_skill: Skill | None = None
    bonus_origin_feat: Feat | None = None
    for trait in species_data.traits:
        if trait.choice is None:
            continue
        raw_choice = species_trait_choices.get(trait.name)
        if raw_choice is None:
            warnings.append(f"{trait.name} requires a choice — set it later via character edit.")
            continue
        if trait.choice.lineage_options:
            try:
                lineage = SpeciesLineage(raw_choice)
            except ValueError as exc:
                raise ValueError(
                    f"{raw_choice!r} is not a valid choice for {trait.name} "
                    f"(options: {', '.join(o.value for o in trait.choice.lineage_options)})."
                ) from exc
            if lineage not in trait.choice.lineage_options:
                raise ValueError(
                    f"{lineage.value!r} is not a valid choice for {trait.name} "
                    f"(options: {', '.join(o.value for o in trait.choice.lineage_options)})."
                )
            species_lineage = lineage
        elif trait.choice.skill_options:
            try:
                skill = Skill(raw_choice.lower())
            except ValueError as exc:
                raise ValueError(
                    f"{raw_choice!r} is not a valid choice for {trait.name} "
                    f"(options: {', '.join(o.value for o in trait.choice.skill_options)})."
                ) from exc
            if skill not in trait.choice.skill_options:
                raise ValueError(
                    f"{skill.value!r} is not a valid choice for {trait.name} "
                    f"(options: {', '.join(o.value for o in trait.choice.skill_options)})."
                )
            bonus_skill = skill
        elif trait.choice.feat_options:
            try:
                feat = Feat(raw_choice)
            except ValueError as exc:
                raise ValueError(
                    f"{raw_choice!r} is not a valid choice for {trait.name} "
                    f"(options: {', '.join(o.value for o in trait.choice.feat_options)})."
                ) from exc
            if feat not in trait.choice.feat_options:
                raise ValueError(
                    f"{feat.value!r} is not a valid choice for {trait.name} "
                    f"(options: {', '.join(o.value for o in trait.choice.feat_options)})."
                )
            bonus_origin_feat = feat
    return species_lineage, bonus_skill, bonus_origin_feat


def resolve_starting_spells(
    character_class: CharacterClass,
    cantrips_known_count: int,
    prepared_spells_count: int,
    starting_cantrips: list[str] | None,
    starting_spells: list[str] | None,
    warnings: list[str],
) -> tuple[list[str], list[str]]:
    """Validate submitted cantrip/spell names against the class's level-1 list.

    Returns ``(known_spells, prepared_spells)`` — cantrips are always placed
    in ``known_spells``; level-1 spells go to ``prepared_spells`` for Wizard
    (prepared caster) and to ``known_spells`` for known-spell casters, mirroring
    :class:`CharacterSheet`'s two spell lists.
    """
    legal_cantrips = {s.name for s in get_spells_for_class(character_class, 1, cantrip=True)}
    legal_spells = {s.name for s in get_spells_for_class(character_class, 1, cantrip=False)}

    known: list[str] = []
    prepared: list[str] = []

    if cantrips_known_count > 0:
        if starting_cantrips is None:
            warnings.append(
                f"{character_class.value} can choose {cantrips_known_count} starting "
                "cantrip(s) — set them later via character edit."
            )
        else:
            for cantrip in starting_cantrips:
                if cantrip not in legal_cantrips:
                    raise ValueError(
                        f"{cantrip!r} is not a level-1 {character_class.value} cantrip."
                    )
                if cantrip not in known:
                    known.append(cantrip)
            if len(known) != cantrips_known_count:
                warnings.append(
                    f"{character_class.value} expects {cantrips_known_count} starting "
                    f"cantrip(s), got {len(known)}."
                )

    if prepared_spells_count > 0:
        if starting_spells is None:
            warnings.append(
                f"{character_class.value} can choose {prepared_spells_count} starting "
                "spell(s) — set them later via character edit."
            )
        else:
            chosen_spells: list[str] = []
            for spell in starting_spells:
                if spell not in legal_spells:
                    raise ValueError(f"{spell!r} is not a level-1 {character_class.value} spell.")
                if spell not in chosen_spells:
                    chosen_spells.append(spell)
            if len(chosen_spells) != prepared_spells_count:
                warnings.append(
                    f"{character_class.value} expects {prepared_spells_count} starting "
                    f"spell(s), got {len(chosen_spells)}."
                )
            if character_class is CharacterClass.WIZARD:
                prepared = chosen_spells
            else:
                known.extend(s for s in chosen_spells if s not in known)

    return known, prepared
