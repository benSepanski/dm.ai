"""Tests for the 2024 attack action economy and cross-turn effect flags —
split out of test_attacks_2024.py to stay under the 600-line test-file
guideline (see AGENTS.md / CLAUDE.md golden principle #8)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from game_engine.interface import Action
from game_engine.rules.dnd_5_5e._reactions import provokes_opportunity_attack
from game_engine.rules.dnd_5_5e.engine import DnD55eEngine
from game_engine.types import (
    ActionType,
    AttackDetails,
    CharacterClass,
    CharacterSheet,
    CombatStateData,
    Condition,
    CoverType,
    DamageType,
    DiceNotation,
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
            engine.resolve_action(_attack(properties=[WeaponProperty.LIGHT]), state)
            engine.resolve_action(
                _attack(
                    weapon_name="Scimitar",
                    mastery=WeaponMastery.NICK,
                    is_offhand=True,
                    properties=[WeaponProperty.LIGHT],
                ),
                state,
            )
            second = engine.resolve_action(
                _attack(
                    weapon_name="Scimitar",
                    mastery=WeaponMastery.NICK,
                    is_offhand=True,
                    properties=[WeaponProperty.LIGHT],
                ),
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

    def test_help_grants_advantage_on_allys_hide_check(self, engine, state):
        """ACT-19: Help grants advantage on the ally's next roll of any kind,
        not just an attack roll — here the ally spends it Hiding."""
        engine.resolve_action(Action(ActionType.HELP, "b", "a"), state)
        assert state.turn_state_for("a").helped is True

        with patch(
            "game_engine.rules.dnd_5_5e._checks.roll_with_advantage", return_value=(18, [18, 3])
        ) as adv:
            engine.resolve_action(Action(ActionType.HIDE, "a", None), state)
        adv.assert_called_once()
        assert state.turn_state_for("a").helped is False

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


class TestHideConsumesArmorStealthPenalty:
    """D2/EQP-02: noisy worn armor imposes disadvantage on the Hide check."""

    def test_hide_with_noisy_armor_rolls_with_disadvantage(self, engine, state):
        state.get_combatant("a").worn_armor = "Chain Mail"
        with patch(
            "game_engine.rules.dnd_5_5e._checks.roll_with_disadvantage",
            return_value=(3, [3, 18]),
        ) as dis:
            engine.resolve_action(Action(ActionType.HIDE, "a", None), state)
        dis.assert_called_once()

    def test_hide_unarmored_rolls_plain(self, engine, state):
        with patch(
            "game_engine.rules.dnd_5_5e._checks.roll_dice", return_value=(18, [18])
        ) as plain:
            engine.resolve_action(Action(ActionType.HIDE, "a", None), state)
        plain.assert_called_once()
