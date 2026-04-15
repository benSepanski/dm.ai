"""
Import all SQLAlchemy models here so Alembic can discover them
via Base.metadata when it imports this package.
"""

from dm_api.db.models.character import Character
from dm_api.db.models.chat import ChatMessage
from dm_api.db.models.combat import CombatState
from dm_api.db.models.location import Location
from dm_api.db.models.proposal import Proposal
from dm_api.db.models.session import GameSession
from dm_api.db.models.world import World

__all__ = [
    "World",
    "Location",
    "Character",
    "GameSession",
    "ChatMessage",
    "CombatState",
    "Proposal",
]
