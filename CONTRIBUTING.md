# Contributing to dm.ai

For AI agent-specific guidance see [AGENTS.md](./AGENTS.md).

---

## Prerequisites

| Tool | Minimum version | Notes |
|---|---|---|
| Python | 3.12 | `pyenv` recommended for version management |
| Node | 22 | `nvm` recommended |
| Docker + Docker Compose | any recent | Local PostgreSQL + Redis |
| `uv` or `pip` | any recent | Python dependency management |
| `claude` CLI | optional | Required only for `AI_PROVIDER=claude_cli` |

---

## Quick Start

**1. Clone and configure environment:**
```bash
git clone <repo>
cd dm.ai
cp .env.example .env
# Edit .env — fill in ANTHROPIC_API_KEY, or set AI_PROVIDER=claude_cli
```

**2. Start backing services:**
```bash
docker-compose up -d
```

**3. Install and run each package (three separate terminals):**

```bash
# Terminal 1 — game-engine (install only; no server to run)
cd game-engine
pip install -e ".[dev]"

# Terminal 2 — dm-api
cd dm-api
pip install -e "../game-engine"
pip install -e ".[dev]"
alembic upgrade head
uvicorn dm_api.main:app --reload --port 8000

# Terminal 3 — dm-ui
cd dm-ui
npm install
npm run dev
```

**4. Open the DM dashboard:** http://localhost:5173

---

## Project Structure

```
dm.ai/
├── AGENTS.md                    — AI agent instructions (read by Claude Code)
├── CONTRIBUTING.md              — this file
├── README.md                    — project overview and architecture diagram
├── docker-compose.yml           — postgres (pgvector), redis, api, ui
├── .env.example                 — copy to .env and fill in secrets
├── docs/
│   ├── architecture.md          — system design and data flow
│   └── api.md                   — all REST + WebSocket endpoints
├── game-engine/                 — installable Python package (no FastAPI)
│   ├── pyproject.toml
│   ├── tests/
│   └── src/game_engine/
│       ├── types.py             — enums + dataclasses (single source of truth)
│       ├── interface.py         — RuleEngine ABC + result dataclasses
│       ├── core/                — dice, conditions, initiative, combat, character
│       └── rules/
│           └── dnd_5_5e/        — DnD55eEngine implementation + data files
├── dm-api/                      — FastAPI service
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/
│   │   └── versions/            — auto-generated; do not hand-edit
│   └── src/dm_api/
│       ├── main.py
│       ├── config.py            — pydantic-settings, reads .env
│       ├── db/                  — SQLAlchemy async models + session factory
│       ├── api/                 — FastAPI route handlers
│       └── ai/                  — DM orchestrator, AI backends, system prompts
└── dm-ui/                       — React 19 frontend
    ├── package.json
    ├── vite.config.ts
    ├── tsconfig.app.json        — TypeScript strict mode enabled
    └── src/
        ├── api/                 — REST client
        ├── store/gameStore.ts   — Zustand store (shared application state)
        └── components/          — BattleMap, CombatTracker, CharacterCard, etc.
```

---

## Running Tests

```bash
# game-engine unit tests
cd game-engine
pytest tests/ -v

# dm-api tests — uses SQLite in-memory; no running Postgres needed
cd dm-api
DATABASE_URL=sqlite+aiosqlite:///:memory: pytest tests/ -v

# dm-ui — type check + lint (no test runner yet)
cd dm-ui
npx tsc --noEmit
npm run lint
```

All three must pass before opening a pull request.

---

## Code Style Guide

### Python

#### Enums over strings — the most important rule

dm.ai enforces a **no magic strings** policy for all domain concepts. Every
fixed-value concept (character class, damage type, condition, ability, skill, action
type, location type, etc.) must be represented as a `str, Enum` subclass.

All canonical enums live in `game_engine/types.py`. Import from there.

