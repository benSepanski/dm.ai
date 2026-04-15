"""Tests for the AI proposals endpoints."""

import uuid

import pytest


async def _create_proposal(client, world_id, session_id):
    """Helper: create a proposal directly via DB-level fixtures via the session chat mock.
    Instead, we insert directly using the db_session fixture for setup.
    """


@pytest.mark.asyncio
async def test_get_proposal_not_found(client):
    """Getting a non-existent proposal returns 404."""
    fake_id = str(uuid.uuid4())
    r = await client.get(f"/api/ai/proposals/{fake_id}")
    assert r.status_code == 404
    assert r.json()["detail"] == "Proposal not found"


@pytest.mark.asyncio
async def test_list_session_proposals_empty(client, world_id):
    """Listing proposals for a session with none returns empty list."""
    # Create a session
    r = await client.post(
        "/api/sessions/",
        json={"world_id": world_id, "name": "ProposalSession"},
    )
    assert r.status_code == 201
    session_id = r.json()["id"]

    r = await client.get(f"/api/ai/sessions/{session_id}/proposals")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_accept_proposal_not_found(client):
    fake_id = str(uuid.uuid4())
    r = await client.post(f"/api/ai/proposals/{fake_id}/accept", json={})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_reject_proposal_not_found(client):
    fake_id = str(uuid.uuid4())
    r = await client.post(f"/api/ai/proposals/{fake_id}/reject", json={})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_proposal_lifecycle(client, world_id, db_session):
    """Create a proposal directly in the DB, then accept it via API."""
    from game_engine.types import ProposalStatus, ProposalType

    from dm_api.db.models.proposal import Proposal

    # Create a session
    r = await client.post(
        "/api/sessions/",
        json={"world_id": world_id, "name": "ProposalLifecycle"},
    )
    assert r.status_code == 201
    session_id = r.json()["id"]

    # Insert a proposal directly into the DB
    proposal = Proposal(
        session_id=uuid.UUID(session_id),
        world_id=uuid.UUID(world_id),
        type=ProposalType.LOCATION,
        content={"name": "Hidden Cave", "description": "A secret cave"},
        status=ProposalStatus.PENDING,
    )
    db_session.add(proposal)
    await db_session.commit()
    await db_session.refresh(proposal)
    proposal_id = str(proposal.id)

    # Get it via API
    r = await client.get(f"/api/ai/proposals/{proposal_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == proposal_id
    assert data["status"] == "pending"
    assert data["type"] == "location"

    # Accept it
    r = await client.post(
        f"/api/ai/proposals/{proposal_id}/accept",
        json={"dm_notes": "Good idea!"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "accepted"
    assert data["dm_notes"] == "Good idea!"


@pytest.mark.asyncio
async def test_proposal_reject(client, world_id, db_session):
    """Create a proposal directly in the DB, then reject it via API."""
    from game_engine.types import ProposalStatus, ProposalType

    from dm_api.db.models.proposal import Proposal

    # Create a session
    r = await client.post(
        "/api/sessions/",
        json={"world_id": world_id, "name": "ProposalReject"},
    )
    assert r.status_code == 201
    session_id = r.json()["id"]

    proposal = Proposal(
        session_id=uuid.UUID(session_id),
        world_id=uuid.UUID(world_id),
        type=ProposalType.CHARACTER,
        content={"name": "Bob the Villain"},
        status=ProposalStatus.PENDING,
    )
    db_session.add(proposal)
    await db_session.commit()
    await db_session.refresh(proposal)
    proposal_id = str(proposal.id)

    r = await client.post(
        f"/api/ai/proposals/{proposal_id}/reject",
        json={"dm_notes": "Not suitable"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "rejected"
    assert data["dm_notes"] == "Not suitable"


@pytest.mark.asyncio
async def test_accept_already_accepted_proposal(client, world_id, db_session):
    """Trying to accept an already-accepted proposal returns 409."""
    from game_engine.types import ProposalStatus, ProposalType

    from dm_api.db.models.proposal import Proposal

    r = await client.post(
        "/api/sessions/",
        json={"world_id": world_id, "name": "ConflictSession"},
    )
    session_id = r.json()["id"]

    proposal = Proposal(
        session_id=uuid.UUID(session_id),
        world_id=uuid.UUID(world_id),
        type=ProposalType.DIALOGUE,
        content={},
        status=ProposalStatus.ACCEPTED,  # already accepted
    )
    db_session.add(proposal)
    await db_session.commit()
    await db_session.refresh(proposal)
    proposal_id = str(proposal.id)

    r = await client.post(f"/api/ai/proposals/{proposal_id}/accept", json={})
    assert r.status_code == 409
