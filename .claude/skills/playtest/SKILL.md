---
name: playtest
description: Boot the dm.ai stack locally (no Docker/Postgres/Redis) and playtest the UI in a headless browser. Use when asked to run the app, playtest the UI, verify a UI/API change end-to-end, or take screenshots of the dashboard.
---

# Playtesting dm.ai

Everything runs locally: SQLite instead of Postgres, in-memory WebSocket
fan-out instead of Redis, and the `claude` CLI as the AI backend (no
`ANTHROPIC_API_KEY` needed). Docker is NOT required.

## Boot / manage the stack

```bash
scripts/playtest.sh start    # installs deps if needed, boots API :8000 + UI :5173
scripts/playtest.sh smoke    # end-to-end browser playtest (Playwright, asserts AI reply)
scripts/playtest.sh stop     # stop both servers
scripts/playtest.sh reset    # stop + wipe the SQLite DB (.playtest/dm.db)
scripts/playtest.sh status   # what's running
```

Logs: `.playtest/api.log`, `.playtest/ui.log`. Screenshots from the smoke
test: `.playtest/shots/`.

The script defaults `ORCHESTRATOR_MODEL` to Haiku so playtest chat turns
return in ~5-10 s. Export `ORCHESTRATOR_MODEL=claude-sonnet-4-6` before
`start` for full-fidelity narrative turns.

## Driving the UI yourself (ad hoc playtests)

Use the `playwright` npm package (globally installed in agent sandboxes;
Chromium lives at `$PLAYWRIGHT_BROWSERS_PATH` or `~/.cache/ms-playwright`,
install with `playwright install chromium` if missing). Write a CommonJS
script and run it with the global module path:

```bash
NODE_PATH="$(npm root -g)" node your_script.cjs
```

Key facts for driving the app (see `scripts/playtest_smoke.cjs` for a
working example):

- `http://localhost:5173/` shows the new-session form (two `input`s +
  "Start Session" button) in a fresh browser context; creating a session
  navigates to `/session/<uuid>`, the shareable session URL.
- Chat input: `[data-testid="chat-input"]`; press Enter to send.
- Messages render as `[data-testid="chat-message"]` with
  `data-role="dm" | "ai" | "system"`. The AI reply arrives via WebSocket —
  wait for the `data-role="ai"` locator (allow up to ~150 s).
- AI world-building proposals appear as cards in the right panel with
  Accept/Reject buttons; combat is driven from the right-panel
  CombatTracker ("Start Combat").
- Characters/monsters with combat stats are created via the REST API
  (`POST /api/characters/` — see docs/running-a-game.md) or the
  "Create Character" wizard.

## Verifying changes

API-only checks can skip the browser: `curl http://localhost:8000/health`,
interactive docs at `http://localhost:8000/docs`. After code changes the
API needs a restart (`stop` + `start` — uvicorn runs without --reload
here); vite hot-reloads UI changes automatically.
