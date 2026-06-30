# Playtest Run — 2026-06-29 — Second UI pass

Second execution of the [agentic UI playtest](../README.md). Driven via Claude
in Chrome against a local stack (datastores in Docker, API + UI on host with
`AI_PROVIDER=claude_cli`).

## Header

- **Date:** 2026-06-29
- **Driver:** Claude Code (model: claude-opus-4-8)
- **Backend:** claude_cli (host API)
- **Stack:** hybrid — Postgres + Redis via docker-compose; API (uvicorn) + UI (vite) on host
- **Focus:** full scenario, with attention to PT-12 (combat) status
- **Spectator URL:** http://localhost:5173/session/fb905acb-9764-40e7-b966-279ae5ba0e19
- **World / Session:** Saltmarsh Reach / fb905acb-9764-40e7-b966-279ae5ba0e19
- **Party:** Bram Holt (Human Fighter 1, STR 17 / AC 16 / HP 12), Sister Wen (Dwarf Cleric 1, WIS 17 / AC 17 / HP 11)

## Phase results

| Phase | Result | Notes / findings |
|---|---|---|
| 1 — Character creation | pass | Wizard works end-to-end for both PCs. Class/species/background cards expand with rich rules text. **Guardrails solid:** Standard Array offers only fixed values; Point Buy enforces 15/stat + 27-pt budget live (verified hitting 27/27 with + disabled); empty name disables Next; skill & language caps enforced (extras grey out); background +2 target disabled in +1 group; Soldier-granted skills greyed in class list. AC/HP computed correctly by engine (Bram 12/16, Wen d8+CON+Dwarven Toughness=11, Scale+DEX+Shield=17). **PT-2 fix confirmed:** mastery warning now human-readable ("set them later via character edit"), no leaked field path. No new findings. (Note: Bram created without his intended shield due to a driver artifact — `form_input` on the React checkbox didn't fire onChange; a real click on Wen's shield worked and AC included +2. Not an app bug.) |
| 2 — Story hook | pass (1 finding) | Opening prompt produced a rich, world-consistent scene (Drowned Bell tavern, Harbormaster Aldric Gosse, Petra Maren soaked with kelp pointing toward the dark lighthouse), ~27s via claude-sonnet-4-6. **PT-10 fix confirmed:** markdown renders correctly (italics, horizontal-rule divider) on both DM and player views. **Finding PT-14:** `proposals=none` — the durable NPCs/location were invented in prose but no proposal card was emitted. |
| 3 — Dialogue | pass, but acceptance untestable (PT-14) | Excellent NPC loop: Petra traces a tidal spiral on Wen's palm, looks toward the dark, drowned-temple lore surfaces; AI ends with per-PC prompts. Live sync to the player tab verified (narration appeared without refresh, read-only). **Could not "accept a proposal" — none exist** (PT-14). |
| 4 — Travel | pass (narratively), PT-14 | Party travels the causeway to the "Saltmarsh Light"; arrival narration strong and grounded (open cottage, two sets of footprints — a child's bare feet from the water, a pulsing glow in the tower). **No location proposal; LOCATION stayed "No location set"** the whole session (PT-14). |
| 5 — Map creation | pass | **Show Map works even with no location** — battle map renders party tokens as **blue PCs** (PT-11 fix confirmed: PC=blue, only party shown out of combat). Token drag grid-snaps on the DM side **and mirrors live to the player tab** (resolves the prior run's open token-sync question). |
| 6 — Combat | pass (after rebase) | **Initially blocked** — but the branch base predated the PT-12 fix (`2ba980c`). After rebasing onto `main` and re-testing on the fixed code, combat works end-to-end: Start Combat opens a **picker dialog** (party pre-checked, inline HP/AC inputs for stat-less characters), Begin Combat enrolls them and rolls initiative (Bram Init 17 / Wen Init 13), **Attack** consumes the action (`turn_state.action_used=true`), a **second Attack is rejected with 409** (action economy enforced), **Next Turn** advances the actor, and **End** posts the mechanical-outcome system message ("Combat ended after 1 round(s). Final state: Bram Holt 12/12 HP, Sister Wen 11/11 HP"). Not exercised: a targeted attack-roll with damage / spell / death saves — the UI's combat buttons submit action-economy declarations, not targeted attacks (separate limitation, not PT-12). |
| 7 — Map exit | pass | Ending the empty combat returned cleanly to "No active combat" with party tokens restored to their prior cells; Hide Map returned to full-width chat with no state glitches. |
| 8 — More discussion | pass (PT-13 confirmed) | Strong DM-led wind-down (party wisely declines the dark tower, takes the keeper's log + a kelp-wrapped bundle, lands a clear next-session hook). **PT-13 fix confirmed:** End Session uses an in-app `ConfirmDialog`, not native `confirm()`. **End Session** stored an accurate 579-char `session_summary` (~9.5s) and detached the browser cleanly to New Session. |

## Findings logged

| ID | Sev | Type | One-liner |
|---|---|---|---|
| PT-14 | major | bug | AI co-DM emitted **no proposals all session** → invented NPCs/locations uncapturable, LOCATION never set, continuity drift |

> **Note on PT-12:** the first combat attempt this run hit PT-12 (empty
> initiative), but that was because the branch base predated the fix. After
> `git rebase` onto `main` (which carries `2ba980c fix(combat): resolve PT-12`),
> combat was re-tested on the fixed code and **works** — see Phase 6 above. PT-12
> is **resolved**, not reopened.

### Confirmed resolved this run (regression checks)
- **PT-1** — New Session has a "World Setting" field (used to seed the co-DM). ✓
- **PT-2** — Mastery warning is human-readable ("set them later via character edit"), no leaked field path. ✓
- **PT-6** — Player view is read-only: badge "Player", DM-only buttons gone, chat input replaced with "You're watching as a player — the DM drives the story." ✓
- **PT-10** — Chat renders markdown (italics, horizontal rules, bold) on DM and player views. ✓
- **PT-11** — Map tokens colored by type (PCs blue); only party shown out of combat. ✓
- **PT-13** — End Session uses an in-app confirm dialog. ✓
- **PT-12** — Start Combat now opens a combatant picker (party pre-checked, inline HP/AC for stat-less); enrolls combatants, rolls initiative, and the engine resolves actions with action-economy enforcement (verified on the rebased code). ✓
- **Bonus:** token-position drag mirrors live to the player tab (prior run's open question).

## Screenshots

- Captured inline throughout (wizard steps for both PCs, Point Buy budget cap at 27/27, player read-only view, each AI narration turn, battle map + token drag + player mirror, empty combat, End Session confirm dialog + New Session detach).

## Summary

Second full UI playtest — **all 8 phases pass on current `main`.** The first combat attempt hit
PT-12 (empty initiative), but only because the branch base predated the fix; after rebasing onto
`main` (which carries `2ba980c`), combat was re-verified end-to-end (picker → enroll → initiative
→ action-economy-enforced actions → turn advance → outcome message), so **PT-12 is resolved**.
The character wizard and its guardrails are rock-solid (Standard Array fixed values; Point Buy
15/stat + 27-pt budget enforced live; skill/language caps; engine-computed HP/AC incl. shield
verified). The AI co-DM's prose was outstanding and world-consistent across the whole arc, and
seven prior findings (PT-1/2/6/10/11/12/13) are confirmed fixed, plus live token-sync to players
now works. The run's **one remaining finding (PT-14)** is the notable gap: the co-DM emitted
**zero `[PROPOSAL]` blocks for an entire session** despite inventing several named NPCs and a new
location, so nothing could be captured as an entity, the LOCATION never got set, and names
drifted — and there's no manual fallback to create a location/NPC. With combat now working, the
**entities/locations/proposals pillar is the one weak spot**; narrative, character creation, map,
and combat are all solid.

### Environment notes
- Hybrid stack: Postgres + Redis via docker-compose; **API (uvicorn) + UI (vite) on the host**
  with `AI_PROVIDER=claude_cli` (no `ANTHROPIC_API_KEY` was available, so the documented
  all-Docker `anthropic` path wasn't used). `DM_TOKEN=dev-dm-token`. `/health` reported
  `ai_ready:true`.
- Driver note: the React shield checkbox isn't toggled by `form_input` (doesn't fire onChange);
  a real click works. Bram was created without his intended shield as a result — a harness
  artifact, not an app bug (verified Wen's shield via real click → AC included +2).
