# dm.ai Implementation Plan — Ideal DM Workflow (Requirements 2–7 core, Requirement 1 as late stretch group)

## Current state (summary)

- **No scale mechanisms anywhere:** `GET /worlds/{id}/locations` (worlds.py:60-70) and `GET /characters/world/{world_id}` (characters.py:163-174) return whole unpaginated tables; no search, no filters, no active/archived concept; `listWorldLocations` is defined in `dm-ui/src/api/client.ts:440` but never called; CharacterCard renders every entity unconditionally.
- **Quests do not exist** in any layer (grep-confirmed zero real hits); Location hierarchy exists structurally (`parent_id`, 9-value `LocationType`) but has no browser UI and no parent-type validation. `embedding: Vector(1536)` columns on World/Location/Character are dead schema — never written or queried.
- **One chat stream, DM-only:** `ChatRole` = DM/AI/SYSTEM only; no PLAYER role, no player composer, no promote flow. Proposals support only Accept/Reject; `ProposalStatus.MODIFIED` is dead code (ai.py:193 always sets ACCEPTED); `ProposalAccept.modifications` is an untyped `dict[str, Any]`; no re-request flow.
- **Combat is spatial-free:** no coordinate/grid/wall/door type in game-engine or dm-api; `Location.map_data` is a dead `dict[str, Any]` column; BattleMap is a hardcoded 10×10 cosmetic grid with drag-only interaction; actions are 3 hardcoded buttons (of 12+ `ActionType` values); every combat endpoint is `require_dm` — players cannot act, and there is no override mechanism beyond the heal/stabilize fiat endpoints.
- **No mode/scene concept:** GameSession has no mode field; "combat mode" is inferred client-side from `combat !== null` plus a manual map toggle; no transition events.
- **AI context silently truncates:** system-prompt world context caps at 20 NPCs/20 locations oldest-first (sessions.py:130-176) with no relevance ranking — at target scale the AI DM is blind to most of the world.
- **Role-based redaction exists and must be preserved:** the current list endpoints project every row through `character_read_for(c, role)` / `location_read_for(loc, role)` (`dm-api/src/dm_api/api/visibility.py:30,58`), which null out DM-only fields (stats, hp, ac, lore, history, known_facts, …) for non-DM callers. Auth is a single shared DM token (`auth.py`); every other caller is PLAYER. Any endpoint rewrite that serializes raw `CharacterRead`/`LocationRead` rows is an information-disclosure regression.
- **Requirement 1 has zero implementation:** no filesystem access in the AI layer, no ingestion pipeline, no notes-path config; `ClaudeCLIBackend` is text-in/text-out with no `cwd`.
- **Migration state confirmed:** Alembic head is `0003_game_configs` in `dm-api/alembic/versions/`, files named `NNNN_<slug>.py`.

## Phase dependency overview

| Phase | Requires | Delivers (Req) |
|---|---|---|
| 1 | — | 2 (status field + archive UI + auto-archive defeated) |
| 2 | 1 | 2 (paginated/filtered/search API; location hierarchy validation; embedding GC) |
| 3 | 2 | 2 (world browser: tree, directory, global search; store off whole-world eager-load) |
| 4 | 2 | 2 (quests, model→UI) |
| 5 | — | 7 (GameMode state + API + mode-pill UI) |
| 6 | 5 | 6, 7 (combat drives mode with prior-mode restore; typed server-side override; combat.py extraction) |
| 7 | 1, 4, 5 | 2 (AI context locality retrieval, kills oldest-first truncation) |
| 8 | — | 3 (player chat channel + player composer) |
| 9 | 8 | 3 (promote-to-main-chat + DM review UI) |
| 10 | 4 | 3 (proposal modify/re-request, data+API+sub-agent) |
| 11 | 10 | 3 (proposal edit/re-request UI) |
| 12 | — | 4 (spatial types + typed MapLayout schema) |
| 13 | 5, 6, 12 | 4 (map generation + rendering + seamless entry/exit) |
| 14 | 13 | 5, 6 (square selection + full action set + override button) |
| 15 | 8, 14 | 5 (player-claimed PC + player-submit endpoint + player end-turn + DM undo + player action panel) |
| 16 [STRETCH] | 5 | 6 (non-combat skill-check endpoint) |
| 17 [STRETCH] | — | 1 (campaign-notes path config + allow-list) |
| 18 [STRETCH] | 4, 10, 17 | 1 (folder ingestion → proposal batch) |

**Core path = Phases 1–15, in order.** Requirement 1 is Phases 17–18 (late group; sequenced so ingestion lands on a complete data model). Every phase leaves the stack runnable, migrations are additive+defaulted, and each phase ends with its own tests plus a short manual verify.

## Global conventions (apply to every phase)

