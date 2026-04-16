"""
Tests for DnD55eEngine action resolution, temp HP, and death saving throws.

Covers:
- Temporary HP absorbs damage before regular HP
- Automatic UNCONSCIOUS/PRONE when HP drops to 0
- Instant death on massive overkill
- Death-save failures when hitting a dying creature
- All non-attack actions (Dash, Disengage, Dodge, Help, Hide, Ready, Search, UseObject)
- Death saving throw mechanics (natural 20, natural 1, successes/failures, stable/dead)
- get_available_actions respects dying/dead state
"""

from __future__ import annotations

import pytest

from game_engine.interface import Action
from game_engine.rules.dnd_5_5e.engine import DnD55eEngine
from game_engine.types import (
    AbilityScoreSet,
    ActionType,
    CharacterClass,
    CharacterSheet,
    CombatStateData,
    Condition,
    DamageType,
    Skill,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def make_fighter(
    id: str = "fighter-1",
    name: str = "Thorin",
    level: int = 5,
    strength: int = 18,
    dexterity: int = 14,
    constitution: int = 16,
    wisdom: int = 12,
    hp_current: int = 44,
    hp_max: int = 44,
    temp_hp: int = 0,
    ac: int = 17,
    speed: int = 30,
    conditions: list[Condition] | None = None,
    proficient_skills: list[Skill] | None = None,
) -> CharacterSheet:
    return CharacterSheet(
        id=id,
        name=name,
        level=level,
        char_class=CharacterClass.FIGHTER,
        ability_scores=AbilityScoreSet(
            strength=strength,
            dexterity=dexterity,
            constitution=constitution,
            intelligence=10,
            wisdom=wisdom,
            charisma=8,
        ),
        hp_current=hp_current,
        hp_max=hp_max,
        temp_hp=temp_hp,
        ac=ac,
        speed=speed,
        conditions=conditions or [],
        proficient_skills=proficient_skills or [],
    )


def make_rogue(
    id: str = "rogue-1",
    name: str = "Serana",
    level: int = 4,
    dexterity: int = 18,
    wisdom: int = 14,
    hp_current: int = 28,
    hp_max: int = 28,
    ac: int = 14,
    proficient_skills: list[Skill] | None = None,
) -> CharacterSheet:
    return CharacterSheet(
        id=id,
        name=name,
        level=level,
        char_class=CharacterClass.ROGUE,
        ability_scores=AbilityScoreSet(
            strength=10,
            dexterity=dexterity,
            constitution=12,
            intelligence=13,
            wisdom=wisdom,
            charisma=10,
        ),
        hp_current=hp_current,
        hp_max=hp_max,
        ac=ac,
        speed=30,
        proficient_skills=(
            proficient_skills
            if proficient_skills is not None
            else [Skill.STEALTH, Skill.PERCEPTION]
        ),
    )


def make_state(*chars: CharacterSheet) -> CombatStateData:
    return CombatStateData(combatants=list(chars))


@pytest.fixture
def engine() -> DnD55eEngine:
    return DnD55eEngine()


@pytest.fixture
def fighter() -> CharacterSheet:
    return make_fighter()


@pytest.fixture
def rogue() -> CharacterSheet:
    return make_rogue()


# ---------------------------------------------------------------------------
# Temporary HP
# ---------------------------------------------------------------------------


class TestTempHP:
    def test_temp_hp_absorbs_before_regular_hp(self, engine: DnD55eEngine) -> None:
        fighter = make_fighter(hp_current=20, hp_max=44, temp_hp=10)
        engine.apply_damage(fighter, 7, DamageType.FIRE)
        assert fighter.temp_hp == 3  # 10 - 7
        assert fighter.hp_current == 20  # unchanged

    def test_temp_hp_fully_consumed(self, engine: DnD55eEngine) -> None:
        fighter = make_fighter(hp_current=20, hp_max=44, temp_hp=5)
        engine.apply_damage(fighter, 5, DamageType.FIRE)
        assert fighter.temp_hp == 0
        assert fighter.hp_current == 20

    def test_damage_overflows_temp_hp_into_regular_hp(self, engine: DnD55eEngine) -> None:
        fighter = make_fighter(hp_current=20, hp_max=44, temp_hp=5)
        engine.apply_damage(fighter, 12, DamageType.FIRE)
        assert fighter.temp_hp == 0
        assert fighter.hp_current == 13  # 20 - (12 - 5) = 20 - 7

    def test_temp_hp_serialization(self) -> None:
        fighter = make_fighter(temp_hp=15)
        d = fighter.to_dict()
        assert d["temp_hp"] == 15
        restored = CharacterSheet.from_dict(d)
        assert restored.temp_hp == 15

    def test_temp_hp_default_zero(self) -> None:
        fighter = make_fighter()
        assert fighter.temp_hp == 0


# ---------------------------------------------------------------------------
# Unconscious / Prone on drop to 0 HP
# ---------------------------------------------------------------------------


class TestDropToZeroHP:
    def test_unconscious_applied_at_zero_hp(self, engine: DnD55eEngine) -> None:
        fighter = make_fighter(hp_current=5)
        engine.apply_damage(fighter, 5, DamageType.FIRE)
        assert fighter.hp_current == 0
        assert Condition.UNCONSCIOUS in fighter.conditions

    def test_prone_applied_at_zero_hp(self, engine: DnD55eEngine) -> None:
        fighter = make_fighter(hp_current=5)
        engine.apply_damage(fighter, 5, DamageType.FIRE)
        assert Condition.PRONE in fighter.conditions

    def test_is_dying_after_drop_to_zero(self, engine: DnD55eEngine) -> None:
        fighter = make_fighter(hp_current=5)
        engine.apply_damage(fighter, 5, DamageType.FIRE)
        assert fighter.is_dying
        assert not fighter.is_dead

    def test_is_alive_false_when_at_zero_hp(self) -> None:
        """is_alive still returns False at 0 HP (unchanged semantics)."""
        fighter = make_fighter(hp_current=0)
        assert not fighter.is_alive

    def test_is_dying_true_at_zero_hp_with_no_failures(self) -> None:
        fighter = make_fighter(hp_current=0)
        assert fighter.is_dying

    def test_is_dying_false_when_alive(self) -> None:
        fighter = make_fighter(hp_current=10)
        assert not fighter.is_dying

    def test_is_dying_false_when_dead(self) -> None:
        fighter = make_fighter(hp_current=0)
        fighter.death_save_failures = 3
        assert not fighter.is_dying

    def test_is_dead_true_at_three_failures(self) -> None:
        fighter = make_fighter(hp_current=0)
        fighter.death_save_failures = 3
        assert fighter.is_dead

    def test_no_conditions_for_non_lethal_hit(self, engine: DnD55eEngine) -> None:
        fighter = make_fighter(hp_current=20)
        engine.apply_damage(fighter, 5, DamageType.FIRE)
        assert Condition.UNCONSCIOUS not in fighter.conditions
        assert Condition.PRONE not in fighter.conditions


# ---------------------------------------------------------------------------
# Instant death (massive damage rule)
# ---------------------------------------------------------------------------


class TestInstantDeath:
    def test_instant_death_overkill_equals_max_hp(self, engine: DnD55eEngine) -> None:
        fighter = make_fighter(hp_current=5, hp_max=44)
        # Overkill = 100 - 5 = 95 >= hp_max (44) → instant death
        engine.apply_damage(fighter, 100, DamageType.FIRE)
        assert fighter.hp_current == 0
        assert fighter.is_dead
        assert fighter.death_save_failures == 3

    def test_no_instant_death_below_max_hp(self, engine: DnD55eEngine) -> None:
        fighter = make_fighter(hp_current=20, hp_max=44)
        # Overkill = 30 - 20 = 10 < hp_max (44) → dying, not dead
        engine.apply_damage(fighter, 30, DamageType.FIRE)
        assert fighter.hp_current == 0
        assert fighter.is_dying
        assert not fighter.is_dead


# ---------------------------------------------------------------------------
# Damage to a dying creature → death save failures
# ---------------------------------------------------------------------------


class TestDamageWhileDying:
    def test_normal_hit_on_dying_adds_one_failure(self, engine: DnD55eEngine) -> None:
        fighter = make_fighter(hp_current=0)
        fighter.death_save_failures = 1
        engine.apply_damage(fighter, 10, DamageType.SLASHING)
        assert fighter.death_save_failures == 2
        assert fighter.hp_current == 0  # HP unchanged

    def test_critical_hit_on_dying_adds_two_failures(self, engine: DnD55eEngine) -> None:
        from game_engine.rules.dnd_5_5e._damage import _apply_damage_impl

        fighter = make_fighter(hp_current=0)
        _apply_damage_impl(fighter, 10, DamageType.SLASHING, is_critical=True)
        assert fighter.death_save_failures == 2

    def test_three_failures_kills_dying_creature(self, engine: DnD55eEngine) -> None:
        fighter = make_fighter(hp_current=0)
        fighter.death_save_failures = 2
        engine.apply_damage(fighter, 5, DamageType.FIRE)
        assert fighter.is_dead

    def test_damage_to_dying_does_not_change_hp(self, engine: DnD55eEngine) -> None:
        fighter = make_fighter(hp_current=0)
        engine.apply_damage(fighter, 50, DamageType.FIRE)
        assert fighter.hp_current == 0

    def test_stable_creature_takes_damage_resets_successes(self, engine: DnD55eEngine) -> None:
        """A stable creature (3 successes) that takes damage becomes unstable."""
        fighter = make_fighter(hp_current=0)
        fighter.death_save_successes = 3  # was stable
        engine.apply_damage(fighter, 5, DamageType.FIRE)
        assert fighter.death_save_successes == 0
        assert fighter.death_save_failures == 1


# ---------------------------------------------------------------------------
# Death Saving Throw action
# ---------------------------------------------------------------------------


class TestDeathSave:
    def test_roll_ten_adds_success(
        self, engine: DnD55eEngine, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import game_engine.rules.dnd_5_5e._actions as actions_mod

        monkeypatch.setattr(actions_mod, "roll_dice", lambda count, sides: (15, [15]))
        fighter = make_fighter(hp_current=0)
        state = make_state(fighter)
        action = Action(ActionType.DEATH_SAVE, fighter.id, None)
        result = engine.resolve_action(action, state)

        assert result.success
        assert fighter.death_save_successes == 1
        assert fighter.death_save_failures == 0

    def test_roll_nine_adds_failure(
        self, engine: DnD55eEngine, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import game_engine.rules.dnd_5_5e._actions as actions_mod

        monkeypatch.setattr(actions_mod, "roll_dice", lambda count, sides: (9, [9]))
        fighter = make_fighter(hp_current=0)
        state = make_state(fighter)
        action = Action(ActionType.DEATH_SAVE, fighter.id, None)
        result = engine.resolve_action(action, state)

        assert not result.success
        assert fighter.death_save_failures == 1
        assert fighter.death_save_successes == 0

    def test_natural_one_adds_two_failures(
        self, engine: DnD55eEngine, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import game_engine.rules.dnd_5_5e._actions as actions_mod

        monkeypatch.setattr(actions_mod, "roll_dice", lambda count, sides: (1, [1]))
        fighter = make_fighter(hp_current=0)
        state = make_state(fighter)
        action = Action(ActionType.DEATH_SAVE, fighter.id, None)
        result = engine.resolve_action(action, state)

        assert not result.success
        assert fighter.death_save_failures == 2

    def test_natural_twenty_revives(
        self, engine: DnD55eEngine, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import game_engine.rules.dnd_5_5e._actions as actions_mod

        monkeypatch.setattr(actions_mod, "roll_dice", lambda count, sides: (20, [20]))
        fighter = make_fighter(hp_current=0)
        fighter.death_save_failures = 2  # On the brink
        state = make_state(fighter)
        action = Action(ActionType.DEATH_SAVE, fighter.id, None)
        result = engine.resolve_action(action, state)

        assert result.success
        assert fighter.hp_current == 1
        assert fighter.death_save_successes == 0
        assert fighter.death_save_failures == 0
        assert Condition.UNCONSCIOUS not in fighter.conditions

    def test_three_successes_means_stable(
        self, engine: DnD55eEngine, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import game_engine.rules.dnd_5_5e._actions as actions_mod

        monkeypatch.setattr(actions_mod, "roll_dice", lambda count, sides: (15, [15]))
        fighter = make_fighter(hp_current=0)
        fighter.death_save_successes = 2  # One more will stabilize
        state = make_state(fighter)
        action = Action(ActionType.DEATH_SAVE, fighter.id, None)
        result = engine.resolve_action(action, state)

        assert result.success
        assert fighter.death_save_successes == 3
        assert "stable" in result.flavor_text.lower()

    def test_three_failures_means_dead(
        self, engine: DnD55eEngine, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import game_engine.rules.dnd_5_5e._actions as actions_mod

        monkeypatch.setattr(actions_mod, "roll_dice", lambda count, sides: (5, [5]))
        fighter = make_fighter(hp_current=0)
        fighter.death_save_failures = 2  # One more will kill
        state = make_state(fighter)
        action = Action(ActionType.DEATH_SAVE, fighter.id, None)
        result = engine.resolve_action(action, state)

        assert not result.success
        assert fighter.death_save_failures == 3
        assert fighter.is_dead
        assert "died" in result.flavor_text.lower()

    def test_death_save_on_living_character_fails(self, engine: DnD55eEngine) -> None:
        fighter = make_fighter(hp_current=10)
        state = make_state(fighter)
        action = Action(ActionType.DEATH_SAVE, fighter.id, None)
        result = engine.resolve_action(action, state)
        assert not result.success
        assert "not dying" in result.flavor_text.lower()


# ---------------------------------------------------------------------------
# get_available_actions — dying / dead checks
# ---------------------------------------------------------------------------


class TestAvailableActions:
    def test_dying_character_only_gets_death_save(self, engine: DnD55eEngine) -> None:
        fighter = make_fighter(hp_current=0)
        state = make_state(fighter)
        actions = engine.get_available_actions(fighter, state)
        assert len(actions) == 1
        assert actions[0].action_type == ActionType.DEATH_SAVE

    def test_dead_character_has_no_actions(self, engine: DnD55eEngine) -> None:
        fighter = make_fighter(hp_current=0)
        fighter.death_save_failures = 3
        state = make_state(fighter)
        actions = engine.get_available_actions(fighter, state)
        assert actions == []

    def test_alive_character_has_all_basic_actions(self, engine: DnD55eEngine) -> None:
        fighter = make_fighter(hp_current=44)
        state = make_state(fighter)
        actions = engine.get_available_actions(fighter, state)
        action_types = {a.action_type for a in actions}
        assert ActionType.ATTACK in action_types
        assert ActionType.DASH in action_types
        assert ActionType.DODGE in action_types
        assert ActionType.DEATH_SAVE not in action_types

    def test_incapacitated_character_has_no_actions(self, engine: DnD55eEngine) -> None:
        fighter = make_fighter(hp_current=44, conditions=[Condition.STUNNED])
        state = make_state(fighter)
        actions = engine.get_available_actions(fighter, state)
        assert actions == []


# ---------------------------------------------------------------------------
# Dash
# ---------------------------------------------------------------------------


class TestDash:
    def test_dash_succeeds(self, engine: DnD55eEngine) -> None:
        fighter = make_fighter()
        state = make_state(fighter)
        action = Action(ActionType.DASH, fighter.id, None)
        result = engine.resolve_action(action, state)
        assert result.success
        assert result.log_entry["dash_active"] is True

    def test_dash_reports_extra_movement(self, engine: DnD55eEngine) -> None:
        fighter = make_fighter(speed=30)
        state = make_state(fighter)
        action = Action(ActionType.DASH, fighter.id, None)
        result = engine.resolve_action(action, state)
        assert result.log_entry["extra_movement"] == 30


# ---------------------------------------------------------------------------
# Disengage
# ---------------------------------------------------------------------------


class TestDisengage:
    def test_disengage_succeeds(self, engine: DnD55eEngine) -> None:
        fighter = make_fighter()
        state = make_state(fighter)
        action = Action(ActionType.DISENGAGE, fighter.id, None)
        result = engine.resolve_action(action, state)
        assert result.success
        assert result.log_entry["disengage_active"] is True


# ---------------------------------------------------------------------------
# Dodge
# ---------------------------------------------------------------------------


class TestDodge:
    def test_dodge_succeeds(self, engine: DnD55eEngine) -> None:
        fighter = make_fighter()
        state = make_state(fighter)
        action = Action(ActionType.DODGE, fighter.id, None)
        result = engine.resolve_action(action, state)
        assert result.success
        assert result.log_entry["dodge_active"] is True

    def test_dodge_flavor_mentions_disadvantage(self, engine: DnD55eEngine) -> None:
        fighter = make_fighter()
        state = make_state(fighter)
        action = Action(ActionType.DODGE, fighter.id, None)
        result = engine.resolve_action(action, state)
        assert "disadvantage" in result.flavor_text.lower()


# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------


class TestHelp:
    def test_help_requires_target(self, engine: DnD55eEngine) -> None:
        fighter = make_fighter()
        state = make_state(fighter)
        action = Action(ActionType.HELP, fighter.id, None)
        result = engine.resolve_action(action, state)
        assert not result.success

    def test_help_grants_advantage(self, engine: DnD55eEngine) -> None:
        fighter = make_fighter(id="f1", name="Fighter")
        rogue = make_rogue(id="r1", name="Rogue")
        state = make_state(fighter, rogue)
        action = Action(ActionType.HELP, fighter.id, rogue.id)
        result = engine.resolve_action(action, state)
        assert result.success
        assert result.log_entry["advantage_granted"] is True
        assert result.log_entry["target_id"] == rogue.id


# ---------------------------------------------------------------------------
# Hide
# ---------------------------------------------------------------------------


class TestHide:
    def test_hide_succeeds_with_high_stealth(
        self, engine: DnD55eEngine, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import game_engine.rules.dnd_5_5e._checks as checks_mod

        # Force roll = 18 so stealth total well above DC 15
        monkeypatch.setattr(checks_mod, "roll_dice", lambda count, sides: (18, [18]))
        rogue = make_rogue(proficient_skills=[Skill.STEALTH])
        state = make_state(rogue)
        action = Action(ActionType.HIDE, rogue.id, None)
        result = engine.resolve_action(action, state)

        assert result.success
        assert Condition.INVISIBLE in result.conditions_applied
        assert Condition.INVISIBLE in rogue.conditions

    def test_hide_fails_with_low_stealth(
        self, engine: DnD55eEngine, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import game_engine.rules.dnd_5_5e._checks as checks_mod

        monkeypatch.setattr(checks_mod, "roll_dice", lambda count, sides: (1, [1]))
        rogue = make_rogue()
        state = make_state(rogue)
        action = Action(ActionType.HIDE, rogue.id, None)
        result = engine.resolve_action(action, state)

        assert not result.success
        assert Condition.INVISIBLE not in result.conditions_applied
        assert Condition.INVISIBLE not in rogue.conditions

    def test_hide_log_includes_stealth_roll(
        self, engine: DnD55eEngine, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import game_engine.rules.dnd_5_5e._checks as checks_mod

        monkeypatch.setattr(checks_mod, "roll_dice", lambda count, sides: (12, [12]))
        rogue = make_rogue()
        state = make_state(rogue)
        action = Action(ActionType.HIDE, rogue.id, None)
        result = engine.resolve_action(action, state)

        assert "stealth_roll" in result.log_entry
        assert "stealth_total" in result.log_entry


# ---------------------------------------------------------------------------
# Ready
# ---------------------------------------------------------------------------


class TestReady:
    def test_ready_succeeds(self, engine: DnD55eEngine) -> None:
        fighter = make_fighter()
        state = make_state(fighter)
        action = Action(ActionType.READY, fighter.id, None)
        result = engine.resolve_action(action, state)
        assert result.success
        assert result.log_entry["readied"] is True


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


class TestSearch:
    def test_search_returns_check_result(
        self, engine: DnD55eEngine, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import game_engine.rules.dnd_5_5e._checks as checks_mod

        monkeypatch.setattr(checks_mod, "roll_dice", lambda count, sides: (16, [16]))
        fighter = make_fighter()
        state = make_state(fighter)
        action = Action(ActionType.SEARCH, fighter.id, None)
        result = engine.resolve_action(action, state)

        assert result.success
        assert "perception_roll" in result.log_entry
        assert "perception_total" in result.log_entry

    def test_search_fails_on_low_roll(
        self, engine: DnD55eEngine, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import game_engine.rules.dnd_5_5e._checks as checks_mod

        monkeypatch.setattr(checks_mod, "roll_dice", lambda count, sides: (2, [2]))
        fighter = make_fighter(wisdom=10)  # +0 mod → total = 2, DC 15
        state = make_state(fighter)
        action = Action(ActionType.SEARCH, fighter.id, None)
        result = engine.resolve_action(action, state)
        assert not result.success


# ---------------------------------------------------------------------------
# Use Object
# ---------------------------------------------------------------------------


class TestUseObject:
    def test_use_object_succeeds(self, engine: DnD55eEngine) -> None:
        fighter = make_fighter()
        state = make_state(fighter)
        action = Action(ActionType.USE_OBJECT, fighter.id, None)
        result = engine.resolve_action(action, state)
        assert result.success


# ---------------------------------------------------------------------------
# CharacterSheet serialization with new fields
# ---------------------------------------------------------------------------


class TestSheetSerialization:
    def test_roundtrip_with_death_saves(self) -> None:
        fighter = make_fighter(hp_current=0, temp_hp=0)
        fighter.death_save_successes = 2
        fighter.death_save_failures = 1
        d = fighter.to_dict()
        restored = CharacterSheet.from_dict(d)
        assert restored.death_save_successes == 2
        assert restored.death_save_failures == 1

    def test_from_dict_defaults_death_saves_to_zero(self) -> None:
        d = {"id": "x", "name": "X", "level": 1, "class": "Fighter"}
        sheet = CharacterSheet.from_dict(d)
        assert sheet.death_save_successes == 0
        assert sheet.death_save_failures == 0
        assert sheet.temp_hp == 0
