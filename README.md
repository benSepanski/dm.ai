# dm.ai — AI-Powered Dungeon Master Toolkit

dm.ai is an AI assistant for tabletop RPG game masters. It is **not** a fully
autonomous DM — it is a powerful toolkit that proposes content (towns, NPCs,
dungeons, dialogue options) while the DM reviews, iterates, and approves, keeping
creative control while reducing prep time to near zero. Worlds are internally
consistent and thematically connected via a pgvector RAG pipeline.

MVP targets **D&D 5.5e**; the architecture is designed for future rule-set expansion.

---

## Quick Start

```bash
cp .env.example .env          # fill in ANTHROPIC_API_KEY
docker-compose up -d          # postgres, redis, api, ui
open http://localhost:5173    # DM dashboard
```

---

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│  dm-ui  (React 19 + Vite + Konva)                              │
│  ChatPanel │ BattleMap │ ProposalCard │ CombatTracker          │
└──────────────────────────┬─────────────────────────────────────┘
                           │ REST + WebSocket
┌──────────────────────────▼─────────────────────────────────────┐
│  dm-api  (FastAPI + Python 3.12)                               │
│  ┌─────────────┐  ┌────────────────────────────────────────┐   │
│  │ REST Routes │  │ AI Layer                               │   │
│  │ /worlds     │  │  DM Orchestrator (Opus 4.6)            │   │
│  │ /sessions   │  │   ├─ World Builder (Opus 4.6)          │   │
│  │ /characters │  │   ├─ Character Gen (Opus 4.6)          │   │
│  │ /locations  │  │   ├─ NPC Agent    (Haiku 4.5)          │   │
│  │ /combat     │  │   └─ Combat Advisor (Haiku 4.5)        │   │
│  │ /ai         │  │  Context Manager + World Consistency   │   │
│  └─────────────┘  └────────────────────────────────────────┘   │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐     │
│  │ PostgreSQL  │  │    Redis     │  │   game-engine      │     │
│  │ + pgvector  │  │  pub/sub     │  │   (Python pkg)     │     │
│  └─────────────┘  └──────────────┘  └────────────────────┘     │
└────────────────────────────────────────────────────────────────┘
```

### WebSocket Real-time Events

| Message type     | Direction       | Purpose                          |
|------------------|-----------------|----------------------------------|
| `map_update`     | server → client | token positions, fog reveal       |
| `combat_update`  | server → client | initiative order, HP, conditions |
| `chat_message`   | server → client | new AI or DM message             |
| `proposal_ready` | server → client | new Proposal awaiting DM review  |
| `entity_update`  | server → client | character/location field changed  |

---

## Repository Layout

```
dm.ai/
├── README.md
├── docker-compose.yml
├── .env.example
├── docs/
│   ├── architecture.md      — deep-dive on AI agent design
│   ├── api-reference.md     — all REST + WS endpoints
│   ├── data-models.md       — full schema definitions
│   └── ai-agents.md         — prompt engineering notes
├── game-engine/             — installable Python package (rule-agnostic + D&D 5.5e)
│   ├── pyproject.toml
│   └── src/game_engine/
│       ├── interface.py     — RuleEngine ABC
│       ├── core/            — dice, conditions, initiative, combat, character
│       └── rules/dnd_5_5e/  — DnD55eEngine implementation
├── dm-api/                  — FastAPI service
│   ├── pyproject.toml
│   ├── alembic/
│   └── src/dm_api/
│       ├── main.py
│       ├── config.py
│       ├── db/              — SQLAlchemy models + session
│       ├── api/             — route handlers
│       └── ai/              — agents + prompts
└── dm-ui/                   — React 19 frontend
    ├── package.json
    ├── vite.config.ts
    └── src/
        ├── api/             — REST client + WebSocket hook
        ├── store/           — Zustand stores
        └── components/      — BattleMap, DMDashboard, etc.
