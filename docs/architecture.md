# dm.ai — Architecture

## System Overview

dm.ai is composed of three deployable units and one installable Python library.

```
┌─────────────────────────────────────────────────────────────────────┐
│  dm-ui  (React 19 + Vite + react-konva, port 5173)                  │
│  DMDashboard · BattleMap · CombatTracker · LocationPanel · CharacterCard│
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTP REST  +  WebSocket
                               │ prefix: /api
┌──────────────────────────────▼──────────────────────────────────────┐
│  dm-api  (FastAPI + asyncio, port 8000)                             │
│                                                                     │
│  ┌──────────────────────┐   ┌───────────────────────────────────┐   │
│  │ REST Route Handlers  │   │ AI Layer                          │   │
│  │  /worlds             │   │  DMOrchestrator                   │   │
│  │  /sessions           │   │  AIBackend ABC                    │   │
│  │  /characters         │   │   ├─ AnthropicBackend             │   │
│  │  /locations          │   │   └─ ClaudeCLIBackend             │   │
│  │  /combat             │   │  System prompt builder            │   │
│  │  /ai (proposals)     │   └───────────────────────────────────┘   │
│  │  /ws/sessions/{id}*  │  (*mounted under the /api prefix)         │
│  └──────────────────────┘                                           │
│                                                                     │
│  ┌─────────────────────┐  ┌──────────┐  ┌──────────────────────┐   │
│  │ PostgreSQL 16       │  │  Redis   │  │   game-engine        │   │
│  │ + pgvector          │  │ pub/sub  │  │   (Python package)   │   │
│  └─────────────────────┘  └──────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                                  │
                               ┌──────────────────▼─────────────────┐
                               │  Anthropic Claude API              │
                               │  or  claude CLI (subprocess)       │
                               └────────────────────────────────────┘
```

---

## game-engine

The `game-engine` package (`game-engine/src/game_engine/`) is an installable
Python library with no FastAPI dependency. It owns all rule-system logic so the
API layer stays rule-agnostic.

### RuleEngine ABC

`game_engine.interface.RuleEngine` defines the contract every rule system must
implement:

| Method | Signature summary | Purpose |
|---|---|---|
| `roll_check` | `(char, skill/ability, dc, advantage, disadvantage) → CheckResult` | Skill / ability check |
| `roll_saving_throw` | `(char, ability, dc, advantage, disadvantage) → SaveResult` | Saving throw (condition auto-fails) |
| `apply_damage` | `(target, damage, damage_type) → CharacterSheet` | Damage with resistance calculation |
| `apply_healing` | `(target, amount) → CharacterSheet` | Healing (wakes dying characters) |
| `apply_condition` | `(target, condition, duration_rounds) → CharacterSheet` | Apply a status condition |
| `remove_condition` | `(target, condition) → CharacterSheet` | Remove a status condition |
| `tick_condition_durations` | `(target) → CharacterSheet` | Decrement timed conditions; remove expired ones |
| `get_available_actions` | `(char, combat_state) → list[Action]` | Legal actions for a character's turn |
| `resolve_action` | `(action, combat_state) → ActionResult` | Resolve and narrate an action |
| `roll_initiative` | `(char) → int` | Initiative roll |
| `validate_character` | `(sheet) → ValidationResult` | Legality check for a character sheet |
| `calculate_proficiency_bonus` | `(level) → int` | Proficiency bonus by level |

Result dataclasses (`CheckResult`, `SaveResult`, `DeathSaveResult`,
`ActionResult`, `ValidationResult`) and the `Action` dataclass are defined in
`interface.py` alongside the ABC.

### D&D 5.5e Engine

