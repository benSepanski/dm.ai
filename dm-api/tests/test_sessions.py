"""Tests for the sessions API endpoints."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from game_engine.types import ProposalType

from dm_api.ai.dm_orchestrator import DMResponse, ProposalPayload


@pytest.mark.asyncio
async def test_create_session(client, world_id):
    r = await client.post(
        "/api/sessions/",
        json={
            "world_id": world_id,
            "name": "Adventure Begins",
            "rule_engine_version": "dnd_5_5e",
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Adventure Begins"
    assert data["world_id"] == world_id
    assert data["rule_engine_version"] == "dnd_5_5e"
    assert data["ended_at"] is None
    assert "id" in data
    assert "started_at" in data


@pytest.mark.asyncio
async def test_create_session_minimal(client, world_id):
    r = await client.post(
        "/api/sessions/",
        json={"world_id": world_id, "name": "Quick Session"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Quick Session"
    assert data["rule_engine_version"] == "dnd_5_5e"


@pytest.mark.asyncio
async def test_get_session(client, world_id):
    r = await client.post(
        "/api/sessions/",
        json={"world_id": world_id, "name": "Test Session"},
    )
    assert r.status_code == 201
    session_id = r.json()["id"]

    r = await client.get(f"/api/sessions/{session_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == session_id
    assert data["name"] == "Test Session"


@pytest.mark.asyncio
async def test_get_session_not_found(client):
    fake_id = str(uuid.uuid4())
    r = await client.get(f"/api/sessions/{fake_id}")
    assert r.status_code == 404
    assert r.json()["detail"] == "Session not found"


@pytest.mark.asyncio
async def test_get_session_messages_empty(client, world_id):
    r = await client.post(
        "/api/sessions/",
        json={"world_id": world_id, "name": "Empty Session"},
    )
    assert r.status_code == 201
    session_id = r.json()["id"]

    r = await client.get(f"/api/sessions/{session_id}/messages")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_end_session(client, world_id):
    """Test ending a session — mock the AI backend to avoid real API calls."""
    r = await client.post(
        "/api/sessions/",
        json={"world_id": world_id, "name": "Session To End"},
    )
    assert r.status_code == 201
    session_id = r.json()["id"]

    # Mock the AI orchestrator so it doesn't make real Anthropic calls
    mock_orchestrator = MagicMock()
    mock_orchestrator.summarize = AsyncMock(return_value="A brief adventure summary.")

    with patch("dm_api.api.sessions.DMOrchestrator", return_value=mock_orchestrator):
        r = await client.put(f"/api/sessions/{session_id}/end")

    assert r.status_code == 200
    data = r.json()
    assert data["id"] == session_id
    assert data["ended_at"] is not None


@pytest.mark.asyncio
async def test_end_session_no_messages(client, world_id):
    """End a session with no chat history — should not call summarize."""
    r = await client.post(
        "/api/sessions/",
        json={"world_id": world_id, "name": "Empty Session To End"},
    )
    assert r.status_code == 201
    session_id = r.json()["id"]

    # No messages means no summarize call needed
    r = await client.put(f"/api/sessions/{session_id}/end")
    assert r.status_code == 200
    data = r.json()
    assert data["ended_at"] is not None


@pytest.mark.asyncio
async def test_end_session_not_found(client):
    fake_id = str(uuid.uuid4())
    r = await client.put(f"/api/sessions/{fake_id}/end")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Session chat — mocked AI backend
# ---------------------------------------------------------------------------


def _mock_orchestrator(
    response_text: str, proposals: list[ProposalPayload] | None = None
) -> MagicMock:
    """Return a DMOrchestrator mock that produces a fixed DMResponse."""
    mock = MagicMock()
    mock.handle_message = AsyncMock(
        return_value=DMResponse(
            response=response_text,
            proposals=proposals or [],
            was_condensed=False,
            tokens_in=100,
            tokens_out=50,
        )
    )
    return mock


@pytest.mark.asyncio
async def test_session_chat_returns_ai_response(client, world_id):
    """POST /sessions/{id}/chat returns the AI response text."""
    r = await client.post(
        "/api/sessions/",
        json={"world_id": world_id, "name": "Chat Test"},
    )
    session_id = r.json()["id"]

    mock_orch = _mock_orchestrator("The tavern smells of pipe smoke and old ale.")
    with patch("dm_api.api.sessions.DMOrchestrator", return_value=mock_orch):
        r = await client.post(
            f"/api/sessions/{session_id}/chat",
            json={"message": "Describe the tavern."},
        )

    assert r.status_code == 200
    data = r.json()
    assert data["response"] == "The tavern smells of pipe smoke and old ale."
    assert data["proposals"] == []


@pytest.mark.asyncio
async def test_session_chat_persists_messages(client, world_id):
    """DM and AI messages are both written to the DB and returned by GET /messages."""
    r = await client.post(
        "/api/sessions/",
        json={"world_id": world_id, "name": "Persist Chat"},
    )
    session_id = r.json()["id"]

    mock_orch = _mock_orchestrator("The gate stands open.")
    with patch("dm_api.api.sessions.DMOrchestrator", return_value=mock_orch):
        await client.post(
            f"/api/sessions/{session_id}/chat",
            json={"message": "What do I see at the city gate?"},
        )

    r = await client.get(f"/api/sessions/{session_id}/messages")
    assert r.status_code == 200
    messages = r.json()
    assert len(messages) == 2
    roles = [m["role"] for m in messages]
    assert "dm" in roles
    assert "ai" in roles


@pytest.mark.asyncio
async def test_session_chat_creates_pending_proposal(client, world_id):
    """When the AI response includes a proposal, it is saved as PENDING."""
    r = await client.post(
        "/api/sessions/",
        json={"world_id": world_id, "name": "Proposal Chat"},
    )
    session_id = r.json()["id"]

    payloads = [
        ProposalPayload(type=ProposalType.LOCATION, content={"name": "Riverbend"}),
        ProposalPayload(type=ProposalType.CHARACTER, content={"name": "Old Tom"}),
    ]
    mock_orch = _mock_orchestrator("You discover a new village.", proposals=payloads)
    with patch("dm_api.api.sessions.DMOrchestrator", return_value=mock_orch):
        r = await client.post(
            f"/api/sessions/{session_id}/chat",
            json={"message": "Explore the road north."},
        )

    assert r.status_code == 200
    data = r.json()
    assert len(data["proposals"]) == 2
    assert data["proposals"][0]["type"] == "location"
    assert data["proposals"][1]["type"] == "character"
    assert all(p["status"] == "pending" for p in data["proposals"])

    # Every proposal is listed under the session (regression: blocks after
    # the first used to be silently dropped).
    r = await client.get(f"/api/ai/sessions/{session_id}/proposals")
    assert r.status_code == 200
    proposals = r.json()
    assert len(proposals) == 2
    assert {p["type"] for p in proposals} == {"location", "character"}


@pytest.mark.asyncio
async def test_session_chat_ai_message_uses_actual_token_count(client, world_id):
    """AI message token_count must come from DMResponse.tokens_out, not len()/4 estimate.

    The condenser's budget arithmetic depends on per-message token counts stored in
    the DB.  Using the API-reported count (tokens_out=50) rather than a
    character-length estimate ensures the budget is accurate.
    """
    r = await client.post(
        "/api/sessions/",
        json={"world_id": world_id, "name": "Token Count Test"},
    )
    session_id = r.json()["id"]

    response_text = "Short reply."
    # tokens_out=50 != len("Short reply.") // 4 == 3
    mock_orch = _mock_orchestrator(response_text)  # tokens_out=50 is hardcoded in helper

    with patch("dm_api.api.sessions.DMOrchestrator", return_value=mock_orch):
        await client.post(
            f"/api/sessions/{session_id}/chat",
            json={"message": "Hello."},
        )

    r = await client.get(f"/api/sessions/{session_id}/messages")
    messages = r.json()
    ai_msg = next(m for m in messages if m["role"] == "ai")
    assert ai_msg["token_count"] == 50, (
        f"Expected token_count=50 (from tokens_out), got {ai_msg['token_count']}. "
        "AI message token count must use DMResponse.tokens_out, not len(content)//4."
    )


@pytest.mark.asyncio
async def test_session_chat_includes_world_context(client):
    """The orchestrator receives world lore + prior session summaries."""
    r = await client.post(
        "/api/worlds/",
        json={
            "name": "Lore World",
            "setting_description": "A frozen wasteland.",
            "lore_summary": "The Ice Court rules from Glacier Keep.",
        },
    )
    world = r.json()["id"]

    # A finished earlier session whose summary should be carried forward.
    r = await client.post("/api/sessions/", json={"world_id": world, "name": "Session One"})
    first_session = r.json()["id"]
    mock_orch = _mock_orchestrator("You brave the tundra.")
    mock_orch.summarize = AsyncMock(return_value="The party crossed the tundra.")
    with patch("dm_api.api.sessions.DMOrchestrator", return_value=mock_orch):
        await client.post(f"/api/sessions/{first_session}/chat", json={"message": "Onward."})
        await client.put(f"/api/sessions/{first_session}/end")

    r = await client.post("/api/sessions/", json={"world_id": world, "name": "Session Two"})
    second_session = r.json()["id"]
    mock_orch2 = _mock_orchestrator("Welcome back.")
    with patch("dm_api.api.sessions.DMOrchestrator", return_value=mock_orch2):
        await client.post(f"/api/sessions/{second_session}/chat", json={"message": "Recap?"})

    ctx = mock_orch2.handle_message.call_args.kwargs["world_context"]
    assert ctx.setting_description == "A frozen wasteland."
    assert ctx.lore_summary == "The Ice Court rules from Glacier Keep."
    assert ctx.prior_session_summaries == ("Session One: The party crossed the tundra.",)


@pytest.mark.asyncio
async def test_session_chat_not_found(client):
    r = await client.post(
        f"/api/sessions/{uuid.uuid4()}/chat",
        json={"message": "Hello?"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_session_chat_rejected_after_end(client, world_id):
    """Chatting with an ended session must return 409, not silently succeed.

    Regression: session_chat had no guard on ended_at; messages would be
    persisted into a concluded session leaving it in an inconsistent state.
    """
    r = await client.post(
        "/api/sessions/",
        json={"world_id": world_id, "name": "Ended Session"},
    )
    assert r.status_code == 201
    session_id = r.json()["id"]

    r = await client.put(f"/api/sessions/{session_id}/end")
    assert r.status_code == 200
    assert r.json()["ended_at"] is not None

    r = await client.post(
        f"/api/sessions/{session_id}/chat",
        json={"message": "One more thing..."},
    )
    assert r.status_code == 409
    assert r.json()["detail"] == "Session has ended"
