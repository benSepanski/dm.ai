"""Tests for POST /sessions/{id}/chat: AI responses, proposals, and PT-21
gated-narration behavior — mocked AI backend throughout.

Split from a larger ``test_sessions.py`` (file-length guideline); session
create/get/end/patch lifecycle tests live in ``test_sessions.py``.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from game_engine.types import ProposalType

from dm_api.ai.backends.base import AIBackendError, AIErrorCategory
from dm_api.ai.dm_orchestrator import DMResponse, ProposalPayload

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
async def test_session_chat_surfaces_ai_auth_error(client, world_id):
    """An AI auth failure becomes a 502 with an actionable, non-bare message."""
    r = await client.post("/api/sessions/", json={"world_id": world_id, "name": "Err"})
    session_id = r.json()["id"]

    mock_orch = MagicMock()
    mock_orch.handle_message = AsyncMock(
        side_effect=AIBackendError(
            AIErrorCategory.AUTH,
            "AI provider rejected the request (authentication failed) — "
            "check ANTHROPIC_API_KEY.",
        )
    )
    with patch("dm_api.api.sessions.DMOrchestrator", return_value=mock_orch):
        r = await client.post(
            f"/api/sessions/{session_id}/chat",
            json={"message": "Begin the tale."},
        )

    assert r.status_code == 502
    assert "ANTHROPIC_API_KEY" in r.json()["detail"]
    assert "Internal Server Error" not in r.json()["detail"]

    # The DM's message is preserved even though the AI turn failed.
    r = await client.get(f"/api/sessions/{session_id}/messages")
    contents = [m["content"] for m in r.json()]
    assert "Begin the tale." in contents


@pytest.mark.asyncio
async def test_session_chat_rate_limit_maps_to_429(client, world_id):
    """A provider rate-limit failure maps to HTTP 429."""
    r = await client.post("/api/sessions/", json={"world_id": world_id, "name": "RL"})
    session_id = r.json()["id"]

    mock_orch = MagicMock()
    mock_orch.handle_message = AsyncMock(
        side_effect=AIBackendError(AIErrorCategory.RATE_LIMIT, "Slow down.")
    )
    with patch("dm_api.api.sessions.DMOrchestrator", return_value=mock_orch):
        r = await client.post(
            f"/api/sessions/{session_id}/chat",
            json={"message": "Onward."},
        )

    assert r.status_code == 429


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


# ---------------------------------------------------------------------------
# PT-21: gated narration only reaches chat once the paired proposal is
# accepted; rejecting the proposal never surfaces it.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_session_chat_pending_narration_not_in_response_before_accept(client, world_id):
    """Narration gated behind a proposal is not present in the chat response
    (nor persisted to the chat transcript) before the proposal is resolved."""
    r = await client.post("/api/sessions/", json={"world_id": world_id, "name": "Gated"})
    session_id = r.json()["id"]

    gated_text = "**Saltmere** spreads above the waterfront, lantern-lit and humming."
    payloads = [
        ProposalPayload(
            type=ProposalType.LOCATION,
            content={"name": "Saltmere"},
            pending_narration=gated_text,
        )
    ]
    mock_orch = _mock_orchestrator(
        "You crest the hill and the coastline comes into view.", proposals=payloads
    )
    with patch("dm_api.api.sessions.DMOrchestrator", return_value=mock_orch):
        r = await client.post(
            f"/api/sessions/{session_id}/chat",
            json={"message": "What do we see?"},
        )

    assert r.status_code == 200
    data = r.json()
    assert gated_text not in data["response"]
    assert len(data["proposals"]) == 1
    proposal = data["proposals"][0]
    assert proposal["pending_narration"] == gated_text
    assert proposal["status"] == "pending"

    # Not persisted to the visible chat transcript either.
    r = await client.get(f"/api/sessions/{session_id}/messages")
    contents = [m["content"] for m in r.json()]
    assert not any(gated_text in c for c in contents)


@pytest.mark.asyncio
async def test_session_chat_pending_narration_appears_after_accept(client, world_id):
    """Accepting the proposal releases the held narration into the chat
    transcript as a new AI ChatMessage."""
    r = await client.post("/api/sessions/", json={"world_id": world_id, "name": "GatedAccept"})
    session_id = r.json()["id"]

    gated_text = "**Saltmere** spreads above the waterfront, lantern-lit and humming."
    payloads = [
        ProposalPayload(
            type=ProposalType.LOCATION,
            content={"name": "Saltmere"},
            pending_narration=gated_text,
        )
    ]
    mock_orch = _mock_orchestrator("You crest the hill.", proposals=payloads)
    with patch("dm_api.api.sessions.DMOrchestrator", return_value=mock_orch):
        r = await client.post(
            f"/api/sessions/{session_id}/chat",
            json={"message": "What do we see?"},
        )
    proposal_id = r.json()["proposals"][0]["id"]

    r = await client.post(f"/api/ai/proposals/{proposal_id}/accept", json={})
    assert r.status_code == 200

    r = await client.get(f"/api/sessions/{session_id}/messages")
    assert r.status_code == 200
    contents = [m["content"] for m in r.json()]
    assert gated_text in contents


@pytest.mark.asyncio
async def test_session_chat_pending_narration_never_surfaces_after_reject(client, world_id):
    """Rejecting the proposal discards the held narration — it never appears
    in the chat transcript."""
    r = await client.post("/api/sessions/", json={"world_id": world_id, "name": "GatedReject"})
    session_id = r.json()["id"]

    gated_text = "**Saltmere** spreads above the waterfront, lantern-lit and humming."
    payloads = [
        ProposalPayload(
            type=ProposalType.LOCATION,
            content={"name": "Saltmere"},
            pending_narration=gated_text,
        )
    ]
    mock_orch = _mock_orchestrator("You crest the hill.", proposals=payloads)
    with patch("dm_api.api.sessions.DMOrchestrator", return_value=mock_orch):
        r = await client.post(
            f"/api/sessions/{session_id}/chat",
            json={"message": "What do we see?"},
        )
    proposal_id = r.json()["proposals"][0]["id"]

    r = await client.post(f"/api/ai/proposals/{proposal_id}/reject", json={})
    assert r.status_code == 200

    r = await client.get(f"/api/sessions/{session_id}/messages")
    assert r.status_code == 200
    contents = [m["content"] for m in r.json()]
    assert not any(gated_text in c for c in contents)


@pytest.mark.asyncio
async def test_session_chat_pending_mismatch_drops_narration_but_keeps_proposal(client, world_id):
    """A PENDING/PROPOSAL count mismatch degrades gracefully: the orchestrator
    already drops unpairable pending text, so the proposal is persisted with
    ``pending_narration=None`` rather than crashing the request."""
    r = await client.post("/api/sessions/", json={"world_id": world_id, "name": "Mismatch"})
    session_id = r.json()["id"]

    # Mismatch handling lives in the orchestrator; here we assert the API
    # layer tolerates a proposal with no pending narration without erroring.
    payloads = [ProposalPayload(type=ProposalType.LOCATION, content={"name": "Glenbrook"})]
    mock_orch = _mock_orchestrator("You arrive at the crossroads.", proposals=payloads)
    with patch("dm_api.api.sessions.DMOrchestrator", return_value=mock_orch):
        r = await client.post(
            f"/api/sessions/{session_id}/chat",
            json={"message": "Onward."},
        )

    assert r.status_code == 200
    data = r.json()
    assert len(data["proposals"]) == 1
    assert data["proposals"][0]["pending_narration"] is None

    proposal_id = data["proposals"][0]["id"]
    r = await client.post(f"/api/ai/proposals/{proposal_id}/accept", json={})
    assert r.status_code == 200

    # No spurious narration message was appended to chat.
    r = await client.get(f"/api/sessions/{session_id}/messages")
    ai_messages = [m for m in r.json() if m["role"] == "ai"]
    assert len(ai_messages) == 1
    assert ai_messages[0]["content"] == "You arrive at the crossroads."


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


@pytest.mark.asyncio
async def test_session_chat_includes_world_entities(client, world_id):
    """World context passed to the orchestrator includes known NPCs and locations."""
    # Create an NPC (open endpoint — no DM token needed for characters).
    r = await client.post(
        "/api/characters/",
        json={
            "world_id": world_id,
            "type": "NPC",
            "name": "Old Hag Meredith",
            "race": "Human",
            "alignment": "neutral evil",
            "personality_traits": "Speaks in riddles and always asks a price.",
        },
    )
    assert r.status_code == 201

    # Create a location (DM-only; client fixture sends DM headers).
    r = await client.post(
        "/api/locations/",
        json={
            "world_id": world_id,
            "type": "building",
            "name": "The Rusty Anchor",
            "description": "A seedy dockside tavern frequented by smugglers.",
        },
    )
    assert r.status_code == 201

    r = await client.post("/api/sessions/", json={"world_id": world_id, "name": "Entity Test"})
    session_id = r.json()["id"]

    mock_orch = _mock_orchestrator("Welcome.")
    with patch("dm_api.api.sessions.DMOrchestrator", return_value=mock_orch):
        await client.post(f"/api/sessions/{session_id}/chat", json={"message": "Begin."})

    ctx = mock_orch.handle_message.call_args.kwargs["world_context"]
    npc_entries = [e for e in ctx.known_npcs if "Old Hag Meredith" in e]
    assert len(npc_entries) == 1, f"Expected NPC entry, got known_npcs={ctx.known_npcs}"
    assert "Human" in npc_entries[0]

    loc_entries = [e for e in ctx.known_locations if "The Rusty Anchor" in e]
    assert (
        len(loc_entries) == 1
    ), f"Expected location entry, got known_locations={ctx.known_locations}"