`game_engine.rules.dnd_5_5e.DnD55eEngine` is the concrete implementation of the
2024 PHB rules (see `docs/phb-parity-spec.md` for the full feature matrix). It
uses a **delegation pattern**: each method delegates to a focused private helper
module in `game_engine/rules/dnd_5_5e/` (`_checks.py`, `_saves.py`,
`_attacks.py`, `_actions.py`, `_conditions.py`, `_damage.py`, `_death.py`,
`_validation.py`). Those helpers in turn use shared utilities from
`game_engine/core/` (dice, conditions, initiative). Beyond the ABC, the engine
exposes 5.5e-specific methods (`roll_death_save`, `stabilize`, `grant_temp_hp`,
`begin_turn`, `passive_score`, `concentration_save_dc`).

Sibling service modules cover the non-combat rule systems, each independently
testable:

- `spellcasting.py` + `_spell_resolution.py` — slot tables (full/half/third/
  pact), multiclass slots, `cast_spell` with upcasting, cantrip scaling,
  rituals, and concentration
- `progression.py` — XP thresholds, `level_up`, multiclass prerequisites
- `character_builder.py` — 2024 creation steps (`build_character`, point buy,
  standard array)
- `resting.py` — short/long rests, hit dice spending, pact slot recovery
- `exploration.py` — encumbrance, jumping, falling, suffocation, travel pace,
  light levels
- `classes.py` — static class identity data (hit die, saves, proficiencies)

Data registries (SRD 5.2 content) live in `game_engine/rules/dnd_5_5e/data/`
as Python modules using enum types for all typed fields: `spells/` (per-level
modules, 100+ spells), `class_features/` (per-class level 1-20 progression
tables), `weapons.py` (full 2024 table with masteries), `armor.py`, `gear.py`,
`species.py`, `backgrounds.py`, `feats.py`, `monsters.py`. Each registry
exposes a typed lookup (`get_spell`, `get_weapon`, `get_progression`, …).

### types package

`game_engine/types/` is the single source of truth for domain types:

**Enums** (`enums/` package) — all `str, Enum` subclasses for wire-compatibility,
split into `_core` (abilities, skills, damage, conditions, magic), `_character`
(classes, species, backgrounds, languages, resources), `_subclasses` (all 52),
`_feats` (all 2024 feats), `_combat` (2024 action list, cover, rests, weapon
categories/masteries), and `_app` (locations, proposals, chat). Highlights:
- `CharacterClass` (13), `Species` (9), `Background` (16), `Subclass` (52),
  `Feat` (75, with `.category`), `Language`, `Alignment`
- `Ability`, `Skill` (with `.governing_ability`), `DamageType`, `Condition`
  (with `.prevents_action()` / `.sets_speed_to_zero()`), `TaskDifficulty`
  (with `.dc`), `LightLevel`
- `ActionType` (the twelve 2024 actions), `CoverType` (with `.ac_bonus`),
  `RestType`, `DeathSaveOutcome`, `UnarmedStrikeOption`, `WeaponCategory`,
  `WeaponMastery`, `WeaponProperty`, `ArmorCategory`
- `SpellSchool`, `SpellComponent`, `SpellRangeType`, `CastingTime`,
  `AreaShape`, `SpellcasterType`, `ClassResource`

**Dataclasses** (`sheets.py`, `character_state.py`):
- `AbilityScoreSet` — six scores with `.get()`, `.set()`, `.modifier()`, serde
- `CharacterSheet` — full 2024 character: origin (species/background/feats/
  languages), multiclass `class_levels`, hit dice pools, death saves, temp HP,
  exhaustion, spell slots, concentration, proficiencies/expertise, masteries,
  inventory, currency; `.is_alive` / `.is_dying` / `.is_dead` / `.can_act` /
  `.effective_speed` / `.d20_modifier`; serde via `_sheet_serde.py`
- `CombatStateData` — combatants + round/turn tracking + per-combatant
  `TurnState` (action economy and transient combat flags)
- `AttackDetails` — weapon stats, properties, mastery, cover, off-hand and
  unarmed options