- **Migrations:** NEW file in `dm-api/alembic/versions/` named `NNNN_<slug>.py`, `down_revision` chained to the previous revision. Current head: `0003_game_configs`. This plan pre-assigns numbers 0004–0012; if execution order changes, renumber to the actual head at execution time (`cd dm-api && alembic heads`).
- **Enums:** new app-level enums go in `game-engine/src/game_engine/types/enums/_app.py`, combat-level in `_combat.py`. Export by adding the name to the import + `__all__` lists in `game-engine/src/game_engine/types/enums/__init__.py`, and re-export from `game-engine/src/game_engine/types/__init__.py` (both files already do this for `LocationType` — add your name to the same two lists).
- **Enum DB columns:** every new `sa.Enum(SomeEnum, ...)` column MUST pass `values_callable=lambda e: [m.value for m in e]` so Postgres labels are the lowercase `.value` strings, not the uppercase member names. Without it, `sa.Enum` emits member names (`ACTIVE`) as PG labels, which mismatches `CREATE TYPE ... ('active', ...)` and `server_default='active'`. `location.py:30-38` does this correctly — copy that pattern verbatim. (`character.py`'s `type` column only gets away without it because `CharacterType` member names equal their values.)
- **Typed boundaries:** no `dict[str, Any]` on any public surface; JSON DB columns are serialization-only, deserialized to typed Pydantic/dataclass objects in-process.
- **Role-based visibility:** any endpoint returning Character or Location rows MUST project each row through `character_read_for(c, role)` / `location_read_for(loc, role)` from `dm-api/src/dm_api/api/visibility.py`, taking `role: ClientRole = Depends(client_role)`. Never serialize raw `model_validate` rows to a potentially-PLAYER caller.
- **File size:** every file < 400 LoC. When a target file would exceed it, create the named NEW sibling module given in the phase.
- **AI sub-agents:** own prompt file `dm-api/src/dm_api/ai/prompts/<name>_prompt.py` (< 60 lines), typed input/output dataclass validated at the boundary, fast `generation_model` (Haiku), constructed from `EffectiveGameConfig` (never raw `Settings`).
- **VALIDATION command sets** (referenced below as "run standard checks"):
  - game-engine: `cd game-engine && black src/ tests/ && isort src/ tests/ && autoflake -r --in-place src/ tests/ && mypy src/ && pytest tests/ -v`
  - dm-api: `cd dm-api && black src/ tests/ && isort src/ tests/ && autoflake -r --in-place src/ tests/ && mypy src/ && DATABASE_URL="sqlite+aiosqlite:///:memory:" AI_PROVIDER="anthropic" ANTHROPIC_API_KEY="test-key" pytest tests/ -v`
  - dm-ui: `cd dm-ui && npx tsc --noEmit && npm run lint`
- **Manual verify:** bring the stack up with `docs/playtest/playtest-stack.sh up` (or `docker compose up`), and **always** tear down with `docs/playtest/playtest-stack.sh down` afterward (per repo memory).

---

## Phase 1 — Entity lifecycle: active/archived/defeated status, auto-archive, archive UI

**Requires:** nothing (first phase). **Serves:** Req 2 (active visible, inactive hidden).
**Goal:** Every NPC/monster and location gets a machine-readable lifecycle state; defeated monsters auto-archive on combat end; the DM can archive/restore from the character list, which hides non-active entities by default. Smallest slice that visibly de-clogs the screen.

**Changes:**
1. `game-engine/src/game_engine/types/enums/_app.py`: add `class CharacterStatus(str, Enum)` with `ACTIVE = "active"`, `ARCHIVED = "archived"`, `DEFEATED = "defeated"`; add `class LocationStatus(str, Enum)` with `ACTIVE = "active"`, `ARCHIVED = "archived"`. Export per global convention (both `__init__.py` files).
2. `dm-api/src/dm_api/db/models/character.py`: add `status: Mapped[CharacterStatus]` column — `sa.Enum(CharacterStatus, name="character_status", create_type=False, values_callable=lambda e: [m.value for m in e])`, `server_default="active"`. The `values_callable` is **required** (see global convention: without it PG gets uppercase `ACTIVE` labels and the `server_default='active'` / `CREATE TYPE ... 'active'` mismatch); copy the enum-column pattern at `location.py:30-38`, which already includes it. Add `status: CharacterStatus = CharacterStatus.ACTIVE` to `CharacterCreate`, `status: CharacterStatus` to `CharacterRead`, `status: CharacterStatus | None = None` to `CharacterUpdate`.
3. `dm-api/src/dm_api/db/models/location.py`: same pattern with `LocationStatus` on `Location` + Create/Read/Update schemas — again with `values_callable=lambda e: [m.value for m in e]` on the `sa.Enum`.
4. NEW migration `dm-api/alembic/versions/0004_entity_status.py`: create the two PG enum types via `op.execute("CREATE TYPE character_status AS ENUM ('active','archived','defeated')")` / `("CREATE TYPE location_status AS ENUM ('active','archived')")` (lowercase labels, matching the `values_callable` output), then `op.add_column` for `characters.status` and `locations.status` with `server_default='active'`.
5. Auto-archive: in `dm-api/src/dm_api/api/combat_utils.py` `sync_combatants_to_db` (the combat-end write-back at lines 77-114). Note the current function only reads `id`, `hp_current`, and `SHEET_STATE_FIELDS` from each combatant dict and loads the corresponding `Character` row — the combatant dicts do **not** carry a type field, and there is no existing `hp_current <= 0` branch; you are adding one. After writing HP back to the loaded `Character` row, check the **row's** own fields: if `character.type` (the column is named `type`, typed `Mapped[CharacterType]`, `character.py:24` — there is no `character_type` column) is `CharacterType.NPC` or `CharacterType.MONSTER` and the written-back `hp_current <= 0`, set `character.status = CharacterStatus.DEFEATED`. PCs untouched (death saves). **Broadcasting:** there is currently NO per-character `entity_update` broadcast on combat end — `end_combat` (combat.py:369) calls `sync_combatants_to_db` and then broadcasts only `combat_update` via `broadcast_combat`; do not assume otherwise. So: collect the ids of characters flipped to DEFEATED (return them from `sync_combatants_to_db` or accumulate in the caller) and, in `end_combat` after commit, explicitly call `ws.broadcast_entity_update(session_id, entity_type="character", entity_id=...)` (ws.py:102) once per defeated character so the character list updates live on all clients.
6. UI plumbing: add `status: string` to `CharacterResponse`/`LocationResponse` and create/update request types in `dm-ui/src/api/client.ts`; add `status` to `CharacterData`/`LocationData` in `dm-ui/src/store/gameStore.ts`; carry it in `mapCharacterResponse` in `dm-ui/src/api/mappers.ts`.
7. UI: `dm-ui/src/components/CharacterCard/CharacterCard.tsx` — default-filter the Monsters/NPCs group to `status === 'active'`; add a "Show inactive (N)" toggle button beneath the group listing archived+defeated entries; add per-entity DM-only "Archive"/"Restore" buttons calling `api.updateCharacter(id, { status })`.

**Data-model / migration:** two PG enums + two defaulted columns (`0004`).
**API contract:** `status` appears in Character/Location payloads and create/patch bodies. No new routes. `end_combat` now emits per-character `entity_update` events for auto-defeated characters.
**UI:** archived/defeated hidden by default; archive/restore buttons; show-inactive toggle.

**VALIDATION:**
- Run standard checks (game-engine + dm-api + dm-ui).
- NEW `dm-api/tests/test_entity_status.py`: create character → assert `status == "active"`; PATCH to `archived` → GET → persisted. Start combat with a monster, drop it to 0 HP, end combat → assert its Character row is `defeated` (and, if the test harness captures WS broadcasts, that an `entity_update` was emitted for it).
- Manual: stack up; create two NPCs; archive one → disappears from list; "Show inactive (1)" → reappears with Restore; run a quick combat, kill the monster, end combat → monster leaves the active list automatically (via the new `entity_update` broadcast, no refresh). Tear down.

---

## Phase 2 — Pagination, filtering & name search on list endpoints; location-hierarchy validation; embedding-column garbage collection

**Requires:** Phase 1 (status to filter on). **Serves:** Req 2.
**Goal:** Replace unbounded list endpoints with typed, paginated, filterable ones — the API backbone for all browsing/search UI — **without losing the role-based redaction the current endpoints apply**, add the missing parent-type/cycle validation on the location hierarchy, and delete the dead pgvector columns (CLAUDE.md principle 9: garbage-collect drift rather than leaving unused schema).

**Changes:**
1. NEW `dm-api/src/dm_api/api/pagination.py`: `PagedResult` generic Pydantic model — `items: list[T]`, `total: int`, `limit: int`, `offset: int` (use `pydantic.BaseModel` with `Generic[T]`). No `dict[str, Any]`.
2. `dm-api/src/dm_api/api/characters.py`: rewrite `GET /world/{world_id}` with FastAPI `Query()` params: `limit: int = Query(50, ge=1, le=200)`, `offset: int = Query(0, ge=0)`, `q: str | None` (case-insensitive `ilike` name substring), `status: CharacterStatus | None`, `character_type: CharacterType | None` (query-param name stays `character_type` for the API; it filters the model's `Character.type` column). Default filter when `status` is omitted: `status != ARCHIVED` (DEFEATED stays queryable but is hidden by Phase 1's UI default). Return `PagedResult[CharacterRead]` with a `func.count()` total. **CRITICAL — preserve redaction:** keep the endpoint's `role: ClientRole = Depends(client_role)` dependency (the current route already has it, characters.py:167) and build the items as `[character_read_for(c, role) for c in rows]` exactly as the current implementation does (characters.py:181, helper at visibility.py:30). Do NOT emit raw `CharacterRead.model_validate(row)` — that would leak DM-only NPC/monster stats, spell lists, and hidden fields to player clients. `total` counts the full match set regardless of redaction (redaction nulls fields, it does not drop rows).
3. `dm-api/src/dm_api/api/worlds.py`: rewrite `GET /{world_id}/locations` the same way with `q`, `location_type: LocationType | None`, `status: LocationStatus | None`, `parent_id: uuid.UUID | None` (children-of navigation; `parent_id` omitted = no parent filter; add `roots_only: bool = False` for top-level fetch), `limit`/`offset`. Return `PagedResult[LocationRead]`. **Same redaction rule:** keep `role: ClientRole = Depends(client_role)` and build items as `[location_read_for(loc, role) for loc in rows]` (current code at worlds.py, helper at visibility.py:58) so DM-only lore/history/known_facts stay hidden from players.
4. `dm-api/src/dm_api/api/locations.py`: add `GET /locations` mirroring the same filters plus required `world_id` (closes the "locations.py has no list route" gap; the tree UI uses this). This new route MUST also take `role: ClientRole = Depends(client_role)` and project items through `location_read_for(loc, role)` — identical redaction to step 3.
5. Location hierarchy validation (closes the "no parent-type validation" gap flagged in the current-state summary): in `dm-api/src/dm_api/api/locations.py` `create_location` and `update_location`, when `parent_id` is set: (a) load the parent and reject with 422 if the parent's `LocationType` is not a legal ancestor tier for the child's type — encode the tier order as a module-level dict `_LOCATION_TIER: dict[LocationType, int]` (`REALM=0, COUNTRY=1, REGION=2, TOWN=3, DISTRICT=4, BUILDING=5, ROOM=6`; `DUNGEON` and `WILDERNESS` are flexible containers at tier 3 — a parent is legal iff `_LOCATION_TIER[parent.location_type] < _LOCATION_TIER[child.location_type]`, matching the 9 values in `_app.py:12-23`); (b) reject cycles on update with 422 by walking `parent_id` upward from the proposed parent with a `visited: set[uuid.UUID]` — if the walk reaches the location being updated or revisits a node, it's a cycle. (Phase 7's ancestor walk gets the same visited-set defense.)
6. Embedding GC: remove the `embedding` columns and `Vector` imports from `dm-api/src/dm_api/db/models/world.py`, `location.py:46`, `character.py:53` (zero call sites, grep-confirmed). NEW migration `dm-api/alembic/versions/0005_drop_dead_embeddings.py` dropping the three columns. Note in the migration docstring: semantic search, if it returns, comes back with a real write path (a typed embedding sub-agent), not a dormant column.
7. `dm-ui/src/api/client.ts`: update `listWorldCharacters`/`listWorldLocations` signatures to accept a typed params object and return the `PagedResult` envelope. Caller updates: **only `listWorldCharacters` has call sites** — `dm-ui/src/components/DMDashboard/DMDashboard.tsx:67` and `dm-ui/src/components/DMDashboard/NewSessionForm.tsx:36` (note: NewSessionForm lives under `components/DMDashboard/`, not a top-level path) — update both to read `.items` (fetch with `limit: 200` so current behavior is unchanged until Phase 3 removes the eager load). `listWorldLocations` has ZERO call sites in dm-ui (only its definition at client.ts:440) — just change its signature; there are no callers to update. Breaking shape change is intentional — no compat shims per repo rule.

**Data-model / migration:** drop 3 dead columns (`0005`); no new columns.
**API contract (breaking, intentional):** `GET /characters/world/{id}?limit&offset&q&status&character_type` → `PagedResult[CharacterRead]` (items role-redacted); `GET /worlds/{id}/locations?...` and NEW `GET /locations?world_id&parent_id&roots_only&location_type&status&q&limit&offset` → `PagedResult[LocationRead]` (items role-redacted); location create/update now 422 on illegal parent tier or cyclic `parent_id`.
**UI:** callers adapted; no new surface.

