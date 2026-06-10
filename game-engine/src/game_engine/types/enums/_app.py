"""
Application-layer enums: locations, proposals, chat.

Internal module — import via :mod:`game_engine.types.enums`.
"""

from __future__ import annotations

from enum import Enum


class LocationType(str, Enum):
    """Classification for a location in the game world."""

    REALM = "realm"
    COUNTRY = "country"
    REGION = "region"
    TOWN = "town"
    DISTRICT = "district"
    BUILDING = "building"
    ROOM = "room"
    DUNGEON = "dungeon"
    WILDERNESS = "wilderness"


class ProposalType(str, Enum):
    """Type of AI-generated proposal for the DM to review."""

    LOCATION = "location"
    CHARACTER = "character"
    DUNGEON = "dungeon"
    DIALOGUE = "dialogue"
    COMBAT_ACTION = "combat_action"


class ProposalStatus(str, Enum):
    """Current status of an AI proposal."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    MODIFIED = "modified"


class ChatRole(str, Enum):
    """Role of the sender in a chat message."""

    DM = "dm"
    AI = "ai"
    SYSTEM = "system"
