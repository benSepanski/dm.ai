"""Tests for the health and readiness endpoints."""

from __future__ import annotations

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
async def test_health_ready_returns_ok_when_db_reachable(client):
    """Readiness probe returns 200 with db=connected when the DB is up."""
    r = await client.get("/health/ready")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["db"] == "connected"
