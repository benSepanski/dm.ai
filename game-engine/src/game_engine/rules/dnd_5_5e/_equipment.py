"""
Worn-equipment identity and AC recomputation (2024 rules, EQP-04/EQP-06/EQP-07).

``CharacterSheet`` stores *which* body armor and shield are worn (``worn_armor``
/ ``worn_shield``), not just the derived ``ac``. Equipping or unequipping armor
recomputes AC through :func:`compute_sheet_ac`, which layers class Unarmored
Defense (barbarian / monk) on top of the base armor table exactly as
:func:`build_character` does — the single source of AC truth for both paths.

Internal module — import the ``equip_*`` / ``unequip_*`` helpers via
:mod:`game_engine.rules.dnd_5_5e`.
"""

from __future__ import annotations

from game_engine.rules.dnd_5_5e.data.armor import ArmorData, compute_armor_class, get_armor
from game_engine.rules.dnd_5_5e.exploration import is_encumbered
from game_engine.types import Ability, ArmorCategory, CharacterClass, CharacterSheet


def compute_sheet_ac(sheet: CharacterSheet, armor: ArmorData | None, shield: bool) -> int:
    """Return *sheet*'s AC wearing *armor* (+shield), incl. Unarmored Defense.

    When *armor* is ``None`` the barbarian (10 + DEX + CON) and monk
    (10 + DEX + WIS, no shield) Unarmored Defense formulas apply if they beat
    the plain unarmored 10 + DEX.
    """
    dex = sheet.ability_scores.modifier(Ability.DEXTERITY)
    ac = compute_armor_class(armor, dex, shield=shield)
    if armor is None:
        if sheet.char_class is CharacterClass.BARBARIAN:
            con = sheet.ability_scores.modifier(Ability.CONSTITUTION)
            ac = max(ac, 10 + dex + con + (2 if shield else 0))
        elif sheet.char_class is CharacterClass.MONK and not shield:
            wis = sheet.ability_scores.modifier(Ability.WISDOM)
            ac = max(ac, 10 + dex + wis)
    return ac


def resolve_body_armor(armor_name: str | None, warnings: list[str]) -> ArmorData | None:
    """Look up worn body armor, appending a warning for unknown / shield input.

    Returns ``None`` (unarmored) for an unknown name or a shield passed as body
    armor (EQP-06) — a shield is equipped separately via ``worn_shield``.
    """
    if not armor_name:
        return None
    armor = get_armor(armor_name)
    if armor is None:
        warnings.append(f"Unknown armor {armor_name!r}; using unarmored AC.")
        return None
    if armor.armor_type is ArmorCategory.SHIELD:
        warnings.append(
            f"{armor.name!r} is a shield, not body armor; treating as unarmored "
            "(equip it via the shield flag)."
        )
        return None
    return armor


def equip_armor(sheet: CharacterSheet, armor_name: str | None) -> list[str]:
    """Equip *armor_name* as body armor (``None`` unarmors) and recompute AC.

    The currently worn shield is preserved. Returns any warnings (unknown
    armor, shield-as-body, or lacking armor training for this class).
    """
    warnings: list[str] = []
    armor = resolve_body_armor(armor_name, warnings)
    sheet.worn_armor = armor.name if armor is not None else None
    if armor is not None and is_armor_untrained(sheet):
        warnings.append(f"{sheet.char_class.value} lacks {armor.armor_type.value} armor training.")
    sheet.ac = compute_sheet_ac(sheet, armor, sheet.worn_shield)
    return warnings


def is_armor_untrained(sheet: CharacterSheet) -> bool:
    """True when wearing body armor whose category the character lacks training in.

    Drives the 2024 PHB armor-training penalty (D2, EQP-03): disadvantage on
    STR/DEX checks and saving throws, and an inability to cast spells, while
    wearing untrained armor. Shields are out of scope, matching the
    equip-time warning this helper also backs.
    """
    if sheet.worn_armor is None:
        return False
    armor = get_armor(sheet.worn_armor)
    return armor is not None and armor.armor_type not in sheet.armor_training


def has_stealth_disadvantage(sheet: CharacterSheet) -> bool:
    """True if the worn armor imposes disadvantage on Stealth checks (D2, EQP-02)."""
    armor = get_armor(sheet.worn_armor) if sheet.worn_armor else None
    return armor is not None and armor.stealth_disadvantage


def armor_speed_penalty(sheet: CharacterSheet) -> int:
    """Return the -10 ft speed penalty for being under the worn armor's Strength
    minimum (D2, EQP-04), else 0.
    """
    armor = get_armor(sheet.worn_armor) if sheet.worn_armor else None
    if armor is None or sheet.ability_scores.get(Ability.STRENGTH) >= armor.min_strength:
        return 0
    return 10


def effective_speed(sheet: CharacterSheet) -> int:
    """``sheet.effective_speed`` minus the Strength-minimum armor penalty (D2, EQP-04),
    further capped at 5 ft while carrying more than the sheet's carrying capacity
    (2024 PHB encumbrance, EQP-10).

    ``CharacterSheet.effective_speed`` is a pure types-layer property with no
    visibility into the rules-layer armor registry or inventory weight, so both
    the under-Strength penalty and the encumbrance cap are layered on here
    instead — mirrors how ``_actions._effective_speed`` layers the Slow
    mastery's combat-only penalty on top of this.
    """
    speed = max(0, sheet.effective_speed - armor_speed_penalty(sheet))
    if speed > 0 and is_encumbered(sheet, sheet.size):
        return min(speed, 5)
    return speed


def unequip_armor(sheet: CharacterSheet) -> None:
    """Remove worn body armor and recompute AC (keeping any worn shield)."""
    sheet.worn_armor = None
    sheet.ac = compute_sheet_ac(sheet, None, sheet.worn_shield)


def equip_shield(sheet: CharacterSheet, equipped: bool = True) -> None:
    """Set whether a shield is worn and recompute AC against current armor."""
    armor = get_armor(sheet.worn_armor) if sheet.worn_armor else None
    sheet.worn_shield = equipped
    sheet.ac = compute_sheet_ac(sheet, armor, equipped)


def unequip_shield(sheet: CharacterSheet) -> None:
    """Remove the worn shield and recompute AC."""
    equip_shield(sheet, False)
