"""Tests for worn-equipment identity, AC recomputation, the shield-as-body
guard, and creature-size wiring (Workstream D1; EQP-04/EQP-06/EQP-07).
"""

from __future__ import annotations

import pytest

from game_engine.rules.dnd_5_5e import (
    build_character,
    equip_armor,
    equip_shield,
    unequip_armor,
    unequip_shield,
)
from game_engine.rules.dnd_5_5e._equipment import (
    armor_speed_penalty,
    effective_speed,
    has_stealth_disadvantage,
    is_armor_untrained,
)
from game_engine.rules.dnd_5_5e.data.armor import compute_armor_class, get_armor
from game_engine.types import (
    Ability,
    AbilityScoreSet,
    Background,
    CharacterClass,
    CharacterSheet,
    CreatureSize,
    InventoryItem,
    Skill,
    Species,
)


def _scores(**kw: int) -> AbilityScoreSet:
    base = dict(strength=15, dexterity=14, constitution=13, intelligence=12, wisdom=10, charisma=8)
    base.update(kw)
    return AbilityScoreSet(**base)


def _build(**overrides) -> CharacterSheet:
    params = dict(
        char_id="pc1",
        name="Aria",
        character_class=CharacterClass.FIGHTER,
        species=Species.HUMAN,
        background=Background.SOLDIER,
        ability_scores=_scores(),
        skill_choices=[Skill.ATHLETICS, Skill.PERCEPTION],
        armor_name="Chain Mail",
    )
    params.update(overrides)
    return build_character(**params).sheet


class TestShieldAsBodyGuard:
    def test_compute_armor_class_rejects_shield_as_body(self):
        """EQP-06: passing a shield as body armor is a misuse — raise, don't
        silently return AC 2."""
        shield = get_armor("Shield")
        assert shield is not None
        with pytest.raises(ValueError):
            compute_armor_class(shield, dex_modifier=2)

    def test_build_with_shield_name_warns_and_does_not_yield_ac_2(self):
        """EQP-06: building with armor_name='Shield' warns and treats the
        character as unarmored (not AC 2)."""
        result = build_character(
            char_id="pc1",
            name="Aria",
            character_class=CharacterClass.FIGHTER,
            species=Species.HUMAN,
            background=Background.SOLDIER,
            ability_scores=_scores(),
            skill_choices=[Skill.ATHLETICS, Skill.PERCEPTION],
            armor_name="Shield",
        )
        assert result.sheet.worn_armor is None
        assert result.sheet.ac != 2
        # DEX 15 → +2, unarmored 10 + 2 = 12.
        assert result.sheet.ac == 12
        assert any("shield" in w.lower() for w in result.warnings)


class TestWornArmorAndEquip:
    def test_build_stores_worn_armor_identity(self):
        sheet = _build(armor_name="Chain Mail")
        assert sheet.worn_armor == "Chain Mail"
        assert sheet.worn_shield is False
        assert sheet.ac == 16  # chain mail base AC

    def test_unequip_then_equip_recomputes_ac(self):
        sheet = _build(armor_name="Chain Mail")
        assert sheet.ac == 16

        unequip_armor(sheet)
        assert sheet.worn_armor is None
        assert sheet.ac == 12  # unarmored 10 + DEX 2

        warnings = equip_armor(sheet, "Plate Armor")
        assert sheet.worn_armor == "Plate Armor"
        assert sheet.ac == 18  # plate base AC (no dex)
        assert warnings == []

    def test_equip_and_unequip_shield_adjusts_ac(self):
        sheet = _build(armor_name="Chain Mail")
        assert sheet.ac == 16

        equip_shield(sheet)
        assert sheet.worn_shield is True
        assert sheet.ac == 18  # 16 + 2

        unequip_shield(sheet)
        assert sheet.worn_shield is False
        assert sheet.ac == 16

    def test_build_with_shield_flag_sets_worn_shield(self):
        sheet = _build(armor_name="Chain Mail", shield=True)
        assert sheet.worn_shield is True
        assert sheet.ac == 18  # 16 + 2

    def test_equip_armor_warns_when_lacking_training(self):
        # Wizards have no heavy-armor training.
        sheet = _build(character_class=CharacterClass.WIZARD, armor_name=None)
        warnings = equip_armor(sheet, "Plate Armor")
        assert sheet.worn_armor == "Plate Armor"
        assert any("training" in w.lower() for w in warnings)

    def test_barbarian_unarmored_defense_survives_equip_cycle(self):
        sheet = _build(character_class=CharacterClass.BARBARIAN, armor_name=None)
        ud_ac = sheet.ac  # 10 + DEX + CON (Unarmored Defense)
        assert ud_ac == 10 + sheet.ability_scores.modifier(
            Ability.DEXTERITY
        ) + sheet.ability_scores.modifier(Ability.CONSTITUTION)

        equip_armor(sheet, "Chain Mail")
        assert sheet.ac == 16

        unequip_armor(sheet)
        assert sheet.ac == ud_ac  # UD restored, not plain 10 + DEX


