# Chargen slice 3: PF2e Wizard — report

Checkpoint: `chargen-wizard` · Branch: `checkpoint/chargen-wizard` · Status: delivered

## What changed and why

The creation wizard now builds a **PF2e Wizard**: arcane thesis, arcane
school, the spellbook (10 cantrips + 5 rank-1 spells of your choice, plus 2
rank-1 spells added from your school's curriculum), and the daily
preparation — 5 cantrips and 2 rank-1 slots prepared from the book, plus
one curriculum cantrip and one curriculum rank-1 spell prepared straight
from the school (the printed rule; neither needs to be in your book). The
finalized sheet shows the whole spellcasting block — spell attack/DC,
slots, focus pool with the school's focus spell, book vs prepared clearly
split — and carries the slice's one post-finalize affordance: **Change
prepared spells**, which reopens just the prep picker while every build
choice stays locked.

Under the hood this is the first exercise of the vision's
scope-agnostic-choice commitment: prepared spells live in a **play-scoped
section** of the character file, beside — never inside — the decision log.
The engine validates them with the same slot machinery as build choices
(one driver), the stored sheet remains a pure function of the log, and the
prep save is the first-ever write path to finalized files — carrying the
full idempotency/stale-view/crash discipline, and byte-leaving the log and
sheet untouched. Changing your arcane school cascades across the scope
boundary: the confirmation lists exactly the curriculum-derived choices
(spellbook curriculum additions, both school preparations, and the rank-1
preparation whose book shrinks), clears them in one durable write, and
leaves the school-independent cantrip preparation standing.

Rules data moved to `pf2e-pc.0.3.0`: 29 spells, 2 theses (Spell Blending,
Spell Substitution), 2 schools (Battle Magic, Protean Form) and the Wizard
class + kit, every record's mechanical fields (action cost, defense,
range/area/targets, duration, traits, heightening entries) transcribed as
structured data and machine-verified against the pinned Foundry snapshot —
zero unwaived mismatches — with pages and names cross-checked against
Archives of Nethys. Existing characters re-pin quietly (additive data).

## How to verify

Run the app on your own campaign directory:

```bash
cargo run --release -p server -- --data-dir ./campaign
```

1. **The first wizard.** Create a character, walk Ancestry and Background
   as usual, then pick **Wizard** at the Class step. Walk thesis → school →
   spellbook (watch the counters) → preparation (the school slots offer the
   curriculum, including spells you did NOT put in your book). Finalize and
   hand-check the spellcasting block against the Player Core: spell attack
   = 3 (trained) + Int, spell DC = 10 + that, cantrips "5+1 prepared",
   rank-1 slots "2+1", focus pool 1 with the school's focus spell named.
2. **The pencil edit.** On the finalized sheet, press *Change prepared
   spells*, swap a cantrip, press Done. Restart the server, reopen the
   sheet: the swap survived. Open the character's JSON in an editor: the
   `log` array is untouched; only the small `prep` section changed.
3. **Illegal prep, caught.** In the prep picker, overfill a rank (add a
   third rank-1 spell): the meter flags it live and Confirm is refused with
   the rule spelled out. Remove one; it saves.
4. **The changed mind.** Mid-wizard with book and prep set, press Change…
   on the arcane school: the prompt lists exactly what will clear (the
   curriculum spellbook additions, the school cantrip and school slot, the
   rank-1 preparation) — your prepared cantrips are not on the list, and
   after the swap they are still there while the new school's focus spell
   shows on the sheet.
5. **The crash.** Kill the server mid-class-step (`kill -9`), restart,
   reopen: resume lands where you were, spellbook and confirmed prep
   intact.
6. **Nothing else moved.** Open one of your existing Fighters — it loads
   unchanged (a quiet re-pin to the new data version is offered, no review
   flags). Create a new Fighter: no spell steps anywhere, no class-feat
   slot missing.
7. **The skeptical inspection.** Hand-edit a wizard's `prep` section (put
   in a spell that isn't in the book, or mangle the JSON), then:

```bash
cargo run --release -p server -- --data-dir ./campaign verify
```

   `PREP-BAD` names the rule (or reports the section unreadable); the
   character still loads either way, and the prep picker offers wholesale
   replacement.
8. **Spot-check three spell records** (suggested: Ignition — heightening
   cantrip; Breathe Fire — save spell; Force Bolt — the Battle Magic focus
   spell) in `rules-data/spells.json` against Archives of Nethys, including
   the structured fields, not just the text.
9. **Intent check — the experiment.** Read "Decisions made inside the
   contract" below and the engine-core listing: does "adding a class is
   data + slot definitions" feel true, with the two sanctioned engine
   amendments honestly bounded?
10. **Intent check — the feel.** Is the spellbook-then-prep flow something
    you would hand a new wizard player at a table?

## Constraints now enforced

All slice-1/2 rows still run. New rows, all green in `cargo test -p checks`:

