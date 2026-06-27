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

### PT-12 — Combat is unwinnable through the UI: Start Combat enrolls nobody (+ monsters have no stats)
- **Status:** open
- **Severity:** blocking
- **Type:** bug
- **Phase:** 6 — Combat
- **Found:** runs/2026-06-26-first-pass.md
- **Steps:** With a party and an accepted hostile (Cinder Hound) present, click **Start Combat** in the combat tracker.
- **Observed:** Combat starts (`COMBAT · ROUND 1`) but shows **"No combatants in initiative order"** — the Attack/Dash/Dodge and Next Turn controls are all disabled, and the battle map goes **blank** ("Tokens appear here once characters join…"). Neither the party nor the monster is enrolled. The combat is completely empty and there is no UI to add anyone.
- **Root cause (two stacked blockers):**
  1. The API `POST /sessions/{id}/combat` accepts `character_ids: list[UUID] = []` (`db/models/combat.py:66` `StartCombatRequest`, enrolled in `api/combat.py:106`), but the UI client sends **no body** — `startCombat: POST /sessions/{id}/combat` with `{ method: "POST" }` and no `character_ids` (`dm-ui/src/api/client.ts:321`). So it always rolls initiative for an empty set. There is also no combatant-selection UI.
  2. Even if the UI sent ids, **AI-proposed monsters have no combat stats** (HP/AC/ability scores) — the Cinder Hound proposal carried only narrative fields — and there is **no UI to set them** (the wizard is PC-only; PATCH is Swagger/DM-token-only). running-a-game.md confirms combat start 422s such characters. So a UI-only DM cannot field an AI-generated enemy at all.
- **Expected:** Start Combat should enroll the relevant combatants (at minimum the party, plus a way to pick which present NPCs/monsters join), i.e. send `character_ids`. And there must be a UI path to give an accepted monster/NPC combat stats (a stat-block editor, or AI proposals should include a full stat block for MONSTER-type characters). Without both, the entire combat pillar is inaccessible from the UI.
- **Evidence:** Post-"Start Combat" screenshot (empty initiative, blank map); api log `POST /combat 201`; code refs above.
- **Notes:** This blocks Phase 6 for UI-only play. Combat resolution itself (engine) was NOT reachable this run because nothing could be enrolled via the UI. Highest-impact fix: have `startCombat` send the party (and selected present hostiles) and surface a combatant picker; pair with a monster stat-block path (relates to PT-2's "AI characters lack combat stats / no UI to set them"). **Compounding cause:** the ended session's `player_character_ids` was `null` (confirmed via `GET /api/sessions/{id}`) — PCs built in the wizard are attached to the *world* but never enrolled into the *session*, so even a smarter Start Combat has no party list to draw from. The New Session form also doesn't let you pick PCs (they don't exist yet at that point). Worth fixing session↔PC linkage generally; it likely also affects any session-scoped party feature. **Deferred** in the PT-1..PT-13 fix pass (explicitly out of scope) — still open.

## Resolved

_Fixed in the PT-1..PT-13 fix pass (branch `claude/jolly-lehmann-aafa53`). PT-12 remains open (deferred)._

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
- **PT-2 weapon-mastery picker:** the wizard still can't *set* masteries in-UI
  (only the warning text was fixed). A mastery-selection step for classes that
  get masteries at level 1 (Fighter: 3) is worth adding.
