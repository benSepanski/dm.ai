"""Tests for starting-equipment expansion (Workstream D3, EQP-05).

``resolve_starting_equipment`` turns a background's free-text ``equipment``
list into structured ``InventoryItem``s + ``Currency``; ``build_character``
wires the result onto the built sheet instead of leaving
``inventory``/``currency`` at their empty/zero defaults.
"""

from __future__ import annotations

from game_engine.rules.dnd_5_5e import build_character, resolve_starting_equipment
from game_engine.rules.dnd_5_5e.data.backgrounds import get_background
from game_engine.rules.dnd_5_5e.data.gear import PACKS_BY_NAME
from game_engine.types import (
    AbilityScoreSet,
    Background,
    CharacterClass,
    CharacterSheet,
    Currency,
    InventoryItem,
    Skill,
    Species,
)


def _scores(**kw: int) -> AbilityScoreSet:
    base = dict(strength=15, dexterity=14, constitution=13, intelligence=12, wisdom=10, charisma=8)
    base.update(kw)
    return AbilityScoreSet(**base)


class TestResolveStartingEquipment:
    def test_empty_equipment_yields_nothing(self):
        items, currency = resolve_starting_equipment([])
        assert items == []
        assert currency == Currency()

    def test_gold_entry_accumulates_into_currency(self):
        items, currency = resolve_starting_equipment(["8 gp"])
        assert items == []
        assert currency.gp == 8

    def test_multiple_gold_entries_sum(self):
        # Not a real background shape, but the parser must not silently drop
        # a second gold entry rather than summing it.
        items, currency = resolve_starting_equipment(["5 gp", "3 gp"])
        assert currency.gp == 8

    def test_pure_numeric_parenthetical_is_a_quantity(self):
        items, _ = resolve_starting_equipment(["Dagger (2)"])
        assert len(items) == 1
        assert items[0].name == "Dagger"
        assert items[0].quantity == 2

    def test_plain_item_defaults_to_quantity_one(self):
        items, _ = resolve_starting_equipment(["Crowbar"])
        assert items == [InventoryItem("Crowbar")]

    def test_non_numeric_parenthetical_stays_in_the_name(self):
        # "Book (prayers)" is a descriptor, not a count — must not be parsed
        # as quantity=<garbage> or silently truncated to "Book".
        items, _ = resolve_starting_equipment(["Book (prayers)"])
        assert len(items) == 1
        assert items[0].name == "Book (prayers)"
        assert items[0].quantity == 1

    def test_choice_placeholder_stays_in_the_name(self):
        items, _ = resolve_starting_equipment(["Artisan's Tools (choice)"])
        assert len(items) == 1
        assert items[0].name == "Artisan's Tools (choice)"
        assert items[0].quantity == 1

    def test_pack_name_expands_into_contents(self):
        pack = PACKS_BY_NAME["explorer's pack"]
        items, currency = resolve_starting_equipment(["Explorer's Pack"])
        assert currency.gp == 0
        assert len(items) == len(pack.contents)
        names = {item.name for item in items}
        assert "Backpack" in names
        assert "Bedroll" in names
        rations = next(item for item in items if item.name == "Rations")
        assert rations.quantity == 10  # "Rations (10)" in the pack contents

    def test_pack_name_match_is_case_insensitive(self):
        items, _ = resolve_starting_equipment(["explorer's pack"])
        assert len(items) == len(PACKS_BY_NAME["explorer's pack"].contents)

    def test_soldier_background_equipment(self):
        # Background.SOLDIER.equipment = ["Spear", "Shortbow", "Arrows (20)",
        # "Gaming Set (choice)", "Healer's Kit", "Quiver", "Traveler's
        # Clothes", "14 gp"] — 7 items, 14 gp, no pack.
        background_data = get_background(Background.SOLDIER)
        assert background_data is not None
        items, currency = resolve_starting_equipment(background_data.equipment)
        assert currency.gp == 14
        assert len(items) == 7
        arrows = next(item for item in items if item.name == "Arrows")
        assert arrows.quantity == 20
        assert any(item.name == "Gaming Set (choice)" for item in items)


class TestBuildCharacterAppliesStartingEquipment:
    def test_build_populates_inventory_and_gold(self):
        result = build_character(
            char_id="pc1",
            name="Dorn",
            character_class=CharacterClass.FIGHTER,
            species=Species.HUMAN,
            background=Background.SOLDIER,
            ability_scores=_scores(),
            skill_choices=[Skill.ATHLETICS, Skill.PERCEPTION],
        )
        sheet = result.sheet
        assert sheet.inventory != []
        assert sheet.currency.gp == 14
        assert any(item.name == "Spear" for item in sheet.inventory)

    def test_different_backgrounds_yield_different_equipment(self):
        acolyte = build_character(
            char_id="pc1",
            name="Kira",
            character_class=CharacterClass.CLERIC,
            species=Species.HUMAN,
            background=Background.ACOLYTE,
            ability_scores=_scores(),
            skill_choices=[Skill.INSIGHT, Skill.RELIGION],
        ).sheet
        assert acolyte.currency.gp == 8
        assert any(item.name == "Holy Symbol" for item in acolyte.inventory)

    def test_starting_equipment_survives_round_trip(self):
        sheet = build_character(
            char_id="pc1",
            name="Dorn",
            character_class=CharacterClass.FIGHTER,
            species=Species.HUMAN,
            background=Background.SOLDIER,
            ability_scores=_scores(),
            skill_choices=[Skill.ATHLETICS, Skill.PERCEPTION],
        ).sheet
        restored = CharacterSheet.from_dict(sheet.to_dict())
        assert restored.currency == sheet.currency
        assert [item.to_dict() for item in restored.inventory] == [
            item.to_dict() for item in sheet.inventory
        ]
