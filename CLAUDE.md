# dm.ai — AI-Assisted D&D Game Engine

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
