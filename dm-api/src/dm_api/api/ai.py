"""AI / proposals API endpoints.

When a LOCATION or CHARACTER proposal is accepted, a concrete entity record is
created in the database so the world state reflects the DM's decision immediately.
The created entity's ID is written back into proposal.content["created_entity_id"]
for traceability (harness-engineering: citation anchors survive the transition).
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from game_engine.types import CharacterType, LocationType, ProposalStatus, ProposalType
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dm_api.api.ws import broadcast_to_session
from dm_api.db.models.character import Character
from dm_api.db.models.location import Location
from dm_api.db.models.proposal import Proposal, ProposalAccept, ProposalRead, ProposalReject
from dm_api.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Entity-creation helpers — validate at the AI boundary, then write typed rows
# ---------------------------------------------------------------------------


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


async def _create_location_from_proposal(
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


async def _create_character_from_proposal(
    proposal: Proposal,
    db: AsyncSession,
) -> uuid.UUID | None:
    """Create a Character record from an accepted CHARACTER proposal.

    Returns the new Character's UUID, or None if the content lacks a name.
    """
    content: dict[str, Any] = proposal.content or {}
    name: str | None = content.get("name")
    if not name:
        logger.warning(
            "accept_proposal: CHARACTER proposal %s has no name — skipping entity creation",
            proposal.id,
        )
        return None

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
    db.add(character)
    await db.flush()
    logger.info(
        "accept_proposal: created Character %s (%s) from proposal %s",
        character.id,
        name,
        proposal.id,
    )
    return character.id


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------


@router.get("/proposals/{proposal_id}", response_model=ProposalRead)
async def get_proposal(
    proposal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ProposalRead:
    result = await db.execute(select(Proposal).where(Proposal.id == proposal_id))
    proposal = result.scalar_one_or_none()
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return ProposalRead.model_validate(proposal)


@router.get("/sessions/{session_id}/proposals", response_model=list[ProposalRead])
async def list_session_proposals(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[ProposalRead]:
    result = await db.execute(
        select(Proposal)
        .where(Proposal.session_id == session_id)
        .order_by(Proposal.created_at.desc())
    )
    proposals = result.scalars().all()
    return [ProposalRead.model_validate(p) for p in proposals]


@router.post("/proposals/{proposal_id}/accept", response_model=ProposalRead)
async def accept_proposal(
    proposal_id: uuid.UUID,
    payload: ProposalAccept,
    db: AsyncSession = Depends(get_db),
) -> ProposalRead:
    """Accept a pending proposal.

    For LOCATION and CHARACTER proposals, this also creates the corresponding
    entity row in the database. The created entity's ID is stored in
    proposal.content["created_entity_id"] for citation traceability.
    """
    result = await db.execute(select(Proposal).where(Proposal.id == proposal_id))
    proposal = result.scalar_one_or_none()
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if proposal.status != ProposalStatus.PENDING:
        raise HTTPException(status_code=409, detail="Proposal is not pending")

    # Apply DM modifications before entity creation so the entity reflects
    # any changes the DM made at review time.
    proposal.status = ProposalStatus.ACCEPTED
    if payload.dm_notes:
        proposal.dm_notes = payload.dm_notes
    if payload.modifications:
        proposal.content = {**(proposal.content or {}), **payload.modifications}

    # Create the concrete world entity for applicable proposal types.
    created_id: uuid.UUID | None = None
    if proposal.type == ProposalType.LOCATION:
        created_id = await _create_location_from_proposal(proposal, db)
    elif proposal.type == ProposalType.CHARACTER:
        created_id = await _create_character_from_proposal(proposal, db)

    if created_id is not None:
        proposal.content = {**(proposal.content or {}), "created_entity_id": str(created_id)}

    await db.commit()
    await db.refresh(proposal)
    result_read = ProposalRead.model_validate(proposal)

    # Notify clients: proposal status changed; if an entity was created, also emit entity_update.
    session_id_str = str(proposal.session_id)
    try:
        await broadcast_to_session(
            session_id_str,
            {
                "type": "proposal_ready",
                "session_id": session_id_str,
                "proposal_id": str(proposal.id),
                "proposal_type": proposal.type.value,
                "status": ProposalStatus.ACCEPTED.value,
            },
        )
        if created_id is not None:
            entity_type = "location" if proposal.type == ProposalType.LOCATION else "character"
            await broadcast_to_session(
                session_id_str,
                {
                    "type": "entity_update",
                    "session_id": session_id_str,
                    "entity_type": entity_type,
                    "entity_id": str(created_id),
                },
            )
    except Exception:
        logger.exception("ws broadcast failed proposal_id=%s", proposal_id)

    return result_read


@router.post("/proposals/{proposal_id}/reject", response_model=ProposalRead)
async def reject_proposal(
    proposal_id: uuid.UUID,
    payload: ProposalReject,
    db: AsyncSession = Depends(get_db),
) -> ProposalRead:
    result = await db.execute(select(Proposal).where(Proposal.id == proposal_id))
    proposal = result.scalar_one_or_none()
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if proposal.status != ProposalStatus.PENDING:
        raise HTTPException(status_code=409, detail="Proposal is not pending")

    proposal.status = ProposalStatus.REJECTED
    if payload.dm_notes:
        proposal.dm_notes = payload.dm_notes

    await db.commit()
    await db.refresh(proposal)
    result_read = ProposalRead.model_validate(proposal)

    try:
        await broadcast_to_session(
            str(proposal.session_id),
            {
                "type": "proposal_ready",
                "session_id": str(proposal.session_id),
                "proposal_id": str(proposal.id),
                "proposal_type": proposal.type.value,
                "status": ProposalStatus.REJECTED.value,
            },
        )
    except Exception:
        logger.exception("ws broadcast failed proposal_id=%s", proposal_id)

    return result_read
