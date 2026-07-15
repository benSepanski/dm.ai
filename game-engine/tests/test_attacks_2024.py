"""Tests for 2024 attack resolution: advantage, cover, crits, masteries,
two-weapon fighting, unarmed options, and the action economy."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from game_engine.interface import Action
from game_engine.rules.dnd_5_5e.engine import DnD55eEngine
from game_engine.types import (
    AbilityScoreSet,
    ActionType,
    AttackDetails,
    CharacterClass,
    CharacterSheet,
    CombatStateData,
    Condition,
    CoverType,
    DamageType,
    DiceNotation,
    Feat,
    UnarmedStrikeOption,
    WeaponMastery,
    WeaponProperty,
)

ATTACKS = "game_engine.rules.dnd_5_5e._attacks"


def _char(char_id: str, **kwargs) -> CharacterSheet:
    defaults = dict(
        name=char_id.title(),
        level=1,
        char_class=CharacterClass.FIGHTER,
        hp_current=30,
        hp_max=30,
        ac=12,
    )
    defaults.update(kwargs)
    return CharacterSheet(id=char_id, **defaults)


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
    return CombatStateData(combatants=[_char("a"), _char("b")])


class TestAdvantageSources:
    def test_attack_vs_restrained_target_has_advantage(self, engine, state):
        state.get_combatant("b").conditions.append(Condition.RESTRAINED)
        with patch(f"{ATTACKS}.roll_with_advantage", return_value=(15, [15, 3])) as adv:
            engine.resolve_action(_attack(), state)
        adv.assert_called_once()

    def test_poisoned_attacker_has_disadvantage(self, engine, state):
        state.get_combatant("a").conditions.append(Condition.POISONED)
        with patch(f"{ATTACKS}.roll_with_disadvantage", return_value=(3, [3, 15])) as dis:
            engine.resolve_action(_attack(), state)
        dis.assert_called_once()

    def test_advantage_and_disadvantage_cancel(self, engine, state):
        state.get_combatant("a").conditions.append(Condition.POISONED)
        state.get_combatant("b").conditions.append(Condition.RESTRAINED)
        with patch(f"{ATTACKS}.roll_dice", return_value=(10, [10])) as straight:
            engine.resolve_action(_attack(), state)
        straight.assert_called()

    def test_prone_target_melee_adv_ranged_dis(self, engine, state):
        state.get_combatant("b").conditions.append(Condition.PRONE)
        with patch(f"{ATTACKS}.roll_with_advantage", return_value=(15, [15, 3])) as adv:
            engine.resolve_action(_attack(), state)
        adv.assert_called_once()
        state.reset_turn("a")
        with patch(f"{ATTACKS}.roll_with_disadvantage", return_value=(3, [3, 15])) as dis:
            engine.resolve_action(_attack(is_ranged=True), state)
        dis.assert_called_once()

    def test_dodging_target_imposes_disadvantage(self, engine, state):
        engine.resolve_action(Action(ActionType.DODGE, "b", None), state)
        with patch(f"{ATTACKS}.roll_with_disadvantage", return_value=(3, [3, 15])) as dis:
            engine.resolve_action(_attack(), state)
        dis.assert_called_once()


class TestCoverAndCrits:
    def test_half_cover_adds_2_ac(self, engine, state):
        # AC 12 + 2 = 14; roll 12 + prof 2 = 14 → hit exactly
        with patch(f"{ATTACKS}.roll_dice", return_value=(12, [12])):
            result = engine.resolve_action(_attack(target_cover=CoverType.HALF), state)
        assert result.success is True
        state.reset_turn("a")
        with patch(f"{ATTACKS}.roll_dice", return_value=(11, [11])):
            result = engine.resolve_action(_attack(target_cover=CoverType.HALF), state)
        assert result.success is False

    def test_total_cover_blocks_targeting(self, engine, state):
        result = engine.resolve_action(_attack(target_cover=CoverType.TOTAL), state)
        assert result.success is False
        assert result.log_entry["error"] == "total_cover"

    def test_melee_hit_vs_paralyzed_is_auto_crit(self, engine, state):
        state.get_combatant("b").conditions.append(Condition.PARALYZED)
        with (
            patch(f"{ATTACKS}.roll_with_advantage", return_value=(15, [15, 3])),
            patch(f"{ATTACKS}.roll_dice", side_effect=[(3, [3]), (4, [4])]),
        ):
            result = engine.resolve_action(_attack(), state)
        assert result.log_entry["critical"] is True
        assert result.damage == 7

    def test_critical_hit_doubles_dice_not_flat_modifier(self, engine, state):
        """ACT-09: a crit on '1d6+2' rolls the 1d6 twice but applies the +2
        modifier once, not twice."""
        with patch(f"{ATTACKS}.roll_dice") as mock_roll:
            mock_roll.side_effect = [(20, [20]), (5, [5]), (3, [3])]
            result = engine.resolve_action(_attack(damage_dice=DiceNotation("1d6+2")), state)
        mock_roll.assert_any_call(1, 6, 2)  # base damage roll includes the modifier
        mock_roll.assert_any_call(1, 6)  # crit-extra roll does not
        assert result.log_entry["critical"] is True
        assert result.damage == 8  # 5 + 3 dice + 2 modifier, added once

    def test_exhaustion_penalizes_attack(self, engine, state):
        state.get_combatant("a").exhaustion_level = 2
        # roll 13 + prof 2 - 4 = 11 vs AC 12 → miss
        with patch(f"{ATTACKS}.roll_dice", return_value=(13, [13])):
            result = engine.resolve_action(_attack(), state)
        assert result.success is False


class TestWeaponMasteries:
    def test_graze_deals_ability_mod_on_miss(self, engine, state):
        actor = state.get_combatant("a")
        actor.ability_scores = AbilityScoreSet(strength=16)
        actor.weapon_masteries = ["Greatsword"]
        with patch(f"{ATTACKS}.roll_dice", return_value=(2, [2])):
            result = engine.resolve_action(
                _attack(weapon_name="Greatsword", mastery=WeaponMastery.GRAZE), state
            )
        assert result.success is False
        assert result.damage == 3
        assert state.get_combatant("b").hp_current == 27

    def test_graze_minimum_damage_is_1_with_negative_ability_mod(self, engine, state):
        actor = state.get_combatant("a")
        actor.ability_scores = AbilityScoreSet(strength=6)  # STR −2
        actor.weapon_masteries = ["Greatsword"]
        with patch(f"{ATTACKS}.roll_dice", return_value=(2, [2])):
            result = engine.resolve_action(
                _attack(weapon_name="Greatsword", mastery=WeaponMastery.GRAZE), state
            )
        # 2024 PHB GRAZE: minimum 1 damage even when ability mod is negative.
        assert result.success is False
        assert result.damage == 1
        assert state.get_combatant("b").hp_current == 29

    def test_topple_forces_save_or_prone(self, engine, state):
        actor = state.get_combatant("a")
        actor.weapon_masteries = ["Maul"]
        with (
            patch(f"{ATTACKS}.roll_dice", return_value=(18, [18])),
            patch("game_engine.rules.dnd_5_5e._saves.roll_dice", return_value=(2, [2])),
        ):
            result = engine.resolve_action(
                _attack(weapon_name="Maul", mastery=WeaponMastery.TOPPLE), state
            )
        assert Condition.PRONE in state.get_combatant("b").conditions
        assert Condition.PRONE in result.conditions_applied

    def test_vex_grants_advantage_on_next_attack(self, engine, state):
        actor = state.get_combatant("a")
        actor.weapon_masteries = ["Rapier"]
        with patch(f"{ATTACKS}.roll_dice", return_value=(18, [18])):
            engine.resolve_action(_attack(weapon_name="Rapier", mastery=WeaponMastery.VEX), state)
        assert state.turn_state_for("a").vexed_target_id == "b"

        # 2024 PHB: Vex lasts "before the end of your next turn" — it must
        # survive the attacker's own begin_turn one round later...
        state.round_number = 2
        engine.begin_turn(actor, state)
        assert state.turn_state_for("a").vexed_target_id == "b"

        # ...and actually grant advantage on the follow-up attack.
        with patch(f"{ATTACKS}.roll_with_advantage", return_value=(15, [15, 3])) as adv:
            engine.resolve_action(_attack(), state)
        adv.assert_called_once()
        assert state.turn_state_for("a").vexed_target_id is None

    def test_vex_expires_after_attackers_turn_after_next(self, engine, state):
        actor = state.get_combatant("a")
        actor.weapon_masteries = ["Rapier"]
        with patch(f"{ATTACKS}.roll_dice", return_value=(18, [18])):
            engine.resolve_action(_attack(weapon_name="Rapier", mastery=WeaponMastery.VEX), state)
        state.round_number = 3
        engine.begin_turn(actor, state)
        assert state.turn_state_for("a").vexed_target_id is None

    def test_sap_disadvantages_target_after_targets_own_begin_turn(self, engine, state):
        actor = state.get_combatant("a")
        target = state.get_combatant("b")
        actor.weapon_masteries = ["Scimitar"]
        with patch(f"{ATTACKS}.roll_dice", return_value=(18, [18])):
            engine.resolve_action(
                _attack(weapon_name="Scimitar", mastery=WeaponMastery.SAP), state
            )
        assert state.turn_state_for("b").sapped is True

        # Sap expires on the sapper's next turn, not the target's — the
        # target's own begin_turn must not clear it.
        engine.begin_turn(target, state)
        assert state.turn_state_for("b").sapped is True

        with patch(f"{ATTACKS}.roll_with_disadvantage", return_value=(3, [3, 15])) as dis:
            engine.resolve_action(_attack(actor="b", target="a"), state)
        dis.assert_called_once()

    def test_mastery_requires_training(self, engine, state):
        # No entry in weapon_masteries → no Topple effect.
        with (
            patch(f"{ATTACKS}.roll_dice", return_value=(18, [18])),
            patch("game_engine.rules.dnd_5_5e._saves.roll_dice", return_value=(2, [2])),
        ):
            engine.resolve_action(_attack(weapon_name="Maul", mastery=WeaponMastery.TOPPLE), state)
        assert Condition.PRONE not in state.get_combatant("b").conditions


class TestTwoWeaponFighting:
    def test_offhand_attack_omits_ability_mod(self, engine, state):
        actor = state.get_combatant("a")
        actor.ability_scores = AbilityScoreSet(strength=16)
        with patch(
            f"{ATTACKS}.roll_dice",
            side_effect=[(15, [15]), (4, [4]), (15, [15]), (4, [4])],
        ):
            engine.resolve_action(_attack(properties=[WeaponProperty.LIGHT]), state)
            result = engine.resolve_action(
                _attack(is_offhand=True, properties=[WeaponProperty.LIGHT]), state
            )
        assert result.damage == 4

    def test_offhand_attack_keeps_negative_ability_mod(self, engine, state):
        """ACT-18: a negative modifier still reduces off-hand damage."""
        state.get_combatant("a").ability_scores = AbilityScoreSet(strength=6)  # -2 mod
        with patch(
            f"{ATTACKS}.roll_dice",
            side_effect=[(15, [15]), (4, [4]), (15, [15]), (4, [4])],
        ):
            engine.resolve_action(_attack(properties=[WeaponProperty.LIGHT]), state)
            result = engine.resolve_action(
                _attack(is_offhand=True, properties=[WeaponProperty.LIGHT]), state
            )
        assert result.damage == 2

    def test_twf_style_adds_ability_mod(self, engine, state):
        actor = state.get_combatant("a")
        actor.ability_scores = AbilityScoreSet(strength=16)
        actor.feats.append(Feat.TWO_WEAPON_FIGHTING)
        with patch(
            f"{ATTACKS}.roll_dice",
            side_effect=[(15, [15]), (4, [4]), (15, [15]), (4, [4])],
        ):
            engine.resolve_action(_attack(properties=[WeaponProperty.LIGHT]), state)
            result = engine.resolve_action(
                _attack(is_offhand=True, properties=[WeaponProperty.LIGHT]), state
            )
        assert result.damage == 7

    def test_offhand_consumes_bonus_action(self, engine, state):
        with patch(f"{ATTACKS}.roll_dice", return_value=(15, [15])):
            engine.resolve_action(_attack(properties=[WeaponProperty.LIGHT]), state)
            engine.resolve_action(
                _attack(is_offhand=True, properties=[WeaponProperty.LIGHT]), state
            )
            second = engine.resolve_action(
                _attack(is_offhand=True, properties=[WeaponProperty.LIGHT]), state
            )
        assert second.success is False
        assert second.log_entry["error"] == "bonus_action_used"

    def test_offhand_attack_without_light_property_rejected(self, engine, state):
        """ACT-04: the off-hand weapon itself must have the Light property."""
        with patch(f"{ATTACKS}.roll_dice", return_value=(15, [15])):
            engine.resolve_action(_attack(properties=[WeaponProperty.LIGHT]), state)
            result = engine.resolve_action(_attack(is_offhand=True, properties=[]), state)
        assert result.success is False
        assert result.log_entry["error"] == "offhand_not_light"
        assert state.turn_state_for("a").bonus_action_used is False

    def test_offhand_attack_without_prior_attack_rejected(self, engine, state):
        """ACT-04: TWF requires a prior Attack-action attack this turn."""
        with patch(f"{ATTACKS}.roll_dice", return_value=(15, [15])):
            result = engine.resolve_action(
                _attack(is_offhand=True, properties=[WeaponProperty.LIGHT]), state
            )
        assert result.success is False
        assert result.log_entry["error"] == "no_light_attack"
        assert state.turn_state_for("a").bonus_action_used is False

    def test_offhand_attack_requires_light_main_hand_weapon(self, engine, state):
        """ACT-04: the *main-hand* weapon must also have been Light — a prior
        Greatsword attack doesn't unlock a Light off-hand attack."""
        with patch(f"{ATTACKS}.roll_dice", return_value=(15, [15])):
            engine.resolve_action(_attack(weapon_name="Greatsword", properties=[]), state)
            result = engine.resolve_action(
                _attack(is_offhand=True, properties=[WeaponProperty.LIGHT]), state
            )
        assert result.success is False
        assert result.log_entry["error"] == "no_light_attack"


