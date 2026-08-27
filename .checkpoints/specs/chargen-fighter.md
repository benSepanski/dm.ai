---
slug: chargen-fighter
status: approved
---

# Chargen slice 1: PF2e Fighter level-1 creation wizard

## Problem

The rebuild needs its first vertical slice, and per the vision roadmap that
slice is character creation: a guided web-UI wizard that produces a durable,
reloadable character. Nothing exists yet — no server, no UI, no persistence,
no ruleset code — so this checkpoint also stands up the walking skeleton those
things live in.

The slice is deliberately one class in one system: the Pathfinder 2e Fighter
at level 1. PF2e is the most structurally demanding of the three target
systems (attribute boosts with per-group constraints, heritage and feat slots
at level 1, four-tier proficiency), so building against it first forces the
decision-log core, the ruleset boundary, and crash-safe persistence to be real
rather than deferred. D&D 5.5e arrives two slices later as the cross-system
stress test; abstractions beyond what one system needs are resisted until it
forces them.

## Requirements

1. A local web server serves the app on localhost; opening it shows a
   character roster (empty on first run) with create / resume / view /
   delete. Delete asks once, then moves the character's file to a `trash/`
   subdirectory of the data dir — recoverable by hand, never hard-deleted by
   the app. Single user, one machine — LAN multi-device play is a later
   epoch.
2. "Create character" opens a guided wizard for a PF2e level-1 Fighter
   following the PF2e creation sequence (concept → ancestry + heritage +
   ancestry feat → background → class → finish attribute boosts → equipment →
   details), with non-linear navigation: any step reachable, unresolved steps
   badged rather than blocking. Changing an already-confirmed choice is
   allowed and clears its dependent decisions — after an explicit
   confirmation listing exactly what will be cleared — reopening those slots
   on the checklist.
3. Character state is a **decision log**: every confirmed choice is recorded
   against a ruleset-defined choice slot with provenance (slot, option ID,
   source, order). The sheet (AC, HP, saves, skills, attacks, inventory,
   Bulk) is derived from the log — never hand-authored — and recomputes
   visibly as choices land.
4. The ruleset boundary exists: PF2e slot definitions, option catalogs,
   validators, and sheet derivation live in a ruleset module the core does
   not import; the core knows characters, slots, decisions, and a
   presentation contract, never PF2e semantics. (One implementation for now;
   the boundary is judged by the dependency rules the architecture doc
   emits, not by speculative generality.)
5. Validation is live and explains itself: a persistent checklist
   distinguishes *incomplete* ("1 skill choice left — from Background") from
   *illegal* ("boosts in this group must go to different attributes"), each
   entry naming the rule and jumping to the offending step. Finalizing
   requires zero illegal entries; incomplete entries block finalize with the
   checklist shown.
6. Every confirmed choice is durably saved server-side before the UI moves
   on: killing the server process (or the browser) at any moment and
   restarting loses at most the in-flight unconfirmed field, and reopening
   the app offers "Resume creating <name> (step N)" at the exact step. No
   confirmed choice is ever duplicated (a retried confirm after a crash
   between save and acknowledgment appends nothing new), and a confirm from
   a stale view of the draft (e.g. a second tab) is rejected with a reload
   prompt rather than silently interleaved.
7. Characters persist as human-inspectable JSON files in a data directory —
   one file per character holding the materialized sheet plus the ordered
   decision log, written crash-safely, with a schema version. These files
   are not disposable scaffolding: later Epoch 1 slices must load them, so
   the schema-version-plus-migration discipline is in scope from this slice.
   Characters record the rules-data version they were built against; replay
   uses the single shipped version this slice. A `verify` command replays
   every character's log and reports any divergence from the stored sheet;
   divergence is reported, the materialized sheet still loads. A file that
   is unparseable or schema-invalid is quarantined and reported on the
   roster while every other character loads — and the app never rewrites or
   normalizes a file on load.
8. Rules data ships as versioned data files with stable IDs and per-record
   license metadata, and the app displays the ORC attribution notice. Breadth
   is a representative subset chosen to exercise every mechanism, not full
   coverage: 3–4 ancestries with their heritages and level-1 ancestry feats,
   4–6 backgrounds (at least one with a constrained boost), the Fighter class
   with enough level-1 class feat options to exercise a prerequisite, the
   skill list, and the Fighter's starting kit plus a small weapons/armor/gear
   list. Candidate set, finalized against Archives of Nethys at implement:
   Dwarf, Human, Elf, Goblin (with their Player Core heritages and level-1
   feats; versatile heritages excluded); Field Medic, Warrior, Blacksmith,
   Hunter, Street Urchin — chosen so the set covers fixed-boost-with-flaw
   and all-free ancestry generation, HP/speed variance, small size, distinct
   Lore skills and skill feats, and a background/class skill collision that
   forces the replacement rule. Full Player Core breadth is the
   `chargen-content` follow-up slice. Data values are checked against a
   published reference before shipping.
9. Finalized characters open in a read-only sheet view rendered from the
   presentation contract; a finalized character can be reopened for viewing
   after server restart, unchanged.

## User stories & flows

