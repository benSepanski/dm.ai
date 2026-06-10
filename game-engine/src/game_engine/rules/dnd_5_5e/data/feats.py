"""D&D 5.5e feat data (2024 PHB chapter 5)."""

from __future__ import annotations

from dataclasses import dataclass, field

from game_engine.types import Ability, Feat


@dataclass(frozen=True)
class FeatData:
    """Typed feat definition.

    ``ability_increase_options`` lists the abilities a general feat can
    raise by 1 (empty for feats granting no increase). Category is
    available via ``feat.category``.
    """

    feat: Feat
    description: str
    prerequisite: str | None = None
    repeatable: bool = False
    ability_increase_options: list[Ability] = field(default_factory=list)


FEATS: dict[Feat, FeatData] = {}


def get_feat(feat: Feat) -> FeatData | None:
    """Look up feat data; None if not registered."""
    return FEATS.get(feat)