- `ClassLevelEntry`, `HitDicePool`, `DeathSaveState`, `SpellSlotState`,
  `Currency`, `InventoryItem` — sheet sub-structures, all with serde

### Extending with a New Rule System

1. Create `game_engine/rules/<system>/` with `__init__.py` and `engine.py`
2. Subclass `RuleEngine` and implement all abstract methods
3. Register the engine in `game_engine/rules/__init__.py`
4. Add system-specific classes to `CharacterClass` (or create a new enum subclass)
5. Write tests in `game_engine/tests/test_<system>_engine.py`

---

## dm-api

`dm-api/src/dm_api/` is a FastAPI service using SQLAlchemy async (asyncpg driver)
and Alembic for migrations.

### FastAPI App

`main.py` creates the `FastAPI` instance with:
- CORS middleware allowing `settings.frontend_url`
- All routes mounted at prefix `/api` via `router.py`
- A health endpoint at `GET /health` (outside the prefix)
- Lifespan context manager (migrations run separately via Alembic)

### Database — 7 Tables

| Table | Key columns | Notes |
|---|---|---|
| `worlds` | `id`, `name`, `setting_description`, `themes` (JSON), `lore_summary`, `embedding` (vector 1536) | Root entity; cascades to everything |
| `sessions` | `id`, `world_id`, `name`, `rule_engine_version`, `player_character_ids` (JSON), `current_location_id`, `session_summary`, `started_at`, `ended_at` | One active session per DM run |
| `characters` | `id`, `world_id`, `type` (PC/NPC/MONSTER), `name`, full stat block, `embedding` (vector 1536) | Shared across sessions |
| `locations` | `id`, `world_id`, `parent_id` (self-referential), `type` (LocationType), `name`, `description`, `lore`, `map_data` (JSON), `embedding` (vector 1536) | Tree hierarchy via `parent_id` |
| `combat_states` | `id`, `session_id` (unique), `round_number`, `current_turn_index`, `initiative_order` (JSON), `combatants` (JSON), `combat_log` (JSON), `turn_states` (JSON, per-combatant action economy) | One active combat per session |
| `proposals` | `id`, `session_id`, `world_id`, `type` (ProposalType), `content` (JSON), `status` (ProposalStatus), `dm_notes` | AI-generated content awaiting DM review |
| `chat_messages` | `id`, `session_id`, `role` (dm/ai/system), `content`, `token_count`, `timestamp` | Full conversation history |

Vector columns use `pgvector.sqlalchemy.Vector(1536)` for semantic search.

### AI Backend Abstraction

`dm_api.ai.backends.base.AIBackend` is an ABC with one abstract method:

```python
async def complete(
    *,
    messages: list[AIMessage],
    system: str,
    model: str,
    max_tokens: int = 4096,
) -> AIResponse
```

Two implementations:
- **`AnthropicBackend`** — uses the Anthropic Python SDK; reads `ANTHROPIC_API_KEY`
- **`ClaudeCLIBackend`** — shells out to the `claude` CLI via subprocess; requires
  `claude` on `$PATH` (install with `npm install -g @anthropic-ai/claude-code`)

The active backend is selected at runtime by `backends/factory.py` based on
`settings.ai_provider`.

### DM Orchestrator

`dm_api.ai.DMOrchestrator` is stateless and session-scoped. Each call to
`handle_message()`:

1. **Condense** — runs `ContextCondenser.condense()` (Haiku, no-op under budget)
   to compress history that exceeds `context_token_limit`.
2. **Build messages** — converts the condensed context to `list[AIMessage]` via
   `_build_messages()`.
3. **Build system prompt** — calls `build_system_prompt(world_id, session_id)`.
4. **Call backend** — calls `backend.complete()` with the orchestrator model (Sonnet
   by default).
5. **Extract proposals** — scans the response for all `[PROPOSAL]...[/PROPOSAL]`
   JSON blocks via `_extract_proposals()` (one block per new entity).
