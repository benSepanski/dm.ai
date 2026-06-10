"""D&D 5.5e adventuring gear, tools, and equipment packs (2024 PHB ch. 6)."""

from __future__ import annotations

from dataclasses import dataclass, field

from game_engine.types import Ability


@dataclass(frozen=True)
class GearData:
    """A piece of adventuring gear."""

    name: str
    cost_gp: float
    weight_lb: float
    description: str


@dataclass(frozen=True)
class ToolData:
    """An artisan's tool or other tool, with its governing ability."""

    name: str
    cost_gp: float
    weight_lb: float
    ability: Ability
    description: str


@dataclass(frozen=True)
class PackData:
    """An equipment pack and its contents (item names reference GEAR)."""

    name: str
    cost_gp: float
    contents: list[str] = field(default_factory=list)


GEAR: list[GearData] = []
TOOLS: list[ToolData] = []
PACKS: list[PackData] = []

GEAR_BY_NAME: dict[str, GearData] = {g.name.lower(): g for g in GEAR}
TOOLS_BY_NAME: dict[str, ToolData] = {t.name.lower(): t for t in TOOLS}
PACKS_BY_NAME: dict[str, PackData] = {p.name.lower(): p for p in PACKS}


def get_gear(name: str) -> GearData | None:
    """Look up gear by case-insensitive name; None if unknown."""
    return GEAR_BY_NAME.get(name.lower())


def get_tool(name: str) -> ToolData | None:
    """Look up a tool by case-insensitive name; None if unknown."""
    return TOOLS_BY_NAME.get(name.lower())