**VALIDATION:**
- Run standard checks.
- NEW `dm-api/tests/test_list_pagination.py`: seed 60 characters → `total == 60`, `len(items) == 50` default, `offset=50` returns 10; `q=` substring filters; archived excluded by default, included with `status=archived`; location `parent_id` filter returns only children. **Redaction assertions:** call the paginated character list with a PLAYER (non-DM) token and assert NPC/monster items have their DM-only fields nulled (same shape `character_read_for` produces today), while a DM-token call returns them; same for a location with DM-only lore.
- Extend with hierarchy cases: parenting a ROOM to a REALM → 201 (legal, ancestor tier is lower) but parenting a REALM to a ROOM → 422; PATCH creating a parent cycle (A→B→A) → 422.
- Manual: stack up; existing character list and session-creation picker still render; `curl "$API/characters/world/$WID?limit=1&q=gob"` → `total` reflects full match count, one item. Tear down.

---

## Phase 3 — World browser UI: location tree + character directory + global search; store off the whole-world eager-load

**Requires:** Phase 2. **Serves:** Req 2 (browse/search at scale).
**Goal:** The DM can browse the whole world — collapsible location tree, searchable character directory, one global search box — active-by-default, archived behind a toggle. Additionally, the game store stops eagerly holding the entire world's characters (which at target scale would silently truncate at the 200-per-page cap).

**Changes:**
1. NEW `dm-ui/src/components/WorldBrowser/WorldBrowser.tsx` (< 400 LoC): a modal/panel opened from a "Browse World" toolbar button, with tabs `Locations | Characters` (a `Quests` tab is added in Phase 4). Props contract: `{ worldId: string; isOpen: boolean; onClose: () => void }`. Each tab: debounced search input, status filter (`active` default, "show archived" checkbox), "Load more" pagination against the Phase 2 endpoints.
2. NEW `dm-ui/src/components/WorldBrowser/LocationTree.tsx` (< 400 LoC): collapsible tree; roots fetched via `GET /locations?world_id&roots_only=true`, children lazily via `?parent_id=`. Archived nodes rendered dimmed. Row action: "Set as current location" (reuse the existing set-current-location path). Cache expanded nodes in a local `Map<parentId, LocationData[]>` component state (not persisted).
3. NEW `dm-ui/src/components/WorldBrowser/SearchBar.tsx` (< 400 LoC): global search input mounted in the DMDashboard top bar (one mount line in `DMDashboard.tsx` — logic lives in the component). Debounced parallel calls to `listWorldCharacters({q, status:'active'})` and `listWorldLocations({q, status:'active'})`; grouped result dropdown; clicking a location sets current location, clicking a character opens WorldBrowser's Characters tab filtered to it.
4. **Kill the whole-world eager-load** (the scale hazard the gap analysis flagged — Phase 2's `limit: 200` was a temporary shim, not the fix): change `DMDashboard.tsx` `hydrateSession` (line ~65-67) to stop dumping `listWorldCharacters` for the whole world into `gameStore.characters`. Instead hydrate the store with only: (a) active PCs (`listWorldCharacters({ character_type: 'PC', status: 'active' })`) and (b) characters at the session's current location (filter or dedicated fetch), plus (c) any character ids referenced by the active combat's combatants — fetched by id via `getCharacter` and merged into the store (add a `upsertCharacters(list)` store action in `gameStore.ts` if one doesn't exist). Combat targeting (CombatTracker) and chat entity references must fetch-by-id on demand for any id not in the store rather than assuming it was preloaded. `NewSessionForm.tsx:36`'s PC picker switches to `listWorldCharacters({ character_type: 'PC', status: 'active' })` (PCs are few; pagination default is fine). The store never again holds "everything" — WorldBrowser/SearchBar own paginated browsing.
5. `dm-ui/src/components/CharacterCard/CharacterCard.tsx`: left rail now shows active PCs + a compact "N other characters — Browse all" link opening WorldBrowser (use the `total` from a `limit:1` paged call for N), instead of dumping every non-PC.
6. `dm-ui/src/components/DMDashboard/DMDashboard.tsx`: two mount lines only (toolbar button + SearchBar) beyond the hydrateSession change in step 4. Do not grow this file otherwise.

**Data-model / migration:** none. **API contract:** consumes Phase 2 only.
**UI:** WorldBrowser modal, lazy location tree, global search bar, de-clogged left rail, store holds a bounded working set instead of the whole world.

**VALIDATION:**
- Run dm-ui standard checks.
- Manual: stack up; create REALM → TOWN (parent=realm) → BUILDING → ROOM; open WorldBrowser, expand realm→town→building→room; archive the room → dims/hides per toggle; type a partial NPC name in the global search → grouped results appear; click a location result → current location changes. Create >10 NPCs at another location → left rail and store stay small; combat started against one of them still resolves (fetch-by-id path). Tear down.

---

## Phase 4 — Quest domain model, CRUD API, and browser tab

**Requires:** Phase 2 (pagination), Phase 3 (WorldBrowser to mount the tab). **Serves:** Req 2 (subquests, partial quests, active-visible).
**Goal:** Quests become first-class data with a full vertical slice: enum → model → migration → routes → UI tab with active-foregrounded display.

**Changes:**
1. `game-engine/src/game_engine/types/enums/_app.py`: add `class QuestStatus(str, Enum)`: `ACTIVE = "active"`, `COMPLETED = "completed"`, `FAILED = "failed"`, `ABANDONED = "abandoned"`. Export per convention.
2. NEW `dm-api/src/dm_api/db/models/quest.py`: `Quest` model — `id: uuid PK`, `world_id: uuid FK worlds.id`, `name: str`, `summary: Text`, `description: Text | None`, `status: QuestStatus` (enum column with `values_callable=lambda e: [m.value for m in e]` per global convention, `server_default="active"`), `location_id: uuid | None FK locations.id`, `giver_character_id: uuid | None FK characters.id`, `parent_quest_id: uuid | None` self-FK (subquests), `created_at`, `updated_at`. Plus `QuestCreate`/`QuestRead`/`QuestUpdate` Pydantic schemas (fully typed).
3. NEW migration `dm-api/alembic/versions/0006_quests.py`: create `quest_status` PG enum (lowercase labels) + `quests` table.
4. NEW `dm-api/src/dm_api/api/quests.py`: `POST /quests`, `GET /quests/{id}`, `PATCH /quests/{id}`, `DELETE /quests/{id}` (all `require_dm`), and `GET /worlds/{world_id}/quests?status&q&parent_quest_id&limit&offset` → `PagedResult[QuestRead]`. The list route follows the same role-projection convention as Phase 2: take `role: ClientRole = Depends(client_role)` and add a `quest_read_for(quest, role)` helper to `dm-api/src/dm_api/api/visibility.py` (mirroring `location_read_for`) that nulls the DM-only `description` field for non-DM callers (`name`/`summary`/`status` are player-visible). Wire the router into `dm-api/src/dm_api/api/router.py`.
5. `dm-ui/src/api/client.ts`: add `QuestResponse`/`CreateQuestRequest`/`UpdateQuestRequest` types + `quests` endpoint group (`createQuest`, `getQuest`, `updateQuest`, `listWorldQuests`).
6. NEW `dm-ui/src/components/WorldBrowser/QuestList.tsx` (< 400 LoC): `Quests` tab in WorldBrowser — active quests always expanded at top; completed/failed/abandoned collapsed behind "Resolved (N)"; "+ New Quest" inline form (name, summary, optional parent quest select); per-quest status dropdown calling `updateQuest`. Subquests indent under their parent.

**Data-model / migration:** `quest_status` enum + `quests` table (`0006`).
**API contract:** new `/quests` CRUD + `/worlds/{id}/quests` paginated list (role-projected items).
**UI:** Quests tab in WorldBrowser.

**VALIDATION:**
- Run standard checks.
- NEW `dm-api/tests/test_quests.py`: create → default ACTIVE; subquest with `parent_quest_id`; list filters by status and `q`; PATCH to COMPLETED persists; DELETE 404s afterward; PLAYER-token list call → `description` is null in items, DM-token call → present.
- Manual: stack up; create quest + subquest in the Quests tab; mark parent COMPLETED → moves into collapsed "Resolved" group. Tear down.

---

## Phase 5 — GameMode: session mode state, transition API, and mode indicator UI

**Requires:** nothing structural. **Serves:** Req 7 (modes of play as data) — vertical slice ending in a visible pill.
**Goal:** Exploration/social/combat/downtime/travel exists as server-authoritative session state, switchable by the DM, live-synced to all clients.

