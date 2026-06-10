"""D&D 5.5e background data (2024 PHB chapter 4)."""

from __future__ import annotations

from dataclasses import dataclass, field

from game_engine.types import Ability, Background, Feat, Skill


@dataclass(frozen=True)
class BackgroundData:
    """Typed background definition (2024 PHB).

    ``ability_scores`` are the three abilities the background can
    increase (+2/+1 or +1/+1/+1 split chosen at creation).
    """

    background: Background
    ability_scores: list[Ability]
    skill_proficiencies: list[Skill]
    tool_proficiency: str
    origin_feat: Feat
    equipment: list[str] = field(default_factory=list)
    description: str = ""


BACKGROUNDS: dict[Background, BackgroundData] = {}


def get_background(background: Background) -> BackgroundData | None:
    """Look up background data; None if not registered."""
    return BACKGROUNDS.get(background)