- **First run.** Ben starts the server, opens the printed localhost URL, sees
  an empty roster, and clicks through creating "Torvald", a Dwarf Fighter:
  picks ancestry (sees boosts apply live in the summary sidebar), heritage,
  ancestry feat, background (watches the skill counter tick down), assigns
  the four free boosts, takes the class kit, names him, finalizes, and lands
  on a correct sheet — AC, HP 20 (10 ancestry + 10 class + Con), Fort/Ref/
  Will, and attack bonuses all matching a hand calculation.
- **The mistake, caught.** Mid-wizard Ben puts two free boosts on Strength;
  the checklist immediately shows the illegal entry with the rule ("boosts
  gained at the same time must go to different attributes") and clicking it
  returns him to the boost step. He moves one boost to Constitution and the
  entry clears from the checklist as he watches.
- **The crash.** Ben kill-9s the server between the background and class
  steps, restarts it, reopens the browser: "Resume creating Torvald (step 4
  of 7)" — every confirmed choice intact, only the half-typed name field
  gone.
- **The skeptical inspection.** Ben opens
  `<data-dir>/characters/torvald.json` in an editor and can read what
  happened: a sheet he recognizes and a decision list in the order he made
  them. He edits the stored sheet's HP by hand, runs `verify`, and is told
  the sheet diverges from replay.
- **Unhappy path — jumping ahead.** Ben goes straight to equipment before
  choosing a class; the step works with what's known, and the checklist shows
  the unresolved earlier steps; finalize is blocked until they're done, with
  every gap listed. He works through the gaps from the checklist and finalize
  unblocks the moment the last one resolves.
- **Unhappy path — draft abandoned.** Ben deletes a half-finished draft from
  the roster; it asks once, then it's gone from the roster and its file sits
  in `trash/` — recoverable by hand, invisible to the app.

## Risks

- **Rules-data transcription errors** (wrong feat prerequisite, wrong kit
  contents) silently poison trust in derived numbers. Mitigated: req 8's
  check against a published reference (Archives of Nethys; the Foundry PF2e
  open data repo as machine-readable ground truth — used for verification
  only, never bulk-imported, so its license terms are not inherited), plus
  golden-sheet tests for hand-verified builds.
- **Disk full or unwritable data dir mid-confirm.** The write fails without
  touching the prior file version; the UI surfaces the failure instead of
  pretending the step saved.
- **Premature abstraction**: designing the core for three systems while
  building one. Mitigated: the core models only slots/decisions/derivation
  used by this slice; the roadmap plans for the boundary to bend at the 5.5e
  slice rather than pretending it won't.
- **Scope creep via equipment**: itemized shopping wants a whole shop UI.
  Mitigated: kit-first with a basic item list; a real shop is out of scope.
- **Licensing missteps.** ORC compliance is believed straightforward
  (mechanics shippable, Golarion proper nouns reserved, notice required) but
  is re-verified against the actual ORC notice requirements before merge.
  **Accepted** residual risk: license understanding may need correction in a
  follow-up.
- **Accepted:** single-user localhost means no identity, visibility, or
  concurrency handling this slice; the Epoch 2 checkpoints own those, and
  some persistence decisions may need revisiting then.

## Out of scope

- Any second class or system, level-up, retraining, or editing finalized
  characters (roadmap slices 2–6). Characters exist at level 1 only; no
  level-2+ rules data (feats, features, progression tables) ships at all.
- LAN access, player identity/claiming, visibility rules, live table state.
- AI anything: no suggestions, no generated backstories.
- Homebrew, DM overrides, house rules, trust modes.
- Itemized shopping UI beyond a basic list; encumbrance beyond Bulk totals.
- Quick-build / random characters; multiple campaigns/data dirs per server.

## What Ben checks

- Walk "first run" end to end and hand-verify Torvald's sheet numbers against
  the Player Core (or Archives of Nethys) — AC, HP, saves, skills, attack
  bonuses, and Bulk.
- Walk "the mistake": double-boost Strength, confirm the checklist names the
  rule, jumps you back, and clears when you fix it. Then change Torvald's
  ancestry after his heritage is chosen: confirm the prompt lists exactly
  what will be cleared and the checklist reopens those steps.
- Walk "the crash": kill -9 mid-wizard, restart, resume; confirm nothing
  confirmed was lost and the resume step is exact.
- Walk "the skeptical inspection" on a throwaway character: read its file,
  judge whether it is genuinely legible; tamper with it and confirm `verify`
  catches it; then delete it and confirm the roster is clean and the file
  landed in `trash/`.
- Intent check on the wizard feel: is this the "good character creation
  dialog through a nice web UI" you meant — would you hand a player this
  wizard at a table tomorrow?
- Spot-check three shipped data records (an ancestry, a background, a feat)
  against Archives of Nethys for fidelity and license tagging.

## Review record

| Role | Verdict | Folded in |
|---|---|---|
| risk-reviewer | advice | delete-to-trash semantics (req 1), no-duplicate/stale-tab confirms (req 6), quarantine + never-rewrite-on-load and file forward-compatibility (req 7), Foundry-data verification-only clause, disk-full risk |
| user-advocate | advice | "mistake" and "jumping ahead" stories closed end-to-end; checklist walk, Bulk hand-check, throwaway-tamper + delete added to What Ben checks |
| scope-warden | advice | req 8 trimmed to representative subset with `chargen-content` follow-up slice added to the roadmap; single-shipped-data-version clause (req 7) |
