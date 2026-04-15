# dm.ai — Architecture

## System Overview

dm.ai is composed of three deployable units and one installable Python library.

```
┌─────────────────────────────────────────────────────────────────────┐
│  dm-ui  (React 19 + Vite + react-konva, port 5173)                  │
│  ChatPanel · BattleMap · ProposalCard · CombatTracker · LocationPanel│
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
│  │  /ws/sessions/{id}   │                                           │
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
| `apply_damage` | `(target, damage, damage_type) → CharacterSheet` | Damage with resistance calculation |
| `apply_condition` | `(target, condition, duration_rounds) → CharacterSheet` | Apply a status condition |
| `remove_condition` | `(target, condition) → CharacterSheet` | Remove a status condition |
| `get_available_actions` | `(char, combat_state) → list[Action]` | Legal actions for a character's turn |
| `resolve_action` | `(action, combat_state) → ActionResult` | Resolve and narrate an action |
| `roll_initiative` | `(char) → int` | Initiative roll |
| `validate_character` | `(sheet) → ValidationResult` | Legality check for a character sheet |
| `calculate_proficiency_bonus` | `(level) → int` | Proficiency bonus by level |

Result dataclasses (`CheckResult`, `ActionResult`, `ValidationResult`) and the
`Action` dataclass are defined in `interface.py` alongside the ABC.

### D&D 5.5e Engine

`game_engine.rules.dnd_5_5e.DnD55eEngine` is the concrete implementation. It uses
a **delegation pattern**: each abstract method delegates to a focused helper module
in `game_engine/core/` (dice, conditions, initiative, combat, character). This
keeps the engine file short and each helper independently testable.

Data tables (spells, monsters, weapons, armor) live in
`game_engine/rules/dnd_5_5e/data/` as Python modules using enum types for all
typed fields.

### types package

`game_engine/types/` is the single source of truth for domain types:

**Enums** (`enums.py`) — all `str, Enum` subclasses for wire-compatibility:
- `CharacterClass` — 13 D&D 5.5e classes
- `Ability` — STR / DEX / CON / INT / WIS / CHA (with `.modifier()` and `.short`)
- `Skill` — all 18 skills (with `.governing_ability`)
- `DamageType` — 13 standard damage types
- `Condition` — 15 standard conditions (with `.prevents_action()` classmethod)
- `ActionType` — 10 combat action types
- `CharacterType` — PC / NPC / MONSTER
- `LocationType` — REALM / COUNTRY / REGION / TOWN / DISTRICT / BUILDING / ROOM / DUNGEON / WILDERNESS
- `ProposalType` — LOCATION / CHARACTER / DUNGEON / DIALOGUE / COMBAT_ACTION
- `ProposalStatus` — PENDING / ACCEPTED / REJECTED / MODIFIED
- `ChatRole` — DM / AI / SYSTEM

**Dataclasses** (`sheets.py`):
- `AbilityScoreSet` — six scores with `.get()`, `.modifier()`, `.to_dict()`, `.from_dict()`
- `CharacterSheet` — full character representation including conditions, resistances,
  immunities; `.is_alive`, `.can_act`, `.to_dict()`, `.from_dict()`
- `CombatStateData` — combatant list + round/turn tracking
- `AttackDetails` — weapon name, damage dice, damage type, attack ability, ranged flag

### Extending with a New Rule System

1. Create `game_engine/rules/<system>/` with `__init__.py` and `engine.py`
2. Subclass `RuleEngine` and implement all nine abstract methods
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
| `combat_states` | `id`, `session_id` (unique), `round_number`, `current_turn_index`, `initiative_order` (JSON), `combatants` (JSON), `combat_log` (JSON) | One active combat per session |
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

1. Builds a system prompt from `build_system_prompt(world_id, session_id)`
2. Converts the chat history from DB format to `list[AIMessage]`
3. Calls `backend.complete()` with the orchestrator model (Sonnet by default)
4. Scans the response for a `[PROPOSAL]...[/PROPOSAL]` JSON block via
   `_extract_proposal()`
5. Returns `{"response": str, "proposal": dict | None}`

The session route (`POST /api/sessions/{id}/chat`) persists both the DM message
and AI response to `chat_messages`, and the proposal (if any) to `proposals`,
before returning to the client.

`summarize()` uses the faster generation model (Haiku) for end-of-session summaries.

### WebSocket and Real-time Events

`/ws/sessions/{session_id}` is a pure WebSocket endpoint. The current
implementation maintains an in-memory connection registry (`dict[str, list[WebSocket]]`)
and broadcasts messages from one client to all other clients in the same session.

Planned message types (defined in `dm-ui/src/api/ws.ts`):

| Type | Direction | Purpose |
|---|---|---|
| `map_update` | server → client | Token positions, fog-of-war reveal |
| `combat_update` | server → client | Initiative order, HP, conditions |
| `chat_message` | server → client | New AI or DM message |
| `proposal_ready` | server → client | New proposal awaiting DM review |
| `entity_update` | server → client | Character or location field change |

---

## dm-ui

The frontend is a React 19 + Vite + TypeScript application with strict mode enabled.

### Component Tree

```
App
└── DMDashboard
    ├── NewSessionForm          (shown when no sessionId in store)
    ├── aside (left)
    │   ├── LocationPanel
    │   └── CharacterCard
    ├── main
    │   ├── BattleMap           (react-konva, collapsible)
    │   └── ChatPanel           (messages + input bar)
    └── aside (right)
        └── CombatTracker