6. **Return** a typed `DMResponse(response, proposals, was_condensed, tokens_in,
   tokens_out)` where `tokens_in/out` reflect the actual orchestrator API call.

The session route (`POST /api/sessions/{id}/chat`) persists both the DM message
and AI response to `chat_messages`, and the proposal (if any) to `proposals`,
before returning to the client.

`summarize()` uses the faster generation model (Haiku) for end-of-session summaries.

### WebSocket and Real-time Events

`/api/ws/sessions/{session_id}` maintains an in-memory connection registry
(`dict[str, list[WebSocket]]`). It serves two roles:

1. **Server-push broadcast** — HTTP endpoints call `broadcast_to_session()` after
   committing state changes so all connected clients receive live updates without
   polling.
2. **Peer relay** — messages sent by one client are forwarded to all other clients
   in the same session (e.g. cursor moves, battle-map drags).

`broadcast_to_session(session_id, event)` in `dm_api.api.ws` is the sole
server-push entry point. Dead connections are pruned silently on each call.

**Server-push event types (implemented):**

| Type | Emitted by | Payload |
|---|---|---|
| `chat_message` | `POST /sessions/{id}/chat` (DM echo immediately after persist, AI reply after the orchestrator returns) | `session_id`, `message_id`, `role` (`dm`\|`ai`), `content` |
| `proposal_ready` | `POST /sessions/{id}/chat`, `POST /ai/proposals/{id}/accept`, `POST /ai/proposals/{id}/reject` | `session_id`, `proposal_id`, `proposal_type`, `status` |
| `combat_update` | `POST /sessions/{id}/combat`, `POST /sessions/{id}/combat/action`, `POST /sessions/{id}/combat/cast-spell`, `POST /sessions/{id}/combat/heal`, `POST /sessions/{id}/combat/stabilize`, `POST /sessions/{id}/combat/next-turn`, `PUT /sessions/{id}/combat/end`, `PATCH /characters/{id}` (write-through while enrolled in an active combat) | `session_id`, `combat` (full `CombatStateRead`) |
| `entity_update` | `POST /ai/proposals/{id}/accept` (when a LOCATION or CHARACTER entity is created) | `session_id`, `entity_type`, `entity_id` |

**Peer-relayed event types (client → other clients, no server handler):**

| Type | Direction | Purpose |
|---|---|---|
| `map_token_move` | client → other clients | Battle-map token drag (`token_id`, `x`, `y`); each client also persists positions in localStorage |

**Multi-process note:** The connection registry is process-local. A multi-worker
deployment requires a shared pub/sub broker (e.g. Redis) to propagate events
across workers. See `config.py` → `redis_url` for the intended connection string.

---

## dm-ui

The frontend is a React 19 + Vite + TypeScript application with strict mode enabled.

### Component Tree

```
App                          (routes: "/" → NewSessionForm or redirect,
│                             "/session/:sessionId" → DMDashboard)
└── DMDashboard             (owns chat input/output, session hydration, layout)
    ├── aside (left)
    │   ├── LocationPanel
    │   └── CharacterCard
    ├── main
    │   ├── BattleMap        (react-konva, collapsible via "Show Map" toggle)
    │   └── (inline) Chat    (message list + input bar — lives in DMDashboard.tsx)
    └── aside (right)
        └── CombatTracker
```

### State Management — Zustand

`src/store/gameStore.ts` is the single source of truth. Key slices:
- `sessionId` / `worldId` — active session and world (persisted to
  localStorage so a refresh resumes the session)
- `messages` — chat history (`{id, role, content, timestamp}[]`), deduped by
  server-assigned message id
- `tokenPositions` — battle-map grid positions keyed by character id
  (persisted to localStorage; synced across clients via `map_token_move`)
- `isLoading` — tracks in-flight AI requests
- `addMessage` / `setMessages` / `moveToken` / `clearSession` — actions

