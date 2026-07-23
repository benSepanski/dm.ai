# dm.ai — API Reference

All REST endpoints are mounted at `/api`. Interactive docs are at `GET /docs`.

Base URL (local): `http://localhost:8000`

---

## Authentication — DM vs. player

A single shared token (`DM_TOKEN` in `.env`; auto-generated and logged at
startup if unset) splits clients into two roles:

- **DM** — sends `X-DM-Token: <token>` on REST requests (and
  `?dm_token=<token>` on the WebSocket URL). Full access.
- **Player** — no/invalid token. Read-only: every write endpoint except
  `POST /api/characters` responds **403** `{ "detail": "DM token required" }`,
  and read endpoints redact DM-only fields to `null`:

| Entity | Hidden from players |
|---|---|
| Character (NPC/monster) | `char_class`, `alignment`, `stats`, `hp_current`, `hp_max`, `ac`, `speed`, `abilities`, `spells`, `known_spells`, `spell_slots`, `equipment`, `personality_traits`, `ideals`, `bonds`, `flaws`, `known_facts`, `interaction_log_summary` |
| Character (PC) | `known_facts`, `interaction_log_summary` |
| Location | `lore`, `history`, `character_associations`, `interaction_log_summary` |
| World | `lore_summary` |
| Proposals | entire `/api/ai/*` surface is DM-only (403) |

### GET /api/auth/role — check the caller's role

**200** → `{ "role": "dm" }` with a valid `X-DM-Token` header, else
`{ "role": "player" }`. Used by the UI to validate the token.

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

### GET /api/worlds/{world_id}/config — per-game configuration

**200** → `GameConfigRead`: `world_id`, `overrides`, `effective` | **404**

`overrides` holds the DM's stored choices (null = inherit the deployment
default from `dm_api.config.Settings`); `effective` is the fully resolved
configuration the engine will actually use. Fields:

| Field | Purpose |
|-------|---------|
| `ai_provider` | `"anthropic"` or `"claude_cli"` backend for this game |
| `orchestrator_model` | Model for full narrative turns |
| `generation_model` | Fast model for summaries / condensation sub-agents |
| `context_token_limit` | Token budget that triggers history condensation |
| `context_preserve_last_n` | Tail messages kept verbatim when condensing |
| `database_url` | Where this game's relational database lives |
| `redis_url` | Where this game's Redis instance lives |

### PUT /api/worlds/{world_id}/config — replace per-game overrides

**Body:** any subset of the fields above; omitted/null fields clear the
override (full-replace semantics, no merge).

**200** → `GameConfigRead` | **404** | **422** (unknown provider, non-positive limits)

Model and context overrides take effect on the next AI call for the game —
no restart needed.

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

## Character Creation  `/api/characters/creation`

Engine-backed creation endpoints that apply 2024 PHB rules — ability scores,
proficiencies, HP, AC, spell slots — so the UI never hard-codes game data.

### GET /api/characters/creation/options — fetch creation reference data

Returns all choices needed to build a level-1 character from the engine's
SRD registries. Safe to cache client-side; the data changes only on engine
updates.

**200** →
```json
{
  "classes": [
    {
      "character_class": "Fighter",
      "hit_die": 10,
      "primary_abilities": ["strength", "dexterity"],
      "saving_throw_proficiencies": ["strength", "constitution"],
      "armor_training": ["light", "medium", "heavy", "shield"],
      "weapon_category_training": ["simple", "martial"],
      "skill_choices": ["acrobatics", "athletics", ...],
      "num_skill_choices": 2,
      "spellcasting": false
    }, ...
  ],
  "species": [
    {
      "species": "Human",
      "creature_type": "humanoid",
      "size_options": ["medium", "small"],
      "speed": 30,
      "darkvision_ft": 0,
      "traits": [{ "name": "Resourceful", "description": "..." }],
      "damage_resistances": [],
      "description": "..."
    }, ...
  ],
  "backgrounds": [
    {
      "background": "Soldier",
      "ability_scores": ["strength", "constitution"],
      "skill_proficiencies": ["athletics", "intimidation"],
      "tool_proficiency": "playing card set",
      "origin_feat": "Savage Attacker",
      "equipment": ["spear", "shortbow", ...],
      "description": "..."
    }, ...
  ],
  "armor": [{ "name": "Chain Mail", "armor_type": "heavy", "base_ac": 16, "dex_bonus": false, "dex_cap": null, "stealth_disadvantage": true }, ...],
  "skills": [{ "skill": "athletics", "governing_ability": "strength" }, ...],
  "languages": ["common", "elvish", ...],
  "alignments": ["Lawful Good", ...],
  "standard_array": [15, 14, 13, 12, 10, 8],
  "point_buy_budget": 27,
  "point_buy_costs": { "8": 0, "9": 1, ..., "15": 9 }
}
```

