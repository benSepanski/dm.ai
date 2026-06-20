"""Tests for spell-list derivation and cast gating (spell_lists module)."""

from __future__ import annotations

from game_engine.rules.dnd_5_5e.character_builder import build_character
from game_engine.rules.dnd_5_5e.data.monsters import MONSTERS
from game_engine.rules.dnd_5_5e.data.spells import get_spell
from game_engine.rules.dnd_5_5e.spell_lists import (
    can_cast,
    cantrips_for_class,
    cantrips_known_count,
    default_spell_selection,
    prepare_spells,
    prepared_spells_count,
    spellcasting_ability_for,
    spells_for_class,
)
from game_engine.types import (
    Ability,
    AbilityScoreSet,
    Background,
    CharacterClass,
    CharacterSheet,
    ClassLevelEntry,
    Skill,
    Species,
)


def _wizard(level: int = 1) -> CharacterSheet:
    result = build_character(
        char_id="w",
        name="Kira",
        character_class=CharacterClass.WIZARD,
        species=Species.HUMAN,
        background=Background.SAGE,
        ability_scores=AbilityScoreSet(
            strength=8, dexterity=14, constitution=13, intelligence=15, wisdom=12, charisma=10
        ),
        skill_choices=[Skill.ARCANA, Skill.INVESTIGATION],
    )
    sheet = result.sheet
    if level != 1:
        sheet.level = level
        sheet.class_levels = [ClassLevelEntry(CharacterClass.WIZARD, level)]
    return sheet


class TestClassLists:
    def test_spells_for_class_filters_by_class_and_level(self):
        spells = spells_for_class(CharacterClass.WIZARD, 1)
        assert spells, "expected level-1 wizard spells in the registry"
        assert all(s.level == 1 and CharacterClass.WIZARD in s.classes for s in spells)

    def test_cantrips_for_class_are_level_zero(self):
        cantrips = cantrips_for_class(CharacterClass.WIZARD)
        assert cantrips
        assert all(c.level == 0 and CharacterClass.WIZARD in c.classes for c in cantrips)

    def test_spellcasting_ability_for(self):
        assert spellcasting_ability_for(_wizard()) is Ability.INTELLIGENCE

    def test_non_caster_has_no_ability(self):
        fighter = build_character(
            char_id="f",
            name="Dorn",
            character_class=CharacterClass.FIGHTER,
            species=Species.HUMAN,
            background=Background.SOLDIER,
            ability_scores=AbilityScoreSet(strength=15, dexterity=14, constitution=13),
            skill_choices=[Skill.ATHLETICS, Skill.PERCEPTION],
        ).sheet
        assert spellcasting_ability_for(fighter) is None
        assert fighter.cantrips == [] and fighter.prepared_spells == []


class TestBuilderPopulatesSpells:
    def test_level_1_wizard_has_derived_spells(self):
        sheet = _wizard()
        assert len(sheet.cantrips) == cantrips_known_count(sheet) == 3
        assert len(sheet.prepared_spells) == prepared_spells_count(sheet) == 4
        # Everything chosen is actually castable.
        for name in sheet.cantrips + sheet.prepared_spells:
            spell = get_spell(name)
            assert spell is not None and can_cast(sheet, spell)


class TestCanCast:
    def test_unprepared_spell_is_not_castable(self):
        sheet = _wizard()
        sheet.cantrips = ["Fire Bolt"]
        sheet.prepared_spells = ["Magic Missile"]
        assert can_cast(sheet, get_spell("Fire Bolt"))
        assert can_cast(sheet, get_spell("Magic Missile"))
        assert not can_cast(sheet, get_spell("Fireball"))
        # Case-insensitive name match.
        sheet.prepared_spells = ["magic missile"]
        assert can_cast(sheet, get_spell("Magic Missile"))


class TestPrepareSpells:
    def test_rejects_off_list_and_over_count(self):
        sheet = _wizard()
        warnings = prepare_spells(
            sheet,
            cantrips=["Fire Bolt"],
            prepared_spells=["Magic Missile", "Cure Wounds"],  # Cure Wounds isn't a wizard spell
        )
        assert sheet.cantrips == ["Fire Bolt"]
        assert sheet.prepared_spells == ["Magic Missile"]
        assert any("Cure Wounds" in w for w in warnings)

    def test_unknown_spell_warns(self):
        sheet = _wizard()
        warnings = prepare_spells(sheet, prepared_spells=["Power Word Lunch"])
        assert sheet.prepared_spells == []
        assert any("Unknown" in w for w in warnings)


class TestMonsterSpellData:
    def test_lich_carries_a_resolvable_spell_list(self):
        lich = next(m for m in MONSTERS if m.name == "Lich")
        assert lich.spellcasting_ability is Ability.INTELLIGENCE
        assert lich.cantrips and lich.prepared_spells
        for name in lich.cantrips + lich.prepared_spells:
            assert get_spell(name) is not None, f"{name} is not in the spell registry"


def test_default_selection_empty_for_non_casters():
    fighter = CharacterSheet(id="f", name="Dorn", level=3, char_class=CharacterClass.FIGHTER)
    assert default_spell_selection(fighter) == ([], [])
