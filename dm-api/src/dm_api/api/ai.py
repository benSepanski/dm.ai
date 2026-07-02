"""AI / proposals API endpoints.

When a LOCATION or CHARACTER proposal is accepted, a concrete entity record is
created in the database so the world state reflects the DM's decision immediately.
The created entity's ID is written back into proposal.content["created_entity_id"]
for traceability (harness-engineering: citation anchors survive the transition).

CHARACTER proposals are additionally deduplicated by (world_id, name) using a
case-insensitive match: if the AI re-proposes an already-established character
(e.g. after resending a duplicate narration turn), accepting the proposal
reuses the existing Character row instead of inserting a second one, and the
response's ``duplicate_merged`` field is set so the DM UI can surface it. This
is enforced at the database layer by a unique index on
``(world_id, lower(name))`` (see ``ix_characters_world_id_lower_name``), so a
race between two concurrent accepts for the same new name cannot both insert:
the losing insert's IntegrityError is caught and it falls back to reusing the
row the winner just committed.

PT-21: a proposal may carry gated ``pending_narration`` — narration text the
model deferred (via ``[PENDING]...[/PENDING]``) until this entity is settled
canon. Accepting the proposal appends that narration as a new AI ChatMessage
(citing the originating turn via ``entity_refs``) and broadcasts it; rejecting
simply discards it — it is never persisted to chat.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from game_engine.types import ChatRole, ProposalStatus, ProposalType
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dm_api.api._proposal_entities import (
    create_character_from_proposal,
    create_location_from_proposal,
)
from dm_api.api.auth import ClientRole, require_dm
from dm_api.api.ws import broadcast_to_session
from dm_api.db.models.chat import ChatMessage
from dm_api.db.models.proposal import Proposal, ProposalAccept, ProposalRead, ProposalReject
from dm_api.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------


@router.get("/proposals/{proposal_id}", response_model=ProposalRead)
async def get_proposal(
    proposal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _role: ClientRole = Depends(require_dm),
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
    _role: ClientRole = Depends(require_dm),
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
    _role: ClientRole = Depends(require_dm),
) -> ProposalRead:
    """Accept a pending proposal.

    For LOCATION and CHARACTER proposals, this also creates the corresponding
    entity row in the database. The created entity's ID is stored in
    proposal.content["created_entity_id"] for citation traceability. For
    CHARACTER proposals, if a Character with the same name (case-insensitive)
    already exists in the world, that existing row is reused instead of
    inserting a duplicate, and the response's ``duplicate_merged`` flag is set.
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
    duplicate_merged = False
    if proposal.type == ProposalType.LOCATION:
        created_id = await create_location_from_proposal(proposal, db)
    elif proposal.type == ProposalType.CHARACTER:
        character_result = await create_character_from_proposal(proposal, db)
        if character_result is not None:
            created_id = character_result.character_id
            duplicate_merged = character_result.duplicate_merged

    if created_id is not None:
        proposal.content = {**(proposal.content or {}), "created_entity_id": str(created_id)}

    # PT-21: gated narration was withheld from chat until this proposal was
    # accepted. Release it now as a new AI ChatMessage, citing the original
    # AI turn's precomputed anchor via entity_refs.
    narration_message: ChatMessage | None = None
    if proposal.pending_narration is not None and proposal.session_id is not None:
        narration_message = ChatMessage(
            session_id=proposal.session_id,
            role=ChatRole.AI,
            content=proposal.pending_narration,
            token_count=len(proposal.pending_narration) // 4,
            entity_refs=[proposal.source_anchor] if proposal.source_anchor else None,
        )
        db.add(narration_message)
        await db.flush()
        await db.refresh(narration_message)

    await db.commit()
    await db.refresh(proposal)
    result_read = ProposalRead.model_validate(proposal)
    result_read.duplicate_merged = duplicate_merged

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
            dm_only=True,
        )
        if created_id is not None:
            await broadcast_to_session(
                session_id_str,
                {
                    "type": "entity_update",
                    "session_id": session_id_str,
                    "entity_type": proposal.type.value,
                    "entity_id": str(created_id),
                },
            )
        if narration_message is not None:
            await broadcast_to_session(
                session_id_str,
                {
                    "type": "chat_message",
                    "session_id": session_id_str,
                    "message_id": str(narration_message.id),
                    "role": ChatRole.AI.value,
                    "content": narration_message.content,
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
    _role: ClientRole = Depends(require_dm),
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

    session_id_str = str(proposal.session_id)
    try:
        await broadcast_to_session(
            session_id_str,
            {
                "type": "proposal_ready",
                "session_id": session_id_str,
                "proposal_id": str(proposal.id),
                "proposal_type": proposal.type.value,
                "status": ProposalStatus.REJECTED.value,
            },
            dm_only=True,
        )
    except Exception:
        logger.exception("ws broadcast failed proposal_id=%s", proposal_id)

    return result_read
