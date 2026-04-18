# dm.ai — AI-Assisted D&D Game Engine

## Harness-Engineering Principles (apply to every AI-touching change)

This repo follows OpenAI's harness-engineering playbook
(<https://openai.com/index/harness-engineering/>). AI-related work must
encode constraints into machine-readable artifacts, not free-form prose.

1. **The repository is the single source of truth.** AGENTS.md, CLAUDE.md,
   docs/architecture.md, and structural tests outrank any out-of-repo hint or
   cached recall. If a fact isn't in the repo, it doesn't exist for the agent.
2. **Layered architecture, mechanically enforced.** Dependencies flow:
   `Types → Config → Repo → Service → Runtime → UI`. No upward imports. Any
   violation is a bug, not a refactor opportunity.
3. **Typed boundaries everywhere.** No `dict[str, Any]` crosses a module's
   public surface. Every AI sub-agent's output is validated against a
   dataclass at the boundary before entering typed internals.
4. **Citation anchors (filepath:line analog).** When condensing or
   summarising, preserve anchors so condensed output traces back to the
   source row. Chat anchors use `msg:<uuid>@<iso-timestamp>`.
5. **Focused, narrow sub-agents.** Each AI sub-task gets its own small
   prompt, fast model (Haiku), and typed output schema. No role-play, no
   bundled instructions. Keep prompts < ~60 lines.
6. **Silent on success, loud on failure.** Verification hooks and the
   condenser are no-ops when their precondition isn't met. Only emit output
   when something non-trivial happened.
7. **Depth-first decomposition.** Break larger AI tasks into
   `design → extract → validate → assemble` sub-steps that are individually
   testable.
8. **Golden principles are mechanical, not manual.** Enum-only domain fields,
   no raw-string dict schemas, and the <400-LoC file limit are enforced by
   code review and structural tests — not docstrings.
9. **Scheduled garbage collection beats live drift.** Prefer running a
   targeted refactor over patching around a drift symptom. When you
   discover an AI agent made a recurring mistake, encode the fix in AGENTS.md
   or a lint rule so it never happens again.

## Project Structure

- `game-engine/` — Rule-agnostic RPG engine with D&D 5.5e implementation (Python)
- `dm-api/` — FastAPI backend with AI orchestration (Python)
- `dm-ui/` — React/TypeScript frontend

## Code Quality Standards

### Python — Strict Type Safety

**Never use hard-coded strings where a typed enum or value type exists.**
Strings are only acceptable for:
- Human-readable display text (names, descriptions, messages)
- Handling raw user input before validation

**Replace dictionaries with dataclasses** when the key set is known at dev time.
If you find yourself writing `dict[str, Any]` or `dict[str, dict]`, define a `@dataclass` instead.

**Use validated value types** to enforce domain constraints at construction time.
Examples: `DiceNotation("2d6+3")` validates dice format, not `str`.
By encoding constraints in types, we eliminate redundant validation in business logic.

**Use enums** for any field with a known finite set of valid values.
Examples: `DamageType.FIRE` not `"fire"`, `Ability.DEXTERITY` not `"dex"`,
`CreatureSize.LARGE` not `"Large"`.

**Never create backward-compatibility aliases or legacy code paths.**
Do complete refactors instead. No `OldName = NewName` aliases, no `isinstance(x, dict)` fallbacks.

### Python — Linting & Formatting

All Python code must pass:
- `black` (line-length 99, target py311)
- `isort` (black profile, line-length 99)
- `autoflake` (remove unused imports and variables)
- `mypy` (disallow untyped defs)

Run locally before committing:
```bash
# game-engine
cd game-engine && black src/ tests/ && isort src/ tests/ && autoflake -r --in-place src/ tests/

# dm-api
cd dm-api && black src/ tests/ && isort src/ tests/ && autoflake -r --in-place src/ tests/
```

### TypeScript (dm-ui)

All frontend code must pass:
- `tsc --noEmit` (strict type checking)
- `eslint` (zero warnings)

### CI

All checks run in GitHub Actions on every push. Ensure CI passes before merging.

## Testing

```bash
# game-engine tests
cd game-engine && pytest tests/ -v

# dm-api tests (needs env vars for SQLite in-memory)
cd dm-api && DATABASE_URL="sqlite+aiosqlite:///:memory:" AI_PROVIDER="anthropic" ANTHROPIC_API_KEY="test-key" pytest tests/ -v

# dm-ui checks
cd dm-ui && npx tsc --noEmit && npm run lint
```

## Key Types (game-engine)

### Enums (`game_engine.types.enums`)
- `Ability`, `Skill`, `CharacterClass`, `CharacterType`
- `DamageType`, `Condition`, `ActionType`
- `SpellSchool`, `CreatureSize`, `CreatureType`
- `ArmorCategory`, `WeaponProperty`
- `LocationType`, `ProposalType`, `ProposalStatus`, `ChatRole`

### Value Types (`game_engine.types.values`)
- `DiceNotation` — validated dice string (e.g. `DiceNotation("2d8+4")`)

### Data Classes (`game_engine.types.sheets`)
- `CharacterSheet`, `AbilityScoreSet`, `CombatStateData`, `AttackDetails`

### Data Definitions (`game_engine.rules.dnd_5_5e`)
- `ClassData`, `SpellData`, `MonsterData`, `WeaponData`, `ArmorData`

## AI Layer (dm-api)

The AI layer lives in `dm-api/src/dm_api/ai/` and is the canonical reference
for harness-engineering patterns in this repo:

- `backends/` — `AIBackend` ABC + Anthropic SDK and claude-CLI implementations
  (the Repo/Gateway layer — AI provider access only, zero business logic).
- `prompts/` — focused sub-agent prompts (`system_prompt.py`,
  `condense_prompt.py`). Each prompt does exactly one job with an explicit
  typed output schema.
- `condenser.py` — `ContextCondenser` sub-agent with typed `HistoryMessage` /
  `CondensedContext` / `MessageAnchor` boundaries. Silent no-op under budget.
- `dm_orchestrator.py` — `DMOrchestrator` (Service layer). Depth-first
  decomposition: `condense → build messages → call backend → extract proposal`.
  Returns a typed `DMResponse`.

### Rules for new AI features

- New AI sub-agents go under `dm_api.ai.*` with their prompt in
  `prompts/<name>_prompt.py` and the orchestration in a sibling module.
- Never accept or return `dict[str, Any]` — define a `@dataclass` (or reuse
  one) for both input and output.
- The AI response is an **untrusted boundary**: parse and validate its JSON
  against the dataclass, degrade gracefully if malformed, never pass an
  unchecked shape into typed internals.
- Use the fast `generation_model` (Haiku) for narrow sub-agents; reserve the
  `orchestrator_model` (Sonnet) for full narrative turns.
- Preserve citation anchors (`msg:<uuid>@<timestamp>`) in any condensed or
  summarised artifact.