### POST /api/characters/creation/build — build a level-1 PC

Runs `build_character` from the 2024 PHB engine and persists the result.
Rule-bending choices (off-list skill, untrained armor) surface as
non-fatal `warnings`; invalid inputs (unknown class/species, out-of-range
scores) return **422**.

**Body:**
```json
{
  "world_id": "uuid",
  "name": "Roderick",
  "character_class": "Fighter",
  "species": "Human",
  "background": "Soldier",
  "ability_scores": { "strength": 15, "dexterity": 14, "constitution": 13, "intelligence": 12, "wisdom": 10, "charisma": 8 },
  "skill_choices": ["athletics", "perception"],
  "background_ability_allocation": null,
  "languages": [],
  "armor_name": "Chain Mail",
  "shield": true,
  "alignment": "Lawful Good"
}
```

`background_ability_allocation` (optional) lets the player direct the background's
+2/+1 ability bonus. If omitted, the engine picks the default allocation for
the background. `armor_name` must match an entry in the `/options` armor list
(or be omitted for no armor). `shield` adds +2 AC.

**201** →
```json
{
  "character": { ...CharacterRead... },
  "warnings": ["Fighter should pick weapon masteries before play."]
}
```
**404** world not found | **422** invalid class/species/background/scores

---

## Characters  `/api/characters`

### POST /api/characters — create character

**Body key fields:** `world_id` (req), `type` (`"PC"` / `"NPC"` / `"MONSTER"`, req),
`name` (req), `race`, `char_class`, `level` (default 1), `stats` (object),
`hp_current`, `hp_max`, `ac`, `speed`, `abilities`, `spells`, `equipment`,
`personality_traits`, `ideals`, `bonds`, `flaws`, `current_location_id`

**201** → `CharacterRead` (all fields above + `id`, `interaction_log_summary`,
`created_at`, `updated_at`, plus two server-derived fields consumed by the
combat tracker's Cast Spell control (PT-28): `known_spells` (deduped union
of `stats.known_spells`/`stats.prepared_spells`, falling back to the
top-level `spells` column when neither is set) and `spell_slots` (from
`stats.spell_slots`) — both `null` when there's nothing to report or the
field is hidden per the role table above)

### GET /api/characters/{char_id} — fetch character

**200** → `CharacterRead` | **404**

### PATCH /api/characters/{char_id} — partial update

All fields optional; only provided fields are changed. Two semantics worth
knowing:

- **`stats` merges key-by-key** into the existing blob (send
  `{"stats": {"conditions": []}}` without re-sending `ability_scores`); a
  key set to `null` is removed.
- **Updates write through to active combat**: if the character is enrolled
  in a live fight, the patched fields are mirrored into the combat snapshot
  (and broadcast as a `combat_update`), so mid-combat patches take effect
  immediately and are not overwritten when combat ends.

**200** → `CharacterRead` (updated) | **404**

### POST /api/characters/{char_id}/rest — take a short or long rest

Resolved by the rule engine (2024 rules). **Short** rest spends Hit Point
Dice (`hit_dice_to_spend`, healing roll + CON each) and restores warlock
pact slots. **Long** rest restores full HP, all Hit Point Dice and spell
slots, drops temp HP, and reduces exhaustion by 1. Spell slots and hit dice
are derived from class/level on first use, then persist in `stats`.

