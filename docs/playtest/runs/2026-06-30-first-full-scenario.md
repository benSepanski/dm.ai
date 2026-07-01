# Playtest Run — 2026-06-30 — First full 8-phase scenario

See the [playbook](../README.md) for the procedure and
[pending-items.md](../pending-items.md) for where issues go.

## Header

- **Date:** 2026-06-30
- **Driver:** Claude Code (model: claude-sonnet-5; switched mid-session from the
  deployment default `claude-sonnet-4-6` via Game Settings — see Phase 4 notes)
- **Backend:** claude_cli
- **Stack:** `docs/playtest/playtest-stack.sh` (Postgres/Redis in Docker,
  API+UI on host)
- **Focus:** full scenario, Phases 1–8
- **World / Session:** The Sunken Coast / The Drowned Bell
  (`bbcb302d-a250-4ffa-8074-d11de6522bc5`)
- **Party:** Dorn Ironfoot (Dwarf Fighter, Soldier), Maret Sable (Elf Wizard, Sage)

## Phase results

| Phase | Result | Notes / findings |
|---|---|---|
| 1 — Character creation | pass (with findings) | Wizard flow itself works well; guardrails mostly solid (empty-form Next disabled, skill/language/mastery caps enforced, point-buy caps at budget). Found PT-16 (no spell/lineage sub-choices) and PT-17 (illegal monster stats silently accepted). |
| 2 — Story hook | pass | Narration named the actual PCs/world; 2 proposals (location + NPC) emitted and accepted cleanly. |
| 3 — Dialogue | pass | NPC dialogue loop and proposal-accept worked; new NPC (Aldric Fenn, the victim) proposed and accepted. |
| 4 — Travel | pass | Consistent world-building; new location + NPC proposed and accepted. Model switched to Sonnet 5 mid-phase (see notes) — the AI handled a duplicate resent message gracefully in-fiction, but it also caused PT-19 (duplicate NPC). |
| 5 — Map creation | pass | Map renders, PC tokens colored correctly (blue, per PT-11's fix), drag mirrored live to a second (player) browser tab. |
| 6 — Combat | **blocked** | Start Combat enrollment works (PT-12 still fixed). But no combat action (Attack/Dash/Dodge) produces any visible feedback, and Attack has no target-selection UI at all — every attack is a silent no-op that still burns the turn. Full round completed with zero damage dealt to anyone. New finding: **PT-15 (blocking)**. |
| 7 — Map exit | pass | Narrated exit, map toggled off cleanly, toolbar reflected state correctly. |
| 8 — More discussion / End Session | pass | Debrief narration was accurate and well-structured; custom `ConfirmDialog` (not native `confirm()`) gates End Session (PT-13 still fixed); `session_summary` was generated and persisted (verified via API). |

## Findings logged

- PT-15 — Combat actions produce no visible feedback and Attack has no target-selection UI (blocking / bug)
- PT-16 — Character creation wizard skips required class/species sub-choices — spells, Elf lineage, Keen Senses (major / bug)
- PT-17 — Illegal combat stats (negative HP, AC 0) are silently accepted on NPC/Monster creation (major / bug)
- PT-18 — Proposal narration commits an entity as fact before the DM can accept/reject it (major / usability)
- PT-19 — Duplicate NPC entities when the AI re-introduces an already-established character (minor / bug)

## Screenshots

Screenshots were captured throughout via the Claude in Chrome MCP tool but not
saved to disk individually; key evidence (combat HP staying full after a full
round, the illegal monster's stat card, the wizard's missing spell step) is
described verbatim in the corresponding pending-items.md entries above.

## Summary

The narrative spine of the app (character creation → story hook → dialogue →
travel → map) is in excellent shape: Sonnet 5 (and Sonnet 4.6 before the
switch) produced consistent, well-paced prose that correctly tracked party
members, world state, and prior turns, and the proposal/accept workflow from
PT-14's fix works well for building out a world live. The map and multiplayer
sync (drag mirrors instantly to a second browser) also held up cleanly.

The blocking finding is combat: the tracker enrolls combatants and enforces
action economy (a stray double-click on Attack was correctly rejected with
"Action already used this turn"), but there is no way to actually select a
target for an attack, and no combat action's outcome — hit, miss, damage, or
even a "no target" error — is ever shown to the DM or players. A full round
of combat left every combatant at full HP with zero visible signal that
anything had gone wrong. This is a regression relative to what Phase 6's
acceptance criteria call for and should be the top priority for the next fix
pass (PT-15).

Two Phase-1 findings compound this: newly created spellcasters get no spells
at all (PT-16), so even if combat worked, a Wizard would have nothing to cast;
and the NPC/Monster creation dialog has no stat validation (PT-17), letting a
DM commit a monster with negative HP without any warning — the exact kind of
guardrail gap the scenario's adversarial-testing step exists to catch.

One design question was raised mid-session by the human operator and is
worth a deliberate product decision rather than a quick fix: proposals are
extracted from narration that has *already* asserted the new entity as fact
in the same chat message, so rejecting a proposal doesn't retract anything
the table already read (PT-18).
