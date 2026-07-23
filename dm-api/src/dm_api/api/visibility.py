"""Player-visible projections of DM-owned entities.

Read endpoints respond with the same schema for every caller, but for
PLAYER-role callers the DM-only fields are nulled before serialisation, so
secrets never leave the server. ``None`` therefore means "absent or hidden";
the player UI renders nothing either way, and the DM role always receives
the full record.

What players may see:
- **Characters** — PCs in full (it's their own sheet) minus DM bookkeeping
  (``known_facts``, ``interaction_log_summary``). NPCs and monsters are
  reduced to name/race/level/location: stat blocks, spells (including the
  derived ``known_spells``/``spell_slots``), equipment, and roleplay hooks
  (personality/ideals/bonds/flaws) would spoil encounters.
- **Locations** — name, type, description, and map data; ``lore`` and
  ``history`` are the DM's planned reveals.
- **Worlds** — name, setting, and themes (the campaign pitch);
  ``lore_summary`` accumulates secrets across sessions.
"""

from __future__ import annotations

from game_engine.types import CharacterType

from dm_api.api.auth import ClientRole
from dm_api.db.models.character import Character, CharacterRead
from dm_api.db.models.location import Location, LocationRead
from dm_api.db.models.world import World, WorldRead


def character_read_for(character: Character, role: ClientRole) -> CharacterRead:
    """Project a Character row into what the given role may see."""
    full = CharacterRead.model_validate(character)
    if role is ClientRole.DM:
        return full
    hidden: dict[str, None] = {"known_facts": None, "interaction_log_summary": None}
    if full.type is not CharacterType.PC:
        hidden.update(
            {
                "char_class": None,
                "alignment": None,
                "stats": None,
                "hp_current": None,
                "hp_max": None,
                "ac": None,
                "speed": None,
                "abilities": None,
                "spells": None,
                "known_spells": None,
                "spell_slots": None,
                "equipment": None,
                "personality_traits": None,
                "ideals": None,
                "bonds": None,
                "flaws": None,
            }
        )
    return full.model_copy(update=hidden)


def location_read_for(location: Location, role: ClientRole) -> LocationRead:
    """Project a Location row into what the given role may see."""
    full = LocationRead.model_validate(location)
    if role is ClientRole.DM:
        return full
    return full.model_copy(
        update={
            "lore": None,
            "history": None,
            "character_associations": None,
            "interaction_log_summary": None,
        }
    )


def world_read_for(world: World, role: ClientRole) -> WorldRead:
    """Project a World row into what the given role may see."""
    full = WorldRead.model_validate(world)
    if role is ClientRole.DM:
        return full
    return full.model_copy(update={"lore_summary": None})