**Body:** `{ "rest_type": "short" | "long", "hit_dice_to_spend": 0 }`

**200** →
```json
{
  "rest_type": "long", "hp_restored": 9, "hit_dice_spent": 0,
  "hit_dice_restored": 3, "slots_restored": true, "exhaustion_reduced": false,
  "character": { ...CharacterRead... }
}
```
**404** unknown character | **409** during active combat, or character is dead

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
initiative is rolled for the listed characters; ties are broken by
Dexterity score.

Returns **409** if active combat already exists for the session, **404** if a
character id doesn't exist, and **422** if an enrolled character has no
combat stats (`hp_max`/`ac` null — typical for characters created from AI
proposals; PATCH the character first).

**201** → `CombatStateRead`: `id`, `session_id`, `location_id`, `round_number` (1),
`current_turn_index` (0), `initiative_order`, `combatants`, `combat_log`,
`turn_states`, `started_at`, `ended_at`

### GET /api/sessions/{session_id}/combat — get active combat state

**200** → `CombatStateRead` | **404** if no active combat

### POST /api/sessions/{session_id}/combat/action — submit an action

Resolves the action through the rule engine and appends it to `combat_log`.
The action economy is enforced across requests via `turn_states`: each
combatant gets one action, one bonus action, and one reaction per turn (an
off-hand attack consumes the bonus action), reset when their turn comes
around. Dodge / Dash / Disengage / Help flags carry over mechanically
until then.

Two reaction events are submitted through this same endpoint, not a
separate one: `"Opportunity Attack"` (`target_id` is the creature whose
movement provoked it; rejected if that creature disengaged this turn or the
reactor's reaction is already spent) and `"Readied Action"` (triggers the
attack stored by an earlier `"Ready"` action on this actor — `target_id`/
`attack_details` are ignored, since the stored action supplies them; both
consume the reaction, not the action). `"Ready"` itself stores a trigger +
target + weapon on the actor's turn state (consuming the action) via
`readied_trigger` (free text, e.g. `"if a creature enters the doorway"`);
if unused, it's lost at the start of the readier's own next turn.

**Body:** `actor_id` (req), `action_type` (req — a 2024 action or reaction
event: `"Attack"`, `"Dash"`, `"Dodge"`, `"Disengage"`, `"Help"`, `"Hide"`,
`"Ready"`, `"Opportunity Attack"`, `"Readied Action"`, …), `target_id`,
`attack_details` (`weapon_name`, `damage_dice`, `damage_type`,
`attack_ability`, `is_ranged`, `is_offhand`, `two_handed`), `readied_trigger`
(only meaningful for `"Ready"`)

When `weapon_name` matches the game-engine weapon registry (`get_weapon`),
`damage_dice`/`damage_type`/`attack_ability`/`is_ranged`/mastery/proficiency
are derived from the registry entry and the actor's training instead of the
request fields, which then only serve as a fallback for weapons outside the
registry (Unarmed Strike, monster natural weapons, homebrew). `is_offhand`
marks a Two-Weapon Fighting off-hand attack; `two_handed` selects a
Versatile weapon's larger die.

**200** → `CombatStateRead` with updated `combat_log` | **404** unknown
actor/target | **422** `"Attack"`/`"Opportunity Attack"` with no `target_id`
| **409** rule rejection (actor can't act; its action / bonus action /
reaction is already spent; no opportunity provoked; nothing readied) —
rejections never enter `combat_log`

### POST /api/sessions/{session_id}/combat/cast-spell — cast a spell

Casts a spell from the SRD registry through the engine's spellcasting
module: slot consumption (with upcasting via `slot_level`), spell attack
rolls, saving throws against the caster's spell save DC, damage and healing
(cantrip level-scaling included), rider conditions, and concentration.
Casting consumes the caster's action / bonus action / reaction per the
spell's casting time. Spell slots derive from class/level the first time a
caster enters combat; spent slots persist on the character after the fight.