```python
# BAD — typo-prone, no IDE support, no static type checking
def deal_damage(target, amount, dtype: str) -> None:
    if dtype == "fyre":  # silent typo bug
        ...

# GOOD — typo caught at import time, IDE autocomplete, mypy-compatible
from game_engine.types import DamageType, CharacterSheet

def deal_damage(target: CharacterSheet, amount: int, dtype: DamageType) -> None:
    if dtype == DamageType.FIRE:
        ...
```

When you need to represent a new game concept that has a fixed set of values, add
a `str, Enum` subclass to `game_engine/types.py` — do not introduce ad-hoc string
constants scattered across the codebase.

#### Typed dataclasses over dicts

Never pass an untyped `dict` as a function argument when the dict represents a
structured entity. Use the typed dataclasses from `game_engine/types.py`.

```python
# BAD — no editor support, no runtime safety
def resolve_action(action: dict, combat_state: dict) -> dict: ...

# GOOD — fully typed, IDE-navigable
from game_engine.interface import Action, ActionResult
from game_engine.types import CombatStateData

def resolve_action(action: Action, combat_state: CombatStateData) -> ActionResult: ...
```

Key types available: `CharacterSheet`, `CombatStateData`, `AttackDetails`,
`AbilityScoreSet`. Result types: `CheckResult`, `ActionResult`, `ValidationResult`.

#### File length

Target **<= 400 lines** per production file and **<= 600 lines** per test file.

When a file approaches the limit, look for natural split points:
- Split a large class into a class definition + private module-level helpers
- Split a large route file into multiple focused route files (e.g., `characters.py`,
  `combat.py`)
- Extract reusable utilities into `_utils.py` or `_helpers.py`

An exception is allowed when splitting would genuinely harm readability (e.g., a
flat data table like `spells.py`). In that case add a comment at the top:

```python
# NOTE: This file intentionally exceeds the 400-line guideline because
# splitting spell data across multiple files would impair readability.
```

When you encounter an existing file that exceeds the limit without a noted
exception, refactor it before adding new code to it.

#### Function length

Functions longer than ~30 lines almost always contain extractable logic. Prefer
named helper functions (not lambdas) for non-trivial extracted pieces.

#### Type hints

Required on all public functions and methods. Return types must be explicit — never
omit them. Add `from __future__ import annotations` at the top of every Python file
to enable forward references without quoting.

#### Docstrings

Required on all public classes and functions. Use Google style:

```python
def roll_check(self, char: CharacterSheet, skill: Skill, dc: int) -> CheckResult:
    """Roll a skill check against a difficulty class.

    Args:
        char: Character performing the check.
        skill: Skill or ability to check.
        dc: Difficulty class to meet or exceed.

    Returns:
        CheckResult with roll details and success flag.
    """
```

Docstrings on private helpers are encouraged but optional; a brief inline comment
is acceptable when the logic is short and self-explanatory.

---

### TypeScript / React

- **Strict mode** is enabled in `tsconfig.app.json`. Do not add `any` without an
  `// eslint-disable-next-line` comment that explains why it is unavoidable.
- **One component per file.** Tightly coupled sub-components may live in the same
  directory but each in its own file.
- **State management:** Use the Zustand store (`useGameStore` from
  `src/store/gameStore.ts`) for any data that more than one component needs. Do not
  use local `useState` for shared state.
- **No CSS files:** This is a prototype that uses inline styles throughout. Keep
  that consistent.
- **ESLint** is configured to fail on any warning (`--max-warnings 0`). Fix
  warnings, do not suppress them without justification.

---

## AI Configuration

Two backends are supported, controlled by the `AI_PROVIDER` env var in `.env`:

