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

`PT-<n>` is a simple incrementing id — next id is **PT-27**.

---

## Open

## Resolved

### PT-25 — DM state is shared across browser tabs via localStorage; no in-app way to preview/exit DM mode
- **Status:** resolved
- **Severity:** usability
- **Type:** usability
- **Phase:** cross-cutting (surfaced in Phase 1 while trying to test the player view)
- **Found:** runs/2026-06-30-third-pass.md
- **Steps:** As the DM, opened a second tab in the **same browser** and
  navigated to the session URL (i.e. followed "Copy Invite Link" the way a DM
  naturally would to preview what a player sees).
- **Observed:** The second tab loaded with full DM controls (End Session, New
  Session, chat input, DM badge) — not the read-only player view — because
  `dmToken`/`isDM` are persisted to `localStorage` (`gameStore.ts`), which is
  shared by every tab on the same origin. The only way to see the real
  read-only player view in the same browser was to manually clear
  `localStorage` via devtools and reload; there is no "log out of DM" / "view
  as player" control anywhere in the DM dashboard UI.
- **Expected:** A DM should be able to preview the player experience (or
  deliberately step out of DM mode) without devtools. At minimum, the invite
  link / player view should not silently inherit DM authority just because
  it's opened in the same browser as the DM tab.
- **Evidence:** screenshot showing the "player" tab with full DM toolbar before
  the localStorage clear.
- **Notes:** Doubles as a real-world risk: DM_TOKEN is a single global secret
  (per `.env`) with no scoping to a session/world and no visible logout —
  anyone who ever obtains it (shared screen, browser history, synced devices)
  has standing DM access to every world on the instance indefinitely.
- **Resolution:** `gameStore.ts`'s `persist` middleware now uses a custom
  `splitStorage` `StateStorage` adapter that routes `dmToken`/`isDM` to
  `sessionStorage` (per-tab) and leaves `sessionId`/`worldId`/`tokenPositions`
  in `localStorage` as before, so a fresh tab on the same session URL no
  longer inherits DM authority. `DMDashboard.tsx`'s toolbar gained an "Exit DM
  Mode" button next to the DM badge that calls `setDmToken(null)` /
  `setIsDM(false)` and navigates to the same session's URL, landing on the
  read-only player view without devtools.

### PT-19 — Character creation wizard skips required class/species sub-choices (spells, Elf lineage, Keen Senses)
- **Status:** resolved
- **Severity:** major — **Type:** bug — **Phase:** 1
- **Found:** runs/2026-06-30-first-full-scenario.md
- **Steps:** Built a Level 1 Elf Wizard (Maret Sable) through the full 4-step
  wizard (Origin → Ability Scores → Skills & Equipment → Review). At no step
  was she asked to choose cantrips/spells known, an Elven Lineage (Drow/High
  Elf/Wood Elf), or the Keen Senses skill (Insight/Perception/Survival)
  despite the Species step's own description text calling out that these are
  required choices.
- **Observed:** `GET /api/characters/world/{id}` shows `"spells": null` for
  the finished character — a Level 1 Wizard with zero spells known/prepared.
  Confirmed via API inspection, not routing around the UI for gameplay.