| Rule | Lives at |
|---|---|
| Replay ignores prep (same log ± any prep → byte-identical stored sheet) | `checks/replay.rs::stored_sheet_is_pure_over_prep` |
| Prep-save writes only prep (+ v2 schema-envelope carve-out fixture) | `checks/prep.rs::prep_save_writes_only_prep` |
| Prep-save idempotency, stale rejection, lifecycle rejection | `checks/prep.rs::prep_save_idempotency_and_stale_rejection` |
| Crash safety: draft-prep, finalized-prep, and school-cascade SIGKILL cycles | `checks/crash_harness.rs::prep_writes_under_sigkill_are_none_or_all` |
| Finalized writers serialize (no lost update) | `checks/prep.rs::finalized_writers_serialize` |
| Prep routes respect the version guard | `checks/version_guard.rs::prep_saves_on_older_pinned_characters_are_rejected` |
| Server authority over raw prep (not-in-book / overfill / non-curriculum / unknown slot / prep-on-Fighter) | `checks/api_authority.rs::raw_illegal_prep_is_rejected_and_writes_nothing` |
| `verify` re-validates prep (illegal / unknown ID / wrong class / broken section; absent silent) | `checks/prep.rs::verify_revalidates_prep` |
| One validation driver, observable (route ↔ verify parity) | `checks/prep.rs::one_validation_driver_route_and_verify_agree` |
| Cascade clears exactly the previewed set | `checks/replay.rs::changing_school_cascades_exactly_as_previewed` |
| Storage v3 (v2 reads, upgrades on first write incl. the prep-save path; v4 refused; absence valid) | `checks/persistence.rs` |
| Broken prep degrades, never quarantines | `checks/persistence.rs::v2_documents_read_and_broken_prep_degrades` |
| Spell records: schema + bounded heightening + curriculum/focus cross-refs | ruleset integrity + `checks/rules_data.rs` |
| Attestation covers the spell partition (zero unwaived mismatches) | `checks/attestation.rs` + `rules-data/attestation.json` |
| Goldens: Sylvenne per school, cascade fixture, revised-prep fixture | `checks/replay.rs` |
| Wizard projection incl. prep < 5 ms | `checks/perf.rs::wizard_fold_with_prep_is_under_5ms` |

## Decisions made inside the contract

- **Engine-core diff (the experiment's deliverable).** Exactly the two
  architected amendments, in full: (1) the scoped-choice machinery —
  `with_scoped` construction, the shared per-slot driver serving both
  scopes, `scoped_projection`/`apply_scoped` (total over hand-edited
  sections), and the existing dependent-clearing/`clear`/`amend`/preview
  operations widened so their reach crosses the scope boundary (no second
  tracker); (2) projection input widening — `project` takes the scoped
  set, scoped slots render into steps flagged `scoped`, and displayed
  sheets append ruleset-supplied scoped sections while `Engine::sheet`
  stays `fold(log)`. No game vocabulary entered the crate (the purity and
  layering checks run over all of it). Everything Wizard-specific lives in
  `ruleset-pf2e` (a `spells` kind module + slot definitions) and data.
- **The concurrency token is the file's write version**, not a separate
  prep-section counter: strictly stronger (any concurrent mutation
  invalidates a stale prep save) and it reuses the slice-1 conflict
  machinery; idempotency rides a `last_request_id` stored in the section.
- **One prep route for both lifecycles** with `expected_state` in the
  request — the architecture's lifecycle-mismatch rejection, without two
  routes duplicating the discipline.
- **Finalized prep saves also reject incomplete sets** (a finished sheet
  stays table-ready); draft saves reject only illegal ones, so the wizard
  can save progress step by step.
- **School preparations come straight from the curriculum** — the printed
  wizard-spellcasting rule ("as well as one extra curriculum cantrip and
  one extra curriculum spell … from your arcane school") — and the
  spellbook gained the printed fourth slot ("you also add two 1st-rank
  spells from the curriculum"). Both are deliberately exercised in goldens
  and e2e with spells that are NOT in the book.
- **Changing schools also clears the rank-1 preparation** (its book loses
  the curriculum additions). The spec's story named the curriculum slot
  and focus spell; the implemented cascade is the honest transitive
  closure, the confirmation lists all of it exactly, and the cantrip
  preparation survives — the property the story was protecting.
- **The Wizard ships `quick_build_deferred: true`** instead of a
  suggested-build block (spec defers its quick build to `wizard-content`);
  data integrity now demands a block *or* that explicit marker, so the
  Fighter's guarantee is undiluted and the marker's removal is
  `wizard-content`'s forcing function.
- **WASM-side parity is structural**, mirroring slice-1's client/server
  posture: the observable parity row pins route ↔ verify on the same
  driver; the browser runs the identical engine function from the same
  commit under the bindings-freshness gate.

## Agent evidence

- `cargo test --workspace`: **131 passed, 0 failed** (engine-core 24 incl.
  7 scoped; ruleset 31; checks 76 across 12 binaries incl. the new
  `prep.rs` five).
- Playwright e2e: **25 passed** — the 20 existing Fighter walks unchanged
  plus 5 new wizard stories (first wizard with hand-checked spellcasting
  block, illegal prep caught+fixed, changed mind with exact cascade list,
  crash at the class step, pencil edit surviving SIGKILL restart). UI unit
  tests 32 passed; `tsc`/eslint clean; clippy zero warnings.
- Budgets: suite execution wall time **15 s** (< 20 s, CI-gated);
  wizard projection incl. prep asserted **< 5 ms**; warm-rebuild gate
  unchanged (CI-measured).
- Deltas: rules-data 0.2.0 → 0.3.0 (+33 records, 450 total IDs in the
  lineage record); WASM binary 908 KB → 1 061 KB (+153 KB, embedded spell
  data + scoped machinery); attestation: **zero unwaived mismatches, zero
  stale waivers** (one new reviewed waiver: `kit.wizard`, book-only like
  the Fighter kit).
- Reference verification: all 29 spells match the pinned Foundry snapshot
  on rank/traditions/traits/actions/defense/range/area/targets/duration
  and heightening shape; pages and Player-Core-only membership (Ray of
  Frost, Mage Hand, Feather Fall correctly excluded as legacy-only)
  cross-checked against the Archives of Nethys index.

## Complaints logged

None — no harness friction this checkpoint.
