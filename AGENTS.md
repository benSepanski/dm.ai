# AGENTS.md — AI Agent Instructions for dm.ai

This file is read by Claude Code and other AI coding agents. For human contributor
guidelines see [CONTRIBUTING.md](./CONTRIBUTING.md).

---

## Repository Layout

```
dm.ai/
├── AGENTS.md
├── CONTRIBUTING.md
├── README.md
├── docker-compose.yml
├── .env.example
├── docs/                        — architecture, API reference, data models
├── game-engine/                 — installable Python package (no FastAPI dependency)
│   ├── pyproject.toml
│   └── src/game_engine/
│       ├── types.py             — ALL enums + typed dataclasses (start here)
│       ├── interface.py         — RuleEngine ABC
│       ├── core/                — dice, conditions, initiative, combat, character
│       └── rules/dnd_5_5e/      — DnD55eEngine (concrete implementation)
├── dm-api/                      — FastAPI service
│   ├── pyproject.toml
│   ├── alembic/                 — DO NOT hand-edit versions/
│   └── src/dm_api/
│       ├── main.py
│       ├── config.py            — Settings (pydantic-settings, reads .env)
│       ├── db/                  — SQLAlchemy models + async session
│       ├── api/                 — route handlers
│       └── ai/                  — DM orchestrator, AI backends, prompts
└── dm-ui/                       — React 19 + Vite + Konva frontend
    ├── package.json
    ├── tsconfig.app.json        — strict mode enabled
    └── src/
        ├── api/                 — REST client
        ├── store/gameStore.ts   — Zustand store (single source of truth)
        └── components/          — BattleMap, CombatTracker, DMDashboard, etc.
```

---

## Before Every Commit

- Run `pytest tests/ -v` inside `game-engine/` — all tests must pass
- Run `pytest tests/ -v` inside `dm-api/` — all tests must pass
- Run `npx tsc --noEmit` inside `dm-ui/` — zero type errors
- Run `npm run lint` inside `dm-ui/` — zero ESLint warnings or errors
- Run `git status` — no untracked files accidentally left behind
- Never commit `.env` files, API keys, or any secrets

---

## Code Style — Non-Negotiable Rules

### 1. No raw string literals for game concepts

**Forbidden:**
```python
# BAD — strings for domain concepts
damage_type = "fire"
char["conditions"].append("stunned")
if char["class"] == "Fighter":
```

**Required:** Use enums from `game_engine.types`:
```python
# GOOD
from game_engine.types import DamageType, Condition, CharacterClass
damage_type = DamageType.FIRE
sheet.conditions.append(Condition.STUNNED)
if sheet.char_class == CharacterClass.FIGHTER:
```

All game concepts with a fixed set of values MUST be `str, Enum` subclasses. This
enables type-checking, IDE autocomplete, and prevents silent typo bugs. Enum types
already defined in `game_engine/types.py`:
`CharacterClass`, `Ability`, `Skill`, `DamageType`, `Condition`, `ActionType`,
`CharacterType`, `LocationType`, `ProposalType`, `ProposalStatus`, `ChatRole`.

### 2. No dict-as-schema anti-pattern

**Forbidden:**
```python
# BAD — untyped dict passed as character or combat state
def apply_damage(target: dict, damage: int, damage_type: str) -> dict: ...
def get_actions(char: dict, combat_state: dict) -> list: ...
```

**Required:** Use typed dataclasses from `game_engine/types.py`:
```python
# GOOD
def apply_damage(target: CharacterSheet, damage: int, damage_type: DamageType) -> CharacterSheet: ...
def get_actions(char: CharacterSheet, combat_state: CombatStateData) -> list[Action]: ...
```

Key types: `CharacterSheet`, `CombatStateData`, `AttackDetails`, `AbilityScoreSet`.

### 3. File length — prefer short files

**Target:** <= 400 lines per production file, <= 600 lines per test file.

Split files at natural seams when approaching the limit (e.g., split a large route
file into multiple focused route files; extract helpers into `_utils.py`).

When an exception is genuinely necessary (e.g., a long data table), add a comment
at the top of the file:

```python
# NOTE: This file intentionally exceeds the 400-line guideline because
# splitting spell data across multiple files would impair readability.
```

When you find an existing file that exceeds the limit without a noted exception,
**refactor it** before adding new code to it.

### 4. Short, focused functions

Functions should do one thing. If a function body exceeds 30 lines, look for
extractable helpers. Prefer named helper functions over inline lambdas for any
non-trivial logic.

### 5. Type hints everywhere

All public functions and methods must have full type annotations including explicit
return types. Use `from __future__ import annotations` at the top of every Python
file for forward-reference support.

---

## AI Provider Configuration

dm.ai supports two AI backends, selected via the `AI_PROVIDER` env var:

| Provider | Required | Setup |
|---|---|---|
| `anthropic` (default) | `ANTHROPIC_API_KEY` | Anthropic API key |
| `claude_cli` | `claude` on `$PATH` | `npm install -g @anthropic-ai/claude-code` |

Model roles (override via env vars in `.env`):

| Env var | Default | Purpose |
|---|---|---|
| `ORCHESTRATOR_MODEL` | `claude-sonnet-4-6` | Main DM chat responses |
| `PLANNING_MODEL` | `claude-sonnet-4-6` | World-building, complex reasoning |
| `GENERATION_MODEL` | `claude-haiku-4-5-20251001` | Quick summaries, flavor text |

---

## Adding New Rule Systems

1. Create `game_engine/rules/<system_name>/` with `__init__.py` and `engine.py`
2. Subclass `game_engine.interface.RuleEngine` and implement every abstract method
3. Register the engine in `game_engine/rules/__init__.py`
4. Add system-specific enum values to `CharacterClass` in `game_engine/types.py`
   (or create a separate enum that extends it)
5. Write tests in `game_engine/tests/test_<system_name>_engine.py`

---

## Adding New D&D 5.5e Content

Data files live in `game_engine/rules/dnd_5_5e/data/`. Use existing entries as
templates. Always use enum types for `damage_type`, `school`, and similar fields.

- `spells.py` — add to the `SPELLS` list
- `monsters.py` — add to the `MONSTERS` list
- `items.py` — add to `WEAPONS` or `ARMOR`

---

## Auto-Generated Files — Do NOT Hand-Edit

- `dm-api/alembic/versions/` — generate with `alembic revision --autogenerate`
- `dm-ui/dist/` — Vite build output
- `dm-ui/node_modules/` — npm install output

---

## Reviewer Checklist

Before treating any task as done, verify:

- [ ] No raw string literals for `CharacterClass`, `DamageType`, `Condition`, `Ability`, `Skill`, `ActionType`
- [ ] No `char: dict` or `combat_state: dict` in public function signatures
- [ ] No file exceeds 400 LoC without a noted exception comment at the top
- [ ] All new public functions and methods have full type annotations
- [ ] All new features have corresponding tests; new bug fixes have regression tests
- [ ] `pytest tests/ -v` passes in both `game-engine/` and `dm-api/`
- [ ] `npx tsc --noEmit` passes in `dm-ui/`
- [ ] `npm run lint` passes with zero warnings in `dm-ui/`
- [ ] No secrets or `.env` files staged for commit
