"""Tests for the DM/player role split.

The DM authenticates with the shared token (X-DM-Token header); everyone
else is a player. Players must not be able to:
- call DM-only endpoints (chat, proposals, combat control, entity writes),
- read DM-only data (NPC stat blocks, location lore, world lore, proposals).

The ``client`` fixture sends the DM token on every request; ``player_client``
sends none.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Role endpoint
# ---------------------------------------------------------------------------


async def test_role_endpoint_with_dm_token(client):
    r = await client.get("/api/auth/role")
    assert r.status_code == 200
    assert r.json() == {"role": "dm"}


async def test_role_endpoint_without_token(player_client):
    r = await player_client.get("/api/auth/role")
    assert r.status_code == 200
    assert r.json() == {"role": "player"}


async def test_role_endpoint_with_wrong_token(player_client):
    r = await player_client.get("/api/auth/role", headers={"X-DM-Token": "wrong-token"})
    assert r.status_code == 200
    assert r.json() == {"role": "player"}


# ---------------------------------------------------------------------------
# DM-only endpoints reject players
# ---------------------------------------------------------------------------


async def test_player_cannot_create_world(player_client):
    r = await player_client.post("/api/worlds/", json={"name": "Sneaky World"})
    assert r.status_code == 403


async def test_player_cannot_create_session_or_chat(client, player_client, world_id):
    r = await player_client.post(
        "/api/sessions/", json={"world_id": world_id, "name": "Player Session"}
    )
    assert r.status_code == 403

    session = await client.post(
        "/api/sessions/", json={"world_id": world_id, "name": "DM Session"}
    )
    session_id = session.json()["id"]

    r = await player_client.post(
        f"/api/sessions/{session_id}/chat", json={"message": "I cast wish"}
    )
    assert r.status_code == 403

    r = await player_client.put(f"/api/sessions/{session_id}/end")
    assert r.status_code == 403


async def test_player_cannot_use_combat_controls(client, player_client, world_id):
    session = await client.post(
        "/api/sessions/", json={"world_id": world_id, "name": "Combat Session"}
    )
    session_id = session.json()["id"]

    assert (await player_client.post(f"/api/sessions/{session_id}/combat")).status_code == 403

    # Start combat as DM, then verify players can watch but not drive it.
    assert (await client.post(f"/api/sessions/{session_id}/combat")).status_code == 201
    assert (await player_client.get(f"/api/sessions/{session_id}/combat")).status_code == 200
    assert (
        await player_client.post(f"/api/sessions/{session_id}/combat/next-turn")
    ).status_code == 403
    assert (
        await player_client.post(
            f"/api/sessions/{session_id}/combat/heal",
            json={"target_id": "someone", "amount": 5},
        )
    ).status_code == 403
    assert (await player_client.put(f"/api/sessions/{session_id}/combat/end")).status_code == 403


async def test_player_cannot_touch_proposals(player_client):
    import uuid as _uuid

    fake_id = str(_uuid.uuid4())
    assert (await player_client.get(f"/api/ai/proposals/{fake_id}")).status_code == 403
    assert (await player_client.get(f"/api/ai/sessions/{fake_id}/proposals")).status_code == 403
    assert (
        await player_client.post(f"/api/ai/proposals/{fake_id}/accept", json={})
    ).status_code == 403
    assert (
        await player_client.post(f"/api/ai/proposals/{fake_id}/reject", json={})
    ).status_code == 403


async def test_player_cannot_modify_characters_or_locations(client, player_client, world_id):
    char = await client.post(
        "/api/characters/",
        json={"world_id": world_id, "type": "PC", "name": "Kira", "level": 3},
    )
    char_id = char.json()["id"]
    assert (
        await player_client.patch(f"/api/characters/{char_id}", json={"hp_current": 99})
    ).status_code == 403
    assert (
        await player_client.post(f"/api/characters/{char_id}/rest", json={"rest_type": "long"})
    ).status_code == 403

    loc = await client.post(
        "/api/locations/",
        json={"world_id": world_id, "type": "building", "name": "Tavern"},
    )
    loc_id = loc.json()["id"]
    assert (
        await player_client.patch(f"/api/locations/{loc_id}", json={"name": "Burned Tavern"})
    ).status_code == 403
    assert (await player_client.delete(f"/api/locations/{loc_id}")).status_code == 403
    assert (
        await player_client.post(
            "/api/locations/",
            json={"world_id": world_id, "type": "building", "name": "Player Fort"},
        )
    ).status_code == 403
    assert (await player_client.delete(f"/api/worlds/{world_id}")).status_code == 403


async def test_player_can_create_a_character(player_client, world_id):
    """Character creation stays open — it's the player-onboarding flow."""
    r = await player_client.post(
        "/api/characters/",
        json={"world_id": world_id, "type": "PC", "name": "New Hero", "level": 1},
    )
    assert r.status_code == 201


# ---------------------------------------------------------------------------
# Redaction of sensitive fields for players
# ---------------------------------------------------------------------------


