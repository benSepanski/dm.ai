"""Tests for the 2024 PHB equipment data: weapons, armor, gear, tools, packs."""

from __future__ import annotations

import re

from game_engine.rules.dnd_5_5e.data.armor import ARMOR, compute_armor_class, get_armor
from game_engine.rules.dnd_5_5e.data.gear import GEAR, PACKS, TOOLS, get_gear, get_tool
from game_engine.rules.dnd_5_5e.data.weapons import WEAPONS, get_weapon
from game_engine.types import (
    Ability,
    ArmorCategory,
    WeaponCategory,
    WeaponMastery,
    WeaponProperty,
)

_QUANTITY_SUFFIX = re.compile(r"\s*\(\d+\)$")


class TestWeapons:
    def test_total_weapon_count(self) -> None:
        assert len(WEAPONS) == 38

    def test_category_partition(self) -> None:
        simple_melee = [w for w in WEAPONS if w.category is WeaponCategory.SIMPLE and w.is_melee]
        simple_ranged = [
            w for w in WEAPONS if w.category is WeaponCategory.SIMPLE and not w.is_melee
        ]
        martial_melee = [w for w in WEAPONS if w.category is WeaponCategory.MARTIAL and w.is_melee]
        martial_ranged = [
            w for w in WEAPONS if w.category is WeaponCategory.MARTIAL and not w.is_melee
        ]
        assert len(simple_melee) == 10
        assert len(simple_ranged) == 4
        assert len(martial_melee) == 18
        assert len(martial_ranged) == 6

    def test_names_are_unique(self) -> None:
        names = [w.name.lower() for w in WEAPONS]
        assert len(names) == len(set(names))

    def test_every_weapon_has_a_mastery(self) -> None:
        for weapon in WEAPONS:
            assert isinstance(weapon.mastery, WeaponMastery), weapon.name

    def test_versatile_weapons_have_versatile_dice(self) -> None:
        versatile = [w for w in WEAPONS if WeaponProperty.VERSATILE in w.properties]
        assert versatile, "expected at least one versatile weapon"
        for weapon in versatile:
            assert weapon.versatile_dice is not None, weapon.name
        for weapon in WEAPONS:
            if WeaponProperty.VERSATILE not in weapon.properties:
                assert weapon.versatile_dice is None, weapon.name

    def test_ammunition_weapons_have_ranges(self) -> None:
        ammunition = [w for w in WEAPONS if WeaponProperty.AMMUNITION in w.properties]
        assert ammunition, "expected at least one ammunition weapon"
        for weapon in ammunition:
            assert weapon.range_normal_ft is not None, weapon.name
            assert weapon.range_long_ft is not None, weapon.name
            assert weapon.range_long_ft > weapon.range_normal_ft, weapon.name

    def test_ammunition_weapons_have_a_resolvable_ammunition_name(self) -> None:
        """EQP-08: every Ammunition weapon must name a real `data.gear` item —
        a structural guard against the property going dead again (harness-
        engineering principle #8: claimed-implemented mechanics need a test
        asserting they have an actual consumer, not just a docstring claim)."""
        ammunition = [w for w in WEAPONS if WeaponProperty.AMMUNITION in w.properties]
        for weapon in ammunition:
            assert weapon.ammunition_name is not None, weapon.name
            assert get_gear(weapon.ammunition_name) is not None, weapon.name

    def test_non_ammunition_weapons_have_no_ammunition_name(self) -> None:
        for weapon in WEAPONS:
            if WeaponProperty.AMMUNITION not in weapon.properties:
                assert weapon.ammunition_name is None, weapon.name

    def test_thrown_weapons_have_ranges(self) -> None:
        for weapon in WEAPONS:
            if WeaponProperty.THROWN in weapon.properties:
                assert weapon.range_normal_ft is not None, weapon.name
                assert weapon.range_long_ft is not None, weapon.name

    def test_get_weapon_longsword(self) -> None:
        longsword = get_weapon("longsword")
        assert longsword is not None
        assert longsword.name == "Longsword"
        assert longsword.category is WeaponCategory.MARTIAL
        assert str(longsword.damage_dice) == "1d8"
        assert str(longsword.versatile_dice) == "1d10"
        assert longsword.mastery is WeaponMastery.SAP
        assert longsword.cost_gp == 15.0
        assert longsword.weight_lb == 3.0

    def test_get_weapon_is_case_insensitive(self) -> None:
        assert get_weapon("HAND CROSSBOW") is get_weapon("hand crossbow")
        assert get_weapon("not a weapon") is None

    def test_lance_is_special(self) -> None:
        lance = get_weapon("lance")
        assert lance is not None
        assert WeaponProperty.SPECIAL in lance.properties
        assert WeaponProperty.TWO_HANDED in lance.properties

    def test_two_handed_property_helper(self) -> None:
        greatsword = get_weapon("greatsword")
        rapier = get_weapon("rapier")
        assert greatsword is not None and greatsword.two_handed
        assert rapier is not None and not rapier.two_handed