| `AI_PROVIDER` | Authentication | How to set up |
|---|---|---|
| `anthropic` (default) | `ANTHROPIC_API_KEY=sk-...` | Get a key from [console.anthropic.com](https://console.anthropic.com) |
| `claude_cli` | None (uses local auth) | `npm install -g @anthropic-ai/claude-code`, then run `claude` to authenticate |

Model roles — override in `.env` to tune cost/capability tradeoffs:

```bash
ORCHESTRATOR_MODEL=claude-sonnet-4-6       # main DM chat responses
PLANNING_MODEL=claude-sonnet-4-6           # world-building, complex proposals
GENERATION_MODEL=claude-haiku-4-5-20251001 # quick summaries, flavor text
```

Rule of thumb: use Haiku for tasks that require fast, high-volume output (NPC
dialogue options, short flavor text); use Sonnet for reasoning-heavy tasks
(world-building proposals, encounter balancing).

---

## Pull Request Process

**Branch naming:** `feat/<name>`, `fix/<name>`, `test/<name>`, `docs/<name>`

**Before opening a PR, verify all of the following:**

- [ ] `pytest tests/ -v` passes in `game-engine/`
- [ ] `pytest tests/ -v` passes in `dm-api/`
- [ ] `npx tsc --noEmit` passes in `dm-ui/`
- [ ] `npm run lint` passes with zero warnings in `dm-ui/`
- [ ] No raw string literals for game domain concepts — use enums from `game_engine/types.py`
- [ ] No untyped `dict` parameters for structured entities — use dataclasses
- [ ] Every new public function/method has type annotations and a docstring
- [ ] New features have tests; new bug fixes have regression tests
- [ ] No file exceeds 400 LoC without a noted exception comment
- [ ] No `.env` files or secrets are staged

**Review focus for reviewers:** Specifically check for files or classes that have
grown too large. If a file exceeds 400 LoC without a noted exception, request a
refactor as part of the review — do not approve with a "clean it up later" comment.

---

## Adding a New Rule System

1. Create `game_engine/rules/<system_name>/` with `__init__.py` and `engine.py`
2. Subclass `game_engine.interface.RuleEngine` and implement every abstract method:
   `roll_check`, `apply_damage`, `apply_condition`, `remove_condition`,
   `get_available_actions`, `resolve_action`, `roll_initiative`,
   `validate_character`, `calculate_proficiency_bonus`
3. Add new enum values to `CharacterClass` in `game_engine/types.py` if the system
   introduces unique classes (or create a system-specific enum subclass)
4. Register the engine in `game_engine/rules/__init__.py`
5. Write tests in `game_engine/tests/test_<system_name>_engine.py`
6. Document the system's key rules and any deviations in `docs/architecture.md`

---

## Adding New D&D 5.5e Content

Data files live in `game_engine/rules/dnd_5_5e/data/`. Use existing entries as
templates. Always use enum types for typed fields (`damage_type`, `school`, etc.),
never raw strings.

### Spells

Edit `game_engine/rules/dnd_5_5e/data/spells.py`. Each entry is a dict with keys:
`name`, `level`, `school`, `casting_time`, `range`, `components`, `duration`,
`description`, `damage_dice`, `damage_type` (use `DamageType` enum), `save`,
`attack_type`.

### Monsters

Edit `game_engine/rules/dnd_5_5e/data/monsters.py`. Each entry includes a full
stat block. Use `DamageType` enum values for `damage_resistances`,
`damage_immunities`, and `damage_vulnerabilities`. Use `Condition` enum values for
`condition_immunities`.

### Items / Weapons / Armor

Edit `game_engine/rules/dnd_5_5e/data/items.py`. Add weapons to `WEAPONS` and
armor to `ARMOR`. Use `DamageType` enum for `damage_type`.

---

## Database Migrations

Always use Alembic — never hand-edit files in `alembic/versions/`.

```bash
cd dm-api

# After changing a SQLAlchemy model:
alembic revision --autogenerate -m "short description of change"

# Review the generated file in alembic/versions/ before applying
alembic upgrade head
```

The test suite uses SQLite in-memory (`DATABASE_URL=sqlite+aiosqlite:///:memory:`)
so you do not need a running Postgres instance to run `dm-api` tests.

---

## Getting Help

- **Bugs / feature requests:** Open a GitHub Issue
- **System design:** See `docs/architecture.md`
- **API endpoints:** See `docs/api.md`
- **AI agent guidance:** See [AGENTS.md](./AGENTS.md)
