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
Wizard changed the engine by **zero lines**. `crates/engine-core`,
`crates/types`, the persistence layer, the routes, and the version guard
are byte-identical to the branch point — the whole class is rules data
(29 spells, 2 theses, 2 schools, the class record) plus ruleset slot
definitions. The storage schema is untouched (still v2).

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

## How to verify

Serve your real campaign as usual, then walk these on your own data:

```bash
cargo run -p server -- --data-dir ./campaign --port 8080
```

1. **The first wizard.** Create a character, pick any ancestry/background,
   then Class → Wizard. Intent checks: there is **no** class-feat card (a
   level-1 Wizard has none — that was the Fighter's slot); trained-skill
   sources say "from Wizard"; the spellbook is one card per rank, cantrips
   and rank 1, with your school's curriculum spells listed first and
   badged. Fill everything, finalize, and read the sheet: does the
   spellcasting block match your hand math (with Int +4: spell attack +7,
   DC 17, 3 rank-1 slots, 6 cantrips/day for Battle Magic), and does
   "Preparation — at the table" match what you meant by keeping daily
   state out of chargen?
2. **Illegal picks stay yours.** In the rank-1 picker, fill the book with
   only one curriculum spell and confirm. The card keeps your picks, shows
   the shortfall right there in red, and the Curriculum meter reads
   "1 of 2". Swap one spell in place and confirm — no clear-and-restart.
3. **The changed mind.** Change the school on that character. The
   confirmation dialog lists only the school itself; afterwards your whole
   spellbook is still checked in the reopened picker, with the new
   curriculum re-judged (fix by swapping, not rebuilding). Intent check:
   is "destroys nothing, re-judges" the behavior you wanted from finding 5?
4. **Nothing else moved.** Open one of your existing finalized Fighters —
   sheet unchanged. Resize the window down to tablet width anywhere in the
   wizard: the layout stacks to one column, nothing overflows or hides.
5. **The feature map.** Skim [docs/feature-map.md](../../../docs/feature-map.md)
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

## Agent evidence

- `cargo test --workspace`: **116 passed, 0 failed** (includes the new
  `class_isolation` binary, replay 16, perf 2); `cargo clippy
  --workspace --all-targets`: **0 warnings**; `cargo fmt` clean.
  Wall time 13 s.
- UI: vitest **36 passed** (5 files), `tsc --noEmit` clean, eslint clean.
- Playwright e2e: **26 passed in ~36 s** — 20 Fighter walks/stories
  (unchanged, the regression net), 4 Wizard stories, 2 layout-stress —
  every step visit swept by `expectSaneLayout`.
- Engine byte-identity: `git diff main...HEAD --stat -- crates/engine-core
  crates/types crates/server/src/persistence crates/server/src/routes.rs
  crates/server/src/version.rs` → **empty** (0 files, 0 lines).
- Hands-on browser passes (Playwright-driven, screenshots reviewed):
  found → fixed the tablet starved-column bug, the illegal-slot collapse,
  and the green-ack-on-illegal-save; final finalized sheet visually
  verified at desktop and tablet widths.

## Complaints logged

One from the first round of this checkpoint (2026-08-28, implement stage):
no clear channel for iterative human feedback during report review — the
findings-gathering flow used here was improvised. Nothing new this round.
