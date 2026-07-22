"""
Typed sub-structures of a character sheet: class levels, hit dice,
death saves, spell slots, currency, and inventory.

Each dataclass carries ``to_dict``/``from_dict`` so the full sheet
serialises losslessly (see the serialization completeness rule in
AGENTS.md).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from game_engine.types.enums import CharacterClass, Subclass


@dataclass(eq=False)
class ClassLevelEntry:
    """One class in a (possibly multiclassed) character's level breakdown.

    ``eq=False`` keeps identity-based ``__eq__``/``__hash__`` (the dataclass
    default for ``eq=True`` sets ``__hash__`` to ``None``, since ``level`` and
    ``subclass`` are mutated in place by :func:`level_up`) so an entry can be
    used as a dict key, e.g. ``compute_spell_slots``'s ``caster_types``
    override (SPL-22).
    """

    character_class: CharacterClass
    level: int
    subclass: Subclass | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "class": self.character_class.value,
            "level": self.level,
            "subclass": self.subclass.value if self.subclass else None,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ClassLevelEntry":
        raw_subclass = d.get("subclass")
        subclass: Subclass | None = None
        if raw_subclass:
            try:
                subclass = Subclass(raw_subclass)
            except ValueError:
                subclass = None
        return cls(
            character_class=CharacterClass(d["class"]),
            level=int(d.get("level", 1)),
            subclass=subclass,
        )


@dataclass
class HitDicePool:
    """A pool of hit dice of a single size (e.g. 5d10 for a level-5 fighter)."""

    die_size: int
    maximum: int
    remaining: int

    def to_dict(self) -> dict[str, int]:
        return {"die_size": self.die_size, "maximum": self.maximum, "remaining": self.remaining}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "HitDicePool":
        maximum = int(d.get("maximum", 0))
        return cls(
            die_size=int(d.get("die_size", 8)),
            maximum=maximum,
            remaining=max(0, min(maximum, int(d.get("remaining", maximum)))),
        )


@dataclass
class DeathSaveState:
    """Death saving throw bookkeeping while a character is dying."""

    successes: int = 0
    failures: int = 0
    is_stable: bool = False
    is_dead: bool = False

    def reset(self) -> None:
        """Clear all death save state (e.g. on regaining hit points)."""
        self.successes = 0
        self.failures = 0
        self.is_stable = False
        self.is_dead = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "successes": self.successes,
            "failures": self.failures,
            "is_stable": self.is_stable,
            "is_dead": self.is_dead,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "DeathSaveState":
        return cls(
            successes=int(d.get("successes", 0)),
            failures=int(d.get("failures", 0)),
            is_stable=bool(d.get("is_stable", False)),
            is_dead=bool(d.get("is_dead", False)),
        )


@dataclass
class SpellSlotState:
    """Spell slots of a single level (slot level 1-9).

    ``is_pact`` distinguishes Warlock pact-magic slots from standard slots
    (SPL-15): the two pools are never merged even when they share a slot
    level, since only pact slots are restored by a short rest — both are
    restored by a long rest.
    """

    slot_level: int
    maximum: int
    remaining: int
    is_pact: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot_level": self.slot_level,
            "maximum": self.maximum,
            "remaining": self.remaining,
            "is_pact": self.is_pact,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "SpellSlotState":
        maximum = int(d.get("maximum", 0))
        return cls(
            slot_level=int(d.get("slot_level", 1)),
            maximum=maximum,
            remaining=max(0, min(maximum, int(d.get("remaining", maximum)))),
            is_pact=bool(d.get("is_pact", False)),
        )


@dataclass
class Currency:
    """Coinage in the five standard denominations."""

    cp: int = 0
    sp: int = 0
    ep: int = 0
    gp: int = 0
    pp: int = 0

    @property
    def total_gp(self) -> float:
        """Total value expressed in gold pieces."""
        return self.cp / 100 + self.sp / 10 + self.ep / 2 + self.gp + self.pp * 10

    def to_dict(self) -> dict[str, int]:
        return {"cp": self.cp, "sp": self.sp, "ep": self.ep, "gp": self.gp, "pp": self.pp}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Currency":
        return cls(
            cp=int(d.get("cp", 0)),
            sp=int(d.get("sp", 0)),
            ep=int(d.get("ep", 0)),
            gp=int(d.get("gp", 0)),
            pp=int(d.get("pp", 0)),
        )


@dataclass
class InventoryItem:
    """A carried item. ``name`` references an item registry entry when one exists."""

    name: str
    quantity: int = 1
    weight_lb: float = 0.0
    equipped: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "quantity": self.quantity,
            "weight_lb": self.weight_lb,
            "equipped": self.equipped,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "InventoryItem":
        return cls(
            name=str(d.get("name", "")),
            quantity=int(d.get("quantity", 1)),
            weight_lb=float(d.get("weight_lb", 0.0)),
            equipped=bool(d.get("equipped", False)),
        )
