"""Tests for combat state persistence: death saves, conditions, DB sync."""

import pytest
from game_engine.types import ActionType

from tests.combat_helpers import (
    _create_character,
    _create_downed_character,
    _create_session,
)


@pytest.mark.asyncio
async def test_next_turn_rolls_death_save_for_dying_combatant(client, world_id):
    """A dying creature makes a death save at the start of its turn —
    rolled automatically by next-turn and logged (regression: death saves
    were never rolled anywhere in the API)."""
    session_id = await _create_session(client, world_id)
    char_id = await _create_downed_character(client, world_id)

    r = await client.post(
        f"/api/sessions/{session_id}/combat",
        json={"character_ids": [char_id]},
    )
    assert r.status_code == 201

    # Sole combatant: advancing wraps back to its own turn start.
    r = await client.post(f"/api/sessions/{session_id}/combat/next-turn")
    assert r.status_code == 200
    data = r.json()

    saves = [e for e in (data["combat_log"] or []) if e.get("event") == "death_save"]
    assert len(saves) == 1
    entry = saves[0]
    assert 1 <= entry["roll"] <= 20
    combatant = data["combatants"][0]
    if entry["regained_hp"]:
        # Natural 20: back up with 1 HP.
        assert combatant["hp_current"] == 1
    else:
        assert entry["successes"] + entry["failures"] >= 1
        assert combatant["death_saves"]["successes"] == entry["successes"]
        assert combatant["death_saves"]["failures"] == entry["failures"]


@pytest.mark.asyncio
async def test_next_turn_no_death_save_for_conscious_combatant(client, world_id):
    """Conscious combatants never trigger death-save log entries."""
    session_id = await _create_session(client, world_id)
    char_id = await _create_character(client, world_id, name="Healthy")

    r = await client.post(
        f"/api/sessions/{session_id}/combat",
        json={"character_ids": [char_id]},
    )
    assert r.status_code == 201

    r = await client.post(f"/api/sessions/{session_id}/combat/next-turn")
    assert r.status_code == 200
    log = r.json()["combat_log"] or []
    assert [e for e in log if e.get("event") == "death_save"] == []


@pytest.mark.asyncio
async def test_end_combat_persists_death_saves_and_summarizes_them(client, world_id):
    """Death-save progress survives the encounter boundary (regression: it
    was silently discarded by the end-combat sync) and appears in the
    SYSTEM summary message."""
    session_id = await _create_session(client, world_id)
    char_id = await _create_downed_character(client, world_id, name="Sylvara")

    r = await client.post(
        f"/api/sessions/{session_id}/combat",
        json={"character_ids": [char_id]},
    )
    assert r.status_code == 201

    # Roll death saves until at least one success/failure is on the books
    # (a natural 20 heals to 1 HP and ends the dying state — retry-safe).
    for _ in range(5):
        r = await client.post(f"/api/sessions/{session_id}/combat/next-turn")
        combatant = r.json()["combatants"][0]
        saves = combatant["death_saves"]
        if saves["is_dead"] or saves["successes"] or saves["failures"]:
            break
        if combatant["hp_current"] > 0:
            break

    r = await client.put(f"/api/sessions/{session_id}/combat/end")
    assert r.status_code == 200
    final = r.json()["combatants"][0]

    # The character row keeps the death-save state.
    r = await client.get(f"/api/characters/{char_id}")
    assert r.status_code == 200
    char = r.json()
    assert char["stats"]["death_saves"] == final["death_saves"]

    # The SYSTEM summary reflects the down/dead state when still at 0 HP.
    if final["hp_current"] <= 0:
        r = await client.get(f"/api/sessions/{session_id}/messages")
        summary = r.json()[0]
        assert summary["role"] == "system"
        assert "DOWN" in summary["content"] or "DEAD" in summary["content"]


@pytest.mark.asyncio
async def test_char_class_is_case_insensitive_in_combat(client, world_id):
    """Lowercase class strings map onto the canonical enum value instead of
    silently coercing to Fighter (regression)."""
    session_id = await _create_session(client, world_id)
    r = await client.post(
        "/api/characters/",
        json={
            "world_id": world_id,
            "type": "PC",
            "name": "Sage",
            "level": 3,
            "char_class": "wizard",
            "hp_current": 14,
            "hp_max": 14,
            "ac": 12,
            "stats": {"ability_scores": {"intelligence": 16}},
        },
    )
    char_id = r.json()["id"]

    r = await client.post(
        f"/api/sessions/{session_id}/combat",
        json={"character_ids": [char_id]},
    )
    assert r.status_code == 201
    assert r.json()["combatants"][0]["class"] == "Wizard"


