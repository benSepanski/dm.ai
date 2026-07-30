"""Bridge between the weapon data registry and attack resolution.

Nothing previously constructed an :class:`~game_engine.types.AttackDetails`
from a registry :class:`~game_engine.rules.dnd_5_5e.data.weapons.WeaponData`,
so ``mastery``, ``properties``, and ``proficient`` were dead in real play —
callers (dm-api) had to hand-populate every field. :func:`to_attack_details`
is the single place that does this conversion correctly.

Internal module — import via :class:`DnD55eEngine` or ``dm_api.api.combat_utils``.
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
    """Build an :class:`AttackDetails` from a registry weapon for *actor*.

    - ``attack_ability``: Finesse weapons use whichever of STR/DEX is higher
      for *actor*; other weapons use STR (melee) or DEX (ranged).
    - ``damage_dice``: swaps to ``versatile_dice`` when *two_handed* and the
      weapon has one.
    - ``proficient``: derived from whether *actor* trained in the weapon's
      :class:`~game_engine.types.WeaponCategory`, not trusted from the caller.
    - ``mastery``: always copied from the registry; whether the actor has
      unlocked it is checked separately at resolution time (see
      ``_attacks._has_mastery``), matching hand-authored ``AttackDetails``.
    - ``is_ranged``: defaults to the weapon's own melee/ranged nature;
      callers may override for e.g. a Thrown melee weapon.
    - ``ammunition_name``: copied from the registry (e.g. "Arrows", "Bolts")
      for weapons with the Ammunition property; drives the ammo check/spend
      in ``_attacks._validate_attack``/``_resolve_attack`` (EQP-08).
    """
    if WeaponProperty.FINESSE in weapon.properties:
        str_mod = actor.ability_scores.modifier(Ability.STRENGTH)
        dex_mod = actor.ability_scores.modifier(Ability.DEXTERITY)
        attack_ability = Ability.DEXTERITY if dex_mod > str_mod else Ability.STRENGTH
    else:
        attack_ability = Ability.STRENGTH if weapon.is_melee else Ability.DEXTERITY

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
        ammunition_name=weapon.ammunition_name,
    )
