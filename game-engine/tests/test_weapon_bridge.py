"""Tests for the weapon-registry -> AttackDetails bridge (Workstream C, EQP-01/EQP-08)."""

from __future__ import annotations

from game_engine.rules.dnd_5_5e._weapon_bridge import to_attack_details
from game_engine.rules.dnd_5_5e.data import get_weapon
from game_engine.types import (
    Ability,
    AbilityScoreSet,
    CharacterClass,
    CharacterSheet,
    DamageType,
    WeaponCategory,
    WeaponMastery,
    WeaponProperty,
)
from game_engine.types.values import DiceNotation


def _char(**kwargs) -> CharacterSheet:
    defaults = dict(id="a", name="Actor", level=1, char_class=CharacterClass.FIGHTER)
    defaults.update(kwargs)
    return CharacterSheet(**defaults)


class TestToAttackDetails:
    def test_martial_weapon_carries_mastery_and_properties(self):
        scimitar = get_weapon("Scimitar")
        assert scimitar is not None
        actor = _char(weapon_category_training=[WeaponCategory.MARTIAL])
        details = to_attack_details(scimitar, actor)
        assert details.mastery is WeaponMastery.NICK
        assert details.properties == [WeaponProperty.FINESSE, WeaponProperty.LIGHT]
        assert details.damage_dice == DiceNotation("1d6")
        assert details.damage_type == DamageType.SLASHING

    def test_wizard_wielding_greatsword_gets_no_proficiency(self):
        greatsword = get_weapon("Greatsword")
        assert greatsword is not None
        actor = _char(char_class=CharacterClass.WIZARD, weapon_category_training=[])
        details = to_attack_details(greatsword, actor)
        assert details.proficient is False

    def test_finesse_weapon_picks_better_of_str_dex(self):
        scimitar = get_weapon("Scimitar")
        assert scimitar is not None
        actor = _char(ability_scores=AbilityScoreSet(strength=16, dexterity=10))
        details = to_attack_details(scimitar, actor)
        assert details.attack_ability is Ability.STRENGTH

        actor2 = _char(ability_scores=AbilityScoreSet(strength=10, dexterity=16))
        details2 = to_attack_details(scimitar, actor2)
        assert details2.attack_ability is Ability.DEXTERITY

    def test_non_finesse_melee_always_uses_strength(self):
        greatsword = get_weapon("Greatsword")
        assert greatsword is not None
        actor = _char(ability_scores=AbilityScoreSet(strength=8, dexterity=18))
        details = to_attack_details(greatsword, actor)
        assert details.attack_ability is Ability.STRENGTH

    def test_ranged_weapon_uses_dexterity(self):
        shortbow = get_weapon("Shortbow")
        assert shortbow is not None
        details = to_attack_details(shortbow, _char())
        assert details.attack_ability is Ability.DEXTERITY
        assert details.is_ranged is True

    def test_versatile_two_handed_uses_bigger_die(self):
        longsword = get_weapon("Longsword")
        assert longsword is not None
        one_handed = to_attack_details(longsword, _char())
        two_handed = to_attack_details(longsword, _char(), two_handed=True)
        assert one_handed.damage_dice == DiceNotation("1d8")
        assert two_handed.damage_dice == DiceNotation("1d10")

    def test_two_handed_no_effect_without_versatile(self):
        greatsword = get_weapon("Greatsword")
        assert greatsword is not None
        details = to_attack_details(greatsword, _char(), two_handed=True)
        assert details.damage_dice == DiceNotation("2d6")

    def test_is_offhand_propagates(self):
        scimitar = get_weapon("Scimitar")
        assert scimitar is not None
        details = to_attack_details(scimitar, _char(), is_offhand=True)
        assert details.is_offhand is True

    def test_is_ranged_override_for_thrown_melee_weapon(self):
        handaxe = get_weapon("Handaxe")
        assert handaxe is not None
        thrown = to_attack_details(handaxe, _char(), is_ranged=True)
        assert thrown.is_ranged is True
        assert thrown.attack_ability is Ability.STRENGTH  # not Finesse