class TestUnarmedOptions:
    def test_grapple_applies_grappled_on_failed_save(self, engine, state):
        with patch("game_engine.rules.dnd_5_5e._saves.roll_dice", return_value=(2, [2])):
            result = engine.resolve_action(
                _attack(unarmed_option=UnarmedStrikeOption.GRAPPLE), state
            )
        assert result.success is True
        assert Condition.GRAPPLED in state.get_combatant("b").conditions

    def test_shove_applies_prone_on_failed_save(self, engine, state):
        with patch("game_engine.rules.dnd_5_5e._saves.roll_dice", return_value=(2, [2])):
            engine.resolve_action(_attack(unarmed_option=UnarmedStrikeOption.SHOVE), state)
        assert Condition.PRONE in state.get_combatant("b").conditions

    def test_target_uses_better_save(self, engine, state):
        target = state.get_combatant("b")
        target.ability_scores = AbilityScoreSet(strength=8, dexterity=18)
        with patch("game_engine.rules.dnd_5_5e._saves.roll_dice", return_value=(10, [10])):
            result = engine.resolve_action(
                _attack(unarmed_option=UnarmedStrikeOption.GRAPPLE), state
            )
        # DC 8 + 0 + 2 = 10; DEX save 10 + 4 = 14 ≥ 10 → escape
        assert result.success is False

    def test_dodging_target_gets_dex_save_advantage_vs_shove(self, engine, state):
        """2024 PHB: Dodge grants advantage on DEX saves. A dodging target choosing
        DEX for a shove must use roll_with_advantage, not a flat roll."""
        target = state.get_combatant("b")
        # Give target higher DEX so it picks DEX over STR.
        target.ability_scores = AbilityScoreSet(strength=8, dexterity=18)
        # Target uses Dodge.
        engine.resolve_action(Action(ActionType.DODGE, "b", None), state)
        # Attacker's turn — shove the dodging target.
        state.reset_turn("a")
        with patch(
            "game_engine.rules.dnd_5_5e._saves.roll_with_advantage", return_value=(15, [15, 3])
        ) as mock_adv:
            engine.resolve_action(_attack(unarmed_option=UnarmedStrikeOption.SHOVE), state)
        mock_adv.assert_called_once()

    def test_non_dodging_target_uses_flat_roll_vs_shove(self, engine, state):
        """Without Dodge the target rolls a plain d20, not with advantage."""
        target = state.get_combatant("b")
        target.ability_scores = AbilityScoreSet(strength=8, dexterity=18)
        with patch(
            "game_engine.rules.dnd_5_5e._saves.roll_dice", return_value=(10, [10])
        ) as mock_flat:
            engine.resolve_action(_attack(unarmed_option=UnarmedStrikeOption.SHOVE), state)
        mock_flat.assert_called_once()


