"""Entity-creation helpers for accepted proposals.

Split out of ``ai.py`` (file-length guideline) — owns turning an accepted
LOCATION/CHARACTER proposal into a concrete database row, including the
CHARACTER dedup-by-name behavior described in ``ai.py``'s module docstring.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any

from game_engine.types import CharacterType, LocationType
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from dm_api.db.models.character import Character
from dm_api.db.models.location import Location
from dm_api.db.models.proposal import Proposal

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CharacterCreationResult:
    """Typed outcome of accepting a CHARACTER proposal.

    ``duplicate_merged`` is True when an existing Character with the same
    name (case-insensitive) already existed in the world and was reused
    instead of inserting a new row.
    """

    character_id: uuid.UUID
    duplicate_merged: bool


def _location_type_from_content(content: dict[str, Any]) -> LocationType:
    """Parse LocationType from proposal content; fall back to BUILDING."""
    raw = content.get("type", "")
    try:
        return LocationType(raw)
    except ValueError:
        return LocationType.BUILDING


def _character_type_from_content(content: dict[str, Any]) -> CharacterType:
    """Parse CharacterType from proposal content; fall back to NPC."""
    raw = content.get("type", "")
    try:
        return CharacterType(raw)
    except ValueError:
        return CharacterType.NPC


async def create_location_from_proposal(
    proposal: Proposal,
    db: AsyncSession,
) -> uuid.UUID | None:
    """Create a Location record from an accepted LOCATION proposal.

    Returns the new Location's UUID, or None if the content lacks a name.
    """
    content: dict[str, Any] = proposal.content or {}
    name: str | None = content.get("name")
    if not name:
        logger.warning(
            "accept_proposal: LOCATION proposal %s has no name — skipping entity creation",
            proposal.id,
        )
        return None

    location = Location(
        world_id=proposal.world_id,
        type=_location_type_from_content(content),
        name=name,
        description=content.get("description"),
        lore=content.get("lore"),
        history=content.get("history"),
    )
    db.add(location)
    await db.flush()
    logger.info(
        "accept_proposal: created Location %s (%s) from proposal %s",
        location.id,
        name,
        proposal.id,
    )
    return location.id


async def _find_existing_character_by_name(
    world_id: uuid.UUID,
    name: str,
    db: AsyncSession,
) -> Character | None:
    """Look up an existing Character in ``world_id`` with a case-insensitive
    name match (e.g. "Vess Moray" vs "vess moray")."""
    result = await db.execute(
        select(Character).where(
            Character.world_id == world_id,
            func.lower(Character.name) == name.lower(),
        )
    )
    return result.scalars().first()


async def create_character_from_proposal(
    proposal: Proposal,
    db: AsyncSession,
) -> CharacterCreationResult | None:
    """Create a Character record from an accepted CHARACTER proposal.

    If a Character with the same name (case-insensitive) already exists in
    this world, no duplicate row is inserted — the existing character's id is
    reused instead, and ``duplicate_merged`` is set on the result so the
    caller can surface that to the DM.

    The (world_id, lower(name)) uniqueness is also enforced at the database
    layer (``ix_characters_world_id_lower_name``), so if a concurrent request
    commits the same name between our pre-check and our insert, the insert
    raises IntegrityError; that race is caught here (inside a SAVEPOINT, so
    only the failed insert is rolled back — not the caller's other pending
    changes on this proposal) and resolved by re-fetching and reusing the row
    the concurrent request just created.

    Returns None if the content lacks a name.
    """
    content: dict[str, Any] = proposal.content or {}
    name: str | None = content.get("name")
    if not name:
        logger.warning(
            "accept_proposal: CHARACTER proposal %s has no name — skipping entity creation",
            proposal.id,
        )
        return None

    existing = await _find_existing_character_by_name(proposal.world_id, name, db)
    if existing is not None:
        logger.info(
            "accept_proposal: CHARACTER proposal %s matches existing Character %s (%s) — "
            "reusing instead of creating a duplicate",
            proposal.id,
            existing.id,
            existing.name,
        )
        return CharacterCreationResult(character_id=existing.id, duplicate_merged=True)

    level_raw = content.get("level", 1)
    try:
        level = int(level_raw)
    except (TypeError, ValueError):
        level = 1

    character = Character(
        world_id=proposal.world_id,
        type=_character_type_from_content(content),
        name=name,
        race=content.get("race"),
        char_class=content.get("class"),
        level=level,
        alignment=content.get("alignment"),
        personality_traits=content.get("personality_traits"),
        ideals=content.get("ideals"),
        bonds=content.get("bonds"),
        flaws=content.get("flaws"),
    )
    try:
        async with db.begin_nested():
            db.add(character)
            await db.flush()
    except IntegrityError:
        # Lost the race: a concurrent accept committed a Character with the
        # same (world_id, lower(name)) between our pre-check and our insert.
        # The SAVEPOINT above rolled back only this insert — the caller's
        # other pending changes on this proposal are untouched — so we can
        # simply look up and reuse the row the winner just created.
        winner = await _find_existing_character_by_name(proposal.world_id, name, db)
        if winner is None:
            # Should be unreachable — the unique index only rejects our
            # insert if a matching row now exists — but never silently
            # swallow an unexplained IntegrityError.
            raise
        logger.info(
            "accept_proposal: CHARACTER proposal %s lost a concurrent-accept race to "
            "existing Character %s (%s) — reusing instead of creating a duplicate",
            proposal.id,
            winner.id,
            winner.name,
        )
        return CharacterCreationResult(character_id=winner.id, duplicate_merged=True)

    logger.info(
        "accept_proposal: created Character %s (%s) from proposal %s",
        character.id,
        name,
        proposal.id,
    )
    return CharacterCreationResult(character_id=character.id, duplicate_merged=False)
