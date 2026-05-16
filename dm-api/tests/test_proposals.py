"""Tests for the AI proposals endpoints — including entity creation on acceptance."""

from __future__ import annotations

import uuid

import pytest
from game_engine.types import ProposalStatus, ProposalType

from dm_api.db.models.character import Character
from dm_api.db.models.location import Location
from dm_api.db.models.proposal import Proposal

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_session(client, world_id: str, name: str = "S") -> str:
    r = await client.post("/api/sessions/", json={"world_id": world_id, "name": name})
    assert r.status_code == 201
    return r.json()["id"]


async def _insert_proposal(
    db_session,
    *,
    world_id: str,
    session_id: str,
    ptype: ProposalType,
    content: dict,
    status: ProposalStatus = ProposalStatus.PENDING,
) -> str:
    proposal = Proposal(
        session_id=uuid.UUID(session_id),
        world_id=uuid.UUID(world_id),
        type=ptype,
        content=content,
        status=status,
    )
    db_session.add(proposal)
    await db_session.commit()
    await db_session.refresh(proposal)
    return str(proposal.id)


# ---------------------------------------------------------------------------
# Basic CRUD / 404 / 409 guards
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_proposal_not_found(client):
    r = await client.get(f"/api/ai/proposals/{uuid.uuid4()}")
    assert r.status_code == 404
    assert r.json()["detail"] == "Proposal not found"


@pytest.mark.asyncio
async def test_list_session_proposals_empty(client, world_id):
    session_id = await _make_session(client, world_id, "Empty")
    r = await client.get(f"/api/ai/sessions/{session_id}/proposals")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_accept_proposal_not_found(client):
    r = await client.post(f"/api/ai/proposals/{uuid.uuid4()}/accept", json={})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_reject_proposal_not_found(client):
    r = await client.post(f"/api/ai/proposals/{uuid.uuid4()}/reject", json={})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_accept_already_accepted_proposal(client, world_id, db_session):
    session_id = await _make_session(client, world_id, "Conflict")
    proposal_id = await _insert_proposal(
        db_session,
        world_id=world_id,
        session_id=session_id,
        ptype=ProposalType.DIALOGUE,
        content={},
        status=ProposalStatus.ACCEPTED,
    )
    r = await client.post(f"/api/ai/proposals/{proposal_id}/accept", json={})
    assert r.status_code == 409