class TestArmor:
    def test_armor_count(self) -> None:
        assert len(ARMOR) == 13

    def test_category_counts(self) -> None:
        by_category = {
            category: [a for a in ARMOR if a.armor_type is category] for category in ArmorCategory
        }
        assert len(by_category[ArmorCategory.LIGHT]) == 3
        assert len(by_category[ArmorCategory.MEDIUM]) == 5
        assert len(by_category[ArmorCategory.HEAVY]) == 4
        assert len(by_category[ArmorCategory.SHIELD]) == 1

    def test_heavy_armor_has_no_dex_bonus(self) -> None:
        for armor in ARMOR:
            if armor.armor_type is ArmorCategory.HEAVY:
                assert armor.dex_bonus is False, armor.name
                assert armor.dex_cap == 0, armor.name

    def test_light_armor_has_uncapped_dex(self) -> None:
        for armor in ARMOR:
            if armor.armor_type is ArmorCategory.LIGHT:
                assert armor.dex_bonus is True, armor.name
                assert armor.dex_cap is None, armor.name

    def test_medium_armor_caps_dex_at_two(self) -> None:
        for armor in ARMOR:
            if armor.armor_type is ArmorCategory.MEDIUM:
                assert armor.dex_bonus is True, armor.name
                assert armor.dex_cap == 2, armor.name

    def test_compute_armor_class_leather(self) -> None:
        leather = get_armor("leather armor")
        assert leather is not None
        assert compute_armor_class(leather, dex_modifier=3) == 14

    def test_compute_armor_class_half_plate_caps_dex(self) -> None:
        half_plate = get_armor("half plate armor")
        assert half_plate is not None
        assert compute_armor_class(half_plate, dex_modifier=3) == 17

    def test_compute_armor_class_plate_ignores_dex(self) -> None:
        plate = get_armor("plate armor")
        assert plate is not None
        assert compute_armor_class(plate, dex_modifier=3) == 18

    def test_compute_armor_class_plate_with_shield(self) -> None:
        plate = get_armor("plate armor")
        assert plate is not None
        assert compute_armor_class(plate, dex_modifier=3, shield=True) == 20

    def test_compute_armor_class_unarmored(self) -> None:
        assert compute_armor_class(None, dex_modifier=2) == 12

    def test_strength_requirements(self) -> None:
        chain_mail = get_armor("chain mail")
        plate = get_armor("plate armor")
        assert chain_mail is not None and chain_mail.min_strength == 13
        assert plate is not None and plate.min_strength == 15


class TestGear:
    def test_gear_is_populated(self) -> None:
        assert len(GEAR) >= 40

    def test_gear_names_are_unique(self) -> None:
        names = [g.name.lower() for g in GEAR]
        assert len(names) == len(set(names))

    def test_gear_entries_have_descriptions(self) -> None:
        for gear in GEAR:
            assert gear.description, gear.name
            assert gear.cost_gp >= 0.0, gear.name
            assert gear.weight_lb >= 0.0, gear.name


class TestTools:
    def test_tool_count(self) -> None:
        assert len(TOOLS) == 25

    def test_thieves_tools(self) -> None:
        thieves_tools = get_tool("thieves' tools")
        assert thieves_tools is not None
        assert thieves_tools.ability is Ability.DEXTERITY
        assert thieves_tools.cost_gp == 25.0

    def test_every_tool_has_a_governing_ability(self) -> None:
        for tool in TOOLS:
            assert isinstance(tool.ability, Ability), tool.name


class TestPacks:
    def test_pack_count_and_costs(self) -> None:
        costs = {p.name: p.cost_gp for p in PACKS}
        assert costs == {
            "Burglar's Pack": 16.0,
            "Diplomat's Pack": 39.0,
            "Dungeoneer's Pack": 12.0,
            "Entertainer's Pack": 40.0,
            "Explorer's Pack": 10.0,
            "Priest's Pack": 33.0,
            "Scholar's Pack": 40.0,
        }

    def test_pack_contents_reference_gear(self) -> None:
        gear_names = {g.name.lower() for g in GEAR}
        for pack in PACKS:
            assert pack.contents, pack.name
            for entry in pack.contents:
                assert isinstance(entry, str)
                item_name = _QUANTITY_SUFFIX.sub("", entry).lower()
                assert item_name in gear_names, f"{pack.name}: {entry!r} not found in GEAR"
