"""Tests for dm_api.api.combat_utils.build_attack_details.

Split out of test_combat_utils.py to stay under the repo's 600-line test-file
guideline (docs/engine-correctness-remediation.md Workstream C added the
registry-bridge coverage here).
"""

from __future__ import annotations

import uuid

from game_engine.types import (
    Ability,
    AbilityScoreSet,
    CharacterClass,
    CharacterSheet,
    DamageType,
    WeaponCategory,
    WeaponMastery,
)
from game_engine.types.values import DiceNotation

from dm_api.api.combat_utils import build_attack_details
from dm_api.db.models.combat import AttackDetailsRequest


def _make_actor(**kwargs) -> CharacterSheet:
    defaults = dict(
        id=uuid.uuid4(),
        name="Actor",
        level=1,
        char_class=CharacterClass.FIGHTER,
        hp_current=10,
        hp_max=10,
        ac=12,
    )
    defaults.update(kwargs)
    return CharacterSheet(**defaults)


class TestBuildAttackDetails:
    def test_none_returns_none(self):
        assert build_attack_details(None) is None

    def test_basic_conversion(self):
        req = AttackDetailsRequest(
            weapon_name="Longsword",
            damage_dice="1d8",
            damage_type=DamageType.SLASHING,
            attack_ability=Ability.STRENGTH,
            is_ranged=False,
        )
        details = build_attack_details(req)
        assert details is not None
        assert details.weapon_name == "Longsword"
        assert details.damage_dice == DiceNotation("1d8")
        assert details.damage_type == DamageType.SLASHING
        assert details.attack_ability == Ability.STRENGTH
        assert details.is_ranged is False

    def test_ranged_weapon(self):
        req = AttackDetailsRequest(
            weapon_name="Shortbow",
            damage_dice="1d6",
            damage_type=DamageType.PIERCING,
            attack_ability=Ability.DEXTERITY,
            is_ranged=True,
        )
        details = build_attack_details(req)
        assert details is not None
        assert details.is_ranged is True
        assert details.attack_ability == Ability.DEXTERITY

    def test_default_values(self):
        req = AttackDetailsRequest()
        details = build_attack_details(req)
        assert details is not None
        assert details.weapon_name == "Unarmed Strike"
        assert details.damage_type == DamageType.BLUDGEONING


class TestBuildAttackDetailsRegistryBridge:
    """Workstream C: registry-known weapon_name pulls mastery/properties/
    proficiency from the registry via the actor, not the (client-controlled)
    request fields."""

    def test_registry_weapon_uses_bridge_when_actor_known(self):
        req = AttackDetailsRequest(
            weapon_name="Scimitar",
            damage_dice="1d4",  # deliberately wrong — should be ignored
            attack_ability=Ability.STRENGTH,  # deliberately wrong — Finesse should win
        )
        actor = _make_actor(
            weapon_category_training=[WeaponCategory.MARTIAL],
            ability_scores=AbilityScoreSet(strength=10, dexterity=16),
        )
        details = build_attack_details(req, actor)
        assert details is not None
        assert details.damage_dice == DiceNotation("1d6")
        assert details.mastery == WeaponMastery.NICK
        assert details.proficient is True
        assert details.attack_ability == Ability.DEXTERITY

    def test_registry_weapon_untrained_not_proficient(self):
        req = AttackDetailsRequest(weapon_name="Greatsword")
        actor = _make_actor(weapon_category_training=[WeaponCategory.SIMPLE])
        details = build_attack_details(req, actor)
        assert details is not None
        assert details.proficient is False

    def test_registry_weapon_two_handed_and_offhand_flags(self):
        req = AttackDetailsRequest(weapon_name="Longsword", two_handed=True)
        actor = _make_actor()
        details = build_attack_details(req, actor)
        assert details is not None
        assert details.damage_dice == DiceNotation("1d10")

        req_offhand = AttackDetailsRequest(weapon_name="Dagger", is_offhand=True)
        details_offhand = build_attack_details(req_offhand, actor)
        assert details_offhand is not None
        assert details_offhand.is_offhand is True

    def test_unregistered_weapon_falls_back_to_request_fields_even_with_actor(self):
        req = AttackDetailsRequest(
            weapon_name="Homebrew Cleaver",
            damage_dice="3d6",
            damage_type=DamageType.SLASHING,
            attack_ability=Ability.STRENGTH,
            is_ranged=False,
        )
        actor = _make_actor()
        details = build_attack_details(req, actor)
        assert details is not None
        assert details.weapon_name == "Homebrew Cleaver"
        assert details.damage_dice == DiceNotation("3d6")
        assert details.mastery is None
