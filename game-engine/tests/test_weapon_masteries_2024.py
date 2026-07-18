"""Tests for 2024 weapon mastery on-hit effects (Graze, Topple, Vex, Sap,
Slow, Cleave). Split out of test_attacks_2024.py (AGENTS.md #3, <=600 lines
per test file)."""

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
    CreatureSize,
    DamageType,
    DiceNotation,
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

    def test_graze_deals_zero_with_negative_ability_mod(self, engine, state):
        """ACT-17: Graze deals damage equal to the ability modifier — there is
        no invented minimum-1 floor, so a negative modifier deals 0."""
        actor = state.get_combatant("a")
        actor.ability_scores = AbilityScoreSet(strength=6)  # STR −2
        actor.weapon_masteries = ["Greatsword"]
        with patch(f"{ATTACKS}.roll_dice", return_value=(2, [2])):
            result = engine.resolve_action(
                _attack(weapon_name="Greatsword", mastery=WeaponMastery.GRAZE), state
            )
        assert result.success is False
        assert result.damage == 0
        assert state.get_combatant("b").hp_current == 30

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

    def test_topple_does_not_affect_prone_immune_target(self, engine, state):
        """EFF-10: Topple must honor is_immune_to_condition like every other
        condition-application path, not append Prone unconditionally."""
        actor = state.get_combatant("a")
        actor.weapon_masteries = ["Maul"]
        state.get_combatant("b").condition_immunities = [Condition.PRONE]
        with (
            patch(f"{ATTACKS}.roll_dice", return_value=(18, [18])),
            patch("game_engine.rules.dnd_5_5e._saves.roll_dice", return_value=(2, [2])),
        ):
            result = engine.resolve_action(
                _attack(weapon_name="Maul", mastery=WeaponMastery.TOPPLE), state
            )
        assert Condition.PRONE not in state.get_combatant("b").conditions
        assert Condition.PRONE not in result.conditions_applied

    def test_slow_reduces_speed_until_attackers_next_turn(self, engine, state):
        """ACT-07: Slow reduces the target's speed by 10 ft until the start
        of the attacker's own next turn, then restores it."""
        from game_engine.rules.dnd_5_5e._actions import _effective_speed

        actor = state.get_combatant("a")
        target = state.get_combatant("b")
        actor.weapon_masteries = ["Club"]
        assert target.speed == 30
        with patch(f"{ATTACKS}.roll_dice", return_value=(18, [18])):
            engine.resolve_action(_attack(weapon_name="Club", mastery=WeaponMastery.SLOW), state)

        target_ts = state.turn_state_for("b")
        assert target_ts.slowed is True
        assert _effective_speed(target, target_ts) == 20

        # Slow lasts until the start of the *attacker's* next turn, not the
        # target's — the target's own begin_turn must not clear it.
        engine.begin_turn(target, state)
        assert state.turn_state_for("b").slowed is True
        assert _effective_speed(target, state.turn_state_for("b")) == 20

        state.round_number = 2
        engine.begin_turn(actor, state)
        assert state.turn_state_for("b").slowed is False
        assert _effective_speed(target, state.turn_state_for("b")) == 30

    def test_push_moves_large_or_smaller_target(self, engine, state):
        """ACT-07: Push moves a Large-or-smaller target 10 ft on a hit."""
        actor = state.get_combatant("a")
        actor.weapon_masteries = ["Greatclub"]
        state.get_combatant("b").size = CreatureSize.LARGE
        with patch(f"{ATTACKS}.roll_dice", return_value=(18, [18])):
            result = engine.resolve_action(
                _attack(weapon_name="Greatclub", mastery=WeaponMastery.PUSH), state
            )
        assert result.log_entry["pushed_ft"] == 10
        assert "push_too_large" not in result.log_entry

    def test_push_does_not_move_huge_target(self, engine, state):
        """ACT-07: a Huge (larger than Large) target is unaffected by Push."""
        actor = state.get_combatant("a")
        actor.weapon_masteries = ["Greatclub"]
        state.get_combatant("b").size = CreatureSize.HUGE
        with patch(f"{ATTACKS}.roll_dice", return_value=(18, [18])):
            result = engine.resolve_action(
                _attack(weapon_name="Greatclub", mastery=WeaponMastery.PUSH), state
            )
        assert result.log_entry["pushed_ft"] == 0
        assert result.log_entry["push_too_large"] is True

    def test_cleave_grants_free_followup_against_a_different_creature(self, engine):
        state = CombatStateData(combatants=[_char("a"), _char("b"), _char("c", ac=5)])
        actor = state.get_combatant("a")
        actor.ability_scores = AbilityScoreSet(strength=16)  # +3 mod
        actor.weapon_masteries = ["Greataxe"]
        with patch(f"{ATTACKS}.roll_dice", return_value=(18, [18])):
            first = engine.resolve_action(
                _attack(weapon_name="Greataxe", mastery=WeaponMastery.CLEAVE), state
            )
        assert first.success is True
        ts = state.turn_state_for("a")
        assert ts.cleave_available is True
        assert ts.cleave_original_target_id == "b"

        cleave_action = Action(
            action_type=ActionType.CLEAVE_ATTACK,
            actor_id="a",
            target_id="c",
            details=AttackDetails(
                weapon_name="Greataxe",
                damage_dice=DiceNotation("1d6"),
                mastery=WeaponMastery.CLEAVE,
            ),
        )
        with patch(f"{ATTACKS}.roll_dice", return_value=(18, [18])):
            second = engine.resolve_action(cleave_action, state)
        assert second.success is True
        # 2024 PHB: Cleave's follow-up omits the ability modifier entirely —
        # roll_dice is mocked to (18, [18]) for both the attack and damage
        # rolls, so the dice-only total is 18, not 18 + 3.
        assert second.damage == 18
        assert state.turn_state_for("a").cleave_used is True
        # The follow-up doesn't count against the Extra Attack pool — a
        # level-1 fighter's one real swing left attacks_made at 1.
        assert state.turn_state_for("a").attacks_made == 1

    def test_cleave_rejects_same_target_and_second_use(self, engine):
        state = CombatStateData(combatants=[_char("a"), _char("b"), _char("c")])
        actor = state.get_combatant("a")
        actor.weapon_masteries = ["Greataxe"]
        with patch(f"{ATTACKS}.roll_dice", return_value=(18, [18])):
            engine.resolve_action(
                _attack(weapon_name="Greataxe", mastery=WeaponMastery.CLEAVE), state
            )

        same_target = Action(
            action_type=ActionType.CLEAVE_ATTACK,
            actor_id="a",
            target_id="b",
            details=_attack().details,
        )
        result = engine.resolve_action(same_target, state)
        assert result.success is False
        assert result.log_entry["error"] == "cleave_same_target"

        with patch(f"{ATTACKS}.roll_dice", return_value=(18, [18])):
            engine.resolve_action(
                Action(
                    action_type=ActionType.CLEAVE_ATTACK,
                    actor_id="a",
                    target_id="c",
                    details=_attack().details,
                ),
                state,
            )
        second_use = Action(
            action_type=ActionType.CLEAVE_ATTACK,
            actor_id="a",
            target_id="c",
            details=_attack().details,
        )
        result = engine.resolve_action(second_use, state)
        assert result.success is False
        assert result.log_entry["error"] == "cleave_unavailable"

    def test_cleave_without_a_prior_grant_is_rejected(self, engine, state):
        result = engine.resolve_action(
            Action(action_type=ActionType.CLEAVE_ATTACK, actor_id="a", target_id="b"), state
        )
        assert result.success is False
        assert result.log_entry["error"] == "cleave_unavailable"

    def test_cleave_followup_between_extra_attack_swings_does_not_exhaust_pool(self, engine):
        """ACT-07: a Cleave follow-up fired between a level-5 fighter's two
        Extra Attack swings must not count against the 2-attack pool — it
        shares _resolve_attack's attacks_made increment with real swings, so
        the follow-up must undo it (see _reactions.resolve_cleave_attack)."""
        state = CombatStateData(combatants=[_char("a", level=5), _char("b"), _char("c")])
        actor = state.get_combatant("a")
        actor.weapon_masteries = ["Greataxe"]
        with patch(f"{ATTACKS}.roll_dice", return_value=(15, [15])):
            first_swing = engine.resolve_action(
                _attack(weapon_name="Greataxe", mastery=WeaponMastery.CLEAVE), state
            )
            cleave = engine.resolve_action(
                Action(
                    action_type=ActionType.CLEAVE_ATTACK,
                    actor_id="a",
                    target_id="c",
                    details=_attack(weapon_name="Greataxe", mastery=WeaponMastery.CLEAVE).details,
                ),
                state,
            )
            second_swing = engine.resolve_action(_attack(), state)
        assert first_swing.success and cleave.success
        assert second_swing.success is True
        assert state.turn_state_for("a").attacks_made == 2