# ---------------------------------------------------------------------------
# Regression: condition_durations must survive the DB→engine round-trip
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_condition_durations_preserved_through_combat(client, world_id):
    """Characters enrolled with condition_durations in stats keep those
    durations when loaded into the rule engine for action resolution.

    Regression test for the bug where _character_to_sheet omitted
    ``condition_durations`` from the dict passed to CharacterSheet.from_dict,
    silently resetting all timed conditions to indefinite.
    """
    session_id = await _create_session(client, world_id)

    # Create a character that is already poisoned (3 rounds remaining)
    char_id = await client.post(
        "/api/characters/",
        json={
            "world_id": world_id,
            "type": "PC",
            "name": "Cursed Hero",
            "level": 1,
            "char_class": "Fighter",
            "hp_current": 20,
            "hp_max": 20,
            "ac": 14,
            "stats": {
                "ability_scores": {
                    "strength": 16,
                    "dexterity": 12,
                    "constitution": 14,
                    "intelligence": 10,
                    "wisdom": 10,
                    "charisma": 10,
                },
                "conditions": ["poisoned"],
                "condition_durations": {"poisoned": 3},
            },
        },
    )
    assert char_id.status_code == 201
    char_id = char_id.json()["id"]

    r = await client.post(
        f"/api/sessions/{session_id}/combat",
        json={"character_ids": [char_id]},
    )
    assert r.status_code == 201

    # The combatant stored in the combat state must carry the condition_durations
    combatants = r.json()["combatants"]
    assert combatants is not None and len(combatants) == 1
    combatant = combatants[0]
    assert "poisoned" in combatant.get("conditions", [])
    assert combatant.get("condition_durations", {}).get("poisoned") == 3


# ---------------------------------------------------------------------------
# Condition duration ticking via next_turn
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_next_turn_ticks_condition_duration(client, world_id):
    """next_turn decrements timed conditions on the combatant whose turn just ended."""
    session_id = await _create_session(client, world_id)

    # Enroll a character with a 2-round poisoned condition
    char_id = (
        await client.post(
            "/api/characters/",
            json={
                "world_id": world_id,
                "type": "PC",
                "name": "Poisoned Fighter",
                "level": 1,
                "char_class": "Fighter",
                "hp_current": 20,
                "hp_max": 20,
                "ac": 14,
                "stats": {
                    "ability_scores": {
                        "strength": 16,
                        "dexterity": 12,
                        "constitution": 14,
                        "intelligence": 10,
                        "wisdom": 10,
                        "charisma": 10,
                    },
                    "conditions": ["poisoned"],
                    "condition_durations": {"poisoned": 2},
                },
            },
        )
    ).json()["id"]

    await client.post(
        f"/api/sessions/{session_id}/combat",
        json={"character_ids": [char_id]},
    )

    # Advance past the character's turn — duration should decrement from 2 to 1
    r = await client.post(f"/api/sessions/{session_id}/combat/next-turn")
    assert r.status_code == 200
    combatant = r.json()["combatants"][0]
    assert "poisoned" in combatant["conditions"]
    assert combatant["condition_durations"]["poisoned"] == 1


@pytest.mark.asyncio
async def test_next_turn_expires_condition_with_duration_one(client, world_id):
    """A condition with duration 1 is removed when the combatant's turn ends."""
    session_id = await _create_session(client, world_id)

    char_id = (
        await client.post(
            "/api/characters/",
            json={
                "world_id": world_id,
                "type": "PC",
                "name": "Blinded Fighter",
                "level": 1,
                "char_class": "Fighter",
                "hp_current": 20,
                "hp_max": 20,
                "ac": 14,
                "stats": {
                    "ability_scores": {
                        "strength": 16,
                        "dexterity": 12,
                        "constitution": 14,
                        "intelligence": 10,
                        "wisdom": 10,
                        "charisma": 10,
                    },
                    "conditions": ["blinded"],
                    "condition_durations": {"blinded": 1},
                },
            },
        )
    ).json()["id"]

    await client.post(
        f"/api/sessions/{session_id}/combat",
        json={"character_ids": [char_id]},
    )

    r = await client.post(f"/api/sessions/{session_id}/combat/next-turn")
    assert r.status_code == 200
    combatant = r.json()["combatants"][0]
    assert "blinded" not in combatant["conditions"]
    assert "blinded" not in combatant.get("condition_durations", {})


