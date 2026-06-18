"""Tests for resting rules and exploration/environment rules."""

from __future__ import annotations

from unittest.mock import patch

from game_engine.rules.dnd_5_5e.exploration import (
    TRAVEL_PACES,
    TravelPace,
    breath_holding_minutes,
    carrying_capacity,
    effectively_blinded_in,
    fall_damage,
    high_jump_height,
    is_encumbered,
    long_jump_distance,
    perception_disadvantage_in,
    push_drag_lift,
)
from game_engine.rules.dnd_5_5e.resting import long_rest, short_rest, spend_hit_die
from game_engine.rules.dnd_5_5e.spellcasting import compute_spell_slots
from game_engine.types import (
    AbilityScoreSet,
    CharacterClass,
    CharacterSheet,
    ClassLevelEntry,
    Condition,
    CreatureSize,
    DamageType,
    HitDicePool,
    InventoryItem,
    LightLevel,
    TaskDifficulty,
)


def _char(**kwargs) -> CharacterSheet:
    defaults = dict(
        id="c",
        name="Hero",
        level=5,
        char_class=CharacterClass.FIGHTER,
        ability_scores=AbilityScoreSet(constitution=14),
        hp_current=10,
        hp_max=40,
        hit_dice=[HitDicePool(die_size=10, maximum=5, remaining=5)],
    )
    defaults.update(kwargs)
    return CharacterSheet(**defaults)


class TestShortRest:
    def test_spend_hit_die_heals_roll_plus_con(self):
        char = _char()
        with patch("game_engine.rules.dnd_5_5e.resting.roll_dice", return_value=(6, [6])):
            healed = spend_hit_die(char)
        assert healed == 8  # 6 + CON 2
        assert char.hit_dice[0].remaining == 4

    def test_short_rest_spends_requested_dice(self):
        char = _char()
        with patch("game_engine.rules.dnd_5_5e.resting.roll_dice", return_value=(5, [5])):
            result = short_rest(char, hit_dice_to_spend=3)
        assert result.hit_dice_spent == 3
        assert char.hp_current == 10 + 3 * 7

    def test_warlock_pact_slots_return_on_short_rest(self):
        char = _char(
            char_class=CharacterClass.WARLOCK,
            level=5,
            class_levels=[ClassLevelEntry(CharacterClass.WARLOCK, 5)],
        )
        char.spell_slots = compute_spell_slots(char.class_levels)
        for slot in char.spell_slots:
            slot.remaining = 0
        result = short_rest(char)
        assert result.slots_restored
        slot = char.spell_slots[0]
        assert (slot.slot_level, slot.remaining) == (3, 2)

    def test_warlock_pact_slots_fully_restored_when_partially_spent(self):
        """A short rest always restores ALL pact slots, not just the ones spent."""
        char = _char(
            char_class=CharacterClass.WARLOCK,
            level=5,
            class_levels=[ClassLevelEntry(CharacterClass.WARLOCK, 5)],
        )
        char.spell_slots = compute_spell_slots(char.class_levels)
        # Spend only 1 of the 2 pact slots.
        char.spell_slots[0].remaining = 1
        result = short_rest(char)
        assert result.slots_restored
        assert char.spell_slots[0].remaining == char.spell_slots[0].maximum


