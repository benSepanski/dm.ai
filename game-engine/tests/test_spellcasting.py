"""Tests for spell slot progression and spell cast resolution."""

from __future__ import annotations

from unittest.mock import patch

from game_engine.rules.dnd_5_5e._spell_resolution import cast_spell
from game_engine.rules.dnd_5_5e.data.spells import SpellData
from game_engine.rules.dnd_5_5e.spellcasting import (
    SpellcasterType,
    cantrip_dice_multiplier,
    compute_spell_slots,
    duration_rounds,
    pact_slots_for_level,
    slots_for_caster_level,
    spell_attack_bonus,
    spell_save_dc,
)
from game_engine.types import (
    Ability,
    AbilityScoreSet,
    CastingTime,
    CharacterClass,
    CharacterSheet,
    ClassLevelEntry,
    CombatStateData,
    Condition,
    DamageType,
    DiceNotation,
    SpellComponent,
    SpellRangeType,
    SpellSchool,
)

RES = "game_engine.rules.dnd_5_5e._spell_resolution"


def _caster(char_id="w", char_class=CharacterClass.WIZARD, level=5, **kwargs) -> CharacterSheet:
    defaults = dict(
        name="Caster",
        char_class=char_class,
        level=level,
        ability_scores=AbilityScoreSet(intelligence=16),
        hp_current=20,
        hp_max=20,
        class_levels=[ClassLevelEntry(char_class, level)],
    )
    defaults.update(kwargs)
    sheet = CharacterSheet(id=char_id, **defaults)
    sheet.spell_slots = compute_spell_slots(sheet.class_levels)
    return sheet


def _spell(**kwargs) -> SpellData:
    defaults = dict(
        name="Test Spell",
        level=1,
        school=SpellSchool.EVOCATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=60,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL],
        classes=[CharacterClass.WIZARD],
        description="test",
    )
    defaults.update(kwargs)
    return SpellData(**defaults)


class TestSlotTables:
    def test_full_caster_level_5(self):
        slots = slots_for_caster_level(5)
        assert [(s.slot_level, s.maximum) for s in slots] == [(1, 4), (2, 3), (3, 2)]

    def test_full_caster_level_20(self):
        slots = slots_for_caster_level(20)
        assert [(s.slot_level, s.maximum) for s in slots] == [
            (1, 4),
            (2, 3),
            (3, 3),
            (4, 3),
            (5, 3),
            (6, 2),
            (7, 2),
            (8, 1),
            (9, 1),
        ]

    def test_half_caster_paladin_level_1_has_slots(self):
        slots = compute_spell_slots([ClassLevelEntry(CharacterClass.PALADIN, 1)])
        assert [(s.slot_level, s.maximum) for s in slots] == [(1, 2)]

    def test_pact_slots(self):
        assert [(s.slot_level, s.maximum) for s in pact_slots_for_level(5)] == [(3, 2)]
        assert [(s.slot_level, s.maximum) for s in pact_slots_for_level(17)] == [(5, 4)]

    def test_multiclass_full_plus_half(self):
        # Wizard 3 + Paladin 2 → caster level 3 + 1 = 4 → [4, 3]
        slots = compute_spell_slots(
            [
                ClassLevelEntry(CharacterClass.WIZARD, 3),
                ClassLevelEntry(CharacterClass.PALADIN, 2),
            ]
        )
        assert [(s.slot_level, s.maximum) for s in slots] == [(1, 4), (2, 3)]

    def test_multiclass_pact_and_standard_slots_kept_separate(self):
        # SPL-15: Warlock 2 (pact: 2 slots at level 1) + Wizard 3 (standard:
        # [4, 2] at levels 1-2) must NOT merge the level-1 pools — only pact
        # slots are restored by a short rest, so merging would let a short
        # rest also refill standard level-1 slots.
        slots = compute_spell_slots(
            [
                ClassLevelEntry(CharacterClass.WARLOCK, 2),
                ClassLevelEntry(CharacterClass.WIZARD, 3),
            ]
        )
        assert [(s.slot_level, s.maximum, s.is_pact) for s in slots] == [
            (1, 4, False),
            (1, 2, True),
            (2, 2, False),
        ]

    def test_caster_types_override_is_hashable(self):
        # SPL-22: ClassLevelEntry must be usable as a dict key so the
        # caster_types override can be built from the caller's own entries.
        entries = [ClassLevelEntry(CharacterClass.FIGHTER, 5)]
        slots = compute_spell_slots(entries, caster_types={entries[0]: SpellcasterType.FULL})
        assert [(s.slot_level, s.maximum) for s in slots] == [(1, 4), (2, 3), (3, 2)]

    def test_dc_and_attack_bonus(self):
        caster = _caster()  # level 5, INT 16
        assert spell_save_dc(caster, Ability.INTELLIGENCE) == 14  # 8 + 3 + 3
        assert spell_attack_bonus(caster, Ability.INTELLIGENCE) == 6

    def test_cantrip_scaling_breakpoints(self):
        assert cantrip_dice_multiplier(1) == 1
        assert cantrip_dice_multiplier(5) == 2
        assert cantrip_dice_multiplier(11) == 3
        assert cantrip_dice_multiplier(17) == 4