class TestArmorTrainingAndStrengthPenalties:
    """Workstream D2 (EQP-02/03/04): Str-minimum speed penalty, Stealth
    disadvantage from noisy armor, and the armor-training gate consumed by
    checks/saves/casting in ``_checks.py``/``_saves.py``/``_spell_resolution.py``."""

    def test_understrength_armor_reduces_speed_by_10(self):
        # Chain Mail's min_strength is 13; STR 10 is under it.
        sheet = _build(armor_name="Chain Mail", ability_scores=_scores(strength=10))
        assert sheet.speed == 30
        assert effective_speed(sheet) == 20
        assert armor_speed_penalty(sheet) == 10

    def test_meeting_strength_minimum_no_speed_penalty(self):
        sheet = _build(armor_name="Chain Mail", ability_scores=_scores(strength=13))
        assert effective_speed(sheet) == 30
        assert armor_speed_penalty(sheet) == 0

    def test_unarmored_no_speed_penalty_regardless_of_strength(self):
        sheet = _build(armor_name=None, ability_scores=_scores(strength=3))
        assert effective_speed(sheet) == 30
        assert armor_speed_penalty(sheet) == 0

    def test_noisy_armor_flags_stealth_disadvantage(self):
        sheet = _build(armor_name="Chain Mail")
        assert has_stealth_disadvantage(sheet)

    def test_no_stealth_disadvantage_unarmored(self):
        sheet = _build(armor_name=None)
        assert not has_stealth_disadvantage(sheet)

    def test_untrained_armor_flagged(self):
        # Wizards have no heavy-armor training.
        sheet = _build(character_class=CharacterClass.WIZARD, armor_name=None)
        equip_armor(sheet, "Plate Armor")
        assert is_armor_untrained(sheet)

    def test_trained_armor_not_flagged(self):
        # Fighters are trained in heavy armor.
        sheet = _build(character_class=CharacterClass.FIGHTER, armor_name="Chain Mail")
        assert not is_armor_untrained(sheet)

    def test_unarmored_never_untrained(self):
        sheet = _build(character_class=CharacterClass.WIZARD, armor_name=None)
        assert not is_armor_untrained(sheet)


class TestEncumbrance:
    """Workstream D3 (EQP-10): carrying over capacity caps speed at 5 ft."""

    def test_overloaded_inventory_caps_speed_at_5(self):
        sheet = _build(armor_name=None, ability_scores=_scores(strength=10))
        assert effective_speed(sheet) == 30
        # STR 10 -> 150 lb capacity; load well past it.
        sheet.inventory.append(InventoryItem(name="Iron Ingots", quantity=20, weight_lb=20.0))
        assert effective_speed(sheet) == 5

    def test_encumbrance_stacks_with_understrength_armor_penalty(self):
        # Chain Mail's min_strength (13) penalty would otherwise apply first;
        # encumbrance caps the result at 5, not 20 - 10.
        sheet = _build(armor_name="Chain Mail", ability_scores=_scores(strength=10))
        sheet.inventory.append(InventoryItem(name="Iron Ingots", quantity=20, weight_lb=20.0))
        assert effective_speed(sheet) == 5

    def test_encumbrance_never_raises_a_speed_already_at_zero(self):
        sheet = _build(armor_name=None, ability_scores=_scores(strength=10))
        sheet.speed = 0
        sheet.inventory.append(InventoryItem(name="Iron Ingots", quantity=20, weight_lb=20.0))
        assert effective_speed(sheet) == 0

    def test_light_load_no_speed_penalty(self):
        sheet = _build(armor_name=None, ability_scores=_scores(strength=10))
        sheet.inventory.append(InventoryItem(name="Rope", weight_lb=5.0))
        assert effective_speed(sheet) == 30


class TestCreatureSize:
    def test_default_size_from_species_primary(self):
        # Human's first size option is Medium.
        assert _build(species=Species.HUMAN).size is CreatureSize.MEDIUM

    def test_small_species_default(self):
        # Halfling is Small-only.
        sheet = _build(species=Species.HALFLING)
        assert sheet.size is CreatureSize.SMALL

    def test_valid_size_override(self):
        # Human allows Medium or Small.
        result = build_character(
            char_id="pc1",
            name="Aria",
            character_class=CharacterClass.FIGHTER,
            species=Species.HUMAN,
            background=Background.SOLDIER,
            ability_scores=_scores(),
            skill_choices=[Skill.ATHLETICS, Skill.PERCEPTION],
            size=CreatureSize.SMALL,
        )
        assert result.sheet.size is CreatureSize.SMALL
        assert not any("can't be" in w for w in result.warnings)

    def test_invalid_size_override_warns_and_falls_back(self):
        # Dwarf is Medium-only; requesting Small is rejected with a warning.
        result = build_character(
            char_id="pc1",
            name="Durin",
            character_class=CharacterClass.FIGHTER,
            species=Species.DWARF,
            background=Background.SOLDIER,
            ability_scores=_scores(),
            skill_choices=[Skill.ATHLETICS, Skill.PERCEPTION],
            size=CreatureSize.SMALL,
        )
        assert result.sheet.size is CreatureSize.MEDIUM
        assert any("can't be" in w.lower() for w in result.warnings)


class TestSizeAndEquipmentSerde:
    def test_round_trip_preserves_size_and_worn_equipment(self):
        sheet = _build(armor_name="Chain Mail", shield=True, size=CreatureSize.SMALL)
        restored = CharacterSheet.from_dict(sheet.to_dict())
        assert restored.size is CreatureSize.SMALL
        assert restored.worn_armor == "Chain Mail"
        assert restored.worn_shield is True
        assert restored.ac == sheet.ac


class TestCreatureSizeRank:
    def test_rank_is_monotonic(self):
        order = [
            CreatureSize.TINY,
            CreatureSize.SMALL,
            CreatureSize.MEDIUM,
            CreatureSize.LARGE,
            CreatureSize.HUGE,
            CreatureSize.GARGANTUAN,
        ]
        assert [s.rank for s in order] == [0, 1, 2, 3, 4, 5]
