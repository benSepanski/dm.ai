"""Tests for the weapon registry → AttackDetails bridge (Workstream C)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from game_engine.interface import Action
from game_engine.rules.dnd_5_5e._weapon_bridge import to_attack_details
from game_engine.rules.dnd_5_5e.data.weapons import get_weapon
from game_engine.rules.dnd_5_5e.engine import DnD55eEngine
from game_engine.types import (
    Ability,
    AbilityScoreSet,
    ActionType,
    AttackDetails,
    CharacterClass,
    CharacterSheet,
    CombatStateData,
    DamageType,
    DiceNotation,
    WeaponCategory,
    WeaponMastery,
    WeaponProperty,
)

ATTACKS = "game_engine.rules.dnd_5_5e._attacks"


def _char(**kwargs) -> CharacterSheet:
    defaults = dict(
        id="a",
        name="A",
        level=1,
        char_class=CharacterClass.FIGHTER,
        hp_current=10,
        hp_max=10,
        ac=12,
    )
    defaults.update(kwargs)
    return CharacterSheet(**defaults)


def _attack(actor="a", target="b", **details_kwargs) -> Action:
    details_kwargs.setdefault("damage_dice", DiceNotation("1d6"))
    details_kwargs.setdefault("damage_type", DamageType.SLASHING)
    return Action(
        action_type=ActionType.ATTACK,
        actor_id=actor,
        target_id=target,
        details=AttackDetails(**details_kwargs),
    )


@pytest.fixture
def engine() -> DnD55eEngine:
    return DnD55eEngine()


@pytest.fixture
def state() -> CombatStateData:
    return CombatStateData(combatants=[_char(id="a"), _char(id="b")])


class TestToAttackDetails:
    def test_mastery_and_proficiency_from_registry(self):
        weapon = get_weapon("Scimitar")
        actor = _char(weapon_category_training=[WeaponCategory.MARTIAL])
        details = to_attack_details(weapon, actor)
        assert details.mastery == WeaponMastery.NICK
        assert details.proficient is True
        assert WeaponProperty.LIGHT in details.properties

    def test_untrained_weapon_not_proficient(self):
        weapon = get_weapon("Greatsword")
        actor = _char(weapon_category_training=[WeaponCategory.SIMPLE])
        details = to_attack_details(weapon, actor)
        assert details.proficient is False

    def test_finesse_picks_higher_of_str_dex(self):
        weapon = get_weapon("Scimitar")
        actor = _char(ability_scores=AbilityScoreSet(strength=10, dexterity=18))
        details = to_attack_details(weapon, actor)
        assert details.attack_ability == Ability.DEXTERITY

    def test_finesse_prefers_strength_when_higher(self):
        weapon = get_weapon("Scimitar")
        actor = _char(ability_scores=AbilityScoreSet(strength=18, dexterity=10))
        details = to_attack_details(weapon, actor)
        assert details.attack_ability == Ability.STRENGTH

    def test_non_finesse_melee_uses_strength(self):
        weapon = get_weapon("Greatsword")
        actor = _char(ability_scores=AbilityScoreSet(strength=10, dexterity=18))
        details = to_attack_details(weapon, actor)
        assert details.attack_ability == Ability.STRENGTH

    def test_ranged_weapon_uses_dexterity_and_is_ranged(self):
        weapon = get_weapon("Longbow")
        actor = _char()
        details = to_attack_details(weapon, actor)
        assert details.attack_ability == Ability.DEXTERITY
        assert details.is_ranged is True

    def test_is_ranged_override(self):
        weapon = get_weapon("Dagger")
        actor = _char()
        details = to_attack_details(weapon, actor, is_ranged=True)
        assert details.is_ranged is True

    def test_versatile_two_handed_uses_larger_die(self):
        weapon = get_weapon("Longsword")
        actor = _char()
        one_handed = to_attack_details(weapon, actor, two_handed=False)
        two_handed = to_attack_details(weapon, actor, two_handed=True)
        assert one_handed.damage_dice == DiceNotation("1d8")
        assert two_handed.damage_dice == DiceNotation("1d10")

    def test_non_versatile_ignores_two_handed(self):
        weapon = get_weapon("Greatsword")
        actor = _char()
        details = to_attack_details(weapon, actor, two_handed=True)
        assert details.damage_dice == DiceNotation("2d6")

    def test_is_offhand_passthrough(self):
        weapon = get_weapon("Dagger")
        actor = _char()
        details = to_attack_details(weapon, actor, is_offhand=True)
        assert details.is_offhand is True

    def test_weapon_name_and_damage_type_from_registry(self):
        weapon = get_weapon("Warhammer")
        actor = _char()
        details = to_attack_details(weapon, actor)
        assert details.weapon_name == "Warhammer"
        assert details.damage_type == weapon.damage_type
        assert details.mastery == WeaponMastery.PUSH

    def test_ammunition_name_from_registry(self):
        weapon = get_weapon("Longbow")
        actor = _char()
        details = to_attack_details(weapon, actor)
        assert details.ammunition_name == "Arrows"

    def test_ammunition_name_none_for_a_weapon_without_the_property(self):
        weapon = get_weapon("Warhammer")
        actor = _char()
        details = to_attack_details(weapon, actor)
        assert details.ammunition_name is None


class TestHeavyPropertyConsumedByAttackResolution:
    """EQP-08: Heavy weapon + attack-ability score below 13 → disadvantage."""

    def test_heavy_weapon_disadvantages_weak_attacker(self, engine, state):
        state.get_combatant("a").ability_scores = AbilityScoreSet(strength=8)
        with patch(f"{ATTACKS}.roll_with_disadvantage", return_value=(3, [3, 15])) as dis:
            engine.resolve_action(_attack(properties=[WeaponProperty.HEAVY]), state)
        dis.assert_called_once()

    def test_heavy_weapon_no_disadvantage_for_strong_attacker(self, engine, state):
        state.get_combatant("a").ability_scores = AbilityScoreSet(strength=16)
        with patch(f"{ATTACKS}.roll_dice", return_value=(10, [10])) as straight:
            engine.resolve_action(_attack(properties=[WeaponProperty.HEAVY]), state)
        straight.assert_called()
