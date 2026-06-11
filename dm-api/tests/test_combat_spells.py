"""Tests for the combat spellcasting, heal, and stabilize endpoints."""

import pytest
from game_engine.types import ActionType

from tests.combat_helpers import (
    _create_caster,
    _create_character,
    _create_downed_character,
    _create_session,
)


def _combatant(data, char_id):
    return next(c for c in data["combatants"] if c["id"] == char_id)


def _slot_remaining(combatant, slot_level):
    slot = next(s for s in combatant["spell_slots"] if s["slot_level"] == slot_level)
    return slot["remaining"]


async def _start_combat(client, world_id, *char_ids):
    session_id = await _create_session(client, world_id)
    r = await client.post(
        f"/api/sessions/{session_id}/combat",
        json={"character_ids": list(char_ids)},
    )
    assert r.status_code == 201
    return session_id, r.json()


# ---------------------------------------------------------------------------
# cast-spell
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cast_cantrip_logs_and_consumes_no_slot(client, world_id):
    """Fire Bolt resolves a spell attack roll and never touches spell slots."""
    wizard_id = await _create_caster(client, world_id, name="Kira")
    target_id = await _create_character(client, world_id, name="Bandit", ac=10)
    session_id, _ = await _start_combat(client, world_id, wizard_id, target_id)

    r = await client.post(
        f"/api/sessions/{session_id}/combat/cast-spell",
        json={"actor_id": wizard_id, "spell_name": "Fire Bolt", "target_ids": [target_id]},
    )
    assert r.status_code == 200
    data = r.json()
    log = data["combat_log"][-1]
    assert log["event"] == "cast_spell"
    assert log["action_type"] == ActionType.MAGIC.value
    assert log["spell"] == "Fire Bolt"
    assert log["slot_level_used"] is None
    outcome = log["outcomes"][0]
    assert outcome["target_id"] == target_id
    assert outcome["attack_total"] is not None
    # A level-3 wizard's slots (4×L1, 2×L2) are untouched by a cantrip.
    assert _slot_remaining(_combatant(data, wizard_id), 1) == 4


@pytest.mark.asyncio
async def test_cast_cure_wounds_heals_downed_ally_and_consumes_slot(client, world_id):
    cleric_id = await _create_caster(client, world_id, name="Maren", char_class="Cleric")
    downed_id = await _create_downed_character(client, world_id, name="Sylvara")
    session_id, _ = await _start_combat(client, world_id, cleric_id, downed_id)

    r = await client.post(
        f"/api/sessions/{session_id}/combat/cast-spell",
        json={"actor_id": cleric_id, "spell_name": "Cure Wounds", "target_ids": [downed_id]},
    )
    assert r.status_code == 200
    data = r.json()
    healed = _combatant(data, downed_id)
    assert healed["hp_current"] >= 1
    assert "unconscious" not in healed["conditions"]
    assert healed["death_saves"]["successes"] == 0
    assert _slot_remaining(_combatant(data, cleric_id), 1) == 3
    assert data["combat_log"][-1]["slot_level_used"] == 1
    assert data["combat_log"][-1]["outcomes"][0]["healing"] >= 1


@pytest.mark.asyncio
async def test_cast_save_spell_records_save_and_damage(client, world_id):
    """A save-DC spell (Sacred Flame) rolls the target's save against the DC."""
    cleric_id = await _create_caster(
        client, world_id, name="Maren", char_class="Cleric", spells=["Sacred Flame"]
    )
    target_id = await _create_character(client, world_id, name="Bandit", hp=50)
    session_id, _ = await _start_combat(client, world_id, cleric_id, target_id)

    r = await client.post(
        f"/api/sessions/{session_id}/combat/cast-spell",
        json={"actor_id": cleric_id, "spell_name": "Sacred Flame", "target_ids": [target_id]},
    )
    assert r.status_code == 200
    outcome = r.json()["combat_log"][-1]["outcomes"][0]
    assert outcome["save_total"] is not None
    assert outcome["save_success"] in (True, False)
    if outcome["save_success"]:
        assert outcome["damage"] == 0  # Sacred Flame deals nothing on a save
    else:
        assert outcome["damage"] >= 1


@pytest.mark.asyncio
async def test_cast_unknown_spell_404(client, world_id):
    wizard_id = await _create_caster(client, world_id)
    session_id, _ = await _start_combat(client, world_id, wizard_id)

    r = await client.post(
        f"/api/sessions/{session_id}/combat/cast-spell",
        json={"actor_id": wizard_id, "spell_name": "Power Word Lunch"},
    )
    assert r.status_code == 404
    assert "Unknown spell" in r.json()["detail"]


