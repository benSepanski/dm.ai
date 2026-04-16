# Code Review Guidelines

This guide helps reviewers quickly identify and address common code quality issues in dm.ai PRs.

---

## Checklist for Every Review

### Code Style & Type Safety ✅

- **No magic strings for game concepts** — `DamageType.FIRE` not `"fire"`, `CharacterClass.ROGUE` not `"Rogue"`
  - Approved magic strings: human-readable display text, error messages, raw user input (before validation)
  - Forbidden magic strings: enum-like concepts, domain logic, business rules
  
- **No untyped `dict` parameters** — use typed dataclasses (`CharacterSheet`, `CombatStateData`, etc.)
  - Exception: method that explicitly deserializes unknown JSON structures

- **All public functions have type hints** — including explicit return types
  - Use `from __future__ import annotations` at file top for forward refs

- **All public classes/functions have docstrings** — Google style (Args, Returns, Raises)

### File & Function Length 📏

**Immediate request for refactoring if:**
- Production file exceeds **400 lines** without a noted exception comment at the top
- Test file exceeds **600 lines** without a noted exception
- Function exceeds **~30 lines** without inline comments explaining complex sections

**Acceptable exceptions (require comment):**
- Data tables (e.g., `spells.py`, `monsters.py`) — mark at top: `# NOTE: This file intentionally exceeds 400 lines...`
- Generated files (e.g., Alembic migrations)
- Flat configuration files

### Test Coverage 🧪

- **New features must have tests** — at least happy path + one edge case
- **Bug fixes must have regression tests** — reproduces the bug, then verifies the fix
- **Deleted code must have associated test cleanup** — remove tests for deleted functions
- **Coverage should not decrease** — game-engine target ≥75%, dm-api target ≥70%

### CI/CD Status 🔄

- **All checks must pass** — no red X's on the PR
- **Linting, type checking, and tests must pass locally** before opening PR:
  ```bash
  # game-engine
  cd game-engine && black src/ tests/ && isort src/ tests/ && autoflake -r --in-place src/ tests/ && mypy src/ && pytest tests/ -v
  
  # dm-api
  cd dm-api && black src/ tests/ && isort src/ tests/ && autoflake -r --in-place src/ tests/ && mypy src/ && pytest tests/ -v
  
  # dm-ui
  cd dm-ui && npm install && npx tsc --noEmit && npm run lint
  ```

---

## Architecture & Design 🏗️

### game-engine Principles

- **Rule system agnostic** — all D&D-specific logic lives in `game_engine/rules/dnd_5_5e/`
- **One responsibility per file** — split large modules into focused helpers
- **Delegation pattern** — `RuleEngine` methods delegate to core helpers (dice, conditions, combat, initiative, character)
- **No FastAPI in game-engine** — it's a pure Python library

### dm-api Principles

- **One route handler per resource** — `characters.py`, `combat.py`, `locations.py`, etc.
- **Async throughout** — `async def`, `await`, proper SQLAlchemy async session handling
- **AIBackend abstraction** — new AI providers must subclass `AIBackend` in `ai/backends/base.py`
- **No business logic in routes** — extract to service layer or `dm_orchestrator.py`

### dm-ui Principles

- **One component per file** — tightly coupled sub-components in same directory
- **Zustand for shared state** — use `useGameStore()` for data needed by multiple components
- **No CSS files** — inline styles only (prototype pattern)
- **Strict TypeScript** — no `any` without ESLint disable comment explaining why

---

## Common Red Flags 🚩

| Issue | Action |
|---|---|
| `isinstance(x, dict)` fallback logic | Request refactor — use typed dataclasses consistently |
| String literals for `DamageType`, `Condition`, `Ability`, etc. | Request enum usage — these are non-negotiable |
| Functions > 30–40 lines without comments | Request breakdown into helpers |
| File > 400 lines without exception comment | Request refactor at natural seam points |
| Missing tests for new public API | Request test cases before approval |
| Type errors in `mypy` output | Request fixes — strict mode is enforced |
| ESLint warnings in dm-ui | Request fixes — zero warnings policy |
| Coverage decreased | Request additional tests to maintain threshold |

---

## Reviewer Workflow

1. **Skim the PR description** — understand the goal and affected areas
2. **Check CI status** — if red, ask author to fix before detailed review
3. **Review file-by-file** — look for the red flags above
4. **Spot-check tests** — happy path + edge case?
5. **Request changes as needed** — be specific ("line X: use `CharacterClass.ROGUE`")
6. **Approve only when confident** — sign off on code quality, not just "looks good"

---

## Tone & Communication

- **Be constructive** — "Can you extract this to `_helpers.py` for clarity?" not "This is too long"
- **Reference the guides** — "See AGENTS.md § No magic strings for game concepts"
- **Praise good practices** — note elegant solutions and good test coverage
- **Be consistent** — same standards apply to all contributors

---

## Examples

### ✅ Good Type Usage

```python
from game_engine.types import DamageType, Condition, CharacterSheet

def apply_damage(target: CharacterSheet, amount: int, damage_type: DamageType) -> CharacterSheet:
    """Apply damage to a target, accounting for resistances.
    
    Args:
        target: Character taking damage.
        amount: Damage in HP.
        damage_type: Type of damage (fire, cold, etc.).
    
    Returns:
        Updated CharacterSheet with damage applied.
    """
    ...
```

### ❌ Bad Type Usage

```python
def apply_damage(target: dict, amount: int, damage_type: str) -> dict:
    # No type safety, no IDE support, silent bugs
    if damage_type == "fyre":  # typo!
        ...
```

### ✅ Good Test

```python
def test_rogue_sneak_attack_applies_once_per_turn():
    """Rogue sneak attack should only apply once per turn."""
    rogue = create_test_character(char_class=CharacterClass.ROGUE)
    target = create_test_character()
    
    # First attack in round — sneak attack applies
    result1 = rogue_engine.resolve_action(...first_attack...)
    assert result1.damage == base_damage + sneak_attack_bonus
    
    # Second attack in same round — sneak attack should NOT apply
    result2 = rogue_engine.resolve_action(...second_attack...)
    assert result2.damage == base_damage  # no bonus
```

### ❌ Bad Test

```python
def test_damage():
    # No setup, no assertion, doesn't test anything
    apply_damage({"hp": 10}, 5, "fire")
```

---

## See Also

- [AGENTS.md](../AGENTS.md) — AI coding standards (no magic strings, typed dataclasses, file length)
- [CONTRIBUTING.md](../CONTRIBUTING.md) — all contributor processes
- [docs/architecture.md](../docs/architecture.md) — system design overview
