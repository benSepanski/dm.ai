"""Tests for 2024 attack resolution: advantage, cover, crits, masteries,
two-weapon fighting, unarmed options, and the action economy."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from game_engine.interface import Action
from game_engine.rules.dnd_5_5e._actions import provokes_opportunity_attack
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
            patch(f"{ATTACKS}.dice_roll", side_effect=[(3, [3]), (4, [4])]),
        ):
            result = engine.resolve_action(_attack(), state)
        assert result.log_entry["critical"] is True
        assert result.damage == 7

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
        with (
            patch(f"{ATTACKS}.roll_dice", return_value=(15, [15])),
            patch(f"{ATTACKS}.dice_roll", return_value=(4, [4])),
        ):
            result = engine.resolve_action(_attack(is_offhand=True), state)
        assert result.damage == 4

    def test_twf_style_adds_ability_mod(self, engine, state):
        actor = state.get_combatant("a")
        actor.ability_scores = AbilityScoreSet(strength=16)
        actor.feats.append(Feat.TWO_WEAPON_FIGHTING)
        with (
            patch(f"{ATTACKS}.roll_dice", return_value=(15, [15])),
            patch(f"{ATTACKS}.dice_roll", return_value=(4, [4])),
        ):
            result = engine.resolve_action(_attack(is_offhand=True), state)
        assert result.damage == 7

    def test_offhand_consumes_bonus_action(self, engine, state):
        with patch(f"{ATTACKS}.roll_dice", return_value=(15, [15])):
            engine.resolve_action(_attack(is_offhand=True), state)
            second = engine.resolve_action(_attack(is_offhand=True), state)
        assert second.success is False
        assert second.log_entry["error"] == "bonus_action_used"


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
        with patch(f"{ATTACKS}.roll_dice", return_value=(15, [15])):
            engine.resolve_action(_attack(), state)
            engine.resolve_action(_attack(), state)
        engine.begin_turn(state.get_combatant("a"), state)
        with patch(f"{ATTACKS}.roll_dice", return_value=(15, [15])):
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


class TestActionEconomyAndConcentration:
    def test_action_used_once_per_turn(self, engine, state):
        # Level-1 fighter: no Extra Attack, so a single attack already spends
        # the action (see TestExtraAttack for the level-5+ multi-attack case).
        with patch(f"{ATTACKS}.roll_dice", return_value=(15, [15])):
            engine.resolve_action(_attack(), state)
            second = engine.resolve_action(_attack(), state)
        assert second.success is False
        assert second.log_entry["error"] == "action_used"

    def test_total_cover_rejection_consumes_no_action_slot(self, engine, state):
        """ACT-05: a rejected attack (total cover) must not burn the action —
        the actor can retry against a legal target."""
        result = engine.resolve_action(_attack(target_cover=CoverType.TOTAL), state)
        assert result.success is False
        assert state.turn_state_for("a").action_used is False
        with patch(f"{ATTACKS}.roll_dice", return_value=(15, [15])):
            retry = engine.resolve_action(_attack(), state)
        assert retry.success is True

    def test_unknown_actor_creates_no_ghost_turn_state(self, engine, state):
        """ACT-05: an action from an actor absent from combat must not create
        a TurnState entry for it."""
        result = engine.resolve_action(_attack(actor="ghost"), state)
        assert result.success is False
        assert result.log_entry["error"] == "actor_not_found"
        assert "ghost" not in state.turn_states

    def test_nick_offhand_attack_does_not_consume_bonus_action(self, engine, state):
        actor = state.get_combatant("a")
        actor.weapon_masteries = ["Scimitar"]
        with patch(f"{ATTACKS}.roll_dice", return_value=(15, [15])):
            result = engine.resolve_action(
                _attack(weapon_name="Scimitar", mastery=WeaponMastery.NICK, is_offhand=True),
                state,
            )
        assert result.success is True
        assert state.turn_state_for("a").bonus_action_used is False
        assert state.turn_state_for("a").nick_used is True

    def test_nick_offhand_attack_limited_to_once_per_turn(self, engine, state):
        actor = state.get_combatant("a")
        actor.weapon_masteries = ["Scimitar"]
        with patch(f"{ATTACKS}.roll_dice", return_value=(15, [15])):
            engine.resolve_action(
                _attack(weapon_name="Scimitar", mastery=WeaponMastery.NICK, is_offhand=True),
                state,
            )
            second = engine.resolve_action(
                _attack(weapon_name="Scimitar", mastery=WeaponMastery.NICK, is_offhand=True),
                state,
            )
        assert second.success is False
        assert second.log_entry["error"] == "nick_used"

    def test_nick_without_mastery_still_consumes_bonus_action(self, engine, state):
        # No Nick mastery unlocked for this weapon: behaves like ordinary TWF.
        with patch(f"{ATTACKS}.roll_dice", return_value=(15, [15])):
            engine.resolve_action(
                _attack(weapon_name="Scimitar", mastery=WeaponMastery.NICK, is_offhand=True),
                state,
            )
            second = engine.resolve_action(
                _attack(weapon_name="Scimitar", mastery=WeaponMastery.NICK, is_offhand=True),
                state,
            )
        assert second.success is False
        assert second.log_entry["error"] == "bonus_action_used"

    def test_begin_turn_resets_economy(self, engine, state):
        with patch(f"{ATTACKS}.roll_dice", return_value=(15, [15])):
            engine.resolve_action(_attack(), state)
        engine.begin_turn(state.get_combatant("a"), state)
        with patch(f"{ATTACKS}.roll_dice", return_value=(15, [15])):
            result = engine.resolve_action(_attack(), state)
        assert result.success is True

    def test_begin_turn_does_not_clear_cross_turn_effect_flags(self, engine, state):
        """begin_turn resets action economy but not Help/Sap/Vex/Hide — those
        expire on their own rule-defined trigger (see CombatStateData.reset_turn)."""
        ts = state.turn_state_for("a")
        ts.hidden = True
        engine.begin_turn(state.get_combatant("a"), state)
        assert state.turn_state_for("a").hidden is True

    def test_damage_forces_concentration_save(self, engine, state):
        target = state.get_combatant("b")
        target.concentrating_on = "Bless"
        with (
            patch(f"{ATTACKS}.roll_dice", return_value=(15, [15])),
            patch(f"{ATTACKS}.dice_roll", return_value=(6, [6])),
            patch("game_engine.rules.dnd_5_5e._saves.roll_dice", return_value=(2, [2])),
        ):
            result = engine.resolve_action(_attack(), state)
        assert result.log_entry["concentration_broken"] == "Bless"
        assert target.concentrating_on is None

    def test_disengage_suppresses_opportunity_attacks(self, engine, state):
        assert provokes_opportunity_attack("a", state) is True
        engine.resolve_action(Action(ActionType.DISENGAGE, "a", None), state)
        assert provokes_opportunity_attack("a", state) is False

    def test_unconscious_actor_cannot_act(self, engine, state):
        actor = state.get_combatant("a")
        actor.conditions.append(Condition.UNCONSCIOUS)
        result = engine.resolve_action(_attack(), state)
        assert result.success is False
        assert result.log_entry["error"] == "cannot_act"
        assert engine.get_available_actions(actor, state) == []

    def test_magic_action_only_for_casters(self, engine, state):
        actor = state.get_combatant("a")
        actions = {a.action_type for a in engine.get_available_actions(actor, state)}
        assert ActionType.MAGIC not in actions
        actor.prepared_spells = ["Fire Bolt"]
        actions = {a.action_type for a in engine.get_available_actions(actor, state)}
        assert ActionType.MAGIC in actions


class TestHelpAndHideSurviveBeginTurn:
    """2024 PHB: Help and Hide grant advantage that outlives a turn boundary
    other than the granting one — begin_turn must not wipe them early."""

    def test_help_grants_allys_next_attack_advantage_after_allys_begin_turn(self, engine):
        state = CombatStateData(combatants=[_char("a"), _char("b"), _char("c")])
        engine.resolve_action(Action(ActionType.HELP, "a", "c"), state)
        assert state.turn_state_for("c").helped is True

        # Help expires at the start of the helper's (a's) next turn, not
        # the helped ally's (c's) own turn.
        engine.begin_turn(state.get_combatant("c"), state)
        assert state.turn_state_for("c").helped is True

        with patch(f"{ATTACKS}.roll_with_advantage", return_value=(15, [15, 3])) as adv:
            engine.resolve_action(_attack(actor="c", target="b"), state)
        adv.assert_called_once()
        assert state.turn_state_for("c").helped is False

    def test_help_expires_at_start_of_helpers_next_turn(self, engine):
        state = CombatStateData(combatants=[_char("a"), _char("b"), _char("c")])
        engine.resolve_action(Action(ActionType.HELP, "a", "c"), state)
        state.round_number = 2
        engine.begin_turn(state.get_combatant("a"), state)
        assert state.turn_state_for("c").helped is False

    def test_hide_grant_survives_own_begin_turn_until_hider_attacks(self, engine, state):
        actor = state.get_combatant("a")
        with patch("game_engine.rules.dnd_5_5e._checks.roll_dice", return_value=(18, [18])):
            engine.resolve_action(Action(ActionType.HIDE, "a", None), state)
        assert state.turn_state_for("a").hidden is True

        engine.begin_turn(actor, state)
        assert state.turn_state_for("a").hidden is True

        with patch(f"{ATTACKS}.roll_with_advantage", return_value=(15, [15, 3])) as adv:
            engine.resolve_action(_attack(), state)
        adv.assert_called_once()
        assert state.turn_state_for("a").hidden is False