async def test_npc_stat_block_redacted_for_players(client, player_client, world_id):
    npc = await client.post(
        "/api/characters/",
        json={
            "world_id": world_id,
            "type": "MONSTER",
            "name": "Ancient Dragon",
            "race": "Dragon",
            "char_class": "Brute",
            "level": 20,
            "alignment": "chaotic evil",
            "hp_current": 300,
            "hp_max": 300,
            "ac": 22,
            "speed": 80,
            "stats": {"strength": 27},
            "abilities": ["Fire Breath"],
            "spells": ["Wish"],
            "equipment": ["Hoard"],
            "personality_traits": "Greedy beyond measure",
            "ideals": "Power",
            "bonds": "Its hoard",
            "flaws": "Pride",
            "known_facts": ["Secretly the king's advisor"],
            "interaction_log_summary": "Ate the last party",
        },
    )
    npc_id = npc.json()["id"]

    # DM sees everything.
    dm_view = (await client.get(f"/api/characters/{npc_id}")).json()
    assert dm_view["hp_max"] == 300
    assert dm_view["known_facts"] == ["Secretly the king's advisor"]

    # Player sees only the public face.
    player_view = (await player_client.get(f"/api/characters/{npc_id}")).json()
    assert player_view["name"] == "Ancient Dragon"
    assert player_view["race"] == "Dragon"
    for hidden in (
        "char_class",
        "alignment",
        "stats",
        "hp_current",
        "hp_max",
        "ac",
        "speed",
        "abilities",
        "spells",
        "equipment",
        "personality_traits",
        "ideals",
        "bonds",
        "flaws",
        "known_facts",
        "interaction_log_summary",
    ):
        assert player_view[hidden] is None, f"{hidden} leaked to player"

    # The world roster applies the same redaction.
    roster = (await player_client.get(f"/api/characters/world/{world_id}")).json()
    monster = next(c for c in roster if c["id"] == npc_id)
    assert monster["hp_max"] is None


async def test_pc_sheet_visible_to_players_except_dm_notes(client, player_client, world_id):
    pc = await client.post(
        "/api/characters/",
        json={
            "world_id": world_id,
            "type": "PC",
            "name": "Kira Swiftblade",
            "char_class": "Fighter",
            "hp_current": 28,
            "hp_max": 28,
            "ac": 17,
            "stats": {"strength": 16},
            "known_facts": ["Has a secret patron"],
            "interaction_log_summary": "DM-only notes",
        },
    )
    pc_id = pc.json()["id"]

    player_view = (await player_client.get(f"/api/characters/{pc_id}")).json()
    assert player_view["char_class"] == "Fighter"
    assert player_view["hp_max"] == 28
    assert player_view["ac"] == 17
    assert player_view["stats"] == {"strength": 16}
    # DM bookkeeping stays hidden even on PCs.
    assert player_view["known_facts"] is None
    assert player_view["interaction_log_summary"] is None


async def test_location_lore_redacted_for_players(client, player_client, world_id):
    loc = await client.post(
        "/api/locations/",
        json={
            "world_id": world_id,
            "type": "building",
            "name": "Old Mill",
            "description": "A creaky mill by the river.",
            "lore": "Hides the cult's entrance",
            "history": "Site of the massacre",
            "map_data": {"grid": [1, 2, 3]},
            "interaction_log_summary": "Party suspicious",
        },
    )
    loc_id = loc.json()["id"]

    dm_view = (await client.get(f"/api/locations/{loc_id}")).json()
    assert dm_view["lore"] == "Hides the cult's entrance"

    player_view = (await player_client.get(f"/api/locations/{loc_id}")).json()
    assert player_view["name"] == "Old Mill"
    assert player_view["description"] == "A creaky mill by the river."
    assert player_view["map_data"] == {"grid": [1, 2, 3]}
    assert player_view["lore"] is None
    assert player_view["history"] is None
    assert player_view["interaction_log_summary"] is None

    # World-level location listing applies the same redaction.
    listing = (await player_client.get(f"/api/worlds/{world_id}/locations")).json()
    assert listing[0]["lore"] is None


async def test_world_lore_redacted_for_players(client, player_client):
    world = await client.post(
        "/api/worlds/",
        json={
            "name": "Faerun",
            "setting_description": "High fantasy",
            "themes": ["intrigue"],
            "lore_summary": "The lich king is already awake",
        },
    )
    world_id = world.json()["id"]

    dm_view = (await client.get(f"/api/worlds/{world_id}")).json()
    assert dm_view["lore_summary"] == "The lich king is already awake"

    player_view = (await player_client.get(f"/api/worlds/{world_id}")).json()
    assert player_view["name"] == "Faerun"
    assert player_view["setting_description"] == "High fantasy"
    assert player_view["lore_summary"] is None


async def test_player_can_read_session_and_messages(client, player_client, world_id):
    """The shared narration (chat history) stays readable for players."""
    session = await client.post(
        "/api/sessions/", json={"world_id": world_id, "name": "Open Session"}
    )
    session_id = session.json()["id"]
    assert (await player_client.get(f"/api/sessions/{session_id}")).status_code == 200
    r = await player_client.get(f"/api/sessions/{session_id}/messages")
    assert r.status_code == 200
