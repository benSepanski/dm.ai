"""Tests for spell slot progression and spell cast resolution."""

from __future__ import annotations

from unittest.mock import patch

from game_engine.rules.dnd_5_5e._spell_resolution import cast_spell
from game_engine.rules.dnd_5_5e.data.spells import SpellData, get_spell
from game_engine.rules.dnd_5_5e.spellcasting import (
    cantrip_dice_multiplier,
    compute_spell_slots,
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

    def test_dc_and_attack_bonus(self):
        caster = _caster()  # level 5, INT 16
        assert spell_save_dc(caster, Ability.INTELLIGENCE) == 14  # 8 + 3 + 3
        assert spell_attack_bonus(caster, Ability.INTELLIGENCE) == 6

    def test_cantrip_scaling_breakpoints(self):
        assert cantrip_dice_multiplier(1) == 1
        assert cantrip_dice_multiplier(5) == 2
        assert cantrip_dice_multiplier(11) == 3
        assert cantrip_dice_multiplier(17) == 4


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
        with patch(f"{RES}.roll_dice") as mock_roll:
            mock_roll.return_value = (40, [])
            cast_spell(caster, spell, Ability.INTELLIGENCE, state, ["t"], slot_level=5)
            count_upcast = mock_roll.call_args_list[0][0][0]
        assert count_base == 8
        assert count_upcast == 10

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


class TestDodgeInteraction:
    """2024 PHB: Dodge grants disadvantage on attacks and DEX-save advantage."""

    def _state_with_dodging_target(self, caster: CharacterSheet) -> CombatStateData:
        target = CharacterSheet(
            id="t",
            name="Target",
            level=1,
            char_class=CharacterClass.FIGHTER,
            hp_current=30,
            hp_max=30,
            ac=10,
        )
        state = CombatStateData(combatants=[caster, target])
        state.turn_state_for("t").dodging = True
        return state

    def test_spell_attack_has_disadvantage_vs_dodging_target(self):
        caster = _caster()
        state = self._state_with_dodging_target(caster)
        spell = _spell(
            level=0,
            attack_roll=True,
            damage_type=DamageType.FIRE,
            damage_dice=DiceNotation("1d10"),
        )
        with patch(f"{RES}.roll_with_disadvantage", return_value=(3, [3, 15])) as dis:
            cast_spell(caster, spell, Ability.INTELLIGENCE, state, ["t"])
        dis.assert_called_once()

    def test_dex_save_has_advantage_vs_dodging_target(self):
        caster = _caster()
        state = self._state_with_dodging_target(caster)
        spell = _spell(
            save=Ability.DEXTERITY,
            half_damage_on_save=True,
            damage_type=DamageType.FIRE,
            damage_dice=DiceNotation("4d6"),
        )
        with patch(
            "game_engine.rules.dnd_5_5e._saves.roll_with_advantage", return_value=(18, [18, 5])
        ) as adv:
            cast_spell(caster, spell, Ability.INTELLIGENCE, state, ["t"])
        adv.assert_called_once()

    def test_non_dex_save_gets_no_advantage_when_dodging(self):
        caster = _caster()
        state = self._state_with_dodging_target(caster)
        spell = _spell(
            save=Ability.CONSTITUTION,
            damage_type=DamageType.FIRE,
            damage_dice=DiceNotation("3d6"),
        )
        with (
            patch("game_engine.rules.dnd_5_5e._saves.roll_with_advantage") as adv,
            patch("game_engine.rules.dnd_5_5e._saves.roll_dice", return_value=(10, [10])),
        ):
            cast_spell(caster, spell, Ability.INTELLIGENCE, state, ["t"])
        adv.assert_not_called()

    def test_incapacitated_dodger_grants_no_benefit(self):
        """Dodge grants no benefit if the target can't act (2024 PHB)."""
        caster = _caster()
        state = self._state_with_dodging_target(caster)
        target = state.get_combatant("t")
        assert target is not None
        target.conditions.append(Condition.INCAPACITATED)
        spell = _spell(
            level=0,
            attack_roll=True,
            damage_type=DamageType.FIRE,
            damage_dice=DiceNotation("1d10"),
        )
        with patch(f"{RES}.roll_with_disadvantage") as dis:
            with patch(f"{RES}.roll_dice", return_value=(15, [15])):
                cast_spell(caster, spell, Ability.INTELLIGENCE, state, ["t"])
        dis.assert_not_called()


class TestRegistryIntegration:
    def test_fireball_full_pipeline(self):
        fireball = get_spell("Fireball")
        assert fireball is not None
        caster = _caster(level=5)
        state = TestCasting()._state(caster)
        result = cast_spell(caster, fireball, Ability.INTELLIGENCE, state, ["t"])
        assert result.success
        assert result.outcomes[0].save_total is not None
