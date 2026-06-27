"""Tests for the health endpoint."""

import pytest


@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_health_has_service(client):
    r = await client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert "service" in data
    assert data["service"] == "dm-api"


@pytest.mark.asyncio
async def test_health_reports_ai_readiness(client):
    """/health surfaces the AI provider + readiness so misconfig is catchable."""
    r = await client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert "ai_provider" in data
    assert "ai_ready" in data
    assert isinstance(data["ai_ready"], bool)
    assert "ai_detail" in data
