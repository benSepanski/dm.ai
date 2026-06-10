# dm.ai — API Reference

All REST endpoints are mounted at `/api`. Interactive docs are at `GET /docs`.

Base URL (local): `http://localhost:8000`

---

## Health

### GET /health

**Response 200** `{ "status": "ok", "service": "dm-api" }`

---

## Worlds  `/api/worlds`

### POST /api/worlds — create a world

**Body:** `name` (req), `setting_description`, `themes` (JSON array), `lore_summary`

**201** → `WorldRead`: `id`, `name`, `setting_description`, `themes`, `lore_summary`, `created_at`, `updated_at`

### GET /api/worlds/{world_id} — fetch a world

**200** → `WorldRead` | **404**

### GET /api/worlds/{world_id}/locations — list all locations in a world

**200** → `LocationRead[]`

### DELETE /api/worlds/{world_id} — delete world + cascades

**204** | **404**

---

## Sessions  `/api/sessions`

### POST /api/sessions — start a session

**Body:** `world_id` (req), `name` (req), `rule_engine_version` (default `"dnd_5_5e"`),
`player_character_ids`, `current_location_id`

**201** → `SessionRead`: `id`, `world_id`, `name`, `rule_engine_version`,
`player_character_ids`, `current_location_id`, `session_summary`, `started_at`, `ended_at`

### GET /api/sessions/{session_id} — fetch a session

**200** → `SessionRead` | **404**

### GET /api/sessions/{session_id}/messages — chat history

Returns all `ChatMessage` rows for the session, ordered by timestamp ascending.

**200** → array of `{ id, session_id, role, content, token_count, timestamp }`

### POST /api/sessions/{session_id}/chat — main AI interaction

Send a DM message; get an AI narrative response plus any world-building
proposals (one per entity the AI introduced — a single turn can carry
several). `response` is clean narration: the raw `[PROPOSAL]` blocks are
stripped before persisting and returning.

**Body:** `{ "message": "The players arrive at Saltmere." }`

**200** →
```json
{
  "response": "The salty air hits the party...",
  "proposals": [
    {
      "id": "uuid", "type": "location",
      "content": { "name": "Saltmere", ... },
      "status": "pending", "dm_notes": null, "created_at": "..."
    }
  ]
}
```
`proposals` is `[]` when no world-building proposal was generated.

### PUT /api/sessions/{session_id}/end — end session

Marks `ended_at` and generates a session summary via the fast model.

**200** → `SessionRead` with `ended_at` and `session_summary` set | **404**

---

## Characters  `/api/characters`

### POST /api/characters — create character

**Body key fields:** `world_id` (req), `type` (`"PC"` / `"NPC"` / `"MONSTER"`, req),
`name` (req), `race`, `char_class`, `level` (default 1), `stats` (object),
`hp_current`, `hp_max`, `ac`, `speed`, `abilities`, `spells`, `equipment`,
`personality_traits`, `ideals`, `bonds`, `flaws`, `current_location_id`

**201** → `CharacterRead` (all fields above + `id`, `interaction_log_summary`,
`created_at`, `updated_at`)

### GET /api/characters/{char_id} — fetch character

**200** → `CharacterRead` | **404**

### PATCH /api/characters/{char_id} — partial update

All fields optional; only provided fields are changed.

**200** → `CharacterRead` (updated) | **404**

### GET /api/characters/world/{world_id} — list world characters

**200** → `CharacterRead[]`

---

## Locations  `/api/locations`

### POST /api/locations — create location

**Body key fields:** `world_id` (req), `type` (req, one of: `realm`, `country`,
`region`, `town`, `district`, `building`, `room`, `dungeon`, `wilderness`),
`name` (req), `parent_id` (UUID, for hierarchy), `description`, `lore`,
`history`, `map_data` (object for BattleMap), `character_associations`

**201** → `LocationRead`: all of the above + `id`, `interaction_log_summary`,
`created_at`, `last_visited_at`

### GET /api/locations/{loc_id} — fetch location

**200** → `LocationRead` | **404**

### PATCH /api/locations/{loc_id} — partial update

Commonly used to write `map_data` after the DM edits the battle map.

**200** → `LocationRead` (updated) | **404**

### DELETE /api/locations/{loc_id} — delete location

**204** | **404**

---

