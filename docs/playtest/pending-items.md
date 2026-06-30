# Playtest Pending Items

The running backlog of bugs and usability issues found during
[agentic UI playtests](./README.md). Newest at the top of **Open**. When an item
is fixed, move it to **Resolved** with the commit/PR that closed it.

This file is the durable signal across runs — keep it honest. A growing list is
fine; a list that hides known problems is not.

## Entry format

```
### PT-<n> — <one-line title>
- **Status:** open | resolved
- **Severity:** blocking | major | minor
- **Type:** bug | usability
- **Phase:** <scenario phase, e.g. "6 — Combat">
- **Found:** <run log filename, e.g. runs/2026-06-26-first-pass.md>
- **Steps:** what you did, through the UI.
- **Observed:** what actually happened.
- **Expected:** what should have happened.
- **Evidence:** screenshot reference / API or console error / log excerpt.
- **Notes:** hypotheses, suspected file, workaround if any.
```

`severity`: **blocking** = can't proceed through the UI; **major** = wrong or
broken but routable around; **minor** = cosmetic or small friction.
`type`: **bug** = behaves incorrectly; **usability** = behaves as built but is
hard/confusing/missing an affordance a real player or DM would expect.

`PT-<n>` is a simple incrementing id — next id is **PT-14**.

---

## Open

_No open items. Next id is **PT-14**._

## Resolved

### PT-12 — Combat is unwinnable through the UI: Start Combat enrolls nobody (+ monsters have no stats)
- **Status:** resolved
- **Severity:** blocking — **Type:** bug — **Phase:** 6 — Combat
- **Resolution:** Replaced the no-op `startCombat()` call (sent an empty body) with a
  **"Start Combat" dialog** (`CombatTracker.tsx`). The dialog lists all world characters
  grouped as Party / Monsters & NPCs. PCs are pre-checked; monsters are optional. Any
  selected character missing `hp_max` or `ac` gets inline number inputs — on **Begin
  Combat** those values are PATCHed first via the existing `PATCH /characters/{id}`
  endpoint, then `POST /sessions/{id}/combat` is called with the full `character_ids`
  list. `CharacterCard.tsx` also now shows a **Monsters & NPCs** section below the Party
  so DMs can see the roster at a glance. `client.ts` gained `patchCharacter()` and the
  `startCombat()` signature now requires `characterIds: string[]`.

### PT-13 — End Session uses a blocking native confirm()
- **Status:** resolved
- **Severity:** minor — **Type:** usability — **Phase:** 8
- **Resolution:** Replaced `window.confirm()` with a reusable in-app
  `ConfirmDialog` (`dm-ui/src/components/common/ConfirmDialog.tsx`), wired into
  End Session in `DMDashboard.tsx`. It was the only `confirm()`/`alert()` use in
  the app.

### PT-11 — Friendly NPC shows as a red "enemy" token, and appears out of scene
- **Status:** resolved
- **Severity:** major — **Type:** bug — **Phase:** 5
- **Resolution:** `BattleMap.tsx` now colors tokens by `CharacterType`
  (PC=blue, NPC=green/ally, MONSTER=red), shows only the party (PCs) outside
  combat (no character→location model exists, so PCs are the safe subset), and
  widened the label truncation so "Maret" no longer reads "Mare".

### PT-10 — Chat does not render markdown
- **Status:** resolved
- **Severity:** major — **Type:** usability — **Phase:** 2 (every AI turn)
- **Resolution:** Added `react-markdown` + `remark-gfm`; a themed
  `ChatMarkdown` component renders DM/AI messages (bold, italics, blockquotes,
  rules, lists). react-markdown is XSS-safe (no raw HTML). System messages stay
  plain.

### PT-9 — Hard to know where game data/config lives and how to run independent games
- **Status:** resolved
- **Severity:** major — **Type:** usability — **Phase:** cross-cutting
- **Resolution:** Added an "Operating your game" section to
  `docs/running-a-game.md` (which `.env` is in effect, `DM_TOKEN` behavior,
  where data lives + pg_dump backup/restore, running independent stacks via
  `docker-compose -p`, provider↔runtime coupling). Effective config is now also
  observable on `/health` (PT-4).

