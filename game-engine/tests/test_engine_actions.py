"""Tests for DnD55eEngine.resolve_action() — attack resolution."""

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
    DamageType,
    DiceNotation,
)


def _make_fighter(
    char_id: str = "fighter-1",
    level: int = 1,
    strength: int = 10,
    ac: int = 10,
    hp_current: int = 20,
    hp_max: int = 20,
) -> CharacterSheet:
    return CharacterSheet(
        id=char_id,
        name="Fighter",
        level=level,
        char_class=CharacterClass.FIGHTER,
        ability_scores=AbilityScoreSet(strength=strength),
        hp_current=hp_current,
        hp_max=hp_max,
        ac=ac,
    )


def _attack_action(actor_id: str, target_id: str) -> Action:
    return Action(
        action_type=ActionType.ATTACK,
        actor_id=actor_id,
        target_id=target_id,
        details=AttackDetails(damage_dice=DiceNotation("1d6"), damage_type=DamageType.SLASHING),
    )


@pytest.fixture
def engine() -> DnD55eEngine:
    return DnD55eEngine()


@pytest.fixture
def combat_state() -> CombatStateData:
    attacker = _make_fighter("attacker", strength=10, ac=10)
    defender = _make_fighter("defender", strength=10, ac=15, hp_current=30, hp_max=30)
    return CombatStateData(combatants=[attacker, defender])


class TestNatural20CriticalHit:
    def test_natural_20_always_hits(self, engine: DnD55eEngine, combat_state: CombatStateData):
        action = _attack_action("attacker", "defender")
        # Force roll_dice to return 20 (natural 20 — always hits regardless of AC).
        with patch("game_engine.rules.dnd_5_5e._attacks.roll_dice", return_value=(20, [20])):
            result = engine.resolve_action(action, combat_state)
        assert result.success is True
        assert result.damage > 0
        assert "CRITICAL HIT" in result.flavor_text

    def test_natural_20_doubles_damage_dice(
        self, engine: DnD55eEngine, combat_state: CombatStateData
    ):
        action = _attack_action("attacker", "defender")
        with patch("game_engine.rules.dnd_5_5e._attacks.roll_dice", return_value=(20, [20])):
            # dice() is called twice on critical — mock it to return fixed values
            with patch(
                "game_engine.rules.dnd_5_5e._attacks.dice_roll",
                side_effect=[(3, [3]), (4, [4])],
            ):
                result = engine.resolve_action(action, combat_state)
        # 3 + 4 + STR mod (0) = 7
        assert result.damage == 7


class TestNatural1AutomaticMiss:
    def test_natural_1_always_misses(self, engine: DnD55eEngine, combat_state: CombatStateData):
        """A natural 1 must always miss even if the total would beat AC."""
        # Attacker has +100 strength modifier hypothetically — but natural 1 still misses.
        attacker = _make_fighter("attacker", strength=30, ac=10)  # STR mod = +10
        defender = _make_fighter("defender", ac=1, hp_current=30, hp_max=30)
        state = CombatStateData(combatants=[attacker, defender])
        action = _attack_action("attacker", "defender")

        with patch("game_engine.rules.dnd_5_5e._attacks.roll_dice", return_value=(1, [1])):
            result = engine.resolve_action(action, state)

        assert result.success is False
        assert result.damage == 0


class TestNormalHitAndMiss:
    def test_hits_when_total_beats_ac(self, engine: DnD55eEngine, combat_state: CombatStateData):
        # defender AC=15; roll 14 + prof(2) + str_mod(0) = 16 → hit
        action = _attack_action("attacker", "defender")
        with patch("game_engine.rules.dnd_5_5e._attacks.roll_dice", return_value=(14, [14])):
            result = engine.resolve_action(action, combat_state)
        assert result.success is True

    def test_misses_when_total_below_ac(self, engine: DnD55eEngine, combat_state: CombatStateData):
        # defender AC=15; roll 5 + prof(2) + str_mod(0) = 7 → miss
        action = _attack_action("attacker", "defender")
        with patch("game_engine.rules.dnd_5_5e._attacks.roll_dice", return_value=(5, [5])):
            result = engine.resolve_action(action, combat_state)
        assert result.success is False

    def test_damage_applied_to_target_on_hit(
        self, engine: DnD55eEngine, combat_state: CombatStateData
    ):
        action = _attack_action("attacker", "defender")
        defender = combat_state.get_combatant("defender")
        assert defender is not None
        initial_hp = defender.hp_current

        with patch("game_engine.rules.dnd_5_5e._attacks.roll_dice", return_value=(14, [14])):
            result = engine.resolve_action(action, combat_state)

        assert result.success is True
        assert defender.hp_current < initial_hp

    def test_no_damage_on_miss(self, engine: DnD55eEngine, combat_state: CombatStateData):
        action = _attack_action("attacker", "defender")
        defender = combat_state.get_combatant("defender")
        assert defender is not None
        initial_hp = defender.hp_current

        with patch("game_engine.rules.dnd_5_5e._attacks.roll_dice", return_value=(5, [5])):
            result = engine.resolve_action(action, combat_state)

        assert result.success is False
        assert result.damage == 0
        assert defender.hp_current == initial_hp


class TestMissingTarget:
    def test_missing_target_returns_failure(
        self, engine: DnD55eEngine, combat_state: CombatStateData
    ):
        action = Action(
            action_type=ActionType.ATTACK,
            actor_id="attacker",
            target_id="nonexistent-id",
        )
        result = engine.resolve_action(action, combat_state)
        assert result.success is False
        assert "No target" in result.flavor_text


class TestNonAttackActions:
    def test_dash_succeeds_with_zero_damage(
        self, engine: DnD55eEngine, combat_state: CombatStateData
    ):
        action = Action(action_type=ActionType.DASH, actor_id="attacker", target_id=None)
        result = engine.resolve_action(action, combat_state)
        assert result.success is True
        assert result.damage == 0

    def test_dodge_succeeds_with_zero_damage(
        self, engine: DnD55eEngine, combat_state: CombatStateData
    ):
        action = Action(action_type=ActionType.DODGE, actor_id="attacker", target_id=None)
        result = engine.resolve_action(action, combat_state)
        assert result.success is True
        assert result.damage == 0