All data shared between more than one component goes through the store. Local
`useState` is only used for purely local UI state (e.g., input field value, map
toggle).

### Battle Map — react-konva

`BattleMap` renders on an HTML5 Canvas via react-konva. Planned features:
- Grid layer with configurable cell size
- Token layer with drag-and-drop (character/monster icons)
- Fog-of-war layer (revealed cells tracked in `map_data` JSON)
- Zoom/pan with mouse wheel and drag

### API Client and WebSocket Hook

`src/api/client.ts` wraps `fetch` for REST calls. `src/api/ws.ts` exports a
WebSocket hook that connects to `/api/ws/sessions/{id}`, dispatches incoming
messages to the Zustand store, auto-reconnects after a drop, and triggers a
full session re-hydration on reconnect to catch up on missed events.

---

## Data Flow — DM Chat to World Update

```
1. DM types a message in ChatPanel → sendMessage()

2. POST /api/sessions/{id}/chat  { message: "..." }

3. dm-api saves DM ChatMessage to DB

4. dm-api: persist DM message, fetch chat history from DB, then
   DMOrchestrator.handle_message(message, history)
   ├─ ContextCondenser.condense(history)  — Haiku, no-op under budget
   ├─ _build_messages(condensed)
   ├─ build_system_prompt(world_id, session_id)
   └─ backend.complete(messages, system, model=orchestrator_model)

5. Claude returns narrative text, optionally with
   [PROPOSAL]{ "type": "location", "content": { ... } }[/PROPOSAL]

6. dm-api saves AI ChatMessage + Proposal (status=pending) to DB

7. Response { response, proposal } returned to client

8. Client displays AI message; ProposalCard shown if proposal != null

9. DM reviews → POST /api/ai/proposals/{id}/accept
   ├─ dm_notes and modifications merged into proposal.content
   ├─ proposal.status set to "accepted"
   ├─ For LOCATION/CHARACTER proposals: concrete DB record created immediately;
   │  created_entity_id written into proposal.content for citation traceability
   └─ (future) embedding indexed for RAG similarity search
```

---

## World Consistency — pgvector RAG (planned)

Three tables carry `embedding vector(1536)` columns: `worlds`, `characters`,
`locations`. The schema is in place; the RAG pipeline is not yet implemented.

Planned flow (once implemented):

1. Embed the DM's prompt using an embedding model
2. Query pgvector for nearest-neighbor lore entries
3. Inject top-k results into the system prompt as "existing world context"

This will prevent contradictions: a settlement described as coastal will remain
coastal; a character established as antagonistic will be recalled as such in later
sessions. Embeddings will be generated and indexed when proposals are accepted.

---

## Context Management — ContextCondenser