**Body:** `actor_id` (req), `spell_name` (req, case-insensitive),
`target_ids` (array), `slot_level` (optional upcast),
`spellcasting_ability` (optional override; required for classes with no
spellcasting ability)

**200** → `CombatStateRead` — the log entry carries
`{"event": "cast_spell", action_type, spell, slot_level_used,
concentration_started, flavor_text, outcomes: [{target_id, hit,
attack_total, save_total, save_success, damage, healing, conditions_applied,
concentration_save_dc, concentration_save_total, concentration_broken}]}`.
`flavor_text` is what the dm-ui combat tracker's Cast Spell control (PT-28)
pushes into the chat feed, mirroring how Attack/Dash/Dodge surface their own
`flavor_text` from `combat.py`.

**404** unknown spell / actor / target | **409** no slot remaining, economy
spent, caster can't act, or casting time too long for combat | **422**
spellcasting ability unresolvable

### POST /api/sessions/{session_id}/combat/heal — heal a combatant

DM adjudication tool (potion, Lay on Hands, narrative fiat) — consumes no
action economy. Healing a dying creature brings it back up and clears its
death saves. For spell healing prefer `cast-spell`.

**Body:** `{ "target_id": "...", "amount": 5 }` (amount ≥ 1)

**200** → `CombatStateRead` (log gains an `{"event": "heal"}` entry) |
**404** | **409** target is dead

### POST /api/sessions/{session_id}/combat/stabilize — stabilize a dying combatant

Marks a dying creature stable (e.g. after a DC 10 Medicine check): it stays
unconscious at 0 HP but stops rolling death saves and is skipped by
`next-turn`.

**Body:** `{ "target_id": "..." }`

**200** → `CombatStateRead` (log gains an `{"event": "stabilize"}` entry) |
**404** | **409** target is dead, not at 0 HP, or already stable

### POST /api/sessions/{session_id}/combat/next-turn — advance the turn

Ticks condition durations for the combatant whose turn is ending, advances
`current_turn_index` (incrementing `round_number` on wrap), **skipping**
combatants who can never act again (the dead, and stable unconscious
creatures), and resets the new combatant's action economy. When the
creature whose turn begins is dying (0 HP, not stable, not dead), its death
saving throw is rolled automatically (2024 PHB: a dying creature saves at
the start of its turn). The result is appended to `combat_log` as an
`{"event": "death_save", roll, outcome, successes, failures, is_stable,
is_dead, regained_hp}` entry; a natural 20 brings the creature back up at
1 HP.

**200** → `CombatStateRead` | **404** no active combat | **409** no combatants

### PUT /api/sessions/{session_id}/combat/end — end combat

Sets `ended_at`, syncs final HP, conditions, death-save state, spell slots,
temp HP, and concentration back to the character rows, and — when combatants
were enrolled — appends a SYSTEM chat message summarizing the mechanical
outcome (rounds, final HP, who went down or died, death-save tallies). That
summary enters the chat history, so the AI DM knows the result when
narration resumes.

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

DM clients append `?dm_token=<DM_TOKEN>`: `proposal_ready` events are
delivered only to connections that authenticated as DM. All other events go
to every connection in the session.

### Message types

| `type` | Direction | Key payload fields | Purpose |
|---|---|---|---|
| `chat_message` | server → client | `message_id`, `role` (`dm`\|`ai`\|`system`), `content` | DM echo (sent immediately), AI reply, or system notice (end-of-combat summary); clients dedupe on `message_id` |
| `combat_update` | server → client | `combat` (full `CombatStateRead`) | Combat state change |
| `proposal_ready` | server → DM clients only | `proposal_id`, `proposal_type`, `status` | Proposal awaiting DM review / resolved |
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
| 403 | `{ "detail": "DM token required" }` | DM-only endpoint called without a valid `X-DM-Token` header |
| 404 | `{ "detail": "X not found" }` | Resource with given ID does not exist |
| 409 | `{ "detail": "..." }` | Conflict (e.g. proposal already acted on, combat already active) |
| 422 | FastAPI validation error | Request body fails Pydantic validation |