```

### State Management — Zustand

`src/store/gameStore.ts` is the single source of truth. Key slices:
- `sessionId` / `worldId` — active session and world
- `messages` — chat history (`{id, role, content, timestamp}[]`)
- `isLoading` — tracks in-flight AI requests
- `addMessage` / `setLoading` — actions

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
WebSocket hook that connects to `/ws/sessions/{id}` and dispatches incoming
messages to the Zustand store.

---

## Data Flow — DM Chat to World Update

```
1. DM types a message in ChatPanel → sendMessage()

2. POST /api/sessions/{id}/chat  { message: "..." }

3. dm-api saves DM ChatMessage to DB

4. DMOrchestrator.handle_message()
   ├─ build_system_prompt(world_id, session_id)
   ├─ fetch chat history from DB
   └─ backend.complete(messages, system, model=orchestrator_model)

5. Claude returns narrative text, optionally with
   [PROPOSAL]{ "type": "location", "content": { ... } }[/PROPOSAL]

6. dm-api saves AI ChatMessage + Proposal (status=pending) to DB

7. Response { response, proposal } returned to client

8. Client displays AI message; ProposalCard shown if proposal != null

9. DM reviews → POST /api/ai/proposals/{id}/accept
   ├─ dm_notes and modifications merged into proposal.content
   ├─ proposal.status set to "accepted"
   └─ (future) Location/Character record created + embedding indexed
```

---

## World Consistency — pgvector RAG

Three tables carry `embedding vector(1536)` columns: `worlds`, `characters`,
`locations`. Before generating new content, the orchestrator:

1. Embeds the DM's prompt using the embedding model
2. Queries pgvector for the nearest-neighbor lore entries
3. Injects the top-k results into the system prompt as "existing world context"

This prevents contradictions: a settlement described as coastal will remain
coastal; a character established as antagonistic will be recalled as such in later
sessions.

The `WorldConsistencyVector` pipeline (in `dm_api/ai/`) handles embedding
generation and similarity search. Embeddings are updated when proposals are
accepted.

---

## Context Management

Long sessions accumulate chat history that can exhaust the model's context window.

`settings.context_token_limit` (default: 180,000 — 80% of the 200k window)
triggers automatic summarization:

1. Token counts are stored on each `ChatMessage` row (`token_count` column)
2. When the running total exceeds the limit, `DMOrchestrator.summarize()` condenses
   older messages using the fast model (Haiku)
3. The summary replaces the compressed messages in the context window
4. `settings.context_preserve_last_n` (default: 5) messages are always kept
   verbatim to preserve immediate conversational continuity
