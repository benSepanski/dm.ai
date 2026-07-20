"""
SpellData schema for the D&D 5.5e spell registry (SRD 5.2 content).

Internal module — import via :mod:`game_engine.rules.dnd_5_5e.data.spells`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from game_engine.types import (
    Ability,
    AreaShape,
    CastingTime,
    CharacterClass,
    Condition,
    DamageType,
    DiceNotation,
    SpellComponent,
    SpellRangeType,
    SpellSchool,
)


@dataclass(frozen=True)
class SpellData:
    """Typed spell definition.

    Mechanical fields drive the spellcasting resolver; ``description``
    is display text only. ``damage_dice`` for cantrips is the level-1
    base — the resolver scales it at character levels 5/11/17.
    """

    name: str
    level: int  # 0 = cantrip
    school: SpellSchool
    casting_time: CastingTime
    range_type: SpellRangeType
    range_ft: int | None
    duration: str
    concentration: bool
    components: list[SpellComponent]
    classes: list[CharacterClass]
    description: str
    ritual: bool = False
    material: str | None = None
    # Attack / save mechanics
    attack_roll: bool = False
    save: Ability | None = None
    half_damage_on_save: bool = False
    # Damage
    damage_type: DamageType | None = None
    damage_dice: DiceNotation | None = None
    secondary_damage_type: DamageType | None = None
    secondary_damage_dice: DiceNotation | None = None
    upcast_damage_per_slot: DiceNotation | None = None
    # Upcast scaling for the secondary pool, independent of the primary
    # pool's ``upcast_damage_per_slot`` (SPL-17) — e.g. Flame Strike scales
    # both its fire and radiant dice, while Ice Storm scales only its
    # bludgeoning (primary) dice and leaves cold (secondary) fixed. `None`
    # means the secondary pool does not upcast.
    secondary_upcast_damage_per_slot: DiceNotation | None = None
    # Healing
    healing_dice: DiceNotation | None = None
    healing_flat: int = 0
    upcast_healing_per_slot: DiceNotation | None = None
    upcast_healing_flat_per_slot: int = 0
    # Revival — bypasses the "no healing while dead" rule for a target whose
    # death saves record it as dead. ``revive_full_heal`` restores the target
    # to full hit points instead of relying on ``healing_dice``/``healing_flat``
    # (used by spells whose text specifies "full hit points" rather than a
    # fixed amount, e.g. Resurrection/True Resurrection).
    revives: bool = False
    revive_full_heal: bool = False
    # Effects
    conditions_applied: list[Condition] = field(default_factory=list)
    area: AreaShape | None = None
    area_size_ft: int | None = None

    @property
    def is_cantrip(self) -> bool:
        return self.level == 0