class TestDurationRounds:
    def test_short_durations_unchanged(self):
        assert duration_rounds("1 round") == 1
        assert duration_rounds("1 minute") == 10
        assert duration_rounds("Concentration, up to 10 minutes") == 100
        assert duration_rounds("1 hour") == 600

    def test_multi_hour_durations_no_longer_silently_none(self):
        # SPL-23: previously only the exact literal "1 hour" matched, so
        # "8 hours" (a real duration in the spell data) fell through to None.
        assert duration_rounds("8 hours") == 4800
        assert duration_rounds("24 hours") == 14400

    def test_unparseable_duration_is_none(self):
        assert duration_rounds("Instantaneous") is None
        assert duration_rounds("Until dispelled") is None


class TestCasting:
    def _state(self, caster, target_hp=30) -> CombatStateData:
        target = CharacterSheet(
            id="t",
            name="Target",
            level=1,
            char_class=CharacterClass.FIGHTER,
            hp_current=target_hp,
            hp_max=target_hp,
            ac=10,
        )
        return CombatStateData(combatants=[caster, target])

    def test_consumes_slot(self):
        caster = _caster()
        state = self._state(caster)
        spell = _spell(
            save=Ability.DEXTERITY,
            damage_type=DamageType.FIRE,
            damage_dice=DiceNotation("3d6"),
            half_damage_on_save=True,
        )
        before = next(s for s in caster.spell_slots if s.slot_level == 1).remaining
        result = cast_spell(caster, spell, Ability.INTELLIGENCE, state, ["t"])
        assert result.success
        after = next(s for s in caster.spell_slots if s.slot_level == 1).remaining
        assert after == before - 1

    def test_no_slot_fails(self):
        caster = _caster()
        for slot in caster.spell_slots:
            slot.remaining = 0
        result = cast_spell(caster, _spell(), Ability.INTELLIGENCE, self._state(caster), [])
        assert not result.success
        assert result.error == "no_slot"

    def test_upcast_adds_dice(self):
        caster = _caster()
        state = self._state(caster)
        spell = _spell(
            damage_type=DamageType.FIRE,
            damage_dice=DiceNotation("8d6"),
            upcast_damage_per_slot=DiceNotation("1d6"),
            save=Ability.DEXTERITY,
            half_damage_on_save=True,
            level=3,
        )
        with patch(f"{RES}.roll_dice") as mock_roll:
            mock_roll.return_value = (30, [])
            cast_spell(caster, spell, Ability.INTELLIGENCE, state, ["t"], slot_level=3)
            count_base = mock_roll.call_args_list[0][0][0]
        caster.spell_slots = compute_spell_slots([ClassLevelEntry(CharacterClass.WIZARD, 9)])
        state.reset_turn(caster.id)  # simulate a new turn: SPL-06 allows one leveled spell each
        with patch(f"{RES}.roll_dice") as mock_roll:
            mock_roll.return_value = (40, [])
            cast_spell(caster, spell, Ability.INTELLIGENCE, state, ["t"], slot_level=5)
            count_upcast = mock_roll.call_args_list[0][0][0]
        assert count_base == 8
        assert count_upcast == 10

    def test_upcast_scales_flat_modifier(self):
        # SPL-05: Magic Missile's upcast notation "1d4+1" should scale its
        # own flat modifier per extra slot level, not just its dice count —
        # a level-2 slot should deal 4d4+4, not 4d4+3.
        caster = _caster()
        state = self._state(caster)
        spell = _spell(
            damage_type=DamageType.FORCE,
            damage_dice=DiceNotation("3d4+3"),
            upcast_damage_per_slot=DiceNotation("1d4+1"),
            level=1,
        )
        with patch(f"{RES}.roll_dice") as mock_roll:
            mock_roll.return_value = (10, [])
            cast_spell(caster, spell, Ability.INTELLIGENCE, state, ["t"], slot_level=1)
            count_base, _, mod_base = mock_roll.call_args_list[0][0]
        caster.spell_slots = compute_spell_slots([ClassLevelEntry(CharacterClass.WIZARD, 9)])
        state.reset_turn(caster.id)  # simulate a new turn: SPL-06 allows one leveled spell each
        with patch(f"{RES}.roll_dice") as mock_roll:
            mock_roll.return_value = (10, [])
            cast_spell(caster, spell, Ability.INTELLIGENCE, state, ["t"], slot_level=3)
            count_upcast, _, mod_upcast = mock_roll.call_args_list[0][0]
        assert (count_base, mod_base) == (3, 3)
        assert (count_upcast, mod_upcast) == (5, 5)  # +2 slot levels → +2 dice, +2 flat

    def test_secondary_pool_upcasts_when_configured(self):
        # SPL-17: a dual-damage spell whose secondary_upcast_damage_per_slot
        # is set (e.g. Flame Strike) scales both pools on upcast.
        caster = _caster()
        state = self._state(caster)
        caster.spell_slots = compute_spell_slots([ClassLevelEntry(CharacterClass.WIZARD, 11)])
        spell = _spell(
            damage_type=DamageType.FIRE,
            damage_dice=DiceNotation("5d6"),
            upcast_damage_per_slot=DiceNotation("1d6"),
            secondary_damage_type=DamageType.RADIANT,
            secondary_damage_dice=DiceNotation("5d6"),
            secondary_upcast_damage_per_slot=DiceNotation("1d6"),
            level=5,
        )
        with patch(f"{RES}.roll_dice") as mock_roll:
            mock_roll.return_value = (10, [])
            cast_spell(caster, spell, Ability.INTELLIGENCE, state, ["t"], slot_level=6)
            primary_count = mock_roll.call_args_list[0][0][0]
            secondary_count = mock_roll.call_args_list[1][0][0]
        assert (primary_count, secondary_count) == (6, 6)  # both +1 die for the +1 slot level

    def test_secondary_pool_fixed_when_not_configured(self):
        # SPL-17/SPL-19: Ice Storm leaves secondary_upcast_damage_per_slot
        # unset, so its cold pool stays fixed while bludgeoning upcasts.
        caster = _caster()
        state = self._state(caster)
        caster.spell_slots = compute_spell_slots([ClassLevelEntry(CharacterClass.WIZARD, 9)])
        spell = _spell(
            damage_type=DamageType.BLUDGEONING,
            damage_dice=DiceNotation("2d10"),
            upcast_damage_per_slot=DiceNotation("1d10"),
            secondary_damage_type=DamageType.COLD,
            secondary_damage_dice=DiceNotation("4d6"),
            level=4,
        )
        with patch(f"{RES}.roll_dice") as mock_roll:
            mock_roll.return_value = (10, [])
            cast_spell(caster, spell, Ability.INTELLIGENCE, state, ["t"], slot_level=5)
            primary_count = mock_roll.call_args_list[0][0][0]
            secondary_count = mock_roll.call_args_list[1][0][0]
        assert primary_count == 3  # 2 + 1 slot level above base
        assert secondary_count == 4  # unchanged

    def test_cantrip_needs_no_slot_and_scales(self):
        caster = _caster(level=11)
        state = self._state(caster)
        spell = _spell(
            level=0,
            attack_roll=True,
            damage_type=DamageType.FIRE,
            damage_dice=DiceNotation("1d10"),
        )
        with patch(f"{RES}.roll_dice") as mock_roll:
            mock_roll.side_effect = [(20, [20]), (15, [])]
            result = cast_spell(caster, spell, Ability.INTELLIGENCE, state, ["t"])
        # second call is damage: 3 dice at level 11
        assert mock_roll.call_args_list[1][0][0] == 3
        assert result.outcomes[0].hit

    def test_save_for_half(self):
        caster = _caster()
        state = self._state(caster)
        spell = _spell(
            save=Ability.DEXTERITY,
            half_damage_on_save=True,
            damage_type=DamageType.FIRE,
            damage_dice=DiceNotation("4d6"),
        )
        with (
            patch(f"{RES}.roll_dice", return_value=(20, [])),
            patch("game_engine.rules.dnd_5_5e._saves.roll_dice", return_value=(20, [20])),
        ):
            result = cast_spell(caster, spell, Ability.INTELLIGENCE, state, ["t"])
        assert result.outcomes[0].save_success is True
        assert result.outcomes[0].damage == 10  # 20 // 2

    def test_healing_adds_modifier(self):
        caster = _caster()
        state = self._state(caster)
        target = state.get_combatant("t")
        target.hp_current = 10
        spell = _spell(
            healing_dice=DiceNotation("2d8"), range_type=SpellRangeType.TOUCH, range_ft=None
        )
        with patch(f"{RES}.roll_dice", return_value=(9, [])):
            result = cast_spell(caster, spell, Ability.INTELLIGENCE, state, ["t"])
        assert result.outcomes[0].healing == 12  # 9 + INT 3
        assert target.hp_current == 22

    def test_conditions_applied_with_duration(self):
        caster = _caster()
        state = self._state(caster)
        spell = _spell(
            save=Ability.WISDOM,
            conditions_applied=[Condition.PARALYZED],
            duration="Concentration, up to 1 minute",
            concentration=True,
        )
        with patch("game_engine.rules.dnd_5_5e._saves.roll_dice", return_value=(1, [1])):
            result = cast_spell(caster, spell, Ability.INTELLIGENCE, state, ["t"])
        target = state.get_combatant("t")
        assert Condition.PARALYZED in target.conditions
        assert target.condition_durations[Condition.PARALYZED] == 10
        assert caster.concentrating_on == spell.name
        assert result.concentration_started

    def test_condition_immune_target_is_unaffected_by_rider(self):
        """EFF-10: a spell's rider condition must honor is_immune_to_condition,
        same as engine.apply_condition — a paralysis-immune target isn't
        paralyzed by a failed save against Hold Person's rider."""
        caster = _caster()
        target = CharacterSheet(
            id="t",
            name="Target",
            level=1,
            char_class=CharacterClass.FIGHTER,
            hp_current=30,
            hp_max=30,
            ac=10,
            condition_immunities=[Condition.PARALYZED],
        )
        state = CombatStateData(combatants=[caster, target])
        spell = _spell(
            save=Ability.WISDOM,
            conditions_applied=[Condition.PARALYZED],
            duration="Concentration, up to 1 minute",
            concentration=True,
        )
        with patch("game_engine.rules.dnd_5_5e._saves.roll_dice", return_value=(1, [1])):
            result = cast_spell(caster, spell, Ability.INTELLIGENCE, state, ["t"])
        assert Condition.PARALYZED not in target.conditions
        assert Condition.PARALYZED not in result.outcomes[0].conditions_applied

    def test_unconscious_rider_still_respects_prone_immunity(self):
        """EFF-10/EFF-14: the Unconscious→Prone carry-over inside
        _apply_condition_impl must also honor is_immune_to_condition for the
        Prone half, not just the primary rider condition."""
        caster = _caster()
        target = CharacterSheet(
            id="t",
            name="Target",
            level=1,
            char_class=CharacterClass.FIGHTER,
            hp_current=30,
            hp_max=30,
            ac=10,
            condition_immunities=[Condition.PRONE],
        )
        state = CombatStateData(combatants=[caster, target])
        spell = _spell(save=Ability.WISDOM, conditions_applied=[Condition.UNCONSCIOUS])
        with patch("game_engine.rules.dnd_5_5e._saves.roll_dice", return_value=(1, [1])):
            cast_spell(caster, spell, Ability.INTELLIGENCE, state, ["t"])
        assert Condition.UNCONSCIOUS in target.conditions
        assert Condition.PRONE not in target.conditions

    def test_concentration_replaces_previous(self):
        caster = _caster(concentrating_on="Bless")
        state = self._state(caster)
        spell = _spell(concentration=True, duration="Concentration, up to 1 minute")
        cast_spell(caster, spell, Ability.INTELLIGENCE, state, [])
        assert caster.concentrating_on == spell.name

    def test_ritual_consumes_no_slot(self):
        caster = _caster()
        state = self._state(caster)
        spell = _spell(ritual=True)
        before = sum(s.remaining for s in caster.spell_slots)
        result = cast_spell(caster, spell, Ability.INTELLIGENCE, state, [], as_ritual=True)
        assert result.success
        assert sum(s.remaining for s in caster.spell_slots) == before

    def test_non_ritual_cannot_be_ritual_cast(self):
        caster = _caster()
        result = cast_spell(
            caster, _spell(), Ability.INTELLIGENCE, self._state(caster), [], as_ritual=True
        )
        assert not result.success
        assert result.error == "not_a_ritual"


