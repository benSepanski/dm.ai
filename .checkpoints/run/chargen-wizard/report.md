# chargen-wizard — report

Checkpoint: `chargen-wizard` · Branch: `checkpoint/chargen-wizard` · Status: delivered

## What changed and why

You can now build a Wizard start to finish: pick the class, an arcane
thesis, an arcane school, and a spellbook — ten cantrips and a rank-1 book
chosen in **one picker per rank**, with the school's curriculum spells
sorted first, badged, and the "at least 2 from your curriculum" minimum
enforced right in the picker by a meter and an in-card message. The
finalized sheet shows the full spellcasting block (spell attack, DC, slots,
cantrips per day, focus pool, the spellbook) and states plainly:
**"Preparation: at the table."**

This is the second version. Your review of the first (findings 1–7 in
[findings.md](findings.md)) triggered a contract revision — spec and
architecture rewritten and re-approved, and **daily preparation moved out
of character creation entirely** (the vision now assigns it to Epoch 8,
where the sheet becomes interactive; the validated design for it is
recorded there). The wizard dialog holds build decisions only.

**The class-addition experiment result is as clean as it gets:** adding the
Wizard changed the engine by **zero lines**. Through the class-addition
commits, `crates/engine-core`, `crates/types`, the persistence layer, the
routes, and the version guard stayed byte-identical to the branch point —
the whole class is rules data (29 spells, 2 theses, 2 schools, the class
record) plus ruleset slot definitions. The storage schema is untouched
(still v2). (Round 2 below then touched shared machinery deliberately —
meter constructors in the types crate and one line in the engine's auto
count meter — as class-agnostic UX improvements, not class code.)

Every one of your findings also became a structural guard, not just a fix:

- "from Fighter" on a Wizard → class names come from the chosen record, and
  a new build-failing lint bans any shipped record name appearing as a
  source literal in the ruleset, plus a sweep that builds a complete
  character of every class and asserts no other class's vocabulary leaks
  into what you see.
- The overflow you spotted → a general layout sweep (no page scroll, no
  element overflow, no starved columns, no clipped controls) now runs on
  **every screen visit in every e2e walk**, plus a wordiest-content stress
  test at desktop and tablet widths. Hands-on testing with it found and
  fixed a real tablet-width bug (the main column starved to a sliver) and
  two feedback bugs (an illegal-confirmed card collapsing shut; a green
  "Saved" ack carrying an illegal save).
- Repeatable Adds → an explicit rule: checkboxes are sets (duplicates
  unrepresentable — the spellbook), Add-trays are bags (grouped ×N rows
  with always-visible removes — equipment), pinned by a UI unit suite.
- The curriculum dead-end and three-slot bookkeeping → dissolved by the
  unified picker; a property test proves every shipped school has a
  satisfiable spellbook with no dead-end pick order.
- The disproportionate clear-cascade → the school slot has no dependents:
  changing school destroys nothing; the curriculum rule simply re-judges
  your standing book and tells you what to swap.

## Round 2 — your interactive review, diagnosed and fixed

Your second review round surfaced five findings (8–12 in findings.md,
with a post-assessment of the cause classes behind them). All five are
fixed, each paired with a structural guard against its class:

- **Finalize dead while "ready" (12, blocker).** Root cause: invisible
  tentative-edit state gating the button. Now: a no-op edit (uncheck/
  recheck, typing and deleting) is unrepresentable as pending state;
  real unconfirmed edits show as an **"Unconfirmed changes" chip** with
  jump links right under Finalize; the sidebar banner stops claiming
  "ready"; leaving to the roster warns before discarding. The class is
  banned by a new **dead-control invariant** in the layout sweep: any
  disabled action button without a visible explanation fails every e2e
  walk — every confirm button now says why it's disabled ("Pick one to
  continue."), and "Fill remaining" hides when moot.
- **"Curriculum 3 of 2" (10).** Meter semantics moved into code, per our
  discussion: `MeterView::requirement` (clamps at target),
  `::exact` and `::budget` (always show true overshoot) in the types
  crate; a lint bans raw meter literals; rulesets just declare intent.
- **Curriculum invisibility (8).** The rank-1 picker splits under labeled
  headers ("School of Battle Magic curriculum" / "Other arcane spells")
  and every curriculum row wears a CURRICULUM chip that survives
  filtering.
- **Details lost after confirming (9).** Confirmed cards have "Details ▼"
  — the school card shows its description, focus spell, and curriculum
  list without undoing anything.
- **Backwards skill attribution (11).** The ownership policy is now
  written into the fold: **fixed grants own a skill and its
  attribution**; a redundant grant or class skill adds one free trained
  pick (the printed rule); a free pick landing on an owned skill
  re-judges in its own card. The replacement-slot machinery is deleted.
  Stored-log compatibility rides the sanctioned path: rules-data bumped
  to pf2e-pc.0.3.1 so the version guard's repair flow covers older
  drafts (none of your live logs contained a replacement decision).