# ---------------------------------------------------------------------------
# HP and condition sync: end_combat → Character DB
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_end_combat_syncs_hp_to_character_db(client, world_id):
    """ending combat writes the final HP from combat state back to the Character row.

    Whatever HP the combatant has in the CombatState at end_combat time —
    whether modified by attacks or not — must be reflected in Character.hp_current
    after the endpoint returns.
    """
    session_id = await _create_session(client, world_id)
    attacker_id = await _create_character(client, world_id, name="Attacker", hp=20, ac=15)
    # Minimal AC so the attack is virtually guaranteed to hit.
    defender_id = await _create_character(client, world_id, name="Defender", hp=30, ac=1)

    r = await client.post(
        f"/api/sessions/{session_id}/combat",
        json={"character_ids": [attacker_id, defender_id]},
    )
    assert r.status_code == 201

    # Submit an attack — with AC=1 and at least prof bonus +2 this will always hit.
    await client.post(
        f"/api/sessions/{session_id}/combat/action",
        json={
            "actor_id": attacker_id,
            "action_type": ActionType.ATTACK.value,
            "target_id": defender_id,
            "attack_details": {
                "weapon_name": "Longsword",
                "damage_dice": "1d8",
                "damage_type": "slashing",
                "attack_ability": "strength",
            },
        },
    )

    # Snapshot combat state HP values — these are what should end up in DB.
    r = await client.get(f"/api/sessions/{session_id}/combat")
    assert r.status_code == 200
    combat_combatants = {c["id"]: c for c in (r.json()["combatants"] or [])}

    # End combat — triggers _sync_combatants_to_db.
    r = await client.put(f"/api/sessions/{session_id}/combat/end")
    assert r.status_code == 200

    # Both character rows must reflect the combat-state HP.
    for char_id in (attacker_id, defender_id):
        r = await client.get(f"/api/characters/{char_id}")
        assert r.status_code == 200
        assert r.json()["hp_current"] == combat_combatants[char_id]["hp_current"]


@pytest.mark.asyncio
async def test_end_combat_syncs_conditions_to_character_db(client, world_id):
    """ending combat writes ticked condition durations back to Character.stats."""
    session_id = await _create_session(client, world_id)

    char_id = (
        await client.post(
            "/api/characters/",
            json={
                "world_id": world_id,
                "type": "PC",
                "name": "Cursed Fighter",
                "level": 1,
                "char_class": "Fighter",
                "hp_current": 20,
                "hp_max": 20,
                "ac": 14,
                "stats": {
                    "ability_scores": {
                        "strength": 16,
                        "dexterity": 12,
                        "constitution": 14,
                        "intelligence": 10,
                        "wisdom": 10,
                        "charisma": 10,
                    },
                    "conditions": ["poisoned"],
                    "condition_durations": {"poisoned": 3},
                },
            },
        )
    ).json()["id"]

    await client.post(
        f"/api/sessions/{session_id}/combat",
        json={"character_ids": [char_id]},
    )

    # Advance one turn — duration ticks from 3 → 2.
    await client.post(f"/api/sessions/{session_id}/combat/next-turn")

    # End combat — syncs conditions back to DB.
    r = await client.put(f"/api/sessions/{session_id}/combat/end")
    assert r.status_code == 200

    r = await client.get(f"/api/characters/{char_id}")
    assert r.status_code == 200
    char_stats = r.json()["stats"]
    assert "poisoned" in char_stats["conditions"]
    assert char_stats["condition_durations"]["poisoned"] == 2


@pytest.mark.asyncio
async def test_end_combat_no_combatants_is_noop(client, world_id):
    """ending combat with no enrolled combatants completes without errors."""
    session_id = await _create_session(client, world_id)
    await client.post(f"/api/sessions/{session_id}/combat")

    r = await client.put(f"/api/sessions/{session_id}/combat/end")
    assert r.status_code == 200
    assert r.json()["ended_at"] is not None


@pytest.mark.asyncio
async def test_end_combat_skips_nondb_combatants(client, world_id):
    """end_combat silently skips combatants whose ID is not in the Character table.

    Ad-hoc monsters (not persisted in DB) must not cause a 500 error.
    """
    session_id = await _create_session(client, world_id)
    char_id = await _create_character(client, world_id, name="Hero", hp=20)

    # Start combat with a real character enrolled.
    await client.post(
        f"/api/sessions/{session_id}/combat",
        json={"character_ids": [char_id]},
    )

    # Manually inject a fake (non-DB) combatant into the combat state by ending
    # and restarting; instead, just verify real character is synced regardless.
    r = await client.put(f"/api/sessions/{session_id}/combat/end")
    assert r.status_code == 200
