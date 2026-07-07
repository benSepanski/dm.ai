"""Weapon-registry -> AttackDetails bridge (root cause: EQP-01, EQP-08).

Before this module existed, nothing constructed an :class:`AttackDetails`
from a :class:`~game_engine.rules.dnd_5_5e.data.weapons.WeaponData`: callers
(dm-api's ``build_attack_details`` in particular) copied a handful of request
fields directly, so ``mastery`` was always ``None``, ``properties`` was
always empty, and ``proficient`` was always ``True`` regardless of the
weapon or the actor's training. The entire mastery/property/proficiency
layer in ``data/weapons.py`` was dead outside hand-crafted unit tests.

``to_attack_details`` is the single place that turns a registry weapon plus
an acting character into the ``AttackDetails`` the resolver actually reads.

Internal module — import via :class:`DnD55eEngine` or call directly from
dm-api's combat layer.
"""

from __future__ import annotations

from game_engine.rules.dnd_5_5e.data.weapons import WeaponData
from game_engine.types import Ability, AttackDetails, CharacterSheet, WeaponProperty


def to_attack_details(
    weapon: WeaponData,
    actor: CharacterSheet,
    *,
    is_offhand: bool = False,
    two_handed: bool = False,
    is_ranged: bool | None = None,
) -> AttackDetails:
    """Build the ``AttackDetails`` *actor* swings when attacking with *weapon*.

    - ``attack_ability`` is Strength for melee / Dexterity for ranged weapons,
      unless the weapon has the Finesse property, in which case the actor's
      better modifier of the two is used.
    - ``damage_dice`` uses ``weapon.versatile_dice`` when *two_handed* is set
      and the weapon has one (no effect on non-Versatile weapons).
    - ``proficient`` is derived from ``actor.weapon_category_training`` vs.
      the weapon's ``WeaponCategory``. Class-specific free-text weapon-access
      notes (e.g. Monk's "martial weapons with the Light or Finesse
      property") are deliberately NOT parsed here — this repo's golden
      principles forbid deriving typed decisions from human-readable
      strings, so that grant is a documented gap (see phb-parity-spec.md)
      rather than a silent guess.
    - ``mastery``/``properties`` are copied straight from the registry;
      whether the actor has *unlocked* the mastery is a separate, later
      check (``_has_mastery``) made at resolution time.

    ``is_ranged`` defaults to ``not weapon.is_melee``; pass it explicitly for
    a melee weapon with the Thrown property being thrown at range.
    """
    attack_ability = Ability.DEXTERITY if not weapon.is_melee else Ability.STRENGTH
    if WeaponProperty.FINESSE in weapon.properties:
        str_mod = actor.ability_scores.modifier(Ability.STRENGTH)
        dex_mod = actor.ability_scores.modifier(Ability.DEXTERITY)
        attack_ability = Ability.DEXTERITY if dex_mod >= str_mod else Ability.STRENGTH

    damage_dice = weapon.damage_dice
    if two_handed and weapon.versatile_dice is not None:
        damage_dice = weapon.versatile_dice

    return AttackDetails(
        weapon_name=weapon.name,
        damage_dice=damage_dice,
        damage_type=weapon.damage_type,
        attack_ability=attack_ability,
        is_ranged=(not weapon.is_melee) if is_ranged is None else is_ranged,
        properties=list(weapon.properties),
        mastery=weapon.mastery,
        proficient=weapon.category in actor.weapon_category_training,
        is_offhand=is_offhand,
    )