Long sessions accumulate chat history that can exhaust the model's context
window. The `ContextCondenser` (`dm_api.ai.condenser`) is a narrow
harness-engineered sub-agent (per
<https://openai.com/index/harness-engineering/>) that compresses history
before the orchestrator call.

### Flow

```
sessions.session_chat
   │
   ▼
fetch ChatMessage rows → wrap each in HistoryMessage(
                                 anchor=MessageAnchor(id, ts, role),
                                 content, token_count)
   │
   ▼
DMOrchestrator.handle_message(history=[HistoryMessage, ...])
   │
   ├── ContextCondenser.condense(...)   — Haiku, silent no-op if under budget
   │     ├─ design   — sum tokens, fast-path if <= limit
   │     ├─ extract  — split tail (preserved) + head (to-condense)
   │     ├─ validate — parse sub-agent JSON into _ParsedCondensation
   │     └─ assemble — CondensedContext(synopsis, key_facts, open_threads,
   │                                     condensed_span, preserved)
   │
   ├── build AIMessage list (condensed sections + preserved tail)
   ├── backend.complete(model=orchestrator_model)  — Sonnet
   └── _extract_proposal() — validated [PROPOSAL]...[/PROPOSAL] JSON
```

### Design properties

| Property | Implementation |
|----------|----------------|
| Typed boundaries | `HistoryMessage`, `CondensedContext`, `MessageAnchor`, `DMResponse` — no `dict[str, Any]` at the API |
| Citation anchors | `msg:<uuid>@<iso-timestamp>` (filepath:line analog), rendered into the sub-agent transcript and preserved in synopsis |
| Silent on success | Returns a pass-through `CondensedContext` with no AI call when `sum(tokens) <= limit` |
| Safe degradation | Malformed sub-agent JSON falls back to synopsis-only instead of raising |
| Fast model | Uses `generation_model` (Haiku); orchestrator keeps Sonnet for narrative |
| Depth-first | `design → extract → validate → assemble` inside `condense()` |

### Settings (`dm_api.config.Settings`)

| Setting | Default | Purpose |
|---------|---------|---------|
| `context_token_limit` | `180_000` | Trigger threshold (≈ 80% of the 200k window) |
| `context_preserve_last_n` | `5` | Tail messages kept verbatim after condensing |
| `log_level` | `"INFO"` | Python log level; set `LOG_LEVEL=DEBUG` for token-count detail |

### Per-game configuration (`dm_api.db.models.game_config`)

`Settings` provides deployment defaults; each game (world) can override them
in its `GameConfig` row, edited by the DM via
`GET/PUT /api/worlds/{world_id}/config` (UI: the "Game Settings" modal).
Overridable per game: `ai_provider`, `orchestrator_model`,
`generation_model`, `context_token_limit`, `context_preserve_last_n`, and
the game's storage locations (`database_url`, `redis_url`).

`resolve_game_config(row | None)` merges overrides with the defaults into a
frozen `EffectiveGameConfig` (typed boundary — no optional fields), and the
sessions API builds the `DMOrchestrator` from it on every chat/summary call,
so changes apply immediately. AI backends are cached per provider, not
per process, so two games may run different providers side by side. The
storage URLs are resolved through the same seam; the API server itself still
binds its engine to `Settings.database_url` at startup, so per-game storage
URLs are honored by tooling/deployments that read the game's effective
config rather than re-routing live requests.

### Injected context sections

When the condenser fires, the orchestrator receives a lead `user` message
containing any non-empty of these labelled sections:

- `[CONDENSED SYNOPSIS]` — narrative summary of the condensed range
- `[ESTABLISHED FACTS]` — world / character / rules facts to persist
- `[OPEN THREADS]` — unresolved hooks and pending player choices
- `[SPAN] msg:<id>@<ts> → msg:<id>@<ts>` — bounds of the condensed range

`system_prompt.py` instructs the DM model to treat these as canonical and
to cite anchors when referring to prior events.

---

## Observability

### Structured Logging

`dm-api` uses Python's standard `logging` module configured in
`dm_api/logging_config.py`. Call `configure_logging()` once at startup
(the lifespan hook in `main.py` does this automatically).

**Log format** — human-readable with key=value pairs for machine parsing:

```
2026-05-09 12:34:55,600 INFO     dm_api.api.ws  ws connect  session_id=abc total=1
2026-05-09 12:34:56,789 INFO     dm_api.main  request  method=POST path=/api/sessions/abc/chat status=200 duration_ms=1430
2026-05-09 12:34:56,001 INFO     dm_api.ai.dm_orchestrator  orchestrator start  session_id=abc world_id=xyz history_len=12
2026-05-09 12:34:56,002 DEBUG    dm_api.ai.condenser  condenser skipped  messages=12 tokens=45000 limit=180000
2026-05-09 12:34:57,400 DEBUG    dm_api.ai.backends.anthropic_backend  anthropic complete  model=claude-sonnet-4-6 tokens_in=1480 tokens_out=312 duration_ms=1398
2026-05-09 12:34:57,401 INFO     dm_api.ai.dm_orchestrator  orchestrator done  session_id=abc model=claude-sonnet-4-6 tokens_in=1480 tokens_out=312 was_condensed=False proposal=none duration_ms=1430
2026-05-09 12:34:58,000 INFO     dm_api.api.ws  ws disconnect  session_id=abc remaining=0
```

**Log levels by module:**

| Logger | INFO events | DEBUG events |
|--------|-------------|-------------|
| `dm_api.main` | every HTTP request (method, path, status, ms) | — |
| `dm_api.api.ws` | connect (session, total connections), disconnect (session, remaining) | dead-connection pruned |
| `dm_api.ai.dm_orchestrator` | start + done (session, model, tokens, ms) | — |
| `dm_api.ai.condenser` | triggered (token counts, messages condensed, facts/threads) | skipped (no-op path) |
| `dm_api.ai.backends.anthropic_backend` | — | model, tokens in/out, ms |
| `dm_api.ai.backends.claude_cli_backend` | — | model, estimated tokens, ms |

### Configuring the Log Level

```bash
# .env or shell export
LOG_LEVEL=DEBUG   # show AI call details and token counts per request
LOG_LEVEL=INFO    # (default) major events only
LOG_LEVEL=WARNING # quiet mode for prod containers
```

Or pass it to uvicorn at startup:

```bash
LOG_LEVEL=DEBUG uvicorn dm_api.main:app --reload
```

### Running Locally

```bash
# Minimal setup — SQLite + no real AI calls (mock backend in tests)
cd dm-api
DATABASE_URL="sqlite+aiosqlite:///:memory:" \
  AI_PROVIDER="anthropic" \
  ANTHROPIC_API_KEY="test-key" \
  LOG_LEVEL=DEBUG \
  uvicorn dm_api.main:app --reload --port 8000
```

### Mocking the AI Backend in Tests

The `AIBackend` ABC makes the AI layer fully mockable without patching subprocess
or network calls. The test suite uses a `_ScriptedBackend` that replays a
pre-set reply queue:

```python
from dm_api.ai.backends.base import AIBackend, AIMessage, AIResponse
from dm_api.ai.dm_orchestrator import DMOrchestrator

class _ScriptedBackend(AIBackend):
    def __init__(self, replies: list[str]) -> None:
        self._replies = list(replies)
        self.calls: list[dict] = []

    async def complete(self, *, messages, system, model, max_tokens=4096):
        reply = self._replies.pop(0) if self._replies else ""
        self.calls.append({"messages": messages, "model": model})
        return AIResponse(content=reply, model=model)

# Usage:
backend = _ScriptedBackend(["The tavern is quiet tonight."])
orchestrator = DMOrchestrator(backend=backend, orchestrator_model="main", generation_model="fast")
result = await orchestrator.handle_message(message="...", session_id="s1", world_id="w1", history=[])
```

For HTTP-level tests, patch `dm_api.api.sessions.DMOrchestrator`:

```python
from unittest.mock import AsyncMock, MagicMock, patch

mock_orch = MagicMock()
mock_orch.handle_message = AsyncMock(return_value=DMResponse(
    response="You find a chest.", proposals=[], was_condensed=False,
    tokens_in=100, tokens_out=50,
))
with patch("dm_api.api.sessions.DMOrchestrator", return_value=mock_orch):
    r = await client.post(f"/api/sessions/{session_id}/chat", json={"message": "look around"})
```

See `dm-api/tests/test_dm_orchestrator.py` and `test_sessions.py` for
complete examples.

### Running the Full Test Suite

```bash
# game-engine (no env vars required)
cd game-engine && pytest tests/ -v

# dm-api (SQLite in-memory, no real AI key needed)
cd dm-api && \
  DATABASE_URL="sqlite+aiosqlite:///:memory:" \
  AI_PROVIDER="anthropic" \
  ANTHROPIC_API_KEY="test-key" \
  pytest tests/ -v
```
