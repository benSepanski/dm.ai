# Agentic UI Playtest

A repeatable, **UI-only** playtest of dm.ai, driven by AI agents acting as the
DM and the players. Every action goes through the real browser UI — no curl, no
Swagger, no direct DB writes — so the playtest exercises exactly what a human
table would touch. Bugs and rough edges are logged to
[`pending-items.md`](./pending-items.md); each run gets its own transcript under
[`runs/`](./runs/).

> **How to re-run this:** tell Claude Code *"run a UI playtest"* (optionally name
> a focus area, e.g. *"…focused on combat"*). Claude follows this document
> top-to-bottom, drives the browser, and appends findings. This file is the
> contract — keep it current as the app changes.

## Why this exists

`docs/sample-session.md` was a one-off playtest run mostly through the API.
This is the opposite: a **standing process** that always goes through the UI,
always logs what it finds, and is meant to be run again and again as we build
the game out together. Each pass should make the next pass smoother and the
[pending-items log](./pending-items.md) is how we accumulate that signal.

## Roles & how agents map to browsers

The app splits clients by the DM token (see
[running-a-game.md](../running-a-game.md)): the browser holding the token is the
**DM** (chat input, proposals, combat tracker, map control); every other browser
is a **read-only player** (sees chat, combat, and map updates live, but cannot
type or act).

| Agent role | Browser | Can do |
|---|---|---|
| **DM agent** | Tab D — unlocked with the DM token | Everything: narrate, review proposals, run combat, move tokens, end session |
| **Player agent(s)** | Tab P1, P2 — joined via invite link | Observe **visually** (screenshot every phase) and interact through the rendered page. Reports the *player experience* and logs anything confusing, missing, or visually wrong on the read-only view |
| **You (human)** | Your own browser | Spectate live at `http://localhost:5173/session/<id>` |

> **Known constraint (validate every run):** players are **read-only** in the
> current UI — a player agent cannot send chat or take actions. So the DM agent
> also *voices the party*: it types each PC's intended action into the DM chat
> in-character ("Dorn draws his axe and steps between Kira and the dock"). The
> player agents' job is to watch their own read-only screens and flag every
> place a real player would want to act but can't. The gap between "players want
> to do things" and "players can only watch" is itself a primary finding — log
> it, don't paper over it.

## Tooling

Drive the browser with the **Claude in Chrome** MCP (`mcp__Claude_in_Chrome__*`)
— it is DOM-aware and far more reliable than pixel clicking. One tab per role;
switch tabs with the MCP's tab tools. If the Chrome extension isn't connected,
ask the human to install/connect it rather than falling back to desktop
computer-use (browsers are read-only at that tier).

### Look at the screen, not just the DOM

Every agent — DM and players alike — must **read the actual rendered page**, not
only the DOM/accessibility tree. Take a screenshot at each numbered step and
*look at it* before moving on. The point of a UI playtest is to catch what only
a human eye would: a DOM-correct app can still be visually broken.

Watch for and log (`type: usability`, tag the title `[visual]`):

- overlap, clipping, or cut-off text; content overflowing its container
- misaligned or off-screen elements; broken responsive layout at the window size
- unreadable contrast, wrong/placeholder colors, missing icons or images
- a battle map that renders wrong (tokens off-grid, wrong colors, blank canvas)
- spinners that never resolve, flashes of unstyled content, layout shift
- state that's correct in the DOM but not *visible* to the user (e.g. a proposal
  card that exists but is rendered behind another panel)

Player agents especially: judge the read-only view as a player *sees* it. If
something looks wrong on screen, that's a finding even if the data is right.

Screenshots at each step become the run transcript's evidence and make bugs
reproducible — attach the relevant one to every logged item.

## Pre-flight

1. **Start the stack** (from repo root):
   ```bash
   docker-compose up        # UI :5173, API :8000, Postgres, Redis
   ```
   or local dev (`uvicorn` + `npm run dev`) per the [README](../../README.md).
2. **Health checks:**
   - `curl http://localhost:8000/health` → `{"status":"ok",...}`
   - Open `http://localhost:5173` in the DM tab — dashboard loads.
3. **DM token:** note the `DM_TOKEN` from `.env` (or the API startup log if
   auto-generated). The DM agent needs it.
4. **Tell the human the spectator URL** once the session exists:
   `http://localhost:5173/session/<session-id>`.
5. **Open the run log:** copy [`runs/_TEMPLATE.md`](./runs/_TEMPLATE.md) to
   `runs/YYYY-MM-DD-<short-slug>.md` and fill the header.

## The scenario (run in order)