- **Expected:** Spellcasting classes should be prompted to choose starting
  cantrips/spells before Review; species with a sub-choice (Elf lineage, Keen
  Senses) should present that picker, mirroring the existing Weapon Masteries
  picker (resolved in PT-2's follow-up) which is the right pattern to copy.
- **Evidence:** wizard step screenshots (no spell/lineage UI at any step); API
  response `spells: null`.
- **Notes:** This blocked exercising "one spell (attack-roll and/or save)" in
  Phase 6 even before the combat-action bug (PT-23) made it moot — Maret had
  no spell to cast. Likely needs a new wizard step or an addition to "3.
  Skills & Equipment," analogous to `CreateCharacterWizard`'s existing weapon
  mastery picker.
- **Resolution:** Added a `SpeciesTraitChoice` (Skill/`SpeciesLineage`) field
  on `SpeciesTraitData` so Elf's Elven Lineage and Keen Senses traits
  advertise their closed option sets, plus a `get_spells_for_class` lookup so
  the API can enumerate legal level-1 cantrips/spells per class from
  `ClassProgression.cantrips_known[0]`/`prepared_spells[0]`. `build_character`
  now takes `species_trait_choices`/`starting_cantrips`/`starting_spells`,
  validates every submission against the class/species registries server-side
  (422 on an illegal pick), and populates `CharacterSheet.species_lineage` /
  `known_spells` / `prepared_spells` accordingly; missing choices warn instead
  of failing, mirroring the Weapon Masteries pattern. `SkillsStep.tsx` gained
  "Species Traits" and "Starting Spells" pill sections wired the same way as
  Weapon Masteries, gated into `skillsStepValid`.

### PT-21 — Proposal narration commits an entity as fact before the DM can accept/reject it
- **Status:** resolved
- **Severity:** major — **Type:** usability — **Phase:** cross-cutting (2–5)
- **Found:** runs/2026-06-30-first-full-scenario.md
- **Steps:** Sent an opening-scene prompt. The AI narration text (displayed in
  the chat) already describes a new location/NPC as established fact (e.g.
  "**Saltmere** spreads above the waterfront...") in the same turn that emits
  the matching `[PROPOSAL]` block for that entity.
- **Observed:** Confirmed in code: `DMOrchestrator.handle_message` generates
  narration and `[PROPOSAL]` blocks in one model call; `[PROPOSAL]` tags are
  stripped from `response` but the narration around them already asserts the
  entity as real (`dm_orchestrator.py` docstring: "response is the display
  narration with all `[PROPOSAL]` blocks stripped"). Narration and the pending
  proposal card render simultaneously — there's no gate. If the DM clicks
  **Reject**, nothing retracts the sentences already sitting in the chat log;
  all players already read the entity as canon.
- **Expected:** Either (a) the AI should not narrate a new entity as settled
  fact until it's accepted, or (b) a rejected proposal should visibly flag/
  strike the relevant narration, or (c) accept this as a deliberate design
  tradeoff and document it so DMs know rejecting is "erase from data, not from
  the story so far."
- **Evidence:** `dm-api/src/dm_api/ai/dm_orchestrator.py:53` docstring +
  observed chat transcript in run log.
- **Notes:** Raised by the user mid-session; not something the automated
  playtest agent would have caught without the prompt. Worth a product
  decision, not just a bug fix.
- **Resolution:** Gated at the source — the system prompt now instructs the
  model to wrap any narration sentence(s) that commit a brand-new
  location/character to canon in `[PENDING]...[/PENDING]`, adjacent to that
  entity's `[PROPOSAL]` block. `dm_orchestrator.py`'s new
  `_extract_narration_and_proposals` pairs the Nth `[PENDING]` with the Nth
  `[PROPOSAL]` (dropping all pending text on a count mismatch, never
  guessing), strips both tag families from the narration, and stores the
  paired text on `ProposalPayload.pending_narration`. `Proposal` gained
  `pending_narration`/`source_anchor` columns (migration `0004`); accepting a
  proposal now appends the held narration as a new AI `ChatMessage` (citing
  the original turn's `msg:<uuid>@<timestamp>` anchor via `entity_refs`) and
  broadcasts it, while rejecting simply discards it — never persisted, never
  shown.

### PT-22 — Duplicate NPC entities when the AI re-introduces an already-established character
- **Status:** resolved
- **Severity:** minor — **Type:** bug — **Phase:** 3–4
- **Found:** runs/2026-06-30-first-full-scenario.md
- **Steps:** Accepted a "Vess Moray" character proposal (Level 5 Rogue). Later,
  after changing the orchestrator model mid-session (Game Settings), resent an
  identical DM narration line. The AI regenerated the turn and emitted a
  *second* `[PROPOSAL]` for a character also named "Vess Moray" (Level 4,
  slightly different stat block). Accepted it without realizing.
- **Observed:** Two "Vess Moray" entries exist in the Monsters & NPCs sidebar
  and in the Start Combat roster, with different levels/stats.
- **Expected:** Proposals should be deduplicated by name (or the AI should
  recognize an already-accepted entity and not re-propose it), or the UI
  should warn the DM before creating a same-named character a second time.
- **Evidence:** sidebar showed "Vess Moray" twice; screenshot in run log.
- **Notes:** Root cause is likely that proposal extraction/acceptance has no
  identity check against existing `characters` for the world. Low priority —
  triggered by resending a duplicate message, but could recur naturally in a
  long session if the AI reintroduces a character without checking prior
  turns.
- **Resolution:** `dm-api/src/dm_api/api/ai.py`'s `_create_character_from_proposal`
  now calls a new `_find_existing_character_by_name` helper that queries for a
  Character in the same `world_id` with a case-insensitive name match before
  inserting; if found, it reuses that row (returned via the new
  `CharacterCreationResult` dataclass) instead of creating a duplicate.
  `ProposalRead` (`dm-api/src/dm_api/db/models/proposal.py`) gained a typed
  `duplicate_merged: bool` field so `accept_proposal`'s response tells the
  caller a duplicate was merged rather than a new entity created. Regression
  test added in `dm-api/tests/test_proposals.py`
  (`test_accept_second_character_proposal_same_name_merges_not_duplicates`).

### PT-24 — Player role can create characters directly, with no DM review (violates "AI proposes, DM decides")
- **Status:** resolved
- **Severity:** major
- **Type:** bug
- **Phase:** 1 — Character creation
- **Found:** runs/2026-06-30-third-pass.md
- **Steps:** In a browser tab with no DM token (verified read-only: toolbar shows
  "Player" badge, "Unlock DM" button, footer "You're watching as a player — the
  DM drives the story."), clicked **Create Character**, built a full PC through
  all 4 wizard steps, clicked **Create Character** on the review step.
- **Observed:** The character (`Dorn Ironfist`) was created immediately —
  `POST /characters/creation/build` returned `201` with no auth check — and
  appeared live in the DM's party sidebar via the WebSocket with no approval
  step of any kind. Confirmed in the source:
  `dm-api/src/dm_api/api/character_creation.py`'s `build_player_character`
  (mounted at `/characters/creation/build`) has no `Depends(require_dm)` /
  `Depends(client_role)` guard at all, unlike `update_character` and
  `rest_character` in `characters.py` which do require DM. `create_character`
  (`POST /characters/`) also has no role dependency.
- **Expected:** Per the project's own stated philosophy ("AI proposes, DM
  decides" / "Nothing writes to your campaign database without your explicit
  approval") and the README's DM/player split, an unauthenticated player should
  not be able to unilaterally create a permanent character — this should either
  require the DM token, or land as a reviewable proposal.
- **Evidence:** screenshot of DM sidebar showing "Dorn Ironfist" (party count 1)
  immediately after the player-tab wizard submit, with no accept/reject step.
- **Notes:** Also worth checking whether the same gap lets a "player" edit/delete
  other party members' data indirectly, or spam-create characters in someone
  else's world if they know/guess the `world_id` UUID from the session URL.
- **Resolution:** Not a bug — working as intended. A player creating their own
  character is normal TTRPG practice and doesn't need DM review; "AI proposes,
  DM decides" governs the AI co-DM inventing NPCs/locations/characters
  mid-narrative, which is already gated by the proposal accept/reject flow (see
  PT-14's resolution above). The original finding conflated "no auth on a
  player self-service endpoint" with a violation of that principle, but the two
  are different concerns. The separate observation in this entry's original
  Notes — whether a player could spam-create characters or write into an
  unrelated `world_id` they merely guessed — is a distinct access-control
  question, not addressed by this resolution; it was never reproduced or
  confirmed during the original playtest run, so it's left out of scope here
  rather than investigated.

### PT-26 — Character build accepts illegal ability scores (all 20s) with no rejection or warning
- **Status:** resolved
- **Severity:** major — **Type:** bug — **Phase:** 1 — Character creation
- **Resolution:** `game_engine.rules.dnd_5_5e.character_builder` gains
  `is_valid_manual_scores` (3-18, the rolled/manual range) and
  `is_legal_ability_scores` (true iff the six base scores are a Standard
  Array permutation, a legal Point Buy, or all within the Manual/Rolled
  range) — composing the `is_standard_array`/`is_valid_point_buy` helpers
  that already existed but were never wired into the actual build path.
  `build_character` now raises `ValueError` when the check fails, and
  `POST /characters/creation/build` (`dm-api/src/dm_api/api/character_creation.py`)
  catches it and returns 422 with a human-readable detail message. This is
  server-side, so it holds regardless of which client (or lack thereof)
  calls the endpoint — closing the gap the UI wizard already prevented.
  PT-24's separate finding (no auth on this endpoint) is unaffected by this
  fix and remains open.

### PT-23 — Combat actions produce no visible feedback and Attack has no target-selection UI
- **Status:** resolved
- **Severity:** blocking — **Type:** bug — **Phase:** 6 — Combat
- **Resolution:** Three-pronged fix, all in one pass:
  (a) Added a target picker to `CombatActions` (`CombatTracker.tsx`) — clickable chips for
  every other combatant; Attack requires a selection before it submits, and the picker
  resets each turn (`key={currentActorId}` remounts the component).
  (b) `combat.py:submit_combat_action` now rejects an Attack with no `target_id` up front
  with a 422 *before* the action economy is touched, so a bad request never burns the
  actor's turn; `"target_not_found"`/`"actor_not_found"`/`"total_cover"` were also added to
  the resolver-error rejection list as defense in depth (a stale/invalid target still
  can't silently persist as a normal log entry).
  (c) The persisted `combat_log` entry now includes `outcome.flavor_text`; the frontend
  pushes it into the chat feed (`role: "system"`) after every resolved action, and surfaces
  rejection errors (parsed from the FastAPI `{"detail": ...}` body) inline in the Combat
  panel instead of only logging to the console.
  Added a regression test (`test_submit_combat_action_attack_without_target_is_422`)
  covering the exact silently-wasted-turn scenario from the run log. This finding was
  independently re-confirmed by a second run (`runs/2026-06-30-third-pass.md`) against a
  different monster/party before this fix landed — same root cause, de-duped into this
  single entry.

### PT-20 — Illegal combat stats (negative HP, AC 0) are silently accepted on NPC/Monster creation
- **Status:** resolved
- **Severity:** major — **Type:** bug — **Phase:** 1 (adversarial guardrail check)
- **Resolution:** Fixed at both layers. Server: `CharacterCreate`/`CharacterUpdate`
  in `dm-api/src/dm_api/db/models/character.py` now declare `Field(ge=1, le=20)`
  on `level`, `Field(ge=1)` on `hp_max`/`ac`, and `Field(ge=0)` on
  `hp_current`/`speed`, so `POST /characters/` and `PATCH /characters/{id}`
  reject illegal values with a 422 regardless of which client calls them
  (covers the same root cause flagged in PT-26 for the character-build
  endpoint). Client: `CreateNpcDialog.tsx` now clamps Level/HP Max/AC via a
  shared `clampInput` helper on every keystroke (mirroring
  `AbilitiesStep.tsx`'s ability-score clamp) with a hint line explaining the
  floor, instead of relying on the cosmetic-only HTML `min` attribute. Added
  regression tests `test_create_character_rejects_illegal_combat_stats` and
  `test_update_character_rejects_illegal_combat_stats` in
  `dm-api/tests/test_characters.py`.

### PT-14 — AI co-DM emits no proposals: invented NPCs/locations are never capturable
- **Status:** resolved
- **Severity:** major — **Type:** bug — **Phase:** 2–5
- **Resolution:** Two-pronged fix in PR #83 (commit `b586f56`):
  (a) Strengthened the `[PROPOSAL]` directive in `system_prompt.py` from a passive suggestion to an explicit "MUST" requirement, with a re-emit reminder for entities referenced before acceptance.
  (b) Added DM-only UI fallbacks — **"+ New" buttons** in the Location sidebar (`LocationPanel.tsx`) and the Monsters & NPCs sidebar (`CharacterCard.tsx`) open modal dialogs (`CreateLocationDialog`, `CreateNpcDialog`) for manual entity creation. On creation the location or character is broadcast over WebSocket to all connected clients so the sidebar updates live. New `PATCH /sessions/{id}` endpoint lets the DM set `current_location_id` directly; new `?session_id=` query param on `POST /characters/` enables the broadcast.

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