## Combat  `/api/sessions/{session_id}/combat`

### POST /api/sessions/{session_id}/combat — start combat

**Body (optional):** `{ "character_ids": [...], "location_id": "..." }` —
initiative is rolled for the listed characters.

Returns **409** if active combat already exists for the session, **404** if a
character id doesn't exist, and **422** if an enrolled character has no
combat stats (`hp_max`/`ac` null — typical for characters created from AI
proposals; PATCH the character first).

**201** → `CombatStateRead`: `id`, `session_id`, `location_id`, `round_number` (1),
`current_turn_index` (0), `initiative_order`, `combatants`, `combat_log`,
`started_at`, `ended_at`

### GET /api/sessions/{session_id}/combat — get active combat state

**200** → `CombatStateRead` | **404** if no active combat

### POST /api/sessions/{session_id}/combat/action — submit an action

Appends the action to `combat_log`.

**Body:** `actor_id` (req), `action_type` (req — e.g. `"attack"`, `"spell"`,
`"dash"`, `"dodge"`, `"hide"`, `"help"`), `target_id`, `spell_name`, `item_name`,
`extra` (free object for rule-specific data)

**200** → `CombatStateRead` with updated `combat_log`

### PUT /api/sessions/{session_id}/combat/end — end combat

Sets `ended_at`, syncs final HP/conditions back to the character rows, and —
when combatants were enrolled — appends a SYSTEM chat message summarizing the
mechanical outcome (rounds, final HP, who went down). That summary enters the
chat history, so the AI DM knows the result when narration resumes.

**200** → `CombatStateRead` | **404**

---

## AI / Proposals  `/api/ai`

### GET /api/ai/proposals/{proposal_id} — fetch proposal

**200** → `ProposalRead`: `id`, `session_id`, `world_id`, `type`, `content`,
`status`, `dm_notes`, `created_at` | **404**

### GET /api/ai/sessions/{session_id}/proposals — list session proposals

Returns all proposals for a session, newest first.

**200** → `ProposalRead[]`

### POST /api/ai/proposals/{proposal_id}/accept — accept a proposal

DM can optionally override fields before accepting.

**Body:** `dm_notes` (string), `modifications` (object merged into `content`)

**200** → `ProposalRead` with `status: "accepted"` | **409** if not pending

### POST /api/ai/proposals/{proposal_id}/reject — reject a proposal

**Body:** `dm_notes` (string, optional)

**200** → `ProposalRead` with `status: "rejected"` | **409** if not pending

---

## WebSocket  `/api/ws/sessions/{session_id}`

Connect to receive real-time session events. Any JSON message sent by a client
is relayed to all other clients in the same session. The server injects
`"session_id"` into each forwarded envelope.

**URL:** `ws://localhost:8000/api/ws/sessions/{session_id}`

### Message types

| `type` | Direction | Key payload fields | Purpose |
|---|---|---|---|
| `chat_message` | server → client | `message_id`, `role` (`dm`\|`ai`\|`system`), `content` | DM echo (sent immediately), AI reply, or system notice (end-of-combat summary); clients dedupe on `message_id` |
| `combat_update` | server → client | `combat` (full `CombatStateRead`) | Combat state change |
| `proposal_ready` | server → client | `proposal_id`, `proposal_type`, `status` | Proposal awaiting DM review / resolved |
| `entity_update` | server → client | `entity_type`, `entity_id` | Character/location created or changed |
| `map_token_move` | client → other clients (peer relay) | `token_id`, `x`, `y` | Battle-map token drag, mirrored on every screen |

### JavaScript example

```javascript
const ws = new WebSocket(`ws://localhost:8000/api/ws/sessions/${sessionId}`);
ws.onmessage = (e) => {
  const msg = JSON.parse(e.data);
  if (msg.type === "proposal_ready") { /* show proposal card */ }
};
ws.send(JSON.stringify({ type: "map_token_move", token_id: "...", x: 3, y: 4 }));
```

---

## Common Error Responses

| Status | Body | When |
|---|---|---|
| 404 | `{ "detail": "X not found" }` | Resource with given ID does not exist |
| 409 | `{ "detail": "..." }` | Conflict (e.g. proposal already acted on, combat already active) |
| 422 | FastAPI validation error | Request body fails Pydantic validation |
