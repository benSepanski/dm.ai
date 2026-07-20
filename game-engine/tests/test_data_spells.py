"""Structural and spot-check tests for the D&D 5.5e spell data registry."""

from __future__ import annotations

import pytest

from game_engine.rules.dnd_5_5e.data.spells import (
    SPELLS,
    SPELLS_BY_NAME,
    SpellData,
    get_spell,
)
from game_engine.rules.dnd_5_5e.data.spells.cantrips import CANTRIPS
from game_engine.rules.dnd_5_5e.data.spells.level1 import LEVEL_1_SPELLS
from game_engine.rules.dnd_5_5e.data.spells.level2 import LEVEL_2_SPELLS
from game_engine.rules.dnd_5_5e.data.spells.level3 import LEVEL_3_SPELLS
from game_engine.rules.dnd_5_5e.data.spells.level4 import LEVEL_4_SPELLS
from game_engine.rules.dnd_5_5e.data.spells.level5 import LEVEL_5_SPELLS
from game_engine.rules.dnd_5_5e.data.spells.level6 import LEVEL_6_SPELLS
from game_engine.rules.dnd_5_5e.data.spells.level7 import LEVEL_7_SPELLS
from game_engine.rules.dnd_5_5e.data.spells.level8 import LEVEL_8_SPELLS
from game_engine.rules.dnd_5_5e.data.spells.level9 import LEVEL_9_SPELLS
from game_engine.types import (
    Ability,
    AreaShape,
    CastingTime,
    Condition,
    DamageType,
    DiceNotation,
    SpellComponent,
    SpellRangeType,
)

MODULES_BY_LEVEL: dict[int, list[SpellData]] = {
    0: CANTRIPS,
    1: LEVEL_1_SPELLS,
    2: LEVEL_2_SPELLS,
    3: LEVEL_3_SPELLS,
    4: LEVEL_4_SPELLS,
    5: LEVEL_5_SPELLS,
    6: LEVEL_6_SPELLS,
    7: LEVEL_7_SPELLS,
    8: LEVEL_8_SPELLS,
    9: LEVEL_9_SPELLS,
}


class TestRegistryStructure:
    def test_total_count(self) -> None:
        assert len(SPELLS) >= 98

    def test_unique_names_case_insensitive(self) -> None:
        names = [s.name.lower() for s in SPELLS]
        assert len(names) == len(set(names))

    def test_registry_matches_modules(self) -> None:
        assert len(SPELLS) == sum(len(m) for m in MODULES_BY_LEVEL.values())
        assert len(SPELLS_BY_NAME) == len(SPELLS)

    @pytest.mark.parametrize("level", sorted(MODULES_BY_LEVEL))
    def test_module_levels(self, level: int) -> None:
        module = MODULES_BY_LEVEL[level]
        assert module, f"level-{level} module is empty"
        for spell in module:
            assert spell.level == level, f"{spell.name} has level {spell.level}, not {level}"

    def test_get_spell_lookup(self) -> None:
        fireball = get_spell("fireball")
        assert fireball is not None
        assert fireball.name == "Fireball"
        assert get_spell("FIREBALL") is fireball
        assert get_spell("no such spell") is None


class TestEverySpellInvariants:
    @pytest.mark.parametrize("spell", SPELLS, ids=lambda s: s.name)
    def test_level_bounds(self, spell: SpellData) -> None:
        assert 0 <= spell.level <= 9
        if spell.level > 0:
            assert not spell.is_cantrip
        else:
            assert spell.is_cantrip

    @pytest.mark.parametrize("spell", SPELLS, ids=lambda s: s.name)
    def test_concentration_duration_text(self, spell: SpellData) -> None:
        if spell.concentration:
            assert "Concentration" in spell.duration
        else:
            assert "Concentration" not in spell.duration

    @pytest.mark.parametrize("spell", SPELLS, ids=lambda s: s.name)
    def test_components_nonempty(self, spell: SpellData) -> None:
        assert spell.components

    @pytest.mark.parametrize("spell", SPELLS, ids=lambda s: s.name)
    def test_material_iff_material_component(self, spell: SpellData) -> None:
        has_m = SpellComponent.MATERIAL in spell.components
        assert has_m == (spell.material is not None)

    @pytest.mark.parametrize("spell", SPELLS, ids=lambda s: s.name)
    def test_save_and_attack_roll_mutually_exclusive(self, spell: SpellData) -> None:
        assert not (spell.attack_roll and spell.save is not None)

    @pytest.mark.parametrize("spell", SPELLS, ids=lambda s: s.name)
    def test_ranged_implies_range_ft(self, spell: SpellData) -> None:
        if spell.range_type is SpellRangeType.RANGED:
            assert spell.range_ft is not None and spell.range_ft > 0
        elif spell.range_type in (SpellRangeType.SELF, SpellRangeType.TOUCH):
            assert spell.range_ft is None

    @pytest.mark.parametrize("spell", SPELLS, ids=lambda s: s.name)
    def test_area_fields_paired(self, spell: SpellData) -> None:
        assert (spell.area is None) == (spell.area_size_ft is None)

    @pytest.mark.parametrize("spell", SPELLS, ids=lambda s: s.name)
    def test_cantrips_have_no_upcast(self, spell: SpellData) -> None:
        if spell.is_cantrip:
            assert spell.upcast_damage_per_slot is None
            assert spell.upcast_healing_per_slot is None
            assert spell.upcast_healing_flat_per_slot == 0
            assert spell.secondary_upcast_damage_per_slot is None

    @pytest.mark.parametrize("spell", SPELLS, ids=lambda s: s.name)
    def test_secondary_upcast_implies_secondary_damage(self, spell: SpellData) -> None:
        # SPL-17: a secondary upcast rate is meaningless without a secondary
        # damage pool to apply it to.
        if spell.secondary_upcast_damage_per_slot is not None:
            assert spell.secondary_damage_dice is not None
            assert spell.secondary_damage_type is not None

    @pytest.mark.parametrize("spell", SPELLS, ids=lambda s: s.name)
    def test_classes_and_description(self, spell: SpellData) -> None:
        assert spell.classes
        assert spell.description.strip()


