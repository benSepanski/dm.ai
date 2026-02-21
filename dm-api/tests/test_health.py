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