```

---

## Technology Stack

| Layer         | Choice                              |
|---------------|-------------------------------------|
| Backend       | Python 3.12 + FastAPI               |
| AI            | Anthropic Claude API (Opus 4.6 / Haiku 4.5) |
| Database      | PostgreSQL 16 + pgvector            |
| Cache/pub-sub | Redis                               |
| Migrations    | Alembic                             |
| Frontend      | TypeScript + React 19 + Vite        |
| Map rendering | react-konva                         |
| State         | Zustand                             |
| Containers    | Docker + docker-compose             |
| Pkg mgmt      | uv (Python) / pnpm (Node)           |

---

## DM Workflow Example

```
DM: "Players arrive at the village of Thornwick."
  → Orchestrator routes to World Builder
  → World Builder RAG-queries existing world lore
  → Generates: town overview, 6 buildings, 4 NPCs
  → ProposalCard presented to DM for review/edit
  → DM accepts → Location + Characters saved, RAG index updated
  → Battle Map renders AI-sketched town grid

DM clicks "Chat as NPC" on innkeeper
  → NPC Sub-Agent returns 3 dialogue options (warm / neutral / guarded)
  → DM selects or rewrites → logged to session + character interaction_log

Players get into a bar fight
  → DM clicks "Start Combat"
  → Initiative rolled (RuleEngine) → CombatTracker populates
  → On each monster turn: Combat Advisor suggests action + flavor text
  → DM approves → RuleEngine resolves → map_update broadcast to all clients
```

---

## Development Milestones

### ✅ Phase 0 — Interface Contracts
- [x] `RuleEngine` ABC (`game-engine/src/game_engine/interface.py`)
- [x] OpenAPI spec (`dm-api/openapi.yaml`)
- [x] WebSocket message type definitions (`dm-ui/src/api/ws.ts`)
- [x] Alembic initial migration (all models)
- [x] `Proposal` JSON schema

### 🔲 Phase 1 — Foundation
- [ ] **WS-A** Game Engine core: dice, conditions, initiative, abstract character
- [ ] **WS-B** Docker + Postgres + Alembic migrations + CRUD API skeleton
- [ ] **WS-C** React project + routing + WS hook + Zustand stores + empty shells
- [ ] **WS-D** Anthropic SDK wired + Orchestrator stub + ContextManager + prompts

### 🔲 Phase 2 — Core Features
- [ ] **WS-A** Full D&D 5.5e rules engine with pytest integration tests
- [ ] **WS-B** All REST endpoints wired + WS broadcast via Redis pub/sub
- [ ] **WS-C** Battle Map: grid, tokens, drag-drop, fog of war, zoom/pan
- [ ] **WS-D** World Builder + Character Gen with pgvector RAG + Proposal flow

### 🔲 Phase 3 — AI Integration
- [ ] **WS-A** NPC sub-agent factory + 3-option dialogue + interaction log
- [ ] **WS-B** CombatState API + initiative UI + Combat Advisor + combat log
- [ ] **WS-C** Token counting middleware + auto-summarization + entity registry
- [ ] **WS-D** Theme extraction + contradiction detection + entity dedup + RAG ranking

### 🔲 Phase 4 — Dungeon + Polish
- [ ] **WS-A** Dungeon layout agent: room graph, traps, encounter sizing, map_data
- [ ] **WS-B** ProposalCard review flow + QuickActions + CharacterCard + LocationPanel
- [ ] **WS-C** Full end-to-end scenario test + load testing for WS connections
- [ ] **WS-D** Docs, API reference, architecture diagrams, README polish

---

## Environment Variables

| Variable              | Description                        |
|-----------------------|------------------------------------|
| `ANTHROPIC_API_KEY`   | Anthropic API key                  |
| `DATABASE_URL`        | PostgreSQL connection string       |
| `REDIS_URL`           | Redis connection string            |
| `SECRET_KEY`          | FastAPI JWT secret                 |
| `FRONTEND_URL`        | CORS allowed origin for dm-ui      |

---

## Contributing

1. All AI-generated content goes through the Proposal flow — nothing writes to DB without DM review
2. Run `pytest game-engine/tests dm-api/tests` before committing
3. Keep rule logic inside `game-engine/` — `dm-api` calls `RuleEngine` methods only