class TestConcentration:
    """Workstream F: spell damage forces a concentration save on the target
    (SPL-02), using the effective post-immunity damage (EFF-07), and an
    Incapacitating rider condition breaks the target's own concentration
    outright (EFF-01)."""

    def _state_with_target(self, caster, **target_kwargs) -> CombatStateData:
        target = CharacterSheet(
            id="t",
            name="Target",
            level=1,
            char_class=CharacterClass.FIGHTER,
            hp_current=30,
            hp_max=30,
            ac=10,
            **target_kwargs,
        )
        return CombatStateData(combatants=[caster, target])

    def test_spell_damage_forces_concentration_save_and_can_break_it(self):
        caster = _caster()
        state = self._state_with_target(caster)
        target = state.get_combatant("t")
        target.concentrating_on = "Haste"
        spell = _spell(damage_type=DamageType.FIRE, damage_dice=DiceNotation("4d6"))
        with (
            patch(f"{RES}.roll_dice", return_value=(20, [20])),
            patch("game_engine.rules.dnd_5_5e._saves.roll_dice", return_value=(1, [1])),
        ):
            result = cast_spell(caster, spell, Ability.INTELLIGENCE, state, ["t"])
        outcome = result.outcomes[0]
        assert outcome.concentration_save_dc == 10  # max(10, 20 // 2)
        assert outcome.concentration_broken == "Haste"
        assert target.concentrating_on is None

    def test_immune_target_forces_no_concentration_save(self):
        """EFF-07: an immune target takes 0 effective damage and rolls no save."""
        caster = _caster()
        state = self._state_with_target(caster, damage_immunities=[DamageType.FIRE])
        target = state.get_combatant("t")
        target.concentrating_on = "Haste"
        spell = _spell(damage_type=DamageType.FIRE, damage_dice=DiceNotation("4d6"))
        with (
            patch(f"{RES}.roll_dice", return_value=(20, [20])),
            patch("game_engine.rules.dnd_5_5e._saves.roll_dice") as mock_save_roll,
        ):
            result = cast_spell(caster, spell, Ability.INTELLIGENCE, state, ["t"])
        mock_save_roll.assert_not_called()
        outcome = result.outcomes[0]
        assert outcome.concentration_save_dc is None
        assert outcome.concentration_broken is None
        assert target.concentrating_on == "Haste"

    def test_incapacitating_rider_breaks_targets_own_concentration(self):
        """EFF-01: 'You lose concentration on a spell if you are
        incapacitated' — a Stunned rider drops the target's own spell."""
        caster = _caster()
        state = self._state_with_target(caster)
        target = state.get_combatant("t")
        target.concentrating_on = "Bless"
        spell = _spell(save=Ability.WISDOM, conditions_applied=[Condition.STUNNED])
        with patch("game_engine.rules.dnd_5_5e._saves.roll_dice", return_value=(1, [1])):
            cast_spell(caster, spell, Ability.INTELLIGENCE, state, ["t"])
        assert Condition.STUNNED in target.conditions
        assert target.concentrating_on is None

    def test_non_incapacitating_rider_does_not_break_concentration(self):
        caster = _caster()
        state = self._state_with_target(caster)
        target = state.get_combatant("t")
        target.concentrating_on = "Bless"
        spell = _spell(save=Ability.WISDOM, conditions_applied=[Condition.FRIGHTENED])
        with patch("game_engine.rules.dnd_5_5e._saves.roll_dice", return_value=(1, [1])):
            cast_spell(caster, spell, Ability.INTELLIGENCE, state, ["t"])
        assert Condition.FRIGHTENED in target.conditions
        assert target.concentrating_on == "Bless"