class TestMinimumDistribution:
    @pytest.mark.parametrize(
        ("level", "minimum"),
        [(0, 12), (1, 16), (2, 12), (3, 12), (4, 10), (5, 10), (6, 8), (7, 6), (8, 6), (9, 6)],
    )
    def test_minimum_per_level(self, level: int, minimum: int) -> None:
        assert len(MODULES_BY_LEVEL[level]) >= minimum


def _require(name: str) -> SpellData:
    spell = get_spell(name)
    assert spell is not None, f"missing spell: {name}"
    return spell


class TestSpotChecks:
    def test_fireball(self) -> None:
        s = _require("Fireball")
        assert s.level == 3
        assert s.damage_type is DamageType.FIRE
        assert s.damage_dice == DiceNotation("8d6")
        assert s.save is Ability.DEXTERITY
        assert s.half_damage_on_save
        assert not s.attack_roll
        assert s.range_type is SpellRangeType.RANGED and s.range_ft == 150
        assert s.area is AreaShape.SPHERE and s.area_size_ft == 20
        assert s.upcast_damage_per_slot == DiceNotation("1d6")

    def test_cure_wounds(self) -> None:
        s = _require("Cure Wounds")
        assert s.level == 1
        assert s.range_type is SpellRangeType.TOUCH
        assert s.healing_dice == DiceNotation("2d8")
        assert s.upcast_healing_per_slot == DiceNotation("2d8")
        assert s.damage_dice is None

    def test_healing_word(self) -> None:
        s = _require("Healing Word")
        assert s.casting_time is CastingTime.BONUS_ACTION
        assert s.healing_dice == DiceNotation("2d4")
        assert s.upcast_healing_per_slot == DiceNotation("2d4")

    def test_magic_missile(self) -> None:
        s = _require("Magic Missile")
        assert s.damage_type is DamageType.FORCE
        assert s.save is None
        assert not s.attack_roll
        assert s.damage_dice is not None
        # SPL-05: the upcast notation carries its own +1 flat modifier per
        # slot level (4d4+4 at a level-2 slot, not 4d4+3).
        assert s.upcast_damage_per_slot == DiceNotation("1d4+1")

    def test_ice_storm(self) -> None:
        s = _require("Ice Storm")
        # SPL-19: 2024 PHB dice (2d10 bludgeoning, was 2d8 in 2014); only
        # the bludgeoning pool upcasts, cold stays fixed at 4d6 (SPL-17).
        assert s.damage_type is DamageType.BLUDGEONING
        assert s.damage_dice == DiceNotation("2d10")
        assert s.upcast_damage_per_slot == DiceNotation("1d10")
        assert s.secondary_damage_type is DamageType.COLD
        assert s.secondary_damage_dice == DiceNotation("4d6")
        assert s.secondary_upcast_damage_per_slot is None

    def test_flame_strike(self) -> None:
        s = _require("Flame Strike")
        # SPL-17: 2024 PHB upcasts BOTH damage types by 1d6 per slot level.
        assert s.damage_dice == DiceNotation("5d6")
        assert s.upcast_damage_per_slot == DiceNotation("1d6")
        assert s.secondary_damage_dice == DiceNotation("5d6")
        assert s.secondary_upcast_damage_per_slot == DiceNotation("1d6")

    def test_shield(self) -> None:
        s = _require("Shield")
        assert s.casting_time is CastingTime.REACTION
        assert s.range_type is SpellRangeType.SELF
        assert s.level == 1

    def test_eldritch_blast(self) -> None:
        s = _require("Eldritch Blast")
        assert s.is_cantrip
        assert s.attack_roll
        assert s.save is None
        assert s.damage_dice == DiceNotation("1d10")
        assert s.damage_type is DamageType.FORCE
        assert s.upcast_damage_per_slot is None

    def test_hold_person(self) -> None:
        s = _require("Hold Person")
        assert s.save is Ability.WISDOM
        assert Condition.PARALYZED in s.conditions_applied
        assert s.concentration
        assert "Concentration" in s.duration

    def test_power_word_kill(self) -> None:
        s = _require("Power Word Kill")
        assert s.level == 9
        assert s.save is None
        assert not s.attack_roll
        assert s.damage_dice is None
        assert s.healing_dice is None

    def test_burning_hands(self) -> None:
        s = _require("Burning Hands")
        assert s.area is AreaShape.CONE and s.area_size_ft == 15
        assert s.range_type is SpellRangeType.SELF
        assert s.damage_dice == DiceNotation("3d6")
        assert s.save is Ability.DEXTERITY and s.half_damage_on_save

    def test_lightning_bolt(self) -> None:
        s = _require("Lightning Bolt")
        assert s.area is AreaShape.LINE and s.area_size_ft == 100
        assert s.damage_dice == DiceNotation("8d6")
        assert s.damage_type is DamageType.LIGHTNING

    def test_spirit_guardians(self) -> None:
        s = _require("Spirit Guardians")
        assert s.area is AreaShape.EMANATION and s.area_size_ft == 15
        assert s.concentration

    def test_detect_magic_is_ritual(self) -> None:
        s = _require("Detect Magic")
        assert s.ritual
        assert s.concentration

    def test_web_restrains(self) -> None:
        s = _require("Web")
        assert s.save is Ability.DEXTERITY
        assert Condition.RESTRAINED in s.conditions_applied

    def test_fear_frightens(self) -> None:
        s = _require("Fear")
        assert s.save is Ability.WISDOM
        assert Condition.FRIGHTENED in s.conditions_applied


