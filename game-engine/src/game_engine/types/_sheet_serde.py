"""
CharacterSheet serialisation helpers.

Internal module — use :meth:`CharacterSheet.to_dict` /
:meth:`CharacterSheet.from_dict`. Every field on the sheet must round-trip
through these two functions (serialization completeness rule, AGENTS.md).
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from game_engine.types.sheets import CharacterSheet

from game_engine.types.character_state import (
    ClassLevelEntry,
    Currency,
    DeathSaveState,
    HitDicePool,
    InventoryItem,
    SpellSlotState,
)
from game_engine.types.enums import (
    Ability,
    Alignment,
    ArmorCategory,
    Background,
    CharacterClass,
    CharacterType,
    Condition,
    DamageType,
    Feat,
    Language,
    Skill,
    Species,
    Subclass,
    WeaponCategory,
)

E = TypeVar("E", bound=Enum)


def _enum_or_none(enum_cls: type[E], value: Any) -> E | None:
    if value is None:
        return None
    try:
        return enum_cls(value)
    except ValueError:
        return None


def _enum_list(enum_cls: type[E], values: list[Any], lowercase: bool = False) -> list[E]:
    result: list[E] = []
    for v in values:
        member = _enum_or_none(enum_cls, str(v).lower() if lowercase else v)
        if member is not None:
            result.append(member)
    return result


def sheet_to_dict(sheet: "CharacterSheet") -> dict[str, Any]:
    """Return a JSON-serialisable dict representation of *sheet*."""
    return {
        "id": sheet.id,
        "name": sheet.name,
        "level": sheet.level,
        "class": sheet.char_class.value,
        "ability_scores": sheet.ability_scores.to_dict(),
        "hp_current": sheet.hp_current,
        "hp_max": sheet.hp_max,
        "ac": sheet.ac,
        "speed": sheet.speed,
        "proficiencies": (
            [s.value for s in sheet.proficient_skills]
            + [a.value for a in sheet.proficient_abilities]
        ),
        "conditions": [c.value for c in sheet.conditions],
        "condition_durations": {c.value: n for c, n in sheet.condition_durations.items()},
        "damage_resistances": [d.value for d in sheet.damage_resistances],
        "damage_immunities": [d.value for d in sheet.damage_immunities],
        "damage_vulnerabilities": [d.value for d in sheet.damage_vulnerabilities],
        "condition_immunities": [c.value for c in sheet.condition_immunities],
        "type": sheet.char_type.value,
        "species": sheet.species.value if sheet.species else None,
        "background": sheet.background.value if sheet.background else None,
        "alignment": sheet.alignment.value if sheet.alignment else None,
        "subclass": sheet.subclass.value if sheet.subclass else None,
        "class_levels": [e.to_dict() for e in sheet.class_levels],
        "xp": sheet.xp,
        "feats": [f.value for f in sheet.feats],
        "languages": [lang.value for lang in sheet.languages],
        "temp_hp": sheet.temp_hp,
        "hit_dice": [h.to_dict() for h in sheet.hit_dice],
        "death_saves": sheet.death_saves.to_dict(),
        "exhaustion_level": sheet.exhaustion_level,
        "spell_slots": [s.to_dict() for s in sheet.spell_slots],
        "concentrating_on": sheet.concentrating_on,
        "cantrips": list(sheet.cantrips),
        "known_spells": list(sheet.known_spells),
        "prepared_spells": list(sheet.prepared_spells),
        "expertise_skills": [s.value for s in sheet.expertise_skills],
        "armor_training": [a.value for a in sheet.armor_training],
        "weapon_category_training": [w.value for w in sheet.weapon_category_training],
        "weapon_training": list(sheet.weapon_training),
        "tool_proficiencies": list(sheet.tool_proficiencies),
        "weapon_masteries": list(sheet.weapon_masteries),
        "inventory": [i.to_dict() for i in sheet.inventory],
        "currency": sheet.currency.to_dict(),
        "darkvision_ft": sheet.darkvision_ft,
    }


def sheet_from_dict(d: dict[str, Any]) -> "CharacterSheet":
    """Create a CharacterSheet from a dict; tolerant of missing keys."""
    from game_engine.types.sheets import AbilityScoreSet, CharacterSheet

    profs = d.get("proficiencies", [])
    skills = _enum_list(Skill, profs, lowercase=True)
    abilities = _enum_list(Ability, profs, lowercase=True)

    char_class = _enum_or_none(CharacterClass, d.get("class")) or CharacterClass.FIGHTER
    char_type = _enum_or_none(CharacterType, d.get("type")) or CharacterType.PC

    condition_durations: dict[Condition, int] = {}
    for cond_str, rounds in d.get("condition_durations", {}).items():
        cond = _enum_or_none(Condition, str(cond_str).lower())
        if cond is not None:
            try:
                condition_durations[cond] = int(rounds)
            except (ValueError, TypeError):
                pass

    return CharacterSheet(
        id=d.get("id", ""),
        name=d.get("name", ""),
        level=int(d.get("level", 1)),
        char_class=char_class,
        ability_scores=AbilityScoreSet.from_dict(d.get("ability_scores", {})),
        hp_current=int(d.get("hp_current", 10)),
        hp_max=int(d.get("hp_max", 10)),
        ac=int(d.get("ac", 10)),
        speed=int(d.get("speed", 30)),
        proficient_skills=skills,
        proficient_abilities=abilities,
        conditions=_enum_list(Condition, d.get("conditions", []), lowercase=True),
        condition_durations=condition_durations,
        damage_resistances=_enum_list(DamageType, d.get("damage_resistances", []), lowercase=True),
        damage_immunities=_enum_list(DamageType, d.get("damage_immunities", []), lowercase=True),
        damage_vulnerabilities=_enum_list(
            DamageType, d.get("damage_vulnerabilities", []), lowercase=True
        ),
        condition_immunities=_enum_list(
            Condition, d.get("condition_immunities", []), lowercase=True
        ),
        char_type=char_type,
        species=_enum_or_none(Species, d.get("species")),
        background=_enum_or_none(Background, d.get("background")),
        alignment=_enum_or_none(Alignment, d.get("alignment")),
        subclass=_enum_or_none(Subclass, d.get("subclass")),
        class_levels=[ClassLevelEntry.from_dict(e) for e in d.get("class_levels", [])],
        xp=int(d.get("xp", 0)),
        feats=_enum_list(Feat, d.get("feats", [])),
        languages=_enum_list(Language, d.get("languages", [])),
        temp_hp=int(d.get("temp_hp", 0)),
        hit_dice=[HitDicePool.from_dict(h) for h in d.get("hit_dice", [])],
        death_saves=DeathSaveState.from_dict(d.get("death_saves", {})),
        exhaustion_level=int(d.get("exhaustion_level", 0)),
        spell_slots=[SpellSlotState.from_dict(s) for s in d.get("spell_slots", [])],
        concentrating_on=d.get("concentrating_on"),
        cantrips=[str(s) for s in d.get("cantrips", [])],
        known_spells=[str(s) for s in d.get("known_spells", [])],
        prepared_spells=[str(s) for s in d.get("prepared_spells", [])],
        expertise_skills=_enum_list(Skill, d.get("expertise_skills", []), lowercase=True),
        armor_training=_enum_list(ArmorCategory, d.get("armor_training", []), lowercase=True),
        weapon_category_training=_enum_list(
            WeaponCategory, d.get("weapon_category_training", []), lowercase=True
        ),
        weapon_training=[str(w) for w in d.get("weapon_training", [])],
        tool_proficiencies=[str(t) for t in d.get("tool_proficiencies", [])],
        weapon_masteries=[str(w) for w in d.get("weapon_masteries", [])],
        inventory=[InventoryItem.from_dict(i) for i in d.get("inventory", [])],
        currency=Currency.from_dict(d.get("currency", {})),
        darkvision_ft=int(d.get("darkvision_ft", 0)),
    )
