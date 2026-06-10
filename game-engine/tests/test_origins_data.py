"""Tests for the 2024 PHB origins data: species, backgrounds, feats."""

from __future__ import annotations

import pytest

from game_engine.rules.dnd_5_5e.data.backgrounds import BACKGROUNDS, get_background
from game_engine.rules.dnd_5_5e.data.feats import FEATS, get_feat
from game_engine.rules.dnd_5_5e.data.species import SPECIES, get_species
from game_engine.types import (
    Ability,
    Background,
    CreatureSize,
    CreatureType,
    DamageType,
    Feat,
    FeatCategory,
    Species,
)


class TestSpecies:
    def test_all_species_registered(self) -> None:
        assert set(SPECIES) == set(Species)

    @pytest.mark.parametrize("species", list(Species))
    def test_species_entry_well_formed(self, species: Species) -> None:
        data = get_species(species)
        assert data is not None
        assert data.species is species
        assert data.creature_type is CreatureType.HUMANOID
        assert data.size_options, f"{species} has no size options"
        assert data.speed > 0
        assert data.darkvision_ft >= 0
        assert data.traits, f"{species} has no traits"
        assert data.description

    @pytest.mark.parametrize("species", list(Species))
    def test_traits_have_names_and_text(self, species: Species) -> None:
        data = SPECIES[species]
        for trait in data.traits:
            assert trait.name
            assert trait.description

    def test_dwarf_darkvision_120(self) -> None:
        assert SPECIES[Species.DWARF].darkvision_ft == 120

    def test_orc_darkvision_120(self) -> None:
        assert SPECIES[Species.ORC].darkvision_ft == 120

    def test_goliath_speed_35(self) -> None:
        assert SPECIES[Species.GOLIATH].speed == 35

    def test_non_goliath_speed_30(self) -> None:
        for species, data in SPECIES.items():
            if species is not Species.GOLIATH:
                assert data.speed == 30, f"{species} speed should be 30"

    def test_halfling_small(self) -> None:
        assert SPECIES[Species.HALFLING].size_options == [CreatureSize.SMALL]

    def test_gnome_small(self) -> None:
        assert SPECIES[Species.GNOME].size_options == [CreatureSize.SMALL]

    def test_human_and_tiefling_medium_or_small(self) -> None:
        for species in (Species.HUMAN, Species.TIEFLING):
            assert set(SPECIES[species].size_options) == {
                CreatureSize.MEDIUM,
                CreatureSize.SMALL,
            }

    def test_no_darkvision_species(self) -> None:
        for species in (Species.HUMAN, Species.GOLIATH, Species.HALFLING):
            assert SPECIES[species].darkvision_ft == 0

    def test_only_dwarf_has_unconditional_resistance(self) -> None:
        assert SPECIES[Species.DWARF].damage_resistances == [DamageType.POISON]
        for species, data in SPECIES.items():
            if species is not Species.DWARF:
                assert data.damage_resistances == []

    def test_get_species_lookup(self) -> None:
        assert get_species(Species.ELF) is SPECIES[Species.ELF]


class TestBackgrounds:
    def test_all_backgrounds_registered(self) -> None:
        assert set(BACKGROUNDS) == set(Background)

    @pytest.mark.parametrize("background", list(Background))
    def test_three_distinct_abilities(self, background: Background) -> None:
        data = BACKGROUNDS[background]
        assert len(data.ability_scores) == 3
        assert len(set(data.ability_scores)) == 3
        assert all(isinstance(a, Ability) for a in data.ability_scores)

    @pytest.mark.parametrize("background", list(Background))
    def test_two_distinct_skills(self, background: Background) -> None:
        data = BACKGROUNDS[background]
        assert len(data.skill_proficiencies) == 2
        assert len(set(data.skill_proficiencies)) == 2

    @pytest.mark.parametrize("background", list(Background))
    def test_origin_feat_category(self, background: Background) -> None:
        data = BACKGROUNDS[background]
        assert data.origin_feat.category == FeatCategory.ORIGIN

    @pytest.mark.parametrize("background", list(Background))
    def test_equipment_tool_and_description(self, background: Background) -> None:
        data = BACKGROUNDS[background]
        assert data.background is background
        assert data.equipment, f"{background} has no equipment"
        assert data.tool_proficiency
        assert data.description

    @pytest.mark.parametrize("background", list(Background))
    def test_equipment_includes_gold(self, background: Background) -> None:
        data = BACKGROUNDS[background]
        assert any(item.endswith("gp") for item in data.equipment)

    def test_acolyte_spot_check(self) -> None:
        data = BACKGROUNDS[Background.ACOLYTE]
        assert data.ability_scores == [
            Ability.INTELLIGENCE,
            Ability.WISDOM,
            Ability.CHARISMA,
        ]
        assert data.origin_feat is Feat.MAGIC_INITIATE

    def test_soldier_spot_check(self) -> None:
        data = BACKGROUNDS[Background.SOLDIER]
        assert data.origin_feat is Feat.SAVAGE_ATTACKER

    def test_get_background_lookup(self) -> None:
        assert get_background(Background.SAGE) is BACKGROUNDS[Background.SAGE]


