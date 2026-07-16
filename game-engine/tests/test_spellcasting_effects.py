"""Tests for spell-cast Dodge interaction, registry-spell integration, and
revival spells. Split out of test_spellcasting.py to stay under the repo's
600-line test-file guideline (see scripts/check_file_lengths.py)."""

from __future__ import annotations

from unittest.mock import patch

from game_engine.rules.dnd_5_5e._spell_resolution import cast_spell
from game_engine.rules.dnd_5_5e.data.spells import SpellData, get_spell
from game_engine.rules.dnd_5_5e.spellcasting import compute_spell_slots
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
    DeathSaveState,
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


def _state(caster, target_hp: int = 30) -> CombatStateData:
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


class TestDodgeInteraction:
    """2024 PHB: Dodge grants disadvantage on incoming spell attack rolls and
    advantage on DEX saves for the dodging creature."""

    def test_dodging_target_gives_spell_attack_disadvantage(self):
        """Spell attack rolls against a dodging target use roll_with_disadvantage."""
        caster = _caster()
        state = _state(caster)
        state.turn_state_for("t").dodging = True
        spell = _spell(
            level=0,
            attack_roll=True,
            damage_type=DamageType.FIRE,
            damage_dice=DiceNotation("1d6"),
        )
        with (
            patch(f"{RES}.roll_with_disadvantage", return_value=(3, [3, 15])) as mock_dis,
            patch(f"{RES}.roll_dice", return_value=(4, [4])),
        ):
            cast_spell(caster, spell, Ability.INTELLIGENCE, state, ["t"])
        mock_dis.assert_called_once()

    def test_non_dodging_target_uses_flat_roll_for_spell_attack(self):
        """Without Dodge, spell attacks use roll_dice (flat), not roll_with_disadvantage."""
        caster = _caster()
        state = _state(caster)
        spell = _spell(
            level=0,
            attack_roll=True,
            damage_type=DamageType.FIRE,
            damage_dice=DiceNotation("1d6"),
        )
        with (
            patch(f"{RES}.roll_with_disadvantage") as mock_dis,
            patch(f"{RES}.roll_dice", return_value=(15, [15])),
        ):
            cast_spell(caster, spell, Ability.INTELLIGENCE, state, ["t"])
        mock_dis.assert_not_called()

    def test_dodging_target_gets_dex_save_advantage(self):
        """Dodging target rolling a DEX save vs a spell uses roll_with_advantage."""
        caster = _caster()
        state = _state(caster)
        state.turn_state_for("t").dodging = True
        spell = _spell(
            save=Ability.DEXTERITY,
            damage_type=DamageType.FIRE,
            damage_dice=DiceNotation("3d6"),
            half_damage_on_save=True,
        )
        with (
            patch(f"{RES}.roll_dice", return_value=(18, [])),
            patch(
                "game_engine.rules.dnd_5_5e._saves.roll_with_advantage",
                return_value=(18, [18, 5]),
            ) as mock_adv,
        ):
            cast_spell(caster, spell, Ability.INTELLIGENCE, state, ["t"])
        mock_adv.assert_called_once()

    def test_dodging_target_gets_no_advantage_on_non_dex_save(self):
        """Dodge only grants advantage on DEX saves; other saves remain unaffected."""
        caster = _caster()
        state = _state(caster)
        state.turn_state_for("t").dodging = True
        spell = _spell(
            save=Ability.WISDOM,
            damage_type=DamageType.PSYCHIC,
            damage_dice=DiceNotation("2d6"),
        )
        with (
            patch(f"{RES}.roll_dice", return_value=(8, [])),
            patch(
                "game_engine.rules.dnd_5_5e._saves.roll_with_advantage",
            ) as mock_adv,
            patch("game_engine.rules.dnd_5_5e._saves.roll_dice", return_value=(10, [10])),
        ):
            cast_spell(caster, spell, Ability.INTELLIGENCE, state, ["t"])
        mock_adv.assert_not_called()


class TestRegistryIntegration:
    def test_fireball_full_pipeline(self):
        fireball = get_spell("Fireball")
        assert fireball is not None
        caster = _caster(level=5)
        state = _state(caster)
        result = cast_spell(caster, fireball, Ability.INTELLIGENCE, state, ["t"])
        assert result.success
        assert result.outcomes[0].save_total is not None


class TestRevival:
    def _dead_target(self) -> CharacterSheet:
        target = CharacterSheet(
            id="t",
            name="Target",
            level=1,
            char_class=CharacterClass.FIGHTER,
            hp_current=0,
            hp_max=30,
            ac=10,
        )
        target.death_saves = DeathSaveState(failures=3, is_dead=True)
        target.conditions = [Condition.UNCONSCIOUS, Condition.PRONE]
        return target

    def test_non_revival_spell_cannot_heal_the_dead(self):
        caster = _caster()
        target = self._dead_target()
        state = CombatStateData(combatants=[caster, target])
        spell = _spell(healing_dice=DiceNotation("8d8"))
        cast_spell(caster, spell, Ability.INTELLIGENCE, state, ["t"])
        assert target.death_saves.is_dead
        assert target.hp_current == 0

    def test_revivify_brings_target_back_at_one_hp(self):
        revivify = get_spell("Revivify")
        assert revivify is not None
        caster = _caster()
        target = self._dead_target()
        state = CombatStateData(combatants=[caster, target])
        result = cast_spell(caster, revivify, Ability.INTELLIGENCE, state, ["t"])
        assert result.success
        assert result.outcomes[0].revived
        assert not target.death_saves.is_dead
        assert target.hp_current == 1
        assert Condition.UNCONSCIOUS not in target.conditions

    def test_raise_dead_brings_target_back_at_one_hp(self):
        raise_dead = get_spell("Raise Dead")
        assert raise_dead is not None
        caster = _caster(level=20)  # needs a 5th-level slot
        target = self._dead_target()
        state = CombatStateData(combatants=[caster, target])
        result = cast_spell(caster, raise_dead, Ability.INTELLIGENCE, state, ["t"])
        assert result.success
        assert result.outcomes[0].revived
        assert not target.death_saves.is_dead
        assert target.hp_current == 1

    def test_resurrection_restores_full_hp(self):
        resurrection = get_spell("Resurrection")
        assert resurrection is not None
        caster = _caster(level=20)  # needs a 7th-level slot
        target = self._dead_target()
        state = CombatStateData(combatants=[caster, target])
        result = cast_spell(caster, resurrection, Ability.INTELLIGENCE, state, ["t"])
        assert result.success
        assert result.outcomes[0].revived
        assert not target.death_saves.is_dead
        assert target.hp_current == target.hp_max == 30

    def test_true_resurrection_restores_full_hp(self):
        true_res = get_spell("True Resurrection")
        assert true_res is not None
        caster = _caster(level=20)  # needs a 9th-level slot
        target = self._dead_target()
        state = CombatStateData(combatants=[caster, target])
        result = cast_spell(caster, true_res, Ability.INTELLIGENCE, state, ["t"])
        assert result.success
        assert result.outcomes[0].revived
        assert not target.death_saves.is_dead
        assert target.hp_current == target.hp_max == 30

    def test_revival_spell_on_living_target_is_a_harmless_heal(self):
        revivify = get_spell("Revivify")
        assert revivify is not None
        caster = _caster()
        state = _state(caster, target_hp=20)
        target = state.get_combatant("t")
        target.hp_current = 15
        result = cast_spell(caster, revivify, Ability.INTELLIGENCE, state, ["t"])
        assert result.success
        assert not result.outcomes[0].revived
        assert target.hp_current == 16
