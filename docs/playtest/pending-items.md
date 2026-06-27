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

### PT-13 — End Session uses a blocking native confirm() (froze the page; can't complete under automation)
- **Status:** resolved
- **Severity:** minor
- **Type:** usability
- **Phase:** 8 — More discussion + End Session
- **Found:** runs/2026-06-26-first-pass.md
- **Steps:** Click **End Session** in the top bar.
- **Observed:** It triggers a synchronous native `window.confirm()` dialog. This **froze the renderer** (the automation's CDP `Input.dispatchMouseEvent` timed out after 30s on the next interaction), and native dialogs are auto-dismissed (cancelled) by browser automation, so the session never actually ended and no summary request fired. A real human can click OK, but the native dialog is unstyled, blocks the whole page, and is fragile in embedded/automated contexts.
- **Expected:** Use an in-app confirmation modal (consistent with the app's styling, non-blocking) for End Session — it's a meaningful, mostly-irreversible action and deserves a real confirm UI, not `window.confirm()`.
- **Evidence:** CDP error "Input.dispatchMouseEvent timed out … renderer may be frozen"; no `PUT /sessions/{id}/...end` request in the api log after two clicks.
- **Notes:** Same pattern likely applies to other `confirm()`/`alert()` uses (e.g. New Session?). Worth a sweep. To verify the summary feature this run, `window.confirm` was overridden to return true so the real button/endpoint could run (see run log) — the dialog mechanism is the finding, not the summary feature.

### PT-12 — Combat is unwinnable through the UI: Start Combat enrolls nobody (+ monsters have no stats)
- **Status:** open
- **Severity:** major (was blocking; PC enrollment now fixed)
- **Type:** bug
- **Phase:** 6 — Combat
- **Found:** runs/2026-06-26-first-pass.md
- **Steps:** With a party and an accepted hostile (Cinder Hound) present, click **Start Combat** in the combat tracker.
- **Observed:** Combat starts (`COMBAT · ROUND 1`) but shows **"No combatants in initiative order"** — the Attack/Dash/Dodge and Next Turn controls are all disabled, and the battle map goes **blank** ("Tokens appear here once characters join…"). Neither the party nor the monster is enrolled. The combat is completely empty and there is no UI to add anyone.
- **Root cause (two stacked blockers):**
  1. ~~The UI client sent no body to `POST /sessions/{id}/combat`.~~ **Fixed:** `startCombat` now sends all PCs with combat stats as `character_ids`.
  2. **Still open:** **AI-proposed monsters have no combat stats** (HP/AC/ability scores) — the Cinder Hound proposal carried only narrative fields — and there is **no UI to set them** (the wizard is PC-only; PATCH is Swagger/DM-token-only). running-a-game.md confirms combat start 422s such characters. So a UI-only DM cannot field an AI-generated enemy at all.
- **Expected:** A UI path to give an accepted monster/NPC combat stats (a stat-block editor, or AI proposals should include a full stat block for MONSTER-type characters). Without this, monsters can't be enrolled.
- **Evidence:** Post-"Start Combat" screenshot (empty initiative, blank map); api log `POST /combat 201`; code refs above.
- **Notes:** PC enrollment root cause fixed. Monster stat-block path still missing. Relates to PT-2 "AI characters lack combat stats / no UI to set them".

### PT-11 — [visual] Friendly NPC shows as a red "enemy" token, and appears out of scene
- **Status:** open
- **Severity:** major
- **Type:** bug
- **Phase:** 5 — Map creation
- **Found:** runs/2026-06-26-first-pass.md
- **Steps:** Accept an NPC (Maret Solde, an ally foreman) and a separate dungeon location. Open the battle map while the party is in the dungeon.
- **Observed:** Two issues: (1) Maret renders as a **red token** — red is the enemy color (party=blue, enemies=red per running-a-game.md). She's a friendly NPC, not a hostile. (2) She appears on the **mine map at all**, even though narratively she's back at the tavern (a different location); the map shows every world character regardless of which location/scene they're in.
- **Expected:** (1) Token color should reflect disposition/type — allied NPCs shouldn't use the enemy color (need an ally/neutral color, or only color red during combat for actual hostiles). (2) Outside combat the map should show the party (and characters actually present at the current location), not every NPC in the world.
- **Evidence:** Phase-5 battle-map screenshot — "Mare" red token at lower-left while "Dorn"/"Kira" are blue.
- **Notes:** Token label is also truncated ("Mare" for "Maret Solde") — minor. Disposition coloring likely keys off CharacterType (PC vs NPC vs MONSTER) rather than combat allegiance. Consider location-scoping the roster shown on the map.

### PT-10 — [visual] Chat does not render markdown; emphasis/quotes/rules show as raw syntax
- **Status:** resolved
- **Severity:** major — **top-priority readability fix (user-flagged twice during the run)**
- **Type:** usability
- **Phase:** 2 — Story hook (recurs on every AI turn)
- **Found:** runs/2026-06-26-first-pass.md
- **Steps:** Send any DM prompt; the AI narration comes back with markdown (the model uses `**bold**`, `> blockquotes`, `---` horizontal rules, headings).
- **Observed:** The chat panel prints the markdown **literally** — e.g. `**You're here about the notice.**`, `> "Six days ago…"`, and `---`/`***` appear as raw characters instead of bold text, indented quotes, and dividers. A full DM turn becomes a hard-to-scan wall of text peppered with asterisks.
- **Expected:** Render the AI narration as markdown (at minimum bold/italic, blockquotes, line breaks, horizontal rules, lists). This is the single biggest readability win for the main chat surface.
- **Evidence:** Phase-2 chat screenshot — literal `**…**`, `>`, `---` visible throughout the DM message.
- **Notes:** The model reliably emits markdown, so this is purely a render-side gap. Add a markdown renderer to the chat message component (sanitize output). Watch that proposal-block stripping still works. Likely dm-ui ChatPanel/message component.

### PT-9 — Hard to know where game data/config lives and how to run independent games
- **Status:** open
- **Severity:** major
- **Type:** usability
- **Phase:** cross-cutting (operability / setup)
- **Found:** runs/2026-06-26-first-pass.md
- **Steps:** Try to (a) point the app at a specific AI backend, (b) run the app outside the default Docker happy-path, and (c) reason about where a campaign's data actually lives and how to start a second, independent game/run without clobbering the first.
- **Observed:** Several papercuts that together make operating the game confusing for a non-author:
  - **Config location is ambiguous.** The canonical `.env` lives at the **repo root** (docker-compose `env_file`), but the api package lives in `dm-api/`. Running the api from `dm-api/` does **not** load the root `.env`, so settings like `DM_TOKEN` silently fall back to defaults/auto-generated values. Nothing tells you which `.env` is in effect.
  - **DM token can silently change.** When `DM_TOKEN` isn't found, the api generates a new one at startup (logged, but easy to miss) — which invalidates any already-unlocked DM browser with no UI-visible reason.
  - **Where the data lives isn't surfaced.** A campaign's durable state is in the `postgres_data` Docker volume, but there's no in-app/CLI way to see "this game = this world/session id, stored here." Backing up, copying, or resetting a single game isn't documented.
  - **No notion of independent runs.** There's no documented way to run two isolated games/instances (e.g. separate DBs/volumes/ports) — useful for parallel playtests or per-table separation. Everything shares one DB and one in-process WebSocket registry.
  - **Backend/runtime coupling is implicit.** Which provider needs which runtime (e.g. `claude_cli` needs the api on the host, not in the Docker image — see PT-7) is not stated where you'd configure it.
- **Expected:** A short "operating your game" reference (and ideally tooling) that makes the following obvious: which `.env`/config is in effect and how to point at a non-default one; where each game's data physically lives and how to back up / copy / reset just that game; how to run independent games (distinct DB/volume/port) for parallel runs; and which AI provider implies which runtime. Surfacing effective config (provider, models, DB, DM-token source) on `/health` or a startup banner would also help (overlaps PT-4).
- **Evidence:** This run required: discovering the root vs `dm-api/` `.env` gap, a DM-token regeneration on first host launch, and manual reconstruction of the DB/redis URLs to attach the host api to the Docker Postgres.
- **Notes:** Partly docs (a "running independent games / where your data lives" section), partly ergonomics (config discovery, effective-config endpoint, a thin CLI or compose profiles for isolated instances). Relates to PT-4 (startup validation) and PT-7 (claude_cli runtime). This is the kind of thing that bites a first-time operator at game night.

### PT-8 — Manual/Rolled ability entry clamps silently (no "max 18" hint)
- **Status:** open
- **Severity:** minor
- **Type:** usability
- **Phase:** 1 — Character creation (adversarial)
- **Found:** runs/2026-06-26-first-pass.md
- **Steps:** Ability Scores → Manual / Rolled → type `20` (or `99`) into any base-score field.
- **Observed:** The field silently snaps the value down to `18`. No label or message explains the cap, so a user who typed 20 just sees it change to 18 with no reason given.
- **Expected:** The clamp is correct (good — it blocks the "all 20s" cheat), but it should be discoverable: show a "base max 18" hint near the inputs, or a brief inline note when a typed value is clamped.
- **Evidence:** form_input results: "Set number input to 18 (previous: 10)" for inputs where 20/99 were sent.
- **Notes:** Positive overall — guardrails across all three methods are solid (Standard Array = fixed values; Point Buy caps at 15 base / 27-pt budget; Manual caps at 18). This item is only about the *silent* clamp. Also worth confirming the lower bound (floor) and whether the engine re-validates server-side on submit (defense in depth).

### PT-7 — Dockerized api can't use `AI_PROVIDER=claude_cli` (no `claude` binary in image)
- **Status:** open
- **Severity:** major
- **Type:** bug
- **Phase:** 2 — Story hook (backend setup)
- **Found:** runs/2026-06-26-first-pass.md
- **Steps:** Set `AI_PROVIDER=claude_cli` and run via `docker-compose`. `docker compose exec api command -v claude` → `NOT_FOUND`.
- **Observed:** The api Docker image (Python base) does not include the `claude` CLI, and the host's `~/.claude` auth isn't mounted. `claude_cli_backend.py` raises `RuntimeError("`claude` CLI not found on PATH…")`. So the documented "use the claude CLI for local/offline" path is unavailable in the default Docker stack.
- **Expected:** Either the docker-compose api service installs + authenticates the CLI (e.g. mount the host `claude` binary and `~/.claude`), or the docs state plainly that `claude_cli` requires running the api on the host, not in Docker.
- **Evidence:** `command -v claude` NOT_FOUND in container; present on host at `/opt/homebrew/bin/claude`.
- **Notes:** README/running-a-game advertise `claude_cli` without this caveat. Workaround for this run: run api on the host with the host CLI.

### PT-6 — Read-only player view still shows the "Describe what happens" chat input + Send
- **Status:** open
- **Severity:** major
- **Type:** bug
- **Phase:** cross-cutting (observed by human spectator)
- **Found:** runs/2026-06-26-first-pass.md
- **Steps:** Open the session URL in a second browser without entering the DM token (read-only player). Look at the chat panel.
- **Observed:** The player view shows the "Describe what happens…" text input and a Send button, even though players are supposed to be read-only with no chat input (per running-a-game.md "Players get a read-only view — no chat input…").
- **Expected:** Player (non-DM) clients should not render the chat input/Send at all (and the server should reject player-authored DM turns regardless).
- **Evidence:** Human spectator on the read-only viewer reported the input bar is present.
- **Notes:** Verify whether sending from a player client is actually accepted by the API or just a stray UI affordance — either way the control shouldn't show. Likely a missing `isDM` gate in the chat input component.

### PT-5 — New characters don't appear on player clients without a manual refresh
- **Status:** resolved
- **Severity:** major
- **Type:** bug
- **Phase:** 1 — Character creation (real-time sync)
- **Found:** runs/2026-06-26-first-pass.md
- **Steps:** With a read-only viewer connected, create a character in the DM client via the wizard. Watch the player's PARTY sidebar.
- **Observed:** The new character did not appear on the read-only viewer until it was manually refreshed. README claims "Real-time Updates — WebSocket broadcasting keeps multiple browser tabs in sync."
- **Expected:** Creating/accepting a character should broadcast over the session WebSocket so all connected clients update the party roster live.
- **Evidence:** Human spectator reported needing to refresh to see Dorn/Kira.
- **Notes:** Character creation likely doesn't emit a WS event (or players don't subscribe to a roster-changed event). Combat/chat do broadcast; character roster apparently doesn't.

### PT-4 — Config (AI provider key) is not validated at startup; fails mid-game
- **Status:** open
- **Severity:** major
- **Type:** usability
- **Phase:** 2 — Story hook (startup/config)
- **Found:** runs/2026-06-26-first-pass.md
- **Steps:** Start the stack with a placeholder/invalid `ANTHROPIC_API_KEY` and `AI_PROVIDER=anthropic`. The app boots and serves normally; the failure only appears on the first AI chat turn.
- **Observed:** No startup validation of the AI backend config. The invalid key is only discovered when a player/DM is mid-session and sends a message — the worst possible time. (User-requested finding.)
- **Expected:** Validate AI backend configuration at startup and fail fast (or log a loud, clear warning): for `anthropic`, that `ANTHROPIC_API_KEY` is present and not the placeholder (ideally a cheap auth ping); for `claude_cli`, that `claude` is on PATH and authenticated. Surface it in `/health` so it's catchable before game night.
- **Evidence:** App served HTTP 200 / `/health` ok despite an unusable AI backend; first chat turn 500'd (see PT-3).
- **Notes:** Pairs with PT-3 (better runtime error message). This one is about catching it *before* anyone is playing. Likely a startup hook in `dm_api.main` / config validation in `config.py`, plus an AI-backend readiness field on `/health`.

### PT-3 — AI provider errors surface to the DM as a bare "Internal Server Error"
- **Status:** resolved
- **Severity:** major
- **Type:** bug
- **Phase:** 2 — Story hook
- **Found:** runs/2026-06-26-first-pass.md
- **Steps:** With an invalid/placeholder `ANTHROPIC_API_KEY`, type any opening prompt in the DM chat and Send.
- **Observed:** A SYSTEM chat message appears: **"Error: Internal Server Error"**. The API logs show the real cause — `anthropic.AuthenticationError: 401 invalid x-api-key` (in `dm_api/ai/backends/anthropic_backend.py:37`, bubbling up as an unhandled 500). The DM has no way to know it's an auth/key problem from the UI.
- **Expected:** The AI boundary should catch provider errors and surface an actionable message, e.g. "AI provider rejected the request (authentication failed — check ANTHROPIC_API_KEY)" or at least "the AI provider is unavailable; your message was saved." Per CLAUDE.md the AI call is an untrusted boundary that must degrade gracefully, and README troubleshooting already tells DMs to "verify ANTHROPIC_API_KEY" — the UI should point there.
- **Evidence:** Chat screenshot (SYSTEM error message); `docker compose logs api` traceback ending in `AuthenticationError: Error code: 401`.
- **Notes:** Distinguish provider-auth (401), rate-limit (429), and transient (5xx/timeout) so the message can be specific. Likely a try/except around the backend `complete()` call in the orchestrator or the `/api/ai` route, mapping provider exceptions to a typed, user-facing degraded response rather than a raw 500. This blocked the rest of the AI-dependent scenario on this run (see run log).

### PT-2 — Wizard can't set Fighter weapon masteries; warning leaks an internal field path
- **Status:** open
- **Severity:** major
- **Type:** bug
- **Phase:** 1 — Character creation
- **Found:** runs/2026-06-26-first-pass.md
- **Steps:** Build a level-1 Fighter (Human, Soldier) through the Create Character wizard and submit. The wizard has no step for weapon masteries.
- **Observed:** Confirmation reads "Dorn Ashvale joins the party! Level 1 Human Fighter — HP 12, AC 18, Speed 30 ft." with a yellow warning: **"Choose 3 weapon masteries (set sheet.weapon_masteries)."** The wizard never offered a way to choose them, and the message exposes the raw internal field path `sheet.weapon_masteries` to the end user.
- **Expected:** Either (a) the wizard includes a weapon-mastery picker for classes that get it at level 1 (Fighter gets 3 in 2024 PHB), or (b) at minimum the warning is phrased for a human ("Your Fighter can choose 3 weapon masteries — set them later via character edit") with no internal field name. Per CLAUDE.md, raw field paths / dev strings shouldn't surface as user-facing text.
- **Evidence:** Post-create confirmation screenshot.
- **Notes:** Two issues bundled: missing UI affordance (masteries can't be set in-UI at all → character is left mechanically incomplete) and a leaked implementation detail in a user-facing warning. Likely dm-ui CharacterCreation review/submit handling + the engine warning text.

### PT-1 — New Session form has no world setting/description field
- **Status:** open
- **Severity:** minor
- **Type:** usability
- **Phase:** 1 — Character creation (world setup)
- **Found:** runs/2026-06-26-first-pass.md
- **Steps:** On the landing "dm.ai — New Session" form, create a brand-new world. The only fields are World Name, Session Name, DM Token.
- **Observed:** A new world is created with no `setting_description`. The form gives no way to describe the world's setting/tone.
- **Expected:** Some way to seed the world's setting in the UI (a description field, or a follow-up step), since the AI co-DM's system prompt is built from the world setting. `docs/sample-session.md` sets a rich `setting_description` via the API for exactly this reason.
- **Evidence:** Landing-page screenshot (form shows only 3 fields).
- **Notes:** Without it, the DM must inject all setting context through the opening chat prompt. Check whether **Game Settings** exposes a world description; if not, this is a real gap. Likely UI: dm-ui NewSessionForm.tsx.

## Resolved

### PT-13 — End Session uses a blocking native confirm()
- **Resolved in:** PR #78 (claude/gifted-hawking-ebnwrt)
- Replaced `window.confirm()` with an in-app styled confirmation modal in `DMDashboard.tsx`.

### PT-10 — Chat does not render markdown
- **Resolved in:** PR #78 (claude/gifted-hawking-ebnwrt)
- Added `react-markdown` to chat message rendering in `DMDashboard.tsx`. All roles (DM, AI, system) now render bold, italic, blockquotes, horizontal rules, headings, and lists.

### PT-5 — New characters don't appear on player clients without a manual refresh
- **Resolved in:** PR #78 (claude/gifted-hawking-ebnwrt)
- `POST /characters/creation/build` now accepts an optional `session_id` and broadcasts an `entity_update` WebSocket event when provided. The character creation wizard passes the current session id so all connected clients receive the new character live.

### PT-3 — AI provider errors surface as a bare "Internal Server Error"
- **Resolved in:** PR #78 (claude/gifted-hawking-ebnwrt)
- `session_chat` now catches backend exceptions and raises a 503 with a provider-specific message (authentication failure, rate limit, or transient error). The frontend `request()` helper also extracts the FastAPI `detail` string from error JSON so the DM sees the actual reason, not an HTTP status phrase.