class TestFeats:
    def test_all_feats_registered(self) -> None:
        assert set(FEATS) == set(Feat)

    @pytest.mark.parametrize("feat", list(Feat))
    def test_feat_entry_well_formed(self, feat: Feat) -> None:
        data = get_feat(feat)
        assert data is not None
        assert data.feat is feat
        assert data.description

    def test_origin_feats_have_no_prerequisite(self) -> None:
        for feat in Feat:
            if feat.category is FeatCategory.ORIGIN:
                assert FEATS[feat].prerequisite is None, feat

    def test_general_feats_require_level_4(self) -> None:
        for feat in Feat:
            if feat.category is FeatCategory.GENERAL:
                prereq = FEATS[feat].prerequisite
                assert prereq is not None, feat
                assert "4" in prereq, feat

    def test_epic_boons_require_level_19(self) -> None:
        for feat in Feat:
            if feat.category is FeatCategory.EPIC_BOON:
                prereq = FEATS[feat].prerequisite
                assert prereq is not None, feat
                assert "19" in prereq, feat

    def test_fighting_style_prerequisite(self) -> None:
        for feat in Feat:
            if feat.category is FeatCategory.FIGHTING_STYLE:
                prereq = FEATS[feat].prerequisite
                assert prereq is not None, feat
                assert "Fighting Style" in prereq, feat

    def test_origin_and_fighting_style_no_ability_increase(self) -> None:
        for feat in Feat:
            if feat.category in (FeatCategory.ORIGIN, FeatCategory.FIGHTING_STYLE):
                assert FEATS[feat].ability_increase_options == [], feat

    def test_epic_boons_grant_ability_increase(self) -> None:
        for feat in Feat:
            if feat.category is FeatCategory.EPIC_BOON:
                assert FEATS[feat].ability_increase_options, feat

    def test_ability_score_improvement(self) -> None:
        data = FEATS[Feat.ABILITY_SCORE_IMPROVEMENT]
        assert data.repeatable is True
        assert len(data.ability_increase_options) == 6
        assert set(data.ability_increase_options) == set(Ability)

    def test_elemental_adept_repeatable(self) -> None:
        assert FEATS[Feat.ELEMENTAL_ADEPT].repeatable is True

    def test_resilient_not_repeatable(self) -> None:
        assert FEATS[Feat.RESILIENT].repeatable is False

    def test_great_weapon_master_strength_only(self) -> None:
        assert FEATS[Feat.GREAT_WEAPON_MASTER].ability_increase_options == [Ability.STRENGTH]

    def test_category_counts(self) -> None:
        by_category: dict[FeatCategory, int] = {}
        for feat in FEATS:
            by_category[feat.category] = by_category.get(feat.category, 0) + 1
        assert by_category[FeatCategory.ORIGIN] == 10
        assert by_category[FeatCategory.GENERAL] == 43
        assert by_category[FeatCategory.FIGHTING_STYLE] == 10
        assert by_category[FeatCategory.EPIC_BOON] == 12

    def test_get_feat_lookup(self) -> None:
        assert get_feat(Feat.LUCKY) is FEATS[Feat.LUCKY]
