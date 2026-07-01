# Playtest Run — 2026-06-30 — Third pass (adversarial, usability-focused)

See the [playbook](../README.md) for the procedure and
[pending-items.md](../pending-items.md) for where issues go.

## Header

- **Date:** 2026-06-30
- **Driver:** Claude Code (model: Claude Sonnet 5)
- **Backend:** claude_cli (host-run API/UI via `docs/playtest/playtest-stack.sh`,
  Postgres/Redis in Docker on isolated ports — a second playtest was already
  running on the default ports, so this run used its own compose project
  `dk73bfe1-playtest` with Postgres on `15532`, Redis on `16479`, API on
  `18200`, UI on `15200`)
- **Stack:** local dev (host API/UI + dockerized datastores), not docker-compose
- **Focus:** full scenario, adversarial + usability emphasis (explicit ask
  from the human this run)
- **Spectator URL:** http://localhost:15200/session/514a0580-d17b-4ad8-bbc9-b0685ab49d50
- **World / Session:** Salt Marsh Chronicles / 514a0580-d17b-4ad8-bbc9-b0685ab49d50
- **Party:** Dorn Ironfist (Dwarf Fighter, Lvl 1), Kira Emberwind (Elf Wizard, Lvl 1)

## Phase results

| Phase | Result | Notes / findings |
|---|---|---|
| 1 — Character creation | pass (with major findings) | PT-24, PT-25, PT-26, and a no-lineage-picker gap (see Summary) |
| 2 — Story hook | pass | narration referenced PCs/world, proposal cards worked |
| 3 — Dialogue | pass | strong NPC generation (Maren Tull), markdown rendering clean |
| 4 — Travel | pass | consistent with established lore (wards, lighthouse) |
| 5 — Map creation | pass | map toggled, monster proposal accepted, token drag works |
| 6 — Combat | blocked (functionally) | Attack has no target picker and fails silently — re-confirmed PT-23, filed by a concurrent run |
| 7 — Map exit | pass | hid cleanly, no state weirdness |
| 8 — More discussion | pass | ConfirmDialog (PT-13) confirmed fixed; AI session summary stored correctly |

## Findings logged

- PT-24 — Player role can create characters directly, with no DM review (bug, major)
- PT-25 — DM state shared across tabs via localStorage; no logout/preview control (usability)
- PT-26 — Character build accepts illegal ability scores (all 20s) silently (bug, major)
- Combat Attack has no target picker and fails silently — independently found
  by a concurrent playtest run and filed as **PT-23**; this run reproduced the
  identical root cause against a different encounter, so it was folded into
  PT-23's notes instead of filed as a separate item.
- Also observed, not filed as a separate item (folded into PT-26's notes): the
  Elf species info box says "Choose a lineage (Drow, High Elf, or Wood Elf)"
  but the wizard has no control anywhere to make that choice — worth a
  follow-up ticket if not already tracked.

## Screenshots

Not saved to disk this run (relayed inline to the human via chat) — see the
in-conversation screenshots for: the shared-DM-token tab, the player-created
"Dorn Ironfist" PC appearing in the DM sidebar, the all-20-stat "Cheater
McMaxstat" character card, the Start Combat picker, and the combat tracker's
Attack button producing no visible effect.

## Summary

Narrative/proposal/map/session-lifecycle phases (2, 3, 4, 5, 7, 8) all held up
well — this is genuinely fun to play and the previously-resolved PT-11/12/13
fixes were re-verified working. The adversarial pass surfaced three
significant new problems, plus re-confirmed one already filed by a concurrent
run: (1) **combat, blocking** — the combat UI's Attack button never collects
a target, so weapon/spell attacks against an enemy cannot actually be
resolved through the UI at all (the failure is silent: HTTP 200, error
buried in `combat_log`); this breaks the core combat loop. A second playtest
running concurrently found the same bug independently and filed it as
**PT-23** — this run's reproduction (against a different monster/party) was
folded into that entry rather than duplicated. (2) **PT-24, major** — an
unauthenticated "player" browser can create and persist arbitrary characters
directly via `/characters/creation/build` with zero DM authorization,
violating the project's own "AI proposes, DM decides" principle. (3)
**PT-26, major** — that same endpoint accepts illegal ability scores (all
20s) with no rejection, so the UI's guardrails are the *only* defense and
there's no server-side backstop. Also flagged **PT-25** (usability): DM-mode
is shared via localStorage across every tab in the same browser with no
in-app way to preview the player view or log out, which also means a leaked
`DM_TOKEN` grants indefinite full access to every world on the instance.