@pytest.mark.asyncio
async def test_cast_without_slot_is_409_and_keeps_log_clean(client, world_id):
    """A level-3 wizard has no 3rd-level slots — Fireball is rejected loudly."""
    wizard_id = await _create_caster(client, world_id)
    target_id = await _create_character(client, world_id, name="Bandit")
    session_id, _ = await _start_combat(client, world_id, wizard_id, target_id)

    r = await client.post(
        f"/api/sessions/{session_id}/combat/cast-spell",
        json={"actor_id": wizard_id, "spell_name": "Fireball", "target_ids": [target_id]},
    )
    assert r.status_code == 409
    assert "spell slots" in r.json()["detail"]

    r = await client.get(f"/api/sessions/{session_id}/combat")
    assert r.json()["combat_log"] in (None, [])


@pytest.mark.asyncio
async def test_cast_spell_consumes_the_action(client, world_id):
    """Casting an action spell spends the action — a follow-up attack is 409."""
    wizard_id = await _create_caster(client, world_id)
    target_id = await _create_character(client, world_id, name="Bandit")
    session_id, _ = await _start_combat(client, world_id, wizard_id, target_id)

    r = await client.post(
        f"/api/sessions/{session_id}/combat/cast-spell",
        json={"actor_id": wizard_id, "spell_name": "Fire Bolt", "target_ids": [target_id]},
    )
    assert r.status_code == 200

    r = await client.post(
        f"/api/sessions/{session_id}/combat/action",
        json={
            "actor_id": wizard_id,
            "action_type": ActionType.ATTACK.value,
            "target_id": target_id,
        },
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_bonus_action_spell_uses_bonus_action(client, world_id):
    """Healing Word is a bonus action: it stacks with an action, not with itself."""
    cleric_id = await _create_caster(client, world_id, name="Maren", char_class="Cleric")
    ally_id = await _create_character(client, world_id, name="Dorn", hp=20)
    session_id, _ = await _start_combat(client, world_id, cleric_id, ally_id)

    r = await client.post(
        f"/api/sessions/{session_id}/combat/cast-spell",
        json={"actor_id": cleric_id, "spell_name": "Healing Word", "target_ids": [ally_id]},
    )
    assert r.status_code == 200

    # Bonus action is spent — a second bonus-action spell is rejected …
    r = await client.post(
        f"/api/sessions/{session_id}/combat/cast-spell",
        json={"actor_id": cleric_id, "spell_name": "Healing Word", "target_ids": [ally_id]},
    )
    assert r.status_code == 409

    # … but the action itself is still available.
    r = await client.post(
        f"/api/sessions/{session_id}/combat/cast-spell",
        json={"actor_id": cleric_id, "spell_name": "Sacred Flame", "target_ids": [ally_id]},
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_cast_by_non_caster_class_requires_explicit_ability(client, world_id):
    fighter_id = await _create_character(client, world_id, name="Dorn")
    target_id = await _create_character(client, world_id, name="Bandit")
    session_id, _ = await _start_combat(client, world_id, fighter_id, target_id)

    r = await client.post(
        f"/api/sessions/{session_id}/combat/cast-spell",
        json={"actor_id": fighter_id, "spell_name": "Fire Bolt", "target_ids": [target_id]},
    )
    assert r.status_code == 422

    r = await client.post(
        f"/api/sessions/{session_id}/combat/cast-spell",
        json={
            "actor_id": fighter_id,
            "spell_name": "Fire Bolt",
            "target_ids": [target_id],
            "spellcasting_ability": "intelligence",
        },
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_cast_spell_unknown_actor_or_target_404(client, world_id):
    wizard_id = await _create_caster(client, world_id)
    session_id, _ = await _start_combat(client, world_id, wizard_id)

    r = await client.post(
        f"/api/sessions/{session_id}/combat/cast-spell",
        json={"actor_id": "not-a-combatant", "spell_name": "Fire Bolt"},
    )
    assert r.status_code == 404

    r = await client.post(
        f"/api/sessions/{session_id}/combat/cast-spell",
        json={"actor_id": wizard_id, "spell_name": "Fire Bolt", "target_ids": ["nobody"]},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_spell_slots_sync_to_character_on_end_combat(client, world_id):
    """Slots spent mid-fight persist to the character's stats blob."""
    cleric_id = await _create_caster(client, world_id, name="Maren", char_class="Cleric")
    ally_id = await _create_character(client, world_id, name="Dorn")
    session_id, _ = await _start_combat(client, world_id, cleric_id, ally_id)

    r = await client.post(
        f"/api/sessions/{session_id}/combat/cast-spell",
        json={"actor_id": cleric_id, "spell_name": "Cure Wounds", "target_ids": [ally_id]},
    )
    assert r.status_code == 200

    r = await client.put(f"/api/sessions/{session_id}/combat/end")
    assert r.status_code == 200

    r = await client.get(f"/api/characters/{cleric_id}")
    slots = r.json()["stats"]["spell_slots"]
    level_1 = next(s for s in slots if s["slot_level"] == 1)
    assert level_1["remaining"] == 3


# ---------------------------------------------------------------------------
# heal / stabilize
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_heal_brings_downed_combatant_back_up(client, world_id):
    downed_id = await _create_downed_character(client, world_id)
    ally_id = await _create_character(client, world_id, name="Dorn")
    session_id, _ = await _start_combat(client, world_id, downed_id, ally_id)

    r = await client.post(
        f"/api/sessions/{session_id}/combat/heal",
        json={"target_id": downed_id, "amount": 5},
    )
    assert r.status_code == 200
    data = r.json()
    healed = _combatant(data, downed_id)
    assert healed["hp_current"] == 5
    assert "unconscious" not in healed["conditions"]
    log = data["combat_log"][-1]
    assert log["event"] == "heal"
    assert log["amount"] == 5
    assert log["hp_after"] == 5


@pytest.mark.asyncio
async def test_heal_caps_at_hp_max(client, world_id):
    char_id = await _create_character(client, world_id, name="Dorn", hp=20)
    session_id, _ = await _start_combat(client, world_id, char_id)

    r = await client.post(
        f"/api/sessions/{session_id}/combat/heal",
        json={"target_id": char_id, "amount": 999},
    )
    assert r.status_code == 200
    assert _combatant(r.json(), char_id)["hp_current"] == 20


@pytest.mark.asyncio
async def test_heal_rejects_zero_amount(client, world_id):
    char_id = await _create_character(client, world_id)
    session_id, _ = await _start_combat(client, world_id, char_id)

    r = await client.post(
        f"/api/sessions/{session_id}/combat/heal",
        json={"target_id": char_id, "amount": 0},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_heal_non_combatant_404(client, world_id):
    char_id = await _create_character(client, world_id)
    session_id, _ = await _start_combat(client, world_id, char_id)

    r = await client.post(
        f"/api/sessions/{session_id}/combat/heal",
        json={"target_id": "nobody", "amount": 5},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_stabilize_dying_combatant(client, world_id):
    downed_id = await _create_downed_character(client, world_id)
    ally_id = await _create_character(client, world_id, name="Dorn")
    session_id, _ = await _start_combat(client, world_id, downed_id, ally_id)

    r = await client.post(
        f"/api/sessions/{session_id}/combat/stabilize",
        json={"target_id": downed_id},
    )
    assert r.status_code == 200
    data = r.json()
    stable = _combatant(data, downed_id)
    assert stable["death_saves"]["is_stable"] is True
    assert stable["hp_current"] == 0
    assert data["combat_log"][-1]["event"] == "stabilize"

    # Already stable → loud 409.
    r = await client.post(
        f"/api/sessions/{session_id}/combat/stabilize",
        json={"target_id": downed_id},
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_stabilize_healthy_combatant_409(client, world_id):
    char_id = await _create_character(client, world_id)
    session_id, _ = await _start_combat(client, world_id, char_id)

    r = await client.post(
        f"/api/sessions/{session_id}/combat/stabilize",
        json={"target_id": char_id},
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_stable_combatant_skips_death_saves_on_next_turn(client, world_id):
    """After stabilizing, next-turn no longer rolls death saves for the target."""
    downed_id = await _create_downed_character(client, world_id)
    ally_id = await _create_character(client, world_id, name="Dorn")
    session_id, _ = await _start_combat(client, world_id, downed_id, ally_id)

    r = await client.post(
        f"/api/sessions/{session_id}/combat/stabilize",
        json={"target_id": downed_id},
    )
    assert r.status_code == 200
    log_len = len(r.json()["combat_log"])

    # Advance through a full round: no death_save events appear.
    for _ in range(2):
        r = await client.post(f"/api/sessions/{session_id}/combat/next-turn")
        assert r.status_code == 200
    events = [e.get("event") for e in (r.json()["combat_log"] or [])[log_len:]]
    assert "death_save" not in events
