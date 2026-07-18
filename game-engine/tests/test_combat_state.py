"""
Tests for game_engine.types.combat_state — CombatStateData, AttackDetails,
ReadiedAction, TurnState (incl. serialisation, persisted by the API between
requests).

Split from test_types.py (file-length guideline).
"""

from __future__ import annotations

from game_engine.types import (
    Ability,
    AttackDetails,
    CharacterClass,
    CharacterSheet,
    CombatStateData,
    DamageType,
    EffectExpiry,
    ReadiedAction,
    TurnState,
    WeaponMastery,
)

# ---------------------------------------------------------------------------
# CombatStateData
# ---------------------------------------------------------------------------


class TestCombatStateData:
    def test_default_construction(self):
        state = CombatStateData()
        assert state.combatants == []
        assert state.round_number == 1
        assert state.current_turn_index == 0

    def test_get_combatant_found(self):
        char = CharacterSheet(id="hero-1", name="Hero", level=1, char_class=CharacterClass.FIGHTER)
        state = CombatStateData(combatants=[char])
        found = state.get_combatant("hero-1")
        assert found is char

    def test_get_combatant_not_found(self):
        state = CombatStateData()
        assert state.get_combatant("nonexistent") is None

    def test_reset_turn_clears_economy_only(self):
        state = CombatStateData(round_number=1)
        ts = state.turn_state_for("a")
        ts.action_used = True
        ts.bonus_action_used = True
        ts.reaction_used = True
        ts.movement_used_ft = 30
        ts.attacks_made = 2
        ts.dodging = True
        ts.disengaging = True
        ts.dashing = True
        ts.hidden = True

        state.reset_turn("a")

        reset = state.turn_state_for("a")
        assert reset.action_used is False
        assert reset.bonus_action_used is False
        assert reset.reaction_used is False
        assert reset.movement_used_ft == 0
        assert reset.attacks_made == 0
        assert reset.dodging is False
        assert reset.disengaging is False
        assert reset.dashing is False
        # Hide is a cross-turn effect (Invisible until attack/verbal-spell/
        # found) — a bare turn reset must never clear it.
        assert reset.hidden is True

    def test_grant_vex_survives_attacker_next_turn_expires_after(self):
        state = CombatStateData(round_number=1)
        state.grant_vex("a", "b")
        assert state.turn_state_for("a").vexed_target_id == "b"

        # "before the end of your next turn" — survives through round 2
        # (attacker a's next turn).
        state.round_number = 2
        state.reset_turn("a")
        assert state.turn_state_for("a").vexed_target_id == "b"

        # Cleared once round 3 begins (the turn after a's next turn).
        state.round_number = 3
        state.reset_turn("a")
        assert state.turn_state_for("a").vexed_target_id is None

    def test_grant_sap_expires_at_start_of_sappers_next_turn(self):
        state = CombatStateData(round_number=1)
        state.grant_sap("a", "b")
        assert state.turn_state_for("b").sapped is True

        # Unrelated combatant's turn beginning must not clear it.
        state.reset_turn("c")
        assert state.turn_state_for("b").sapped is True

        # Sapper a's next turn (round 2) clears it if unused.
        state.round_number = 2
        state.reset_turn("a")
        assert state.turn_state_for("b").sapped is False

    def test_grant_help_expires_at_start_of_helpers_next_turn(self):
        state = CombatStateData(round_number=1)
        state.grant_help("a", "c")
        assert state.turn_state_for("c").helped is True

        # The helped ally's own turn beginning must not clear the flag —
        # only the helper's next turn does.
        state.reset_turn("c")
        assert state.turn_state_for("c").helped is True

        state.round_number = 2
        state.reset_turn("a")
        assert state.turn_state_for("c").helped is False


# ---------------------------------------------------------------------------
# AttackDetails
# ---------------------------------------------------------------------------


class TestAttackDetails:
    def test_defaults(self):
        details = AttackDetails()
        assert details.weapon_name == "Unarmed Strike"
        # ACT-11: 2024 unarmed strike is a fixed 1 + ability modifier; "1d1"
        # always rolls 1.
        assert details.damage_dice == "1d1"
        assert details.damage_type == DamageType.BLUDGEONING
        assert details.attack_ability == Ability.STRENGTH
        assert details.is_ranged is False

    def test_custom_construction(self):
        details = AttackDetails(
            weapon_name="Longsword",
            damage_dice="1d8",
            damage_type=DamageType.SLASHING,
            attack_ability=Ability.STRENGTH,
            is_ranged=False,
        )
        assert details.weapon_name == "Longsword"
        assert details.damage_type == DamageType.SLASHING

    def test_round_trip_defaults(self):
        assert AttackDetails.from_dict(AttackDetails().to_dict()) == AttackDetails()

    def test_round_trip_all_fields_set(self):
        details = AttackDetails(
            weapon_name="Scimitar",
            damage_dice="1d6",
            damage_type=DamageType.SLASHING,
            attack_ability=Ability.DEXTERITY,
            is_ranged=False,
            mastery=WeaponMastery.NICK,
            proficient=True,
            is_offhand=True,
            long_range=True,
        )
        assert AttackDetails.from_dict(details.to_dict()) == details

    def test_from_dict_tolerates_missing_keys(self):
        details = AttackDetails.from_dict({"weapon_name": "Scimitar"})
        assert details.weapon_name == "Scimitar"
        assert details.mastery is None


# ---------------------------------------------------------------------------
# ReadiedAction serialisation
# ---------------------------------------------------------------------------


class TestReadiedActionSerde:
    def test_round_trip_with_details(self):
        readied = ReadiedAction(
            trigger="if b enters the doorway",
            target_id="b",
            details=AttackDetails(weapon_name="Longbow", is_ranged=True),
        )
        assert ReadiedAction.from_dict(readied.to_dict()) == readied

    def test_round_trip_without_details(self):
        readied = ReadiedAction(trigger="", target_id=None, details=None)
        assert ReadiedAction.from_dict(readied.to_dict()) == readied


# ---------------------------------------------------------------------------
# TurnState serialisation (persisted by the API between requests)
# ---------------------------------------------------------------------------


class TestTurnStateSerde:
    def test_round_trip_defaults(self):
        ts = TurnState()
        assert TurnState.from_dict(ts.to_dict()) == ts

    def test_round_trip_all_fields_set(self):
        ts = TurnState(
            action_used=True,
            bonus_action_used=True,
            reaction_used=True,
            movement_used_ft=25,
            attacks_made=2,
            dodging=True,
            disengaging=True,
            dashing=True,
            hidden=True,
            light_attack_used=True,
            leveled_spell_cast=True,
            helped=True,
            helped_expiry=EffectExpiry("helper-1", 3),
            sapped=True,
            sapped_expiry=EffectExpiry("sapper-1", 4),
            vexed_target_id="target-7",
            vexed_expiry=EffectExpiry("attacker-1", 5),
            readied=ReadiedAction("if b moves", "b", AttackDetails(weapon_name="Dagger")),
        )
        assert TurnState.from_dict(ts.to_dict()) == ts

    def test_from_dict_tolerates_missing_keys(self):
        ts = TurnState.from_dict({"action_used": True})
        assert ts.action_used is True
        assert ts.bonus_action_used is False
        assert ts.vexed_target_id is None
        assert ts.readied is None

    def test_reset_turn_clears_unused_readied_action(self):
        state = CombatStateData(round_number=1)
        ts = state.turn_state_for("a")
        ts.readied = ReadiedAction("if b moves", "b", None)
        state.reset_turn("a")
        assert state.turn_state_for("a").readied is None