class TestRequiredSpellsPresent:
    REQUIRED: dict[int, list[str]] = {
        0: [
            "Fire Bolt",
            "Eldritch Blast",
            "Sacred Flame",
            "Toll the Dead",
            "Chill Touch",
            "Poison Spray",
            "Acid Splash",
            "Ray of Frost",
            "Shocking Grasp",
            "Mind Sliver",
            "Guidance",
            "Light",
        ],
        1: [
            "Magic Missile",
            "Burning Hands",
            "Cure Wounds",
            "Healing Word",
            "Shield",
            "Sleep",
            "Thunderwave",
            "Bless",
            "Bane",
            "Guiding Bolt",
            "Inflict Wounds",
            "Mage Armor",
            "Faerie Fire",
            "Hex",
            "Hunter's Mark",
            "Detect Magic",
        ],
        2: [
            "Misty Step",
            "Shatter",
            "Scorching Ray",
            "Hold Person",
            "Invisibility",
            "Aid",
            "Lesser Restoration",
            "Spiritual Weapon",
            "Moonbeam",
            "Darkness",
            "Web",
            "Mirror Image",
        ],
        3: [
            "Fireball",
            "Lightning Bolt",
            "Counterspell",
            "Dispel Magic",
            "Fly",
            "Haste",
            "Slow",
            "Spirit Guardians",
            "Revivify",
            "Fear",
            "Hypnotic Pattern",
            "Mass Healing Word",
        ],
        4: [
            "Ice Storm",
            "Polymorph",
            "Banishment",
            "Wall of Fire",
            "Dimension Door",
            "Greater Invisibility",
            "Blight",
            "Stoneskin",
        ],
        5: [
            "Cone of Cold",
            "Hold Monster",
            "Cloudkill",
            "Flame Strike",
            "Greater Restoration",
            "Mass Cure Wounds",
            "Raise Dead",
            "Wall of Stone",
        ],
        6: ["Chain Lightning", "Disintegrate", "Heal", "Harm", "Sunbeam", "True Seeing"],
        7: [
            "Forcecage",
            "Finger of Death",
            "Fire Storm",
            "Teleport",
            "Resurrection",
            "Plane Shift",
        ],
        8: ["Sunburst", "Power Word Stun", "Dominate Monster", "Earthquake", "Holy Aura"],
        9: [
            "Meteor Swarm",
            "Power Word Kill",
            "Wish",
            "Time Stop",
            "Mass Heal",
            "True Resurrection",
        ],
    }

    @pytest.mark.parametrize(
        ("level", "name"),
        [(level, name) for level, names in REQUIRED.items() for name in names],
    )
    def test_required_spell(self, level: int, name: str) -> None:
        spell = _require(name)
        assert spell.level == level
