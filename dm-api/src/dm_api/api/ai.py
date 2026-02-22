import uuid

from fastapi import APIRouter, Depends, HTTPException
from game_engine.types import ProposalStatus
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dm_api.db.models.proposal import Proposal, ProposalAccept, ProposalRead, ProposalReject
from dm_api.db.session import get_db

router = APIRouter()


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
    result = await db.execute(select(Proposal).where(Proposal.id == proposal_id))
    proposal = result.scalar_one_or_none()
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if proposal.status != ProposalStatus.PENDING:
        raise HTTPException(status_code=409, detail="Proposal is not pending")

    proposal.status = ProposalStatus.ACCEPTED
    if payload.dm_notes:
        proposal.dm_notes = payload.dm_notes
    if payload.modifications:
        merged = {**(proposal.content or {}), **payload.modifications}
        proposal.content = merged

    await db.commit()
    await db.refresh(proposal)
    return ProposalRead.model_validate(proposal)


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
    return ProposalRead.model_validate(proposal)
