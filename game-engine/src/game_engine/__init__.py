"""dm.ai game engine – rule-agnostic RPG game engine."""

from game_engine.interface import (
    Action,
    ActionResult,
    CheckResult,
    RuleEngine,
    ValidationResult,
)
from game_engine.types import (
    Ability,
    AbilityScoreSet,
    ActionType,
    AttackDetails,
    CharacterClass,
    CharacterSheet,
    CharacterType,
    ChatRole,
    CombatStateData,
    Condition,
    DamageType,
    LocationType,
    ProposalStatus,
    ProposalType,
    Skill,
)

__all__ = [
    # interface
    "Action",
    "ActionResult",
    "CheckResult",
    "RuleEngine",
    "ValidationResult",
    # types — enums
    "Ability",
    "ActionType",
    "CharacterClass",
    "CharacterType",
    "ChatRole",
    "Condition",
    "DamageType",
    "LocationType",
    "ProposalStatus",
    "ProposalType",
    "Skill",
    # types — dataclasses
    "AbilityScoreSet",
    "AttackDetails",
    "CharacterSheet",
    "CombatStateData",
]
