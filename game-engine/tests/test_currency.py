"""Tests for coin debit/credit and equipment purchase (Workstream D3, EQP-11).

``Currency`` previously had a ``total_gp`` property with no consumer and no
way to actually change a character's coin; ``purchase_item`` ties
``spend_gold`` to the weapon/armor/gear/tool/pack registries' ``cost_gp``,
the same way ``resolve_starting_equipment`` ties starting gold to the
background equipment tables.
"""

from __future__ import annotations

from game_engine.rules.dnd_5_5e import build_character, can_afford, credit_gold, purchase_item
from game_engine.rules.dnd_5_5e._currency import from_copper, spend_gold, to_copper
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


def _sheet(**currency_kwargs) -> CharacterSheet:
    sheet = build_character(
        char_id="pc1",
        name="Dorn",
        character_class=CharacterClass.FIGHTER,
        species=Species.HUMAN,
        background=Background.SOLDIER,
        ability_scores=_scores(),
        skill_choices=[Skill.ATHLETICS, Skill.PERCEPTION],
    ).sheet
    sheet.currency = Currency(**currency_kwargs) if currency_kwargs else sheet.currency
    return sheet


class TestCopperConversion:
    def test_to_copper_sums_all_denominations(self):
        assert to_copper(Currency(cp=5, sp=2, ep=1, gp=3, pp=1)) == 5 + 20 + 50 + 300 + 1000

    def test_from_copper_uses_fewest_higher_denominations(self):
        currency = from_copper(1275)
        assert currency == Currency(cp=5, sp=7, ep=0, gp=2, pp=1)

    def test_from_copper_never_reintroduces_electrum(self):
        # 150 cp could be 1 ep + 10 cp under an electrum-aware breakdown, but
        # change is only ever made in pp/gp/sp/cp.
        assert from_copper(150) == Currency(sp=5, gp=1)

    def test_round_trip_of_an_already_canonical_balance(self):
        original = Currency(cp=7, sp=3, gp=8, pp=2)
        assert from_copper(to_copper(original)) == original

    def test_round_trip_preserves_total_value_even_with_electrum(self):
        # Electrum collapses into equivalent gp/sp/cp, but the total value
        # (what actually matters for affordability) is unchanged.
        original = Currency(cp=99, sp=9, ep=1, gp=42, pp=3)
        assert to_copper(from_copper(to_copper(original))) == to_copper(original)


class TestCanAfford:
    def test_exact_amount_is_affordable(self):
        assert can_afford(Currency(gp=10), 10.0)

    def test_insufficient_funds(self):
        assert not can_afford(Currency(gp=9, sp=9), 10.0)

    def test_mixed_denominations_cover_a_fractional_cost(self):
        # 2 sp = 0.2 gp, enough for a 0.1 gp dart.
        assert can_afford(Currency(sp=2), 0.1)


class TestSpendGold:
    def test_spend_debits_and_reduces_total(self):
        currency = Currency(gp=10)
        assert spend_gold(currency, 4.0)
        assert currency == Currency(gp=6)

    def test_spend_breaks_higher_denominations_when_needed(self):
        # 1 gp, spend 0.5 gp (5 sp) -> no gp left, 5 sp change.
        currency = Currency(gp=1)
        assert spend_gold(currency, 0.5)
        assert currency == Currency(sp=5)

    def test_insufficient_funds_leaves_currency_unchanged(self):
        currency = Currency(gp=1)
        assert not spend_gold(currency, 5.0)
        assert currency == Currency(gp=1)


class TestCreditGold:
    def test_credit_increases_total_value(self):
        currency = Currency(gp=1)
        credit_gold(currency, 0.5)
        assert currency == Currency(gp=1, sp=5)


class TestPurchaseItem:
    def test_purchase_debits_currency_and_adds_inventory(self):
        sheet = _sheet(gp=10)
        assert purchase_item(sheet, "Dagger")
        assert sheet.currency.total_gp == 8  # Dagger costs 2 gp
        assert any(item.name == "Dagger" and item.quantity == 1 for item in sheet.inventory)

    def test_purchase_quantity_multiplies_cost(self):
        sheet = _sheet(gp=10)
        assert purchase_item(sheet, "Dagger", quantity=3)
        assert sheet.currency.total_gp == 4  # 3 x 2 gp

    def test_purchase_stacks_onto_an_existing_matching_item(self):
        sheet = _sheet(gp=10)
        sheet.inventory.append(InventoryItem(name="Dagger", quantity=2, weight_lb=1.0))
        assert purchase_item(sheet, "Dagger")
        daggers = [item for item in sheet.inventory if item.name == "Dagger"]
        assert len(daggers) == 1
        assert daggers[0].quantity == 3

    def test_purchase_unaffordable_item_mutates_nothing(self):
        sheet = _sheet(gp=1)
        before_inventory = list(sheet.inventory)
        assert not purchase_item(sheet, "Plate Armor")
        assert sheet.currency == Currency(gp=1)
        assert sheet.inventory == before_inventory

    def test_purchase_unknown_item_mutates_nothing(self):
        sheet = _sheet(gp=10)
        assert not purchase_item(sheet, "Bag of Holding")
        assert sheet.currency == Currency(gp=10)

    def test_purchase_pack_expands_into_contents_and_charges_pack_price(self):
        sheet = _sheet(gp=100)
        assert purchase_item(sheet, "Explorer's Pack")
        assert sheet.currency.total_gp == 90  # Explorer's Pack costs 10 gp
        assert any(item.name == "Bedroll" for item in sheet.inventory)

    def test_purchase_survives_round_trip(self):
        sheet = _sheet(gp=10)
        purchase_item(sheet, "Dagger")
        restored = CharacterSheet.from_dict(sheet.to_dict())
        assert restored.currency == sheet.currency
        assert [item.to_dict() for item in restored.inventory] == [
            item.to_dict() for item in sheet.inventory
        ]