**Changes:**
1. `game-engine/src/game_engine/types/enums/_app.py`: add `class GameMode(str, Enum)`: `EXPLORATION = "exploration"`, `SOCIAL = "social"`, `COMBAT = "combat"`, `DOWNTIME = "downtime"`, `TRAVEL = "travel"`. Export per convention.
2. `dm-api/src/dm_api/db/models/session.py`: add `current_mode: Mapped[GameMode]` (enum column with `values_callable=lambda e: [m.value for m in e]`, `server_default="exploration"`) AND `previous_mode: Mapped[GameMode | None]` (same enum type, nullable, no default — Phase 6 uses it to restore the pre-combat mode so combat doesn't always dump the session back to exploration); add `current_mode: GameMode` to `SessionRead`; NEW Pydantic `SessionModeUpdate(mode: GameMode)`.
3. NEW migration `dm-api/alembic/versions/0007_session_mode.py`: `game_mode` PG enum (lowercase labels) + `sessions.current_mode` column defaulted + nullable `sessions.previous_mode` column.
4. NEW `dm-api/src/dm_api/api/session_mode.py` (keeps `sessions.py`, already ~448 LoC, from growing): `PATCH /sessions/{id}/mode` (`require_dm`) validating `GameMode`, writing the column, returning `SessionRead`. Wire into `router.py`.
5. `dm-api/src/dm_api/api/ws.py`: add `mode_changed` to the documented event set + `broadcast_mode_change(session_id, mode)` helper. Model it on `broadcast_entity_update` (ws.py:102) — the broadcast helper that actually lives in `ws.py` — i.e. a thin wrapper calling `broadcast_to_session(session_id, {"type": "mode_changed", "session_id": str(session_id), "mode": mode.value})`. (Do NOT look for `broadcast_combat` in ws.py — that helper lives in `combat_utils.py:58` and wraps `broadcast_to_session` from the API-layer side.)
6. `dm-ui/src/store/gameStore.ts`: add `mode: GameMode-string` to the session slice + `setMode` action; `dm-ui/src/api/mappers.ts`: map `current_mode` from the session response (shared hydration + WS path); `dm-ui/src/api/ws.ts`: extend the `WsEvent` union (lines 22-33) with `{ type: 'mode_changed'; mode: string }` and handle → `setMode`.
7. NEW `dm-ui/src/components/ModeIndicator/ModeIndicator.tsx` (< 400 LoC): pill showing current mode (one color per mode) with a 300ms highlight animation on change; DM-only `<select>` of the five modes calling new client method `api.setSessionMode(sessionId, mode)`. Mount with one line in `DMDashboard.tsx`'s top bar.

**Data-model / migration:** `game_mode` enum + two columns (`0007`).
**API contract:** `PATCH /sessions/{id}/mode` → `SessionRead`; new `mode_changed` WS event.
**UI:** live mode pill + DM switcher.

**VALIDATION:**
- Run standard checks.
- NEW `dm-api/tests/test_session_mode.py`: new session defaults `exploration`; PATCH to `downtime` persists; invalid value → 422; non-DM PATCH → 403.
- Manual: stack up; two tabs (DM + player); DM switches Exploration→Social → player tab's pill updates live. Tear down.

---

## Phase 6 — Combat drives mode (with prior-mode restore); typed DM override on combat actions; combat.py extraction

**Requires:** Phase 5. **Serves:** Req 7 (seamless combat transitions) + Req 6 (override as a real mechanism).
**Goal:** Combat start/end auto-flips `current_mode` and — because Req 7 demands smooth transitions between ALL five modes, not a hardcoded fall-back — end_combat restores whatever mode the session was in before combat (social stays social, travel stays travel). The action endpoint gains a first-class typed override so the DM can force a specific engine rejection through, audited in the combat log. Because `combat.py` is already 401 LoC (over the repo's own <400 hard limit), this phase also extracts the action handler into a named sibling so this phase and Phase 13 have room to land.

**Changes:**
1. **Extraction first:** `dm-api/src/dm_api/api/combat.py` is 401 LoC. Move the combat action handler (`POST /sessions/{id}/combat/action` and its helpers) into NEW `dm-api/src/dm_api/api/combat_actions.py`, wired into `router.py` as its own router (same path prefix — external routes unchanged). `combat.py` keeps start/end/next-turn/get; both files must end this phase < 400 LoC and stay under it through Phases 13–15 (Phase 13's map code goes in `combat.py`'s start/end, Phase 15's player path gets its own `combat_player.py`).
2. `dm-api/src/dm_api/api/combat.py` `start_combat`: set `session.previous_mode = session.current_mode` and then `session.current_mode = GameMode.COMBAT` in the same transaction; call `broadcast_mode_change`. `end_combat`: restore `session.current_mode = session.previous_mode or GameMode.EXPLORATION` (EXPLORATION only as the null-fallback, e.g. combats started before this column existed), clear `session.previous_mode = None`, and broadcast the restored mode. Combat entered from SOCIAL/TRAVEL/DOWNTIME must land back in that mode, not exploration.
3. `game-engine/src/game_engine/types/enums/_combat.py`: add `class OverrideReason(str, Enum)`: `DM_FIAT = "dm_fiat"`, `RULE_EXCEPTION = "rule_exception"`, `NARRATIVE = "narrative"`. Export per convention.
4. `dm-api/src/dm_api/db/models/combat.py`: add `override: OverrideReason | None = None` to `CombatActionRequest` (enum, not a bool, per golden rule).
5. `dm-api/src/dm_api/api/combat_actions.py` action handler (post-extraction): when `override` is set and the engine rejection is a *ruling* category (`cannot_act`, `action_used`, `bonus_action_used`, `total_cover`), bypass the 409, apply the action, and append a combat_log entry recording `override` + reason. **Never** bypass `actor_not_found`/`target_not_found` — those are integrity errors, not rulings.
6. `dm-ui/src/api/client.ts`: add optional `override` to `CombatActionRequest` (UI button lands in Phase 14).

**Data-model / migration:** none (uses Phase 5's `previous_mode` column; override is a request-only field; combat_log is existing JSON).
**API contract:** `POST /sessions/{id}/combat/action` accepts optional `override: OverrideReason`; combat start/end now mutate session mode (end restores the pre-combat mode) + emit `mode_changed`.
**UI:** none new — Phase 5's pill visibly flips on combat start/end (the phase's demo).

**VALIDATION:**
- Run standard checks.
- NEW `dm-api/tests/test_combat_override_and_mode.py`: start combat → session `current_mode == "combat"`; end → restored. **Restore case:** PATCH session to `social`, start combat → `combat`, end combat → `social` (not exploration); null-`previous_mode` fallback → `exploration`. Consume the turn's action, resubmit without override → 409; with `override=dm_fiat` → 200 and combat_log contains the override entry; `override` with a bogus target id → still 404/409 (integrity not bypassable).
- Assert both `combat.py` and `combat_actions.py` are < 400 LoC (`wc -l`).
- Manual: stack up; set mode to Social; start combat → pill flips to COMBAT automatically; end → flips back to SOCIAL. Tear down.

---

## Phase 7 — World-context locality retrieval (AI sees the *relevant* world, not the oldest 20 rows)

**Requires:** Phases 1 (status), 4 (quests), 5 (mode). **Serves:** Req 2's AI-facing half — the gap analysis's biggest scale-fidelity failure.
**Goal:** Replace oldest-first truncation in the AI DM's per-turn context with locality/recency ranking: current location's ancestors+children, recently-interacted active characters, and active quests, plus current mode.

**Changes:**
1. `dm-api/src/dm_api/db/models/character.py`: add `last_interacted_at: Mapped[datetime | None]` column (mirrors the existing unused `Location.last_visited_at`). NEW migration `dm-api/alembic/versions/0008_character_last_interacted.py`.
2. Write-throughs: set `last_interacted_at = now()` on Character PATCH (`characters.py`), on enrollment in combat (`combat.py` `start_combat`), and on combat-end write-back (`combat_utils.py`). Set `Location.last_visited_at = now()` when a session's `current_location_id` changes (`sessions.py` PATCH path).
3. `dm-api/src/dm_api/api/sessions.py` world-context builder (lines ~130-176): replace the flat `_WORLD_ENTITY_LIMIT` oldest-first slices with ranked selection, still capped at 20 each: locations = current location + its ancestors (walk `parent_id` upward — **cycle-safe**: track a `visited: set[uuid.UUID]` and stop the walk if a node repeats, so a malformed cyclic hierarchy can never infinite-loop the context builder; Phase 2's create/update validation rejects cycles going forward, but pre-existing data must not hang the AI turn) + its direct children, then most-recent `last_visited_at`, `status == ACTIVE` first; characters = `status == ACTIVE` ordered by `last_interacted_at desc nulls last`; add `active_quests` (top 10 ACTIVE by `updated_at`) and `current_mode`. If the context-builder logic pushes `sessions.py` past 400 LoC, extract it to NEW `dm-api/src/dm_api/api/world_context.py`.
4. Extend the typed `WorldContext` dataclass consumed by `build_system_prompt` with `active_quests: list[QuestSummary]` (new small frozen dataclass: `name`, `summary`, `status`) and `current_mode: GameMode`.
5. `dm-api/src/dm_api/ai/prompts/system_prompt.py`: render active quests and current mode into the prompt; add one instruction line to bias narration/proposal types by mode (e.g. no COMBAT_ACTION proposals during DOWNTIME).

**Data-model / migration:** one nullable column (`0008`).
**API contract:** none external (internal context shape changes).
**UI:** none.

**VALIDATION:**
- Run standard checks.
- NEW `dm-api/tests/test_world_context_ranking.py`: seed 30 characters where #25 has a recent `last_interacted_at` and #1 is ARCHIVED → context includes #25, excludes the ARCHIVED one; seed nested locations with a current ROOM → its parent BUILDING and TOWN are included ahead of unrelated old locations; active quest appears; completed quest does not; a manually-seeded cyclic `parent_id` chain → context builder returns (visited-set) instead of hanging.
- Manual: stack up; with >20 NPCs, chat about the current location → AI references a locally relevant NPC that oldest-first truncation would have dropped. Tear down.

---

## Phase 8 — Player chat channel: data, API, and player composer

**Requires:** nothing structural. **Serves:** Req 3 (players have their own chat).
**Goal:** Players get a real composer that submits drafts to a channel separate from main chat (never sent to the AI); the DM's promote flow lands in Phase 9.

**Changes:**
1. `game-engine/src/game_engine/types/enums/_app.py`: add `PLAYER = "player"` to `ChatRole`; add `class PlayerDraftStatus(str, Enum)`: `PENDING = "pending"`, `PROMOTED = "promoted"`, `DISCARDED = "discarded"`. Export per convention.
2. NEW `dm-api/src/dm_api/db/models/player_draft.py`: `PlayerDraft` model — `id`, `session_id FK`, `display_name: str` (v1 identity = client-supplied display name; explicitly not accounts — record this decision in the module docstring), `content: Text`, `status: PlayerDraftStatus` (enum column with `values_callable=lambda e: [m.value for m in e]`, `server_default="pending"`), `created_at`. Plus `PlayerDraftCreate(display_name, content)` / `PlayerDraftRead` schemas.
3. NEW migration `dm-api/alembic/versions/0009_player_drafts.py`: `player_draft_status` enum + `player_drafts` table + `ALTER TYPE chat_role ADD VALUE 'player'` (note: `ADD VALUE` must run outside a transaction block — use `op.execute` with autocommit, or a separate `op.get_bind().execution_options(isolation_level="AUTOCOMMIT")` step).
4. NEW `dm-api/src/dm_api/api/player_chat.py` router (wire into `router.py`):
   - `POST /sessions/{id}/chat/player-draft` — **not** `require_dm`; creates a PENDING draft; does **not** invoke `DMOrchestrator`; broadcasts new WS event `player_draft_ready` `{draft_id, session_id, status}`.
   - `GET /sessions/{id}/chat/player-drafts?status=` — DM sees all; player callers get drafts matching their `display_name` query param. **Trust model — state this explicitly in the router docstring:** `display_name` is client-supplied and unauthenticated (all players share the anonymous PLAYER role), so this filter is a *convenience scoping*, NOT an access control — any player who guesses another player's display name can list their PENDING drafts. Draft confidentiality between players is explicitly out of scope for v1 (trusted-table assumption); if it's ever needed, it requires real per-player identity, not a query-param filter.
5. `dm-api/src/dm_api/api/ws.py`: add `player_draft_ready` to the documented event set.
6. UI: `dm-ui/src/api/client.ts` add `submitPlayerDraft`, `listPlayerDrafts` + types; `dm-ui/src/api/ws.ts` add `player_draft_ready` to the `WsEvent` union (handler refetches drafts); `dm-ui/src/store/gameStore.ts` add `playerDrafts: PlayerDraftData[]` slice + `'player'` to the `ChatMessage` role union; map in `mappers.ts`.
7. NEW `dm-ui/src/components/PlayerChat/PlayerChat.tsx` (< 400 LoC): for non-DM users, replaces the static "you're watching" notice (`DMDashboard.tsx:462-474`) — a display-name field (persisted to localStorage), a composer, and the player's own draft list with PENDING/PROMOTED/DISCARDED badges.

**Data-model / migration:** enum + table + chat_role value (`0009`).
**API contract:** two new routes; `player_draft_ready` WS event. Draft listing by `display_name` is convenience filtering, not authorization (documented).
**UI:** player composer + own-draft list.

**VALIDATION:**
- Run standard checks.
- NEW `dm-api/tests/test_player_chat.py`: draft submitted without DM token → 200, status PENDING, no AI ChatMessage created; DM lists all drafts; player list filtered by display_name — with a test comment noting this asserts the *filter behavior only*, not confidentiality (any display_name value is accepted; that is the documented v1 trust model).
- Manual: stack up; player tab (no DM token) submits a draft → appears in their list as Pending; DM tab sees it via `GET .../player-drafts`. Tear down.

---

## Phase 9 — Promote player message into main chat + DM review UI

**Requires:** Phase 8. **Serves:** Req 3 (one-click approve into main chat).
**Goal:** The DM sees pending drafts as cards and one-click promotes into the main transcript as a `player`-role message everyone sees.

**Changes:**
1. `dm-api/src/dm_api/api/player_chat.py`: add `POST /sessions/{id}/chat/player-draft/{draft_id}/promote` (`require_dm`) — 409 unless draft is PENDING; writes `ChatMessage(role=ChatRole.PLAYER, content=f"{draft.display_name}: {draft.content}")` into main chat; sets draft `PROMOTED`; broadcasts a normal `chat_message` WS event + a `player_draft_ready` update. Add `POST .../discard` (`require_dm`) → `DISCARDED`. Mirrors the Proposal accept/reject shape in `ai.py:171-281`.
2. `dm-ui/src/api/client.ts`: add `promotePlayerDraft`, `discardPlayerDraft`.
3. NEW `dm-ui/src/components/PlayerDraftCard/PlayerDraftCard.tsx` (< 400 LoC): props `{ draft: PlayerDraftData }`; shows display_name + content + "Send to main chat" / "Discard" buttons. Rendered as a "Player messages (N)" list in `DMDashboard.tsx`'s right rail above Proposals (one mount block).
4. Chat rendering: in `DMDashboard.tsx`'s role-color map (lines 17-27) add a distinct background for role `'player'`; player messages render through `ChatMarkdown.tsx` like DM messages.

**Data-model / migration:** none.
**API contract:** promote + discard routes; `chat_message` events may now carry `role: "player"`.
**UI:** DM draft cards; player-styled messages in the transcript.

**VALIDATION:**
- Run standard checks.
- Extend `dm-api/tests/test_player_chat.py`: promote → ChatMessage with role `player` in `GET /sessions/{id}/messages`, draft PROMOTED; promote again → 409; discard → DISCARDED, no main-chat write; promote without DM token → 403.
- Manual: two tabs; player submits draft → DM card appears; DM clicks "Send to main chat" → message lands in both transcripts with player styling; discard a second draft → never appears in main chat. Tear down.

---

## Phase 10 — Proposal modify + re-request: typed edits, MODIFIED status, reviser sub-agent (data + API)

**Requires:** Phase 4 (QuestProposalEdit references quests; also add `ProposalType.QUEST` here). **Serves:** Req 3 (approve / modify / re-request).
**Goal:** Make `ProposalStatus.MODIFIED` real, replace the untyped modifications dict, add quest proposals, and add an AI re-request path — backend only (UI in Phase 11).

**Changes:**
1. `game-engine/src/game_engine/types/enums/_app.py`: add `QUEST = "quest"` to `ProposalType`. Export already covered. Note: `system_prompt.py` derives its proposal-type token list automatically from the enum (`_PROPOSAL_TYPES = "|".join(pt.value for pt in ProposalType)`, system_prompt.py:29), so adding the enum member is sufficient to put `quest` in the prompt's type list — do NOT hand-edit any enumerated type string there.
2. `dm-api/src/dm_api/db/models/proposal.py`: replace `ProposalAccept.modifications: dict[str, Any] | None` with `modifications: LocationProposalEdit | CharacterProposalEdit | QuestProposalEdit | None` — three NEW Pydantic models in the same file (all-optional fields matching each proposal type's known content shape: e.g. `LocationProposalEdit(name, description, location_type)`), discriminated against `proposal.type` in the handler. Add `superseded_proposal_id: Mapped[uuid.UUID | None]` self-FK column to `Proposal` + expose on `ProposalRead`.
3. NEW migration `dm-api/alembic/versions/0010_proposal_supersede.py`: add `proposals.superseded_proposal_id` self-FK + `ALTER TYPE proposal_type ADD VALUE 'quest'` (same autocommit note as Phase 8).
4. `dm-api/src/dm_api/api/ai.py` `accept_proposal`: validate the edit model matches `proposal.type` (422 otherwise). **Merge semantics (the current code dict-spreads at ai.py:196 — a Pydantic model is not spreadable and a naive `model_dump()` would clobber real content values with `None`s):** compute `edits = payload.modifications.model_dump(exclude_unset=True)` (fields the DM never set are omitted entirely) and merge via `proposal.content = {**content, **edits}`. When `edits` is empty (DM sent an edit object with no fields set, or no `modifications` at all) the content is unchanged and `status = ProposalStatus.ACCEPTED`; when `edits` is non-empty set `status = ProposalStatus.MODIFIED`. Add `_create_quest_from_proposal` so `ProposalType.QUEST` materializes a `Quest` row (alongside the existing LOCATION/CHARACTER branches at ai.py:201-204).
5. `dm-api/src/dm_api/ai/prompts/system_prompt.py`: update the prose guidance around lines 144-145 — which currently instructs that only *location* and *character* proposals create entities — to state that quest proposals also create entities on acceptance (the type token list itself needs no edit per step 1).
6. NEW `dm-api/src/dm_api/ai/prompts/re_request_prompt.py` (< 60 lines): input = original proposal JSON + DM feedback; output = strict JSON matching the proposal-content schema for that type.
7. NEW `dm-api/src/dm_api/ai/proposal_reviser.py`: `ProposalReviser` sub-agent (sibling of `ContextCondenser`) — typed input dataclass `RevisionRequest(proposal_type, original_content, dm_feedback)`, typed validated output, `generation_model` from `EffectiveGameConfig`, graceful `None` on malformed AI JSON.
8. `dm-api/src/dm_api/api/ai.py`: add `POST /ai/proposals/{id}/re-request` (`require_dm`, body requires `dm_notes: str`): 409 unless PENDING; marks original `REJECTED`; calls `ProposalReviser`; on success inserts a new PENDING proposal with `superseded_proposal_id` = original and broadcasts `proposal_ready`; on reviser failure returns 502 leaving the original REJECTED with its notes.

**Data-model / migration:** one column + one enum value (`0010`).
**API contract:** accept body takes typed edits and may return MODIFIED; NEW `POST /ai/proposals/{id}/re-request`; QUEST proposals materialize Quest rows on accept.
**UI:** none this phase.

**VALIDATION:**
- Run standard checks.
- NEW `dm-api/tests/test_proposal_modify_rerequest.py` (mock the backend): accept with edits → status MODIFIED, created entity reflects edited name; accept with an edit object that sets only `name` → other content fields (e.g. description) unchanged, NOT nulled; accept without edits (or an all-unset edit object) → ACCEPTED, content byte-identical; edit model mismatching type → 422; re-request → original REJECTED, new PENDING with `superseded_proposal_id`; accept a QUEST proposal → Quest row exists.
- Manual: curl-accept a proposal with a name edit → GET shows MODIFIED and the entity has the edited name. Tear down.

---

## Phase 11 — Proposal review UI: inline edit form, re-request button, lineage

**Requires:** Phase 10. **Serves:** Req 3.
**Goal:** Turn the read-only proposal card into an editable review surface with a third "Re-request" action.

**Changes:**
1. `dm-ui/src/api/client.ts`: add `reRequestProposal(id, dmNotes)`; type `acceptProposal`'s body to carry the per-type edit object (send ONLY the fields the DM actually changed, matching the server's `exclude_unset` merge semantics — do not send untouched fields).
2. `dm-ui/src/components/ProposalCard/ProposalCard.tsx` (223 LoC — room to grow; split out a `ProposalEditForm.tsx` sibling if it approaches 400): render the known editable fields per proposal type (`location`: name/description/type; `character`: name/race/class/level/hp/ac; `quest`: name/summary) as controlled inputs pre-filled from `content`; "Accept" sends changed fields as `modifications` (MODIFIED badge already renders); add "Re-request with feedback" button that requires the notes textarea to be non-empty and calls `reRequestProposal`; when `superseded_proposal_id` is set, show a "↻ revision of…" link line referencing the prior proposal.

**Data-model / migration:** none. **API contract:** consumes Phase 10.
**UI:** editable proposal card + re-request + lineage.

**VALIDATION:**
- Run dm-ui standard checks.
- Manual: stack up; trigger an AI turn proposing a location; edit its name, Accept → entity created with edited name, card shows Modified; on another proposal click Re-request with feedback → new pending proposal appears chained to the old. Tear down.

---

## Phase 12 — Spatial types + typed MapLayout schema on Location & CombatState

**Requires:** nothing structural. **Serves:** Req 4 (room boundaries, doors, obstacles) — foundation only.
**Goal:** Give the stack a typed, opt-in spatial vocabulary and retire the dead `map_data: dict[str, Any]`. Purely descriptive — no distance math wired into combat resolution (theater-of-mind keeps working).

**Scope decision (explicit):** doors are **positional-only visual markers** in v1. `Door.is_open` is authored/generated data that affects rendering only; there is NO open/close interaction endpoint and closed doors do NOT constrain movement or line-of-sight (nothing does — the map is positional, not adjudicated). This is a deliberate match to the "positional, not artful / theater-of-mind" scope, recorded here so the verbatim "doors" requirement is consciously partially-scoped rather than silently half-delivered. A door-toggle endpoint is a natural follow-up if playtests want it.

**Changes:**
1. NEW `game-engine/src/game_engine/types/spatial.py`: frozen dataclasses — `GridCoordinate(x: int, y: int)`; `class TerrainType(str, Enum)`: `FLOOR`, `WALL`, `DIFFICULT`, `WATER`, `VOID`; `WallSegment(start: GridCoordinate, end: GridCoordinate)`; `Door(position: GridCoordinate, is_open: bool)`; `MapLayout(width: int, height: int, walls: list[WallSegment], doors: list[Door], obstacles: list[GridCoordinate])`. Export via `game_engine.types` (`__init__.py` import + `__all__`).
2. NEW `dm-api/src/dm_api/db/models/map_schema.py`: Pydantic `MapLayoutSchema` (+ nested `WallSegmentSchema`/`DoorSchema`/`CoordSchema`) mirroring the engine dataclasses, with `to_engine()`/`from_engine()` converters. This is the serialization boundary — DB columns stay JSON, but the API surface is typed.
3. `dm-api/src/dm_api/db/models/location.py`: change `map_data` typing on `LocationCreate`/`LocationRead`/`LocationUpdate` from `dict[str, Any] | None` to `MapLayoutSchema | None` (SA column unchanged).
4. `dm-api/src/dm_api/db/models/combat.py`: add `map_layout` nullable JSON column to `CombatState`; add `map_layout: MapLayoutSchema | None` to the combat read/response schema.
5. NEW migration `dm-api/alembic/versions/0011_combat_map_layout.py`: `op.add_column('combat_states', sa.Column('map_layout', sa.JSON(), nullable=True))`.

**Data-model / migration:** one nullable column (`0011`); `map_data` API typing tightened (breaking for arbitrary dicts — intentional; the column had no writers).
**API contract:** Location `map_data` and CombatState `map_layout` validate against `MapLayoutSchema`; malformed → 422.
**UI:** none this phase.

**VALIDATION:**
- Run standard checks.
- NEW `game-engine/tests/test_spatial.py`: construct `MapLayout`; assert frozen (mutation raises); round-trip through the dm-api schema converters. NEW `dm-api/tests/test_map_schema.py`: create a location with a valid layout → GET returns structure; malformed layout → 422.
- Manual: curl-create a location with a 12×8 layout including one wall and one door; GET it back typed. Tear down.

---

## Phase 13 — Map generation sub-agent + seamless combat map entry/exit

**Requires:** Phases 5, 6 (mode + broadcasts + prior-mode restore), 12 (schema). **Serves:** Req 4 (pull up or generate combat maps, seamlessly).
**Goal:** Starting combat loads the location's authored map or generates one (positions-only, not artful) via a Haiku sub-agent, persists it on `CombatState`, and the UI auto-shows the rendered geometry; ending combat cleans up tokens and signals the scene transition. (Reminder: per Phase 12's scope decision, doors are rendered visual markers only — no interaction.)

**Changes:**
1. NEW `dm-api/src/dm_api/ai/prompts/map_gen_prompt.py` (< 60 lines): input = location name + description + max dimension; output = strict JSON matching `MapLayoutSchema` — room boundaries as walls, doors, obstacles; positional only.
2. NEW `dm-api/src/dm_api/ai/map_generator.py`: `MapGenerator` service — typed input `MapGenRequest(name: str, description: str, max_dim: int = 20)`, typed output `MapLayoutSchema`, boundary-validated; on malformed AI JSON or backend error, degrade gracefully to a blank 10×10 floor grid (combat must never fail to start because of map generation). Uses `generation_model` from `EffectiveGameConfig`.
3. `dm-api/src/dm_api/api/combat.py` `start_combat`: if `location_id` is present — use `location.map_data` when set, else call `MapGenerator` with the location's name/description; persist to `CombatState.map_layout`; include in the response and `combat_update` broadcast. `end_combat`: broadcast a NEW WS event `scene_transition` `{session_id, from_mode: "combat", to_mode: <the mode actually restored>}` (add to `ws.py`'s documented set) after the Phase 6 mode restore — `to_mode` is the value of `session.current_mode` after the restore (i.e. the pre-combat mode, or `exploration` only when `previous_mode` was null). Do NOT hardcode the literal `"exploration"`. If this pushes `combat.py` toward 400 LoC, move `start_combat`'s map-resolution logic into a helper in `combat_utils.py` (or a NEW `dm-api/src/dm_api/api/combat_maps.py`) — every touched file stays < 400 LoC.
4. UI: `dm-ui/src/store/gameStore.ts` add `mapLayout` to the `ActiveCombat` slice; map it in `mappers.ts` `mapCombatResponse`; `dm-ui/src/api/ws.ts` add `scene_transition` (with its `to_mode` field) to the `WsEvent` union — handler clears `tokenPositions` (currently persisted indefinitely at gameStore.ts:173).
5. `dm-ui/src/components/BattleMap/BattleMap.tsx`: replace the hardcoded `COLS=10, ROWS=10` with `mapLayout.width/height` (fallback to 10×10 when null); draw walls as Konva `Line`s, doors as small colored rects (open = green outline, closed = brown fill — display only, no click handler per the Phase 12 scope decision), obstacle cells as gray rects under the tokens.
6. `dm-ui/src/components/DMDashboard/DMDashboard.tsx`: auto-show the map when `mode === 'combat'` (initialize the existing `showMap` state from mode, keep the manual toggle as an override), auto-hide on `scene_transition`.

**Data-model / migration:** none (uses Phase 12 column).
**API contract:** `POST /sessions/{id}/combat` response + `combat_update` include `map_layout`; NEW `scene_transition` WS event whose `to_mode` reflects the restored pre-combat mode.
**UI:** real geometry rendered; map auto-appears on combat start and clears on end.

**VALIDATION:**
- Run standard checks.
- NEW `dm-api/tests/test_map_generator.py` (mock backend): valid JSON → typed schema; malformed → blank-grid fallback, no raise; start combat with a location → `CombatState.map_layout` non-null; location with authored `map_data` → used verbatim, no AI call; combat started from SOCIAL → `scene_transition.to_mode == "social"`.
- Manual: stack up; from Exploration start combat in a described location → map auto-opens with walls/doors/obstacles and pill flips to COMBAT; end combat → map hides, pill reverts, stale token positions cleared. Tear down.

---

## Phase 14 — Square selection + full action set + DM override button

**Requires:** Phase 13 (rendered map), Phase 6 (override API). **Serves:** Reqs 5 & 6 (DM-side interaction; player-side lands in Phase 15).
**Goal:** Click a square to select it; the action panel covers the full `ActionType` enum from a config table; when the engine 409s, the DM gets an Override button that resubmits with `OverrideReason`.

**Changes:**
1. `dm-ui/src/components/BattleMap/BattleMap.tsx`: add `selectedCell: {x: number, y: number} | null` state; click handler on empty grid cells sets it (click again or Escape clears); render a highlight rect on the selected cell; new prop `onCellSelect?: (cell: {x: number; y: number} | null) => void` so CombatTracker can consume the selection. Keep the coordinate shape matching `GridCoordinate` (named `x`/`y` ints).
2. NEW `dm-ui/src/components/CombatTracker/actionConfig.ts`: a typed config table `ACTION_CONFIG: { action: string; label: string; needsTarget: boolean; isBonusEligible: boolean }[]` covering the full 2024 list — Attack, Dash, Dodge, Disengage, Help, Hide, Influence, Magic, Ready, Search, Study, Utilize — matching `ActionType` values in `game-engine/src/game_engine/types/enums/_combat.py:12-26`.
3. `dm-ui/src/components/CombatTracker/CombatTracker.tsx`: replace the hardcoded 3-button set (lines 79-83) with buttons generated from `actionConfig.ts`; keep the existing target pill-list for `needsTarget` actions, and when a map token sits on the selected cell, pre-select that combatant as target (map-assisted targeting; server-side range checks are out of scope until distances are engine-computed).
4. Override UI: when `submitAction` returns 409, render the existing inline error plus a DM-only "Override (DM fiat)" button that resubmits the identical request with `override: 'dm_fiat'` (Phase 6 API). Show the override entry from the returned combat_log as the synthetic system chat message.
5. If `CombatTracker.tsx` (currently ~650 LoC, already over guideline) grows, extract `StartCombatDialog` into NEW `dm-ui/src/components/CombatTracker/StartCombatDialog.tsx` as part of this phase to get both files under 400 LoC.

**Data-model / migration:** none. **API contract:** consumes Phase 6.
**UI:** square selection + highlight; 12-action panel; override button.

**VALIDATION:**
- Run dm-ui standard checks.
- Manual: start combat; click an empty square → highlight; click a token's square → that combatant pre-selected as Attack target; run Attack → resolves; use the same combatant's action twice → 409 with an Override button; click Override → succeeds and the log line notes the override; run Disengage/Hide/Dodge from the new buttons → each resolves through the engine. Tear down.

---

## Phase 15 — Player turns: PC claim, player-submit endpoint, player end-turn, DM undo, player action panel

**Requires:** Phase 8 (display_name identity), Phase 14 (action panel + square selection). **Serves:** Req 5's core promise — *player* selects square + action; engine approves **unless the DM overrides**; the turn flow is player-driven. This is core, not stretch.
**Goal:** A player claims a PC by display name, and on that PC's turn can submit actions through a non-DM endpoint that the engine adjudicates; illegal actions are rejected for players (no bypass); the player can end their own turn; and the DM gets a real reversal lever over player-committed actions (undo-last), delivering the "unless the DM overrides" clause of Req 5 on the player path.

**Trust model (state this in `pc_claim.py`'s module docstring and here):** v1 player identity is the honor system. Auth is a single shared DM token; all players share the anonymous PLAYER role, and `display_name` is arbitrary client input with first-come claims — so any player at the table *can* echo another player's display_name and act as their PC. This is a **conscious scope decision** for a trusted table, not an oversight: the "engine adjudicates the right player" guarantee is against accidents (acting out of turn, acting as an unclaimed PC), not against a malicious tablemate. The named future hardening is a per-claim secret token returned by `POST /claim` and required on submit — out of scope for v1.

**Changes:**
1. NEW `dm-api/src/dm_api/db/models/pc_claim.py` (per typed-boundary rule, a small table, not a JSON blob on session): `PcClaim(id, session_id FK, character_id FK, display_name: str, created_at)` with a unique constraint on `(session_id, character_id)`; `PcClaimCreate`/`PcClaimRead` schemas; module docstring records the honor-system trust model above. NEW migration `dm-api/alembic/versions/0012_pc_claims.py` — this migration ALSO adds a nullable JSON column `combat_states.last_player_action_snapshot` (used by the undo path in step 4).
2. NEW `dm-api/src/dm_api/api/pc_claims.py`: `POST /sessions/{id}/claim` (not `require_dm`; body `{character_id, display_name}`; 409 if the PC is already claimed by a different name; only `CharacterType.PC` claimable) and `GET /sessions/{id}/claims`. `DELETE /sessions/{id}/claim/{character_id}` is `require_dm` (DM can evict). Wire into `router.py`.
3. NEW `dm-api/src/dm_api/api/combat_player.py` (combat.py is at the 400-LoC line even after Phase 6's extraction — the player path gets its own module, wired into `router.py`): `POST /sessions/{id}/combat/action/submit` — **not** `require_dm`. Body is a NEW dedicated schema `PlayerCombatActionSubmit` (defined in `dm-api/src/dm_api/db/models/combat.py` next to `CombatActionRequest`): the same action fields as `CombatActionRequest` (action type, target, etc.) **plus** `display_name: str`, with **no** `override` field and `model_config = ConfigDict(extra="forbid")` so a client that sends `override` (or any unknown field) gets a 422 — Pydantic silently ignores unknown fields by default, so `extra="forbid"` is what makes the rejection real. Do not reuse the DM's `CombatActionRequest`. Handler: validates the claim table maps `display_name` → the current-turn combatant's character id (403 otherwise, 409 if not that PC's turn); **snapshots the pre-action state** — deep-copy `combat.combatants` + turn fields (`current_turn_index`, `round_number`) into `combat.last_player_action_snapshot` — then runs the exact same `DnD55eEngine.resolve_action` path as the DM endpoint. Engine success commits and broadcasts `combat_update`; engine rejection → 409, never bypassable by players.
4. **DM override of player actions (the second clause of Req 5 — not deferred):** in `combat_player.py`, add `POST /sessions/{id}/combat/undo-last-player-action` (`require_dm`) — 409 if `last_player_action_snapshot` is null; otherwise restores `combat.combatants` + turn fields from the snapshot, clears the snapshot (single-level undo — one player action deep, by design), appends a combat_log audit entry `{event: "dm_undo", reason: OverrideReason}` (reuse Phase 6's `OverrideReason` enum in the request body), commits, and broadcasts `combat_update`. Each new player submit overwrites the snapshot, so the DM's undo window is "since the last player action" — exactly the moment Req 5's override clause covers. (A full multi-action pending-approval queue mirroring the Proposal PENDING pattern remains future work, but the DM is never without a reversal lever over a player-committed action.)
5. **Player end-turn (the turn flow must not dead-end):** the existing `next_turn` endpoint (combat.py:267) is `require_dm`, so without this the DM would have to click next-turn after every player action. Add `POST /sessions/{id}/combat/next-turn/submit` in `combat_player.py` — **not** `require_dm`; body `{display_name: str}` (same `extra="forbid"` discipline); 403 unless the claim table maps `display_name` to the **current-turn** combatant's character; then runs the same advance logic as the DM `next_turn` (extract that logic into a shared helper in `combat_utils.py` so the two endpoints don't duplicate it) and broadcasts `combat_update`. The DM's `next-turn` remains for NPC/monster turns and as a fallback.
6. UI: `dm-ui/src/api/client.ts` add `claimPc`, `listPcClaims`, `submitPlayerAction`, `submitPlayerEndTurn`, `undoLastPlayerAction`. NEW `dm-ui/src/components/CombatTracker/PlayerActionPanel.tsx` (< 400 LoC): rendered for non-DM users; a "Claim your character" PC dropdown (uses the Phase 8 display name); when `combat.combatants[current_turn_index]` is the claimed PC, shows the Phase 14 action buttons (reusing `actionConfig.ts` and BattleMap square selection) submitting via `submitPlayerAction`, plus an "End turn" button calling `submitPlayerEndTurn`; otherwise shows "Waiting — it's {name}'s turn". Mount in `CombatTracker.tsx`'s non-DM render path. DM side: in `CombatTracker.tsx`'s DM render path, show a small "Undo last player action" button whenever the latest combat_log entry came from a player submit (enabled state can simply be optimistic — the endpoint 409s harmlessly when there's nothing to undo), with an `OverrideReason` picker defaulting to `dm_fiat`.
7. DM oversight summary (how Req 5's "engine approves unless the DM overrides" is fully delivered on the player path): engine adjudication is the auto-approval default (Req 6); the DM's reversal lever over an already-committed player action is step 4's undo; the DM's forward-forcing lever remains Phase 6/14's `override` on the DM path; heal/stabilize fiat endpoints remain for narrative correction.

**Data-model / migration:** `pc_claims` table + `combat_states.last_player_action_snapshot` JSON column (`0012`).
**API contract:** claim CRUD; NEW `POST /sessions/{id}/combat/action/submit` (server-authoritative player path — not client-side gating; `override` in the body → 422); NEW `POST /sessions/{id}/combat/next-turn/submit` (current-turn claimant only); NEW `POST /sessions/{id}/combat/undo-last-player-action` (`require_dm`).
**UI:** player claim dropdown + turn-gated action panel with End turn; DM undo button.

**VALIDATION:**
- Run standard checks.
- NEW `dm-api/tests/test_player_combat_submit.py`: claim a PC; on its turn, submit legal action without DM token → 200, state mutates; submit for an unclaimed/other PC → 403; not your turn → 409; illegal action (double action) → 409; request body containing `override` → 422 (`extra="forbid"`); second claim of same PC by another name → 409; player end-turn by the current-turn claimant → turn advances; end-turn by a non-claimant → 403; after a player action, DM undo → combatants + turn fields match the pre-action snapshot and combat_log has the `dm_undo` audit entry; undo again → 409 (single-level); undo without DM token → 403.
- Assert `combat_player.py` < 400 LoC.
- Manual: two browsers; player claims a PC; DM starts combat; on the PC's turn the player clicks a square, picks Attack, picks target → resolves in both browsers; player clicks End turn → initiative advances without DM input; player tries acting on the monster's turn → blocked; DM clicks "Undo last player action" after a player attack → HP and turn state revert in both browsers; DM overrides an engine rejection on their own path → works. Tear down.

---

## Phase 16 — [STRETCH] Non-combat skill-check endpoint (engine enforcement outside combat)

**Requires:** Phase 5 (mode context), Phase 6 (OverrideReason). **Serves:** Req 6 beyond combat.
**Goal:** "Engine enforces, DM overrides" applies to exploration/social/downtime via a typed check endpoint that posts mechanical results to chat so the AI doesn't confabulate.

**Changes:**
1. game-engine: **no new code needed — the entrypoint already exists.** `DnD55eEngine.resolve_check` (`game-engine/src/game_engine/rules/dnd_5_5e/engine.py:116`) already takes `(char: CharacterSheet, skill: Skill | Ability | str, dc: int, advantage: bool = False, disadvantage: bool = False)` and returns the existing `CheckResult` dataclass from `game_engine.interface` (fields: `success: bool, roll: int, total: int, dc: int, margin: int`). Do NOT create a new `CheckResult` in `game_engine.types`, do NOT invent a new signature, and do NOT wrap the method in a new module-level function — reuse what's there. The DC conversion is also already done: `TaskDifficulty` has a `.dc` property (`_core.py:246-249`, backed by `_TASK_DIFFICULTY_DCS` — VERY_EASY=5 … NEARLY_IMPOSSIBLE=30).
2. NEW `dm-api/src/dm_api/api/checks.py`: `POST /sessions/{id}/check` (`require_dm` v1) — typed request `{character_id, ability: Ability, skill: Skill | None, difficulty: TaskDifficulty}`; load the character's sheet, call `engine.resolve_check(sheet, skill if skill is not None else ability, dc=difficulty.dc)`, and return a Pydantic response mirroring the engine `CheckResult` fields (`success/roll/total/dc/margin`); write a SYSTEM ChatMessage with the mechanical outcome and broadcast `chat_message`. Wire into `router.py`.
3. UI: a small "Request Check" button next to the ModeIndicator opening a 4-field form (character, ability, skill, difficulty); result lands in chat.

**VALIDATION:** game-engine already tests `resolve_check`; add a dm-api test that the endpoint maps `TaskDifficulty.HARD` to `dc == 20` in the result and posts a SYSTEM message; manual roll via UI shows in transcript. Tear down.

---

## Phase 17 — [STRETCH, Req-1 group] Campaign-notes path config + allow-listing

**Requires:** nothing structural. **Serves:** Req 1 foundation (safe filesystem access).
**Goal:** A per-world campaign-notes directory, validated against an operator allow-list root — the security prerequisite for ingestion.

**Changes:**
1. `dm-api/src/dm_api/config.py`: add `campaign_notes_root: str | None = None` Settings field (operator-configured; ingestion disabled when unset).
2. `dm-api/src/dm_api/db/models/game_config.py`: add nullable `campaign_notes_path: str | None` to `GameConfig`/`GameConfigUpdate`/`EffectiveGameConfig` + `resolve_game_config()`. Server-side validator: `Path(path).resolve()` must be under `Path(campaign_notes_root).resolve()` (reject traversal with 400).
3. NEW migration `dm-api/alembic/versions/0013_campaign_notes_path.py`.
4. Expose via existing `GET/PUT /api/worlds/{world_id}/config` (`worlds.py`); add the field to `dm-ui/src/components/GameSettings/GameSettingsModal.tsx`.
5. `docker-compose.yml`: add a commented, documented read-only volume-mount pattern for the notes root into the `api` service.

**VALIDATION:** dm-api tests: path under root accepted; `../etc` rejected 400; unset root → any path rejected. Manual: set a valid path in Game Settings → persists; traversal path → error. Tear down.

---

## Phase 18 — [STRETCH, Req-1 group] Campaign-notes ingestion → proposal batch

**Requires:** Phases 4 & 10 (quests + QUEST proposals + typed edits), 17 (validated path). **Serves:** Req 1 payoff.
**Goal:** Point the system at a notes folder and get a deduplicated batch of PENDING LOCATION/CHARACTER/QUEST proposals flowing through the existing DM-approval loop — idempotent on re-run.

**Changes:**
1. NEW `dm-api/src/dm_api/ai/ingest/__init__.py` + typed dataclasses: `CampaignNoteFile(relative_path: str, content: str)`, `IngestedWorldDraft(locations: list[...], characters: list[...], quests: list[...])` — boundary-validated like `ProposalPayload`.
2. NEW `dm-api/src/dm_api/ai/prompts/ingest_prompt.py` (< 60 lines): one job — per-file entity extraction to strict JSON.
3. NEW `dm-api/src/dm_api/ai/campaign_ingestor.py`: `CampaignIngestor` — depth-first `read files (*.md/*.txt under the validated path) → per-file Haiku extraction → validate → assemble` → emit PENDING `Proposal` rows. Dedup by case-insensitive name against existing world Characters/Locations/Quests before emitting (pre-empts PT-22 at bulk scale).
4. Idempotency: NEW `dm-api/db/models/ingested_file.py` — `IngestedFile(world_id, relative_path, content_hash, ingested_at)` with unique `(world_id, relative_path)`; skip unchanged hashes on re-run. NEW migration `0014_ingested_files.py`.
5. NEW `dm-api/src/dm_api/api/ingest.py`: `POST /worlds/{world_id}/ingest` (`require_dm`) → runs ingestor, returns `{files_scanned, files_skipped, proposals_created}`. Wire into `router.py`.
6. UI: "Start from folder" note in `NewSessionForm.tsx` (path is set in Game Settings; button triggers ingest) + review the resulting batch through the existing ProposalCard flow (Phase 11's edit form applies). Optional thin CLI script `scripts/ingest.sh` calling `POST /worlds` + `POST /worlds/{id}/ingest` from within a notes folder.

**VALIDATION:** dm-api test with a temp fixture dir + mocked backend: N files → N validated PENDING proposals; immediate re-run → 0 new (hash skip); name collision with existing NPC → skipped; path outside root → 400. Manual: mount a small sample folder, run ingest, accept a few proposals → real Location/Character/Quest rows appear in the WorldBrowser. Tear down.

---

## Closing notes

- **Core path (1–15) fully covers Requirements 2–7**, including the AI-facing scale fix (Phase 7), server-authoritative player turns with player end-turn and a DM undo lever (Phase 15) — neither is deferred to stretch — and role-based redaction is preserved through every endpoint rewrite (Phase 2).
- **Requirement 1 is the explicit late group (17–18)**, sequenced so ingestion lands on a complete data model (quests, statuses, typed proposal edits) rather than being bolted on early and re-proposing half the world.
- **Conscious v1 scope decisions, recorded where they live:** player identity is honor-system display names (Phases 8 & 15 — trusted-table assumption, per-claim tokens named as the hardening path); doors are positional-only visual markers with no open/close interaction (Phase 12); DM undo of player actions is single-level (Phase 15).
- **Migration numbers 0004–0014 assume this execution order**; renumber against `alembic heads` if phases are reordered.
- **UI is never dark for more than two consecutive phases** (worst stretch: 6–7 backend-only, bracketed by the Phase 5 pill and Phase 8 player composer), and every phase ends with tests + a manual click-through or curl script and a stack teardown.