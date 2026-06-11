"""Shared fixtures-as-helpers for the combat API test modules."""


async def _create_session(client, world_id):
    r = await client.post(
        "/api/sessions/",
        json={"world_id": world_id, "name": "Combat Session"},
    )
    assert r.status_code == 201
    return r.json()["id"]


async def _create_character(client, world_id, *, name: str = "Hero", hp: int = 20, ac: int = 14):
    r = await client.post(
        "/api/characters/",
        json={
            "world_id": world_id,
            "type": "PC",
            "name": name,
            "level": 3,
            "char_class": "Fighter",
            "hp_current": hp,
            "hp_max": hp,
            "ac": ac,
            "stats": {
                "ability_scores": {
                    "strength": 16,
                    "dexterity": 14,
                    "constitution": 14,
                    "intelligence": 10,
                    "wisdom": 12,
                    "charisma": 8,
                }
            },
        },
    )
    assert r.status_code == 201
    return r.json()["id"]


async def _create_statless_npc(client, world_id, *, name: str = "Tavern Tough"):
    """An NPC the way an accepted AI character proposal creates it: roleplay
    fields only, no hp/ac/stats."""
    r = await client.post(
        "/api/characters/",
        json={"world_id": world_id, "type": "NPC", "name": name, "level": 1},
    )
    assert r.status_code == 201
    return r.json()["id"]


async def _create_downed_character(client, world_id, *, name: str = "Sylvara"):
    """A character already at 0 HP (dying) with full combat stats."""
    r = await client.post(
        "/api/characters/",
        json={
            "world_id": world_id,
            "type": "PC",
            "name": name,
            "level": 3,
            "char_class": "Wizard",
            "hp_current": 0,
            "hp_max": 14,
            "ac": 12,
            "stats": {"ability_scores": {"dexterity": 14}},
        },
    )
    assert r.status_code == 201
    return r.json()["id"]


async def _create_caster(
    client,
    world_id,
    *,
    name: str = "Kira",
    char_class: str = "Wizard",
    hp: int = 14,
    spells: list[str] | None = None,
):
    """A level-3 full caster with known spells (slots derive from class/level)."""
    r = await client.post(
        "/api/characters/",
        json={
            "world_id": world_id,
            "type": "PC",
            "name": name,
            "level": 3,
            "char_class": char_class,
            "hp_current": hp,
            "hp_max": hp,
            "ac": 12,
            "spells": spells or ["Fire Bolt", "Cure Wounds", "Healing Word"],
            "stats": {
                "ability_scores": {
                    "intelligence": 16,
                    "wisdom": 16,
                    "dexterity": 14,
                    "constitution": 12,
                }
            },
        },
    )
    assert r.status_code == 201
    return r.json()["id"]


async def _create_dead_monster(client, world_id, *, name: str = "Slain Goblin"):
    """A monster that is already dead (skipped by next-turn)."""
    r = await client.post(
        "/api/characters/",
        json={
            "world_id": world_id,
            "type": "MONSTER",
            "name": name,
            "level": 1,
            "char_class": "Fighter",
            "hp_current": 0,
            "hp_max": 7,
            "ac": 13,
            "stats": {
                "ability_scores": {"dexterity": 10},
                "death_saves": {"is_dead": True},
            },
        },
    )
    assert r.status_code == 201
    return r.json()["id"]
