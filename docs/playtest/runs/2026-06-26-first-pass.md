# Playtest Run — 2026-06-26 — First UI pass

First execution of the [agentic UI playtest](../README.md). Driven via Claude in
Chrome against the local Docker stack.

## Header

- **Date:** 2026-06-26
- **Driver:** Claude Code (model: claude-opus-4-8)
- **Backend:** anthropic
- **Stack:** docker-compose
- **Focus:** full scenario (char creation → hook → dialogue → travel → map → combat → map exit → discussion)
- **Spectator URL:** http://localhost:5173/session/96bf1aaf-6519-4e06-8f14-3e2433ab5d30
- **World / Session:** Emberfall Reach / 96bf1aaf-6519-4e06-8f14-3e2433ab5d30
- **Party:** Dorn Ashvale (Human Fighter 1, STR 17 / AC 18 / HP 12), Kira Veth (Elf Wizard 1, INT 17 / AC 12 / HP 8)

## Phase results

| Phase | Result | Notes / findings |
|---|---|---|
| 1 — Character creation | pass (3 findings) | Wizard works end-to-end. Live final-score calc, contextual armor/skill handling, double-pick prevention all good. **Adversarial:** "all 20s" is blocked at every method — Standard Array offers only fixed values, Point Buy caps at 15 base / 27-pt budget (live), Manual/Rolled clamps base to 18; empty origin disables Next. Findings: PT-1 (no world-setting field), PT-2 (Fighter weapon masteries unsettable + leaked field path), PT-8 (silent clamp, no "max 18" hint). HP/AC computed correctly for both PCs. |
| 2 — Story hook | pass (after backend swap) | First attempt with `AI_PROVIDER=anthropic` 500'd — placeholder `ANTHROPIC_API_KEY` → 401, surfaced as opaque "Internal Server Error" (PT-3, PT-4). Switched to `AI_PROVIDER=claude_cli` on a host-run api (PT-7, PT-9 surfaced during setup). Retry succeeded: rich world-consistent narration (Maret Solde, Verath Shaft Three) + 2 proposals (location Cinderhollow + NPC), ~39s via claude-sonnet-4-6. Finding: PT-10 (chat renders markdown literally). |
| 3 — Dialogue | pass | Accepted both proposals (location + NPC) → rendered live in sidebar. NPC dialogue loop excellent: distinct miners (Cotter/Pellin) gave concrete, actionable leads (east passage/third landing, orange "breathing" crack, burned lift cable, "take rope"); Maret stayed in character (urgency, brother Edric). No spurious proposals on a pure-conversation turn. PT-10 (literal markdown) reconfirmed. |
| 4 — Travel | pass | Descent narrated with continuity (Kira recognizes "thermal bloom" from her scholar background; burned lift-cable, laid-down tools, breathing crack all carried forward). Produced + accepted a dungeon location proposal ("Verath Shaft Three — Third Level, East Passage"). Strong world consistency. |
| 5 — Map creation | pass (1 finding) | Map renders (grid + blue party tokens Dorn/Kira); token drag works and grid-snaps on the DM side. Cross-client mirroring to the spectator pending human confirm (docs say positions may be per-browser). Finding: PT-11 (friendly NPC Maret shows as red enemy token, and appears out of scene). |
| 6 — Combat | BLOCKED | UI-only combat is unwinnable → PT-12. Start Combat enrolls nobody ("No combatants in initiative order", map blanks, controls disabled) because the UI omits `character_ids`; and AI-proposed monsters have no combat stats with no UI to set them. Engine combat could not be exercised via the UI this run. Resolved the encounter in narration to continue. Also reconfirmed PT-11: after End, both Maret (ally) and Cinder Hound (enemy) show as red tokens — indistinguishable. |
| 7 — Map exit | pass | Hide Map toggles cleanly back to full-width chat, no state glitches; map state restored on re-show. |
| 8 — More discussion | pass (1 finding) | Strong DM-led wind-down: Maret takes the hard news about Edric in character; party lands a concrete next-session hook (rest a day, read the "V. SHAFT III — SURVEY LOG"). Reject-with-note flow tested (rejected a duplicate Cinder Hound proposal). **End Session** generated a high-quality, accurate `session_summary` (stored; ~11s via generation model) and detached the browser to the New Session screen. Finding: PT-13 (End Session uses a blocking native confirm() — needed a `window.confirm` override to complete under automation). |