class TestOneLeveledSpellPerTurn:
    """SPL-06: 2024 PHB — at most one leveled spell per turn; cantrips/rituals exempt."""

    def _state(self, caster, target_hp=30) -> CombatStateData:
        target = CharacterSheet(
            id="t",
            name="Target",
            level=1,
            char_class=CharacterClass.FIGHTER,
            hp_current=target_hp,
            hp_max=target_hp,
            ac=10,
        )
        return CombatStateData(combatants=[caster, target])

    def test_second_leveled_spell_same_turn_rejected(self):
        caster = _caster()
        state = self._state(caster)
        spell = _spell(level=1)
        first = cast_spell(caster, spell, Ability.INTELLIGENCE, state, ["t"])
        assert first.success
        second = cast_spell(caster, spell, Ability.INTELLIGENCE, state, ["t"])
        assert not second.success
        assert second.error == "leveled_spell_already_cast"
        # No second slot was consumed.
        assert (
            sum(s.remaining for s in caster.spell_slots)
            == sum(s.maximum for s in caster.spell_slots) - 1
        )

    def test_cantrip_after_leveled_spell_is_allowed(self):
        caster = _caster()
        state = self._state(caster)
        cast_spell(caster, _spell(level=1), Ability.INTELLIGENCE, state, ["t"])
        cantrip = _spell(level=0, name="Test Cantrip")
        result = cast_spell(caster, cantrip, Ability.INTELLIGENCE, state, ["t"])
        assert result.success

    def test_ritual_after_leveled_spell_is_allowed(self):
        caster = _caster()
        state = self._state(caster)
        cast_spell(caster, _spell(level=1), Ability.INTELLIGENCE, state, ["t"])
        ritual = _spell(ritual=True)
        result = cast_spell(caster, ritual, Ability.INTELLIGENCE, state, [], as_ritual=True)
        assert result.success

    def test_leveled_spell_allowed_again_next_turn(self):
        caster = _caster()
        state = self._state(caster)
        spell = _spell(level=1)
        cast_spell(caster, spell, Ability.INTELLIGENCE, state, ["t"])
        state.reset_turn(caster.id)
        result = cast_spell(caster, spell, Ability.INTELLIGENCE, state, ["t"])
        assert result.success