# ---------------------------------------------------------------------------
# Basic lifecycle (non-entity proposal types)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_proposal_lifecycle_dialogue(client, world_id, db_session):
    """DIALOGUE proposals are accepted without entity creation."""
    session_id = await _make_session(client, world_id, "Lifecycle")
    proposal_id = await _insert_proposal(
        db_session,
        world_id=world_id,
        session_id=session_id,
        ptype=ProposalType.DIALOGUE,
        content={"text": "Welcome, traveller."},
    )

    r = await client.get(f"/api/ai/proposals/{proposal_id}")
    assert r.status_code == 200
    assert r.json()["status"] == "pending"

    r = await client.post(
        f"/api/ai/proposals/{proposal_id}/accept",
        json={"dm_notes": "Great line!"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "accepted"
    assert data["dm_notes"] == "Great line!"
    assert "created_entity_id" not in (data.get("content") or {})


@pytest.mark.asyncio
async def test_proposal_reject(client, world_id, db_session):
    session_id = await _make_session(client, world_id, "RejectTest")
    proposal_id = await _insert_proposal(
        db_session,
        world_id=world_id,
        session_id=session_id,
        ptype=ProposalType.CHARACTER,
        content={"name": "Villain"},
    )

    r = await client.post(
        f"/api/ai/proposals/{proposal_id}/reject",
        json={"dm_notes": "Not suitable"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "rejected"
    assert data["dm_notes"] == "Not suitable"


# ---------------------------------------------------------------------------
# Entity creation: LOCATION proposal
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_accept_location_proposal_creates_location(client, world_id, db_session):
    """Accepting a LOCATION proposal creates a Location row."""
    from sqlalchemy import select

    session_id = await _make_session(client, world_id, "LocProposal")
    proposal_id = await _insert_proposal(
        db_session,
        world_id=world_id,
        session_id=session_id,
        ptype=ProposalType.LOCATION,
        content={
            "name": "Hidden Cave",
            "type": "building",
            "description": "A secret cave behind the waterfall.",
            "lore": "Dwarves built it centuries ago.",
        },
    )

    r = await client.post(f"/api/ai/proposals/{proposal_id}/accept", json={})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "accepted"
    entity_id = data["content"]["created_entity_id"]
    assert entity_id is not None

    # Verify the Location row exists in the DB.
    result = await db_session.execute(select(Location).where(Location.id == uuid.UUID(entity_id)))
    loc = result.scalar_one_or_none()
    assert loc is not None
    assert loc.name == "Hidden Cave"
    assert loc.description == "A secret cave behind the waterfall."
    assert loc.lore == "Dwarves built it centuries ago."
    assert str(loc.world_id) == world_id


@pytest.mark.asyncio
async def test_accept_location_proposal_applies_dm_modifications(client, world_id, db_session):
    """DM modifications are merged into content before the Location is created."""
    from sqlalchemy import select

    session_id = await _make_session(client, world_id, "LocMod")
    proposal_id = await _insert_proposal(
        db_session,
        world_id=world_id,
        session_id=session_id,
        ptype=ProposalType.LOCATION,
        content={"name": "Old Mine", "description": "Original description."},
    )

    r = await client.post(
        f"/api/ai/proposals/{proposal_id}/accept",
        json={"modifications": {"name": "Haunted Mine", "description": "Updated description."}},
    )
    assert r.status_code == 200
    data = r.json()
    entity_id = data["content"]["created_entity_id"]

    result = await db_session.execute(select(Location).where(Location.id == uuid.UUID(entity_id)))
    loc = result.scalar_one()
    assert loc.name == "Haunted Mine"
    assert loc.description == "Updated description."


@pytest.mark.asyncio
async def test_accept_location_proposal_no_name_skips_entity(client, world_id, db_session):
    """A LOCATION proposal without a name is accepted but no entity is created."""
    session_id = await _make_session(client, world_id, "NoName")
    proposal_id = await _insert_proposal(
        db_session,
        world_id=world_id,
        session_id=session_id,
        ptype=ProposalType.LOCATION,
        content={"description": "A mysterious place with no name yet."},
    )

    r = await client.post(f"/api/ai/proposals/{proposal_id}/accept", json={})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "accepted"
    assert "created_entity_id" not in (data.get("content") or {})


# ---------------------------------------------------------------------------
# Entity creation: CHARACTER proposal
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_accept_character_proposal_creates_character(client, world_id, db_session):
    """Accepting a CHARACTER proposal creates a Character row."""
    from sqlalchemy import select

    session_id = await _make_session(client, world_id, "CharProposal")
    proposal_id = await _insert_proposal(
        db_session,
        world_id=world_id,
        session_id=session_id,
        ptype=ProposalType.CHARACTER,
        content={
            "name": "Elara Dawnwhisper",
            "type": "npc",
            "race": "Elf",
            "char_class": "Wizard",
            "level": 5,
            "personality_traits": "Curious and bookish.",
        },
    )

    r = await client.post(f"/api/ai/proposals/{proposal_id}/accept", json={})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "accepted"
    entity_id = data["content"]["created_entity_id"]

    result = await db_session.execute(
        select(Character).where(Character.id == uuid.UUID(entity_id))
    )
    char = result.scalar_one_or_none()
    assert char is not None
    assert char.name == "Elara Dawnwhisper"
    assert char.race == "Elf"
    assert char.char_class == "Wizard"
    assert char.level == 5
    assert char.personality_traits == "Curious and bookish."
    assert str(char.world_id) == world_id


@pytest.mark.asyncio
async def test_accept_character_proposal_unknown_type_defaults_to_npc(
    client, world_id, db_session
):
    """An unrecognised character type falls back to NPC."""
    from sqlalchemy import select

    session_id = await _make_session(client, world_id, "TypeFallback")
    proposal_id = await _insert_proposal(
        db_session,
        world_id=world_id,
        session_id=session_id,
        ptype=ProposalType.CHARACTER,
        content={"name": "Mystery Entity", "type": "unknown_type"},
    )

    r = await client.post(f"/api/ai/proposals/{proposal_id}/accept", json={})
    assert r.status_code == 200
    entity_id = r.json()["content"]["created_entity_id"]

    result = await db_session.execute(
        select(Character).where(Character.id == uuid.UUID(entity_id))
    )
    char = result.scalar_one()
    from game_engine.types import CharacterType

    assert char.type == CharacterType.NPC


@pytest.mark.asyncio
async def test_accept_character_proposal_no_name_skips_entity(client, world_id, db_session):
    """A CHARACTER proposal without a name is accepted but no entity is created."""
    session_id = await _make_session(client, world_id, "CharNoName")
    proposal_id = await _insert_proposal(
        db_session,
        world_id=world_id,
        session_id=session_id,
        ptype=ProposalType.CHARACTER,
        content={"race": "Human"},
    )

    r = await client.post(f"/api/ai/proposals/{proposal_id}/accept", json={})
    assert r.status_code == 200
    assert "created_entity_id" not in (r.json().get("content") or {})