## Findings logged

| ID | Sev | Type | One-liner |
|---|---|---|---|
| PT-1 | minor | usability | New Session form has no world setting/description field |
| PT-2 | major | bug | Wizard can't set Fighter weapon masteries; warning leaks `sheet.weapon_masteries` |
| PT-3 | major | bug | AI provider errors surface as bare "Internal Server Error" |
| PT-4 | major | usability | AI provider config not validated at startup; fails mid-game (user-requested) |
| PT-5 | major | bug | New characters don't sync to player clients without refresh (user-observed) |
| PT-6 | major | bug | Read-only player view still shows the chat input + Send (user-observed) |
| PT-7 | major | bug | Dockerized api can't use `claude_cli` (no `claude` binary in image) |
| PT-8 | minor | usability | Manual/Rolled ability entry clamps to 18 silently (no hint) |
| PT-9 | major | usability | Hard to know where game data/config lives & how to run independent games (user-requested) |
| PT-10 | major | usability | **[visual] Chat doesn't render markdown — raw `**`/`>`/`---`/`#` (user-flagged ×2)** |
| PT-11 | major | bug | [visual] Friendly NPC shows as red enemy token; appears out of scene |
| PT-12 | **blocking** | bug | Combat unwinnable in UI: Start Combat enrolls nobody; monsters have no stats |
| PT-13 | minor | usability | End Session uses a blocking native confirm() |

## What worked well (positives)

- Character wizard: end-to-end for both martial + caster; live final-score calc; contextual armor/skill handling; double-pick prevention; correct HP/AC from the engine.
- **Guardrails are solid** — "all 20s" is impossible (Standard Array fixed values, Point Buy 15/27 cap, Manual clamp to 18; empty origin disables Next).
- AI DM quality (via `claude_cli` / sonnet) was excellent and **world-consistent** across 6 turns: distinct NPC voices, callbacks (thermal bloom, Edric, the breathing crack), concrete actionable leads, and a clean session summary.
- Proposal flow (accept → live in sidebar; reject-with-note) works well.
- Map renders and token drag/grid-snap work on the DM side.

## Screenshots

- Captured inline during the run (wizard each step, the hook, proposals, dialogue, travel, battle map + token drag, empty combat, retreat, End Session → New Session screen).

## Summary

A near-complete first UI playtest. **7 of 8 phases passed** (character creation, story hook,
dialogue, travel, map creation, map exit, discussion + end-session summary). **Phase 6 (combat)
is blocked** for UI-only play (PT-12): Start Combat enrolls no one and AI monsters have no
settable stats, so the combat pillar can't be exercised from the UI at all — the single most
important fix. The run also surfaced an environment gap (the `anthropic` key was a placeholder;
ran on `claude_cli` via a host api after PT-7/PT-9 setup friction) and a top user-flagged
readability issue (PT-10, chat doesn't render markdown). AI narrative quality and the character
wizard/guardrails were the standout strengths. 13 findings logged (1 blocking, 9 major, 3 minor).

### Open questions for the human (spectator checks)
- **PT-5 / token sync:** did the new characters appear, and did Dorn's token move, on your
  read-only viewer **without** a refresh? (Couldn't verify cross-client from the driver side.)
- Confirm **PT-6**: your read-only viewer showed a "Describe what happens" input — does sending
  from it actually post, or is it just a stray control?

### Environment notes (how this run was driven)
- Backend swapped to `AI_PROVIDER=claude_cli` on a **host-run api** (`dm-api/.venv`, python3.13)
  bound to the Docker Postgres/Redis; `DM_TOKEN=dev-dm-token`.
- Docker `ui` repointed at the host api via `docker-compose.override.yml`
  (`extra_hosts: api:host-gateway`) — local-only, not committed.
- To revert to the default stack: remove the override file, `docker compose up -d api ui`,
  set a real `ANTHROPIC_API_KEY` (or keep `claude_cli` but run the api on the host).
