"""
D&D 5.5e spell-list derivation and cast gating.

Spell *slots* are computed from class + level (see
:mod:`.spellcasting`); this module does the same for the spells a caster
actually has. The castable surface of a character is:

* ``cantrips`` — known cantrips, always castable (no slot);
* ``prepared_spells`` — leveled spells the caster has prepared/known,
  castable with a slot.

Both are *derivable*: the class spell list (``SpellData.classes``) and the
per-class ``cantrips_known`` / ``prepared_spells`` count tables
(:class:`ClassProgression`) say which spells are eligible and how many a
caster of a given level has. :func:`default_spell_selection` turns that into
a concrete starting selection; :func:`can_cast` is the cast-time gate;
:func:`prepare_spells` re-selects within the same limits (e.g. after a long
rest).
"""

from __future__ import annotations

from game_engine.rules.dnd_5_5e.data.class_features import CLASS_PROGRESSIONS
from game_engine.rules.dnd_5_5e.data.spells import SPELLS, SpellData, get_spell
from game_engine.types import Ability, CharacterClass, CharacterSheet, ClassLevelEntry


def spells_for_class(cls: CharacterClass, max_spell_level: int) -> list[SpellData]:
    """Leveled spells (1..*max_spell_level*) on *cls*'s spell list."""
    return [s for s in SPELLS if cls in s.classes and 1 <= s.level <= max_spell_level]


def cantrips_for_class(cls: CharacterClass) -> list[SpellData]:
    """Cantrips (level 0) on *cls*'s spell list."""
    return [s for s in SPELLS if cls in s.classes and s.level == 0]


def _spellcasting_entries(sheet: CharacterSheet) -> list[ClassLevelEntry]:
    """Class entries that grant spellcasting, highest level first."""
    entries = sheet.class_levels or [
        ClassLevelEntry(character_class=sheet.char_class, level=sheet.level)
    ]
    casting = [
        e
        for e in entries
        if (p := CLASS_PROGRESSIONS.get(e.character_class)) is not None
        and p.spellcasting_ability is not None
    ]
    return sorted(casting, key=lambda e: e.level, reverse=True)


def spellcasting_ability_for(sheet: CharacterSheet) -> Ability | None:
    """The caster's spellcasting ability (primary class), or None.

    Multiclass simplification: the highest-level spellcasting class wins.
    """
    entries = _spellcasting_entries(sheet)
    if not entries:
        return None
    progression = CLASS_PROGRESSIONS.get(entries[0].character_class)
    return progression.spellcasting_ability if progression else None


def highest_castable_slot_level(sheet: CharacterSheet) -> int:
    """Highest spell-slot level the caster has (0 if none)."""
    return max((s.slot_level for s in sheet.spell_slots if s.maximum > 0), default=0)


def cantrips_known_count(sheet: CharacterSheet) -> int:
    """Number of cantrips the caster knows at its level (summed if multiclass)."""
    total = 0
    for entry in _spellcasting_entries(sheet):
        progression = CLASS_PROGRESSIONS.get(entry.character_class)
        if progression and progression.cantrips_known and 1 <= entry.level <= 20:
            total += progression.cantrips_known[entry.level - 1]
    return total


def prepared_spells_count(sheet: CharacterSheet) -> int:
    """Number of leveled spells the caster prepares (summed if multiclass)."""
    total = 0
    for entry in _spellcasting_entries(sheet):
        progression = CLASS_PROGRESSIONS.get(entry.character_class)
        if progression and progression.prepared_spells and 1 <= entry.level <= 20:
            total += progression.prepared_spells[entry.level - 1]
    return total


def can_cast(sheet: CharacterSheet, spell: SpellData) -> bool:
    """True if *sheet* may cast *spell* — a known cantrip or a prepared spell."""
    pool = sheet.cantrips if spell.is_cantrip else sheet.prepared_spells
    target = spell.name.lower()
    return any(name.lower() == target for name in pool)


def default_spell_selection(sheet: CharacterSheet) -> tuple[list[str], list[str]]:
    """Derive a deterministic starting (cantrips, prepared) selection.

    Picks the lowest-level spells alphabetically up to the class counts —
    enough that a freshly built caster is never empty. Players may override
    via :func:`prepare_spells`.
    """
    primary = _spellcasting_entries(sheet)
    if not primary:
        return [], []
    cls = primary[0].character_class

    n_cantrips = cantrips_known_count(sheet)
    cantrips = sorted(s.name for s in cantrips_for_class(cls))[:n_cantrips]

    n_prepared = prepared_spells_count(sheet)
    leveled = sorted(
        spells_for_class(cls, highest_castable_slot_level(sheet)),
        key=lambda s: (s.level, s.name),
    )
    prepared = [s.name for s in leveled][:n_prepared]
    return cantrips, prepared


def prepare_spells(
    sheet: CharacterSheet,
    cantrips: list[str] | None = None,
    prepared_spells: list[str] | None = None,
) -> list[str]:
    """Set the caster's prepared cantrips/spells, validated against class+level.

    Each name must be on a spellcasting class's list and within the caster's
    slot range; the count must not exceed the class table. Returns a list of
    human-readable warnings for any rejected entry (rejected entries are
    dropped). Lists left as ``None`` are unchanged.
    """
    warnings: list[str] = []
    classes = [e.character_class for e in _spellcasting_entries(sheet)]
    if not classes:
        return [f"{sheet.name} is not a spellcaster."]

    eligible_cantrips = {s.name.lower() for c in classes for s in cantrips_for_class(c)}
    max_level = highest_castable_slot_level(sheet)
    eligible_leveled = {s.name.lower() for c in classes for s in spells_for_class(c, max_level)}

    if cantrips is not None:
        valid = _filter(cantrips, eligible_cantrips, "cantrip", sheet.name, warnings)
        limit = cantrips_known_count(sheet)
        if len(valid) > limit:
            warnings.append(f"{sheet.name} can know only {limit} cantrips; extras dropped.")
            valid = valid[:limit]
        sheet.cantrips = valid

    if prepared_spells is not None:
        valid = _filter(prepared_spells, eligible_leveled, "spell", sheet.name, warnings)
        limit = prepared_spells_count(sheet)
        if len(valid) > limit:
            warnings.append(f"{sheet.name} can prepare only {limit} spells; extras dropped.")
            valid = valid[:limit]
        sheet.prepared_spells = valid

    return warnings


def _filter(
    names: list[str], eligible: set[str], kind: str, who: str, warnings: list[str]
) -> list[str]:
    """Keep names that resolve to a real, class-eligible spell of *kind*."""
    kept: list[str] = []
    for name in names:
        spell = get_spell(name)
        if spell is None:
            warnings.append(f"Unknown {kind}: {name}.")
        elif name.lower() not in eligible:
            warnings.append(f"{who} can't {kind == 'cantrip' and 'know' or 'prepare'} {name}.")
        else:
            kept.append(spell.name)
    return kept
