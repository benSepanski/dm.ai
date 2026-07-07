"""Tests for reaction resolution: opportunity attacks and readied actions
(ACT-02, ACT-06). Split from test_attacks_2024.py (file-length guideline) —
mirrors the ._reactions module split from ._attacks."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from game_engine.interface import Action
from game_engine.rules.dnd_5_5e.engine import DnD55eEngine
from game_engine.types import (
    ActionType,
    AttackDetails,
    CharacterClass,
    CharacterSheet,
    CombatStateData,
    DamageType,
    DiceNotation,
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


def _opportunity_attack(actor="a", target="b", **details_kwargs) -> Action:
    details_kwargs.setdefault("damage_dice", DiceNotation("1d6"))
    details_kwargs.setdefault("damage_type", DamageType.SLASHING)
    return Action(
        action_type=ActionType.OPPORTUNITY_ATTACK,
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


class TestOpportunityAttacks:
    """ACT-02: reaction economy and opportunity attacks."""

    def test_opportunity_attack_hits_and_consumes_reaction(self, engine, state):
        with patch(f"{ATTACKS}.roll_dice", return_value=(15, [15])):
            result = engine.resolve_action(_opportunity_attack(), state)
        assert result.success is True
        assert state.turn_state_for("a").reaction_used is True

    def test_second_opportunity_attack_same_round_is_rejected(self, engine, state):
        with patch(f"{ATTACKS}.roll_dice", return_value=(15, [15])):
            engine.resolve_action(_opportunity_attack(), state)
            second = engine.resolve_action(_opportunity_attack(), state)
        assert second.success is False
        assert second.log_entry["error"] == "reaction_used"

    def test_disengaged_mover_provokes_no_opportunity_attack(self, engine, state):
        engine.resolve_action(Action(ActionType.DISENGAGE, "b", None), state)
        result = engine.resolve_action(_opportunity_attack(), state)
        assert result.success is False
        assert result.log_entry["error"] == "no_opportunity"
        # Rejected — no reaction spent, so a later legitimate opportunity
        # attack this round is still available.
        assert state.turn_state_for("a").reaction_used is False

    def test_unknown_mover_is_rejected_before_spending_a_reaction(self, engine, state):
        result = engine.resolve_action(_opportunity_attack(target="ghost"), state)
        assert result.success is False
        assert result.log_entry["error"] == "target_not_found"
        assert state.turn_state_for("a").reaction_used is False

    def test_reaction_refreshes_at_start_of_reactors_own_next_turn(self, engine, state):
        with patch(f"{ATTACKS}.roll_dice", return_value=(15, [15])):
            engine.resolve_action(_opportunity_attack(), state)
        engine.begin_turn(state.get_combatant("a"), state)
        assert state.turn_state_for("a").reaction_used is False
        with patch(f"{ATTACKS}.roll_dice", return_value=(15, [15])):
            result = engine.resolve_action(_opportunity_attack(), state)
        assert result.success is True


class TestReadiedActions:
    """ACT-06: Ready stores an attack, triggered later via a reaction."""

    def test_ready_stores_the_attack_and_trigger(self, engine, state):
        action = Action(
            action_type=ActionType.READY,
            actor_id="a",
            target_id="b",
            details=AttackDetails(
                damage_dice=DiceNotation("1d6"), damage_type=DamageType.SLASHING
            ),
            readied_trigger="if b comes through the doorway",
        )
        result = engine.resolve_action(action, state)
        assert result.success is True
        readied = state.turn_state_for("a").readied
        assert readied is not None
        assert readied.trigger == "if b comes through the doorway"
        assert readied.target_id == "b"
        # Readying consumes the action, not the reaction.
        assert state.turn_state_for("a").action_used is True
        assert state.turn_state_for("a").reaction_used is False

    def test_readied_action_resolves_stored_attack_and_consumes_reaction(self, engine, state):
        engine.resolve_action(
            Action(ActionType.READY, "a", "b", AttackDetails(damage_dice=DiceNotation("1d6"))),
            state,
        )
        with patch(f"{ATTACKS}.roll_dice", return_value=(15, [15])):
            result = engine.resolve_action(Action(ActionType.READIED_ACTION, "a", None), state)
        assert result.success is True
        assert state.turn_state_for("a").readied is None
        assert state.turn_state_for("a").reaction_used is True

    def test_readied_action_with_nothing_stored_is_rejected(self, engine, state):
        result = engine.resolve_action(Action(ActionType.READIED_ACTION, "a", None), state)
        assert result.success is False
        assert result.log_entry["error"] == "no_readied_action"

    def test_readied_action_is_rejected_once_reaction_already_spent(self, engine, state):
        engine.resolve_action(
            Action(ActionType.READY, "a", "b", AttackDetails(damage_dice=DiceNotation("1d6"))),
            state,
        )
        state.turn_state_for("a").reaction_used = True
        result = engine.resolve_action(Action(ActionType.READIED_ACTION, "a", None), state)
        assert result.success is False
        assert result.log_entry["error"] == "reaction_used"

    def test_unused_readied_action_is_lost_at_start_of_readiers_own_next_turn(self, engine, state):
        engine.resolve_action(
            Action(ActionType.READY, "a", "b", AttackDetails(damage_dice=DiceNotation("1d6"))),
            state,
        )
        engine.begin_turn(state.get_combatant("a"), state)
        assert state.turn_state_for("a").readied is None