class TestExtraAttack:
    """ACT-01/ACT-05: attacks-per-Attack-action by class level, and
    validation running before any economy slot is consumed."""

    def test_level5_fighter_makes_two_attacks_then_third_is_rejected(self, engine):
        state = CombatStateData(combatants=[_char("a", level=5), _char("b")])
        with patch(f"{ATTACKS}.roll_dice", return_value=(15, [15])):
            first = engine.resolve_action(_attack(), state)
            second = engine.resolve_action(_attack(), state)
            third = engine.resolve_action(_attack(), state)
        assert first.success and second.success
        assert third.success is False
        assert third.log_entry["error"] == "action_used"
        assert state.turn_state_for("a").attacks_made == 2

    def test_extra_attack_survives_begin_turn_reset(self, engine):
        state = CombatStateData(combatants=[_char("a", level=5), _char("b")])
        # roll_dice now also serves damage rolls (ACT-09) — alternate a
        # comfortable-hit attack roll with a small damage roll so 4 hits
        # don't accidentally drop "b" to 0 HP and grant Prone advantage on
        # the later attacks (which would fall through to the real,
        # unmocked roll_with_advantage and make this test flaky).
        hits = [(15, [15]), (1, [1]), (15, [15]), (1, [1])]
        with patch(f"{ATTACKS}.roll_dice", side_effect=hits):
            engine.resolve_action(_attack(), state)
            engine.resolve_action(_attack(), state)
        engine.begin_turn(state.get_combatant("a"), state)
        with patch(f"{ATTACKS}.roll_dice", side_effect=list(hits)):
            first = engine.resolve_action(_attack(), state)
            second = engine.resolve_action(_attack(), state)
        assert first.success and second.success
        assert state.turn_state_for("a").attacks_made == 2

    def test_multiclass_takes_best_extra_attack_tier(self, engine):
        # Fighter 11 (3 attacks) / Barbarian 5 (2 attacks) — 2024 PHB: Extra
        # Attack features don't stack, so the higher tier wins, not the sum.
        from game_engine.types import ClassLevelEntry

        actor = _char(
            "a",
            level=16,
            class_levels=[
                ClassLevelEntry(character_class=CharacterClass.FIGHTER, level=11),
                ClassLevelEntry(character_class=CharacterClass.BARBARIAN, level=5),
            ],
        )
        state = CombatStateData(combatants=[actor, _char("b")])
        with patch(f"{ATTACKS}.roll_dice", return_value=(15, [15])):
            for _ in range(3):
                result = engine.resolve_action(_attack(), state)
                assert result.success is True
            fourth = engine.resolve_action(_attack(), state)
        assert fourth.success is False
        assert fourth.log_entry["error"] == "action_used"