### PT-8 — Manual/Rolled ability entry clamps silently
- **Status:** resolved
- **Severity:** minor — **Type:** usability — **Phase:** 1
- **Resolution:** `AbilitiesStep.tsx` shows a "Base scores must be 3–18 …" hint
  for the manual method. The clamp behavior is unchanged.

### PT-7 — Dockerized api can't use `AI_PROVIDER=claude_cli`
- **Status:** resolved
- **Severity:** major — **Type:** bug — **Phase:** 2
- **Resolution:** Documented plainly in `docs/running-a-game.md` and
  `README.md` that `claude_cli` requires running the API on the host (not in
  the Docker image); the Docker stack uses `anthropic`. `/health` now reports
  `ai_ready` to catch a missing CLI before play.

### PT-6 — Read-only player view still shows the chat input + Send
- **Status:** resolved
- **Severity:** major — **Type:** bug — **Phase:** cross-cutting
- **Resolution:** Already fixed in the current code and verified: the chat
  input is gated on `isDM` (defaults `false`) in `DMDashboard.tsx`, and the
  server route `POST /sessions/{id}/chat` is `require_dm`-gated. The original
  spectator report predates both gates.

### PT-5 — New characters don't appear on player clients without a manual refresh
- **Status:** resolved
- **Severity:** major — **Type:** bug — **Phase:** 1
- **Resolution:** The wizard build endpoint accepts an optional `session_id`
  and broadcasts an `entity_update` (`broadcast_entity_update` in `ws.py`); the
  wizard passes the active session id. The existing frontend `entity_update`
  handler refetches and upserts, so the PARTY sidebar updates live.

### PT-4 — Config (AI provider key) is not validated at startup
- **Status:** resolved
- **Severity:** major — **Type:** usability — **Phase:** 2
- **Resolution:** `check_ai_readiness` (no-network config check) runs in the
  startup `lifespan` and logs a loud warning when the backend isn't ready;
  `/health` now reports `ai_provider`, `ai_ready`, and `ai_detail`.

### PT-3 — AI provider errors surface as a bare "Internal Server Error"
- **Status:** resolved
- **Severity:** major — **Type:** bug — **Phase:** 2
- **Resolution:** Backends raise a typed `AIBackendError` with an
  `AIErrorCategory` (AUTH / RATE_LIMIT / TRANSIENT) and a DM-facing message;
  the chat route maps it to 502/429/503 with an actionable `detail` (e.g.
  "check ANTHROPIC_API_KEY") and preserves the DM's message.

### PT-2 — Wizard weapon-mastery warning leaked an internal field path
- **Status:** resolved
- **Severity:** major — **Type:** bug — **Phase:** 1
- **Resolution:** The engine warning is rephrased for humans with no internal
  field path ("Your class can choose N weapon masteries — set them later via
  character edit"). A full in-wizard mastery **picker** is deferred (tracked as
  a follow-up; the finding accepts the rephrase as the minimum fix).

### PT-1 — New Session form has no world setting/description field
- **Status:** resolved
- **Severity:** minor — **Type:** usability — **Phase:** 1
- **Resolution:** `NewSessionForm.tsx` adds an optional "World Setting"
  textarea, passed as `setting_description` to `createWorld` — seeding the AI
  co-DM's system prompt.

### Follow-ups created during the fix pass
- **PT-2 weapon-mastery picker:** resolved in PR #81. The wizard now renders a
  "Weapon Masteries" pill-picker in the Skills & Equipment step for Fighter (3),
  Barbarian (2), and Rogue (2). Weapons are filtered to class-eligible choices;
  the "Next" button requires the correct count before advancing; masteries are
  written to the character sheet on create (no more "set later" warning when
  chosen through the wizard).