Each phase has an **intent** (what we're testing) and an **acceptance check**
(what "working" looks like). After every phase, log any bug or friction to
[`pending-items.md`](./pending-items.md) and note the phase result in the run
log. If a phase is **blocking** (you cannot proceed through the UI), stop, log it
as `severity: blocking`, and write up how far you got.

### Phase 1 — Character creation
- **Intent:** the in-UI **Create Character** wizard builds a valid level-1 party
  end-to-end (origin → ability scores → skills → review).
- **Do:** In tab D, create a world + first session on the dashboard. Then build
  **2 contrasting PCs** through the wizard (e.g. a martial and a caster) so later
  phases exercise both attacks and spells.
- **Check:** each PC lands in the left sidebar with HP/AC/stats populated; review
  step warnings (if any) are understandable.

### Phase 2 — Story hook
- **Intent:** the DM agent can open the fiction and the AI co-DM responds with a
  usable hook.
- **Do:** DM types an opening-scene prompt naming the PCs and setting. Wait for
  the AI reply.
- **Check:** narration arrives; it references the actual PCs/world; any durable
  invention (location/NPC) shows up as a **proposal card** in the right panel.

### Phase 3 — Dialogue
- **Intent:** NPC conversation loop works and proposals can be accepted.
- **Do:** DM drives a short back-and-forth with an NPC from the hook, voicing a
  PC's questions. Accept at least one proposal (e.g. the NPC) so it becomes a
  real entity.
- **Check:** accepted proposal appears as a character/location for everyone;
  player tabs see the dialogue narration live.

### Phase 4 — Travel
- **Intent:** moving the party to a new place flows narratively and the AI keeps
  world consistency.
- **Do:** DM narrates the party traveling toward a destination implied by the
  hook. Let the AI describe the journey and arrival.
- **Check:** arrival is consistent with established lore; if a new location is
  invented it arrives as a proposal.

### Phase 5 — Map creation
- **Intent:** a battle map exists for the destination and renders for everyone.
- **Do:** Accept/trigger the destination location, toggle **Show Map**, confirm
  party tokens render. Drag a token in tab D.
- **Check:** map shows; token drag mirrors to player tabs and your spectator
  browser (note: positions are per-browser for late joiners — verify).

### Phase 6 — Combat
- **Intent:** the full combat loop runs through the tracker on engine rules.
- **Do:** Have an enemy appear (proposal → accept, or DM-created NPC/monster —
  **note** if the UI can't create a monster without Swagger, that's a finding).
  Ensure combatants have combat stats. **Start Combat**, roll initiative, take
  at least: one **weapon attack**, one **spell** (attack-roll and/or save), one
  **turn advance**, and drive a PC to **0 HP** to exercise death saves if it
  arises naturally. End combat.
- **Check:** initiative order is sane; actions resolve with dice + 2024 rules;
  action economy is enforced (second attack rejected); HP/conditions/slots sync
  back; ending combat posts the mechanical-outcome system message.

### Phase 7 — Map exit
- **Intent:** leaving the encounter map returns cleanly to narrative play.
- **Do:** Hide the map / narrate the party leaving the location.
- **Check:** map toggles off without state weirdness; roster tokens behave.

### Phase 8 — More discussion (DM-led wind-down)
- **Intent:** post-combat narrative, aftermath, and continuity hold up.
- **Do:** DM narrates aftermath, voices a short party debrief, then **End
  Session**.
- **Check:** end-of-combat outcome informs the narration; **End Session**
  produces a stored AI summary.

## Logging rules (during the run)

- **Bugs and friction → [`pending-items.md`](./pending-items.md)** immediately,
  using the entry format defined there. One entry per issue. Include the phase,
  what you did, what happened, what you expected, and a screenshot reference.
- **"Hard to use" counts.** Confusing labels, missing affordances (e.g. "no way
  to do X in the UI"), silent failures, anything a real DM/player would stumble
  on — log it as `type: usability`.
- **Visual bugs count.** Anything that looks wrong on the rendered screen
  (overlap, clipping, misalignment, bad contrast, broken map, never-resolving
  spinner) — log it as `type: usability` with `[visual]` in the title and attach
  the screenshot. These are the findings a screen-reading agent exists to catch.
- **Blocking issues** (`severity: blocking`): stop the run, finish the write-up,
  and report back. Don't route around the UI to keep going — routing around it
  hides the bug.
- **Don't fix during a playtest.** Observe and log only; fixes are a separate
  session so the run stays a clean signal of current state.

## After the run

1. Finish the per-run log in `runs/` (outcome, phases reached, screenshots,
   summary of findings with links to the `pending-items.md` entries created).
2. Confirm every new issue is in `pending-items.md`.
3. **Commit** the run log + updated `pending-items.md` on a branch and report a
   short summary to the human (phases passed, blocking issues, top friction).
4. Leave the stack running if the human is still spectating; otherwise note it.