- **Bonus fix found by the new stories:** a slot made illegal from
  elsewhere (school change, background grant) now explains itself at the
  card, not only in the sidebar checklist.

Predictions from the post-assessment were verified: the Int-shrink
re-judge is now pinned by a test, budget overspend shows negative
remaining, quick-build is honestly labeled, and language duplicates are
impossible by data integrity. Sheet-side spell details are noted for
Epoch 8 (same class as finding 9).

## How to verify

Serve your real campaign as usual, then walk these on your own data:

```bash
cargo run -p server -- --data-dir ./campaign --port 8080
```

1. **The first wizard.** Create a character, pick any ancestry/background,
   then Class → Wizard. Intent checks: there is **no** class-feat card (a
   level-1 Wizard has none — that was the Fighter's slot); trained-skill
   sources say "from Wizard"; the spellbook is one card per rank, with
   the curriculum under its own labeled header and CURRICULUM chips on
   each row — is that now impossible to miss? Pick all three Battle
   Magic curriculum spells: the meter reads "2 of 2", never "3 of 2".
   Fill everything, finalize, and read the sheet: does the spellcasting
   block match your hand math (with Int +4: spell attack +7, DC 17, 3
   rank-1 slots, 6 cantrips/day), and does "Preparation — at the table"
   match what you meant by keeping daily state out of chargen?
2. **Illegal picks stay yours.** In the rank-1 picker, fill the book with
   only one curriculum spell and confirm. The card keeps your picks, shows
   the shortfall right there in red, and the Curriculum meter reads
   "1 of 2". Swap one spell in place and confirm — no clear-and-restart.
3. **The changed mind.** Change the school on that character. The
   confirmation dialog lists only the school itself; afterwards your whole
   spellbook is still checked in the reopened picker, with the new
   curriculum re-judged (fix by swapping, not rebuilding). Intent check:
   is "destroys nothing, re-judges" the behavior you wanted from finding 5?
4. **The honest finalize.** With everything complete, toggle a checkbox
   off and back on, or type into Notes and delete it — Finalize stays
   enabled. Make a real edit and leave it unconfirmed: Finalize disables
   WITH an "Unconfirmed changes" chip naming the slot (click it to jump),
   and "← Roster" warns before discarding. Intent check: is this the
   honesty you wanted from the dead-button finding?
5. **The owned skill.** On a Fighter, pick Thievery as a free trained
   skill, then take the Street Urchin background. No "replacement skill"
   card appears; instead the trained-skills card says "Thievery now comes
   from Background: Street Urchin — pick a different skill" with your
   picks preloaded, and the sheet attributes Thievery to the background.
   Swap in place. Intent check: is this the flip you asked for in
   finding 11?
6. **Committed but readable.** Click "Details ▼" on your confirmed school
   card — description, focus spell, and curriculum list, no undo needed.
7. **Nothing else moved.** Open one of your existing finalized Fighters —
   sheet unchanged. Resize the window down to tablet width anywhere in the
   wizard: the layout stacks to one column, nothing overflows or hides.
8. **The feature map.** Skim [docs/feature-map.md](../../../docs/feature-map.md)
   — each user-visible flow mapped to its UI file, engine code, and pinning
   tests. Intent check: is this the maintenance aid you had in mind?

## Constraints now enforced

Every row of the revised architecture's Constraints emitted table is green
in the repo's own tooling (`cargo test --workspace` + `npm test` + Playwright):

| Rule | Where it lives |
|---|---|
| engine-core byte-identical (the experiment's zero) | evidence below: empty diff over `crates/engine-core`, `crates/types`, persistence, routes, version guard; layering/purity rows guard the boundary |
| Spellbook satisfiability, every school, no dead ends | `checks/replay.rs` (`every_school_has_a_satisfiable_spellbook_and_no_dead_ends`) |
| School change destroys nothing, re-judges | `checks/replay.rs` (`changing_school_rejudges_instead_of_clearing`) + changed-mind e2e story |
| Class-feat slot hidden; class-named skill sources | Sylvenne + Torvald goldens, `checks/replay.rs` |
| Spell-record lint: bounded heightening, stable IDs, license, cross-refs | `checks/rules_data.rs` + ruleset integrity tests |
| Attestation: spell + class-feature partitions, zero unwaived | `checks/attestation.rs` |
| Layout sweep on every step visit + wordiest-content stress at 2 widths | `ui/e2e/layout.ts` wired into `helpers.ts`; `ui/e2e/layout.spec.ts` |
| Card-local confirm feedback (refusal, offline, illegal-saved) | `ui/e2e/wizard-class.spec.ts` illegal-picks story; `stories.spec.ts` server-down story |
| No shipped-record name as a ruleset source literal | `checks/class_isolation.rs` (build-failing lint) |
| Cross-class contamination sweep, automatic for every future class | `checks/class_isolation.rs` |
| Kind→control mapping total and exclusive (sets vs bags) | `ui/src/SlotCard.test.tsx` + `SlotCard.grid.test.tsx` |
| Storage untouched: schema v2, no new write paths | `checks/persistence.rs`, `checks/no_rewrite_on_load.rs` (unchanged) |
| Golden per shipped school + re-judge fixture | `checks/replay.rs` (Sylvenne/Battle Magic golden; Protean re-judge) |
| Wizard projection < 5 ms | `checks/perf.rs` |
| **(R2)** Meter display and state can never disagree | `MeterView` constructors + types tests; literal lint in `checks/class_isolation.rs` |
| **(R2)** No dead controls: a disabled action explains itself visibly | `ui/e2e/layout.ts` dead-control invariant, swept on every step visit |
| **(R2)** No-op edits never arm pending state | `sameSelection`/`isRealEdit` + `ui/src/pending.test.ts`; meander story |
| **(R2)** Grants own skills and attribution; collisions add a free pick | `skill_resolution` + ruleset unit tests; Krivvy golden; owned-skill story |
| **(R2)** Shrink-direction re-judge (Int drops after picks) | `shrinking_intelligence_rejudges_over_count_skill_picks` |

## Decisions made inside the contract

- **Wizard quick build is deferred** (`quick_build_deferred: true` on the
  class record): a one-click wizard would have to invent a spellbook; the
  roster's quick-build stays Fighter-only until a curated build ships.
- **Curriculum minimum message fires only when the book is full** — while
  picking, the meter carries the state; the red message appears at confirm
  time so it never nags mid-selection.
- **Illegal-confirmed slots stay open, preloaded** (fix where the problem
  is); the closed-summary-with-Change presentation is reserved for legal
  complete slots. The status-grid unit test now pins this.
- **Bounded bags** (per-item max in a tray) have no consumer yet; the
  vocabulary extension is deferred to Epoch 8's first real need.
- Sheet wording for the non-prep note: a `Preparation` row valued
  "at the table" with one explanatory detail line.
- Legacy-language sweep run over the final diff (no detour vocabulary or
  transitional comments survive; the restore was done with
  `git restore --source`, not by hand-unediting).
- **(R2)** Rules-data version bumped to pf2e-pc.0.3.1 (data records
  unchanged; the bump exists because deleting the replacement slots
  changes stored-log vocabulary, and the version guard is the sanctioned
  compat path). Attestation re-run: zero unwaived mismatches.
- **(R2)** Group headings render only when a catalog spans two labeled
  groups; the badge chip is the filtering-proof signal. List-slot (bag)
  grouping keeps its existing shopping-group headings.
- **(R2)** A conflict reload from another tab now KEEPS in-progress
  edits (pruned against the reloaded truth) instead of wiping them;
  clear-slot and fill-remaining still reset pending deliberately.

## Agent evidence

- `cargo test --workspace`: **122 passed, 0 failed** (class_isolation now
  3 incl. the meter-literal lint; types meter constructors 3; ruleset 33
  incl. ownership + shrink tests); `cargo clippy --workspace
  --all-targets`: **0 warnings**; `cargo fmt` clean.
- UI: vitest **43 passed** (6 files, incl. the pending/no-op and
  groupedRows suites), `tsc --noEmit` clean, eslint clean.
- Playwright e2e: **30 passed in ~40 s** — 20 Fighter walks/stories, 8
  Wizard stories (4 new: meander, overshoot, details-stay-readable,
  owned-skill), 2 layout-stress — every step visit swept by the extended
  `expectSaneLayout` (now incl. the dead-control invariant).
- Engine byte-identity: `git diff main...HEAD --stat -- crates/engine-core
  crates/types crates/server/src/persistence crates/server/src/routes.rs
  crates/server/src/version.rs` → **empty** (0 files, 0 lines).
- Hands-on browser passes (Playwright-driven, screenshots reviewed):
  round 1 found → fixed the tablet starved-column bug, the illegal-slot
  collapse, and the green-ack-on-illegal-save. Round 2 visually verified
  badges/group headers, the capped and overshoot meters, confirmed-card
  details, the pending chip, the leave dialog, and tablet stacking — and
  caught a confirm-hint layout squeeze (fixed, re-verified).

## Complaints logged

One from the first round of this checkpoint (2026-08-28, implement stage):
no clear channel for iterative human feedback during report review — the
findings-gathering flow used here was improvised. Nothing new this round.