class TestLongRest:
    def test_restores_everything(self):
        char = _char(temp_hp=5, exhaustion_level=3)
        char.hit_dice[0].remaining = 1
        char.spell_slots = compute_spell_slots([ClassLevelEntry(CharacterClass.WIZARD, 3)])
        char.spell_slots[0].remaining = 0
        result = long_rest(char)
        assert char.hp_current == char.hp_max
        assert char.temp_hp == 0  # temp HP ends on a long rest
        assert char.hit_dice[0].remaining == 5  # 2024: ALL hit dice return
        assert all(s.remaining == s.maximum for s in char.spell_slots)
        assert char.exhaustion_level == 2
        assert result.exhaustion_reduced

    def test_no_effect_on_dead(self):
        char = _char()
        char.death_saves.is_dead = True
        result = long_rest(char)
        assert result.hp_restored == 0

    def test_long_rest_clears_death_saves_and_unconscious_for_stable_character(self):
        """A stable-unconscious character wakes with full HP, cleared death saves,
        and UNCONSCIOUS removed. Regression: long_rest() used to skip both steps
        that _apply_healing_impl performs for 0-HP→positive transitions."""
        char = _char(hp_current=0, conditions=[Condition.UNCONSCIOUS, Condition.POISONED])
        char.death_saves.successes = 3
        char.death_saves.is_stable = True
        char.condition_durations = {Condition.UNCONSCIOUS: 0}

        result = long_rest(char)

        assert char.hp_current == char.hp_max
        assert result.hp_restored == char.hp_max
        # Death save state must be cleared.
        assert char.death_saves.successes == 0
        assert char.death_saves.failures == 0
        assert not char.death_saves.is_stable
        # UNCONSCIOUS must be lifted; other conditions (poisoned) stay.
        assert Condition.UNCONSCIOUS not in char.conditions
        assert Condition.POISONED in char.conditions
        assert Condition.UNCONSCIOUS not in char.condition_durations


class TestEncumbrance:
    def test_carrying_capacity(self):
        assert carrying_capacity(10) == 150
        assert carrying_capacity(10, CreatureSize.LARGE) == 300
        assert carrying_capacity(10, CreatureSize.TINY) == 75
        assert push_drag_lift(10) == 300

    def test_is_encumbered(self):
        char = _char(ability_scores=AbilityScoreSet(strength=10))
        char.inventory = [InventoryItem(name="Iron Ingots", quantity=10, weight_lb=20.0)]
        assert is_encumbered(char)
        char.inventory = [InventoryItem(name="Rope", weight_lb=5.0)]
        assert not is_encumbered(char)


class TestEnvironment:
    def test_jumps(self):
        assert long_jump_distance(16) == 16
        assert long_jump_distance(16, running_start=False) == 8
        assert high_jump_height(3) == 6
        assert high_jump_height(3, running_start=False) == 3

    def test_fall_damage_and_prone(self):
        char = _char(hp_current=40)
        with patch("game_engine.rules.dnd_5_5e.exploration.roll_dice", return_value=(7, [3, 4])):
            dealt = fall_damage(char, 25)  # 2d6
        assert dealt == 7
        assert Condition.PRONE in char.conditions

    def test_fall_damage_caps_at_20d6(self):
        char = _char(hp_current=40)
        with patch(
            "game_engine.rules.dnd_5_5e.exploration.roll_dice", return_value=(70, [])
        ) as mock_roll:
            fall_damage(char, 1000)
        assert mock_roll.call_args[0][0] == 20

    def test_fall_respects_resistance(self):
        char = _char(hp_current=40, damage_resistances=[DamageType.BLUDGEONING])
        with patch("game_engine.rules.dnd_5_5e.exploration.roll_dice", return_value=(10, [])):
            dealt = fall_damage(char, 30)
        assert dealt == 5

    def test_breath_holding(self):
        assert breath_holding_minutes(2) == 3
        assert breath_holding_minutes(-5) == 1

    def test_travel_paces(self):
        assert TRAVEL_PACES[TravelPace.FAST].miles_per_day == 30
        assert TRAVEL_PACES[TravelPace.NORMAL].feet_per_minute == 300
        assert "Stealth" in TRAVEL_PACES[TravelPace.SLOW].note

    def test_typical_dcs(self):
        assert TaskDifficulty.VERY_EASY.dc == 5
        assert TaskDifficulty.MEDIUM.dc == 15
        assert TaskDifficulty.NEARLY_IMPOSSIBLE.dc == 30

    def test_light_levels(self):
        assert perception_disadvantage_in(LightLevel.DIM)
        assert not perception_disadvantage_in(LightLevel.BRIGHT)
        assert effectively_blinded_in(LightLevel.DARKNESS)
        assert not effectively_blinded_in(LightLevel.DARKNESS, darkvision_ft=60)
