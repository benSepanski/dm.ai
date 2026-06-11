"""Tests for per-game configuration (GET/PUT /worlds/{world_id}/config)."""

from __future__ import annotations

import uuid
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from dm_api.ai.dm_orchestrator import DMResponse
from dm_api.config import settings


@pytest.mark.asyncio
async def test_get_config_defaults_when_unset(client, world_id):
    """A game with no stored config reports null overrides + deployment defaults."""
    r = await client.get(f"/api/worlds/{world_id}/config")
    assert r.status_code == 200
    data = r.json()
    assert data["world_id"] == world_id
    assert all(v is None for v in data["overrides"].values())
    effective = data["effective"]
    assert effective["ai_provider"] == settings.ai_provider
    assert effective["orchestrator_model"] == settings.orchestrator_model
    assert effective["generation_model"] == settings.generation_model
    assert effective["context_token_limit"] == settings.context_token_limit
    assert effective["context_preserve_last_n"] == settings.context_preserve_last_n
    assert effective["database_url"] == settings.database_url
    assert effective["redis_url"] == settings.redis_url


@pytest.mark.asyncio
async def test_put_config_sets_overrides(client, world_id):
    payload = {
        "ai_provider": "anthropic",
        "orchestrator_model": "claude-opus-4-8",
        "generation_model": "claude-haiku-4-5-20251001",
        "context_token_limit": 50_000,
        "context_preserve_last_n": 3,
        "database_url": "postgresql+asyncpg://dm:pw@game-db:5432/curse_of_strahd",
        "redis_url": "redis://game-redis:6379",
    }
    r = await client.put(f"/api/worlds/{world_id}/config", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["overrides"] == payload
    # Effective values mirror the overrides once set.
    for key, value in payload.items():
        assert data["effective"][key] == value

    # Persisted: a fresh GET returns the same overrides.
    r = await client.get(f"/api/worlds/{world_id}/config")
    assert r.status_code == 200
    assert r.json()["overrides"] == payload


@pytest.mark.asyncio
async def test_put_config_partial_falls_back_to_defaults(client, world_id):
    """Unset fields stay on deployment defaults while set fields override."""
    r = await client.put(
        f"/api/worlds/{world_id}/config",
        json={"orchestrator_model": "claude-opus-4-8"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["overrides"]["orchestrator_model"] == "claude-opus-4-8"
    assert data["overrides"]["generation_model"] is None
    assert data["effective"]["orchestrator_model"] == "claude-opus-4-8"
    assert data["effective"]["generation_model"] == settings.generation_model
    assert data["effective"]["database_url"] == settings.database_url


@pytest.mark.asyncio
async def test_put_config_clears_overrides(client, world_id):
    """PUT is full-replace: omitted fields revert to deployment defaults."""
    r = await client.put(
        f"/api/worlds/{world_id}/config",
        json={"orchestrator_model": "claude-opus-4-8", "context_token_limit": 50_000},
    )
    assert r.status_code == 200

    r = await client.put(f"/api/worlds/{world_id}/config", json={})
    assert r.status_code == 200
    data = r.json()
    assert all(v is None for v in data["overrides"].values())
    assert data["effective"]["orchestrator_model"] == settings.orchestrator_model
    assert data["effective"]["context_token_limit"] == settings.context_token_limit


@pytest.mark.asyncio
async def test_put_config_rejects_unknown_provider(client, world_id):
    r = await client.put(
        f"/api/worlds/{world_id}/config",
        json={"ai_provider": "openai"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_put_config_rejects_non_positive_token_limit(client, world_id):
    r = await client.put(
        f"/api/worlds/{world_id}/config",
        json={"context_token_limit": 0},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_config_unknown_world_404(client):
    fake_id = str(uuid.uuid4())
    r = await client.get(f"/api/worlds/{fake_id}/config")
    assert r.status_code == 404
    r = await client.put(f"/api/worlds/{fake_id}/config", json={})
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# The AI path honors the per-game config
# ---------------------------------------------------------------------------


def _mock_orchestrator(response_text: str) -> MagicMock:
    mock = MagicMock()
    mock.handle_message = AsyncMock(
        return_value=DMResponse(
            response=response_text,
            proposals=[],
            was_condensed=False,
            tokens_in=100,
            tokens_out=50,
        )
    )
    mock.summarize = AsyncMock(return_value="A short summary.")
    return mock


@pytest.mark.asyncio
async def test_chat_uses_per_game_models(client, world_id):
    """Session chat constructs the orchestrator from the game's config overrides."""
    r = await client.put(
        f"/api/worlds/{world_id}/config",
        json={
            "orchestrator_model": "claude-opus-4-8",
            "generation_model": "claude-haiku-4-5-20251001",
            "context_token_limit": 50_000,
            "context_preserve_last_n": 3,
        },
    )
    assert r.status_code == 200

    r = await client.post("/api/sessions/", json={"world_id": world_id, "name": "Config Chat"})
    session_id = r.json()["id"]

    mock_orch = _mock_orchestrator("The dragon stirs.")
    with patch("dm_api.api.sessions.DMOrchestrator", return_value=mock_orch) as orch_cls:
        r = await client.post(
            f"/api/sessions/{session_id}/chat",
            json={"message": "Wake the dragon."},
        )

    assert r.status_code == 200
    orch_cls.assert_called_once_with(
        backend=ANY,
        orchestrator_model="claude-opus-4-8",
        generation_model="claude-haiku-4-5-20251001",
        context_token_limit=50_000,
        context_preserve_last_n=3,
    )


@pytest.mark.asyncio
async def test_chat_uses_defaults_without_config(client, world_id):
    """Without overrides the orchestrator is built from deployment defaults."""
    r = await client.post("/api/sessions/", json={"world_id": world_id, "name": "Default Chat"})
    session_id = r.json()["id"]

    mock_orch = _mock_orchestrator("All quiet.")
    with patch("dm_api.api.sessions.DMOrchestrator", return_value=mock_orch) as orch_cls:
        r = await client.post(
            f"/api/sessions/{session_id}/chat",
            json={"message": "Listen at the door."},
        )

    assert r.status_code == 200
    orch_cls.assert_called_once_with(
        backend=ANY,
        orchestrator_model=settings.orchestrator_model,
        generation_model=settings.generation_model,
        context_token_limit=settings.context_token_limit,
        context_preserve_last_n=settings.context_preserve_last_n,
    )


@pytest.mark.asyncio
async def test_end_session_summary_uses_per_game_models(client, world_id):
    """End-of-session summarization also honors the game's model overrides."""
    r = await client.put(
        f"/api/worlds/{world_id}/config",
        json={"generation_model": "claude-haiku-4-5-20251001"},
    )
    assert r.status_code == 200

    r = await client.post("/api/sessions/", json={"world_id": world_id, "name": "Config End"})
    session_id = r.json()["id"]

    mock_orch = _mock_orchestrator("The party rests.")
    with patch("dm_api.api.sessions.DMOrchestrator", return_value=mock_orch) as orch_cls:
        await client.post(f"/api/sessions/{session_id}/chat", json={"message": "Rest."})
        r = await client.put(f"/api/sessions/{session_id}/end")

    assert r.status_code == 200
    assert r.json()["session_summary"] == "A short summary."
    for call in orch_cls.call_args_list:
        assert call.kwargs["generation_model"] == "claude-haiku-4-5-20251001"
