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

`PT-<n>` is a simple incrementing id — next id is **PT-15**.

---

## Open

### PT-14 — AI co-DM emits no proposals for a whole session: invented NPCs/locations are never capturable, and LOCATION never gets set
- **Status:** open
- **Severity:** major
- **Type:** bug
- **Phase:** 2–5 (Story hook / Dialogue / Travel / Map)
- **Found:** runs/2026-06-29-second-pass.md
- **Steps:** Through the DM chat, ran a full 4-turn narrative arc (open scene → NPC dialogue → travel to a clearly-new named location → wind-down), each turn introducing durable entities by name (Harbormaster Aldric Gosse, Petra Maren, the lightkeeper, and a brand-new location "the Saltmarsh Light" / the keeper's cottage).
- **Observed:** **Zero proposal cards** appeared across the entire session. The orchestrator logged `proposals=none` on all four turns; `GET /api/ai/sessions/{id}/proposals` returns `[]`; none of the 8 stored messages contains a `[PROPOSAL]` marker — so the model never emitted the blocks (it is **not** a parse/drop bug). Consequently the **LOCATION sidebar stayed "No location set"** the whole session, and there was **no way for the DM to accept/capture** Aldric, Petra, or the lighthouse as real entities. The Phase 3 "accept at least one proposal" check and the Phase 4 "new location arrives as a proposal" check could not be exercised at all. A downstream symptom: continuity drifted (the lightkeeper, implied to be Petra's *father* in turn 1, became "Edda Maren … she" by the wind-down) — with no accepted entities there is no canonical roster in the world context to anchor names.
- **Expected:** Per the system prompt's **STRUCTURED PROPOSALS** directive (`dm-api/src/dm_api/ai/prompts/system_prompt.py:129-145`: "When you introduce a new location, character, dungeon… append a machine-readable proposal block"), introducing a new named NPC or location should append a `[PROPOSAL]` block, surface a proposal card, and on accept create the entity / set the location. The whole proposal→entity→location→map pillar depends on this.
- **Evidence:** API log `proposals=none` ×4 (turns at 22:09/22:11/22:13/22:17, model claude-sonnet-4-6 via claude_cli); `proposals` endpoint `[]`; messages scan = 0 `[PROPOSAL]` markers; LOCATION sidebar "No location set" screenshots throughout.
- **Notes:** **Nondeterministic model compliance** — the 2026-06-26 first pass got 2 proposals from the same model/backend; this run got none. So the mechanism is wired correctly end-to-end but the AI silently fails to emit proposals, and there is **no UI fallback** to create a location/NPC by hand (Create Character is PC-only). Because that fallback is missing, an AI that "forgets" to propose leaves the world permanently empty — locations never exist, so even map-for-a-place and any location-scoped feature can't be reached. Worth hardening: (a) reinforce/repeat the proposal directive (and/or a post-turn check that re-prompts for proposals when new proper nouns appear), and/or (b) add a manual "create location / NPC" affordance so the DM isn't fully dependent on AI compliance.

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
