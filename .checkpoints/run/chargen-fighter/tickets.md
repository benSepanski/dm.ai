# chargen-fighter — ticket plan

Run state for the implement stage. Governing docs (do not diverge):
- `.checkpoints/specs/chargen-fighter.md` (approved ba13d2a4498d)
- `.checkpoints/architecture/chargen-fighter.md` (approved b4e01fd3e3b3)

States: `[ ]` todo · `[~]` in progress · `[x]` done · `[!]` blocked (note why)

## Tickets

- [x] **1. Constraints emitted** (architecture "Constraints emitted" table,
  verbatim): cargo workspace skeleton (`types`, `engine-core`, `ruleset-pf2e`,
  `wasm`, `server`, `checks`), `clippy.toml` (disallowed methods/types),
  `deny.toml`, `[workspace.lints]` + `#![forbid(unsafe_code)]` in engine
  crates, `checks/crate_layering.rs` (edge allowlist, banned crate names,
  kind-module import scan, storage-doc export scan), `ui/` scaffold (Vite +
  React) with strict `tsconfig.json` + `eslint.config.js`
  (no-explicit-any, no-restricted-imports), `.github/workflows/ci.yml`
  running every row. Checks that need the app to exist (`persistence`,
  `crash_harness`, `confirm_idempotency`, `no_rewrite_on_load`,
  `api_authority`, `replay`, `rules_data`, `perf`) are stubbed as
  `#[ignore]`-free failing-if-absent placeholders? — NO: they land with
  their feature tickets; ticket 1 lands the files' *slots* in CI config so
  wiring is never an afterthought. Layering check green before ticket 2.
- [x] **2. `types` crate**: IDs, decision/log shapes, checklist entry,
  presentation contract (sheet view model), request/response enums for the
  WASM boundary, API wire types. serde + tsify derives on everything
  boundary-crossing.
- [x] **3. `engine-core`**: choice slot (unlock condition, option source,
  validators, effects), slot-graph resolution, log append/replay, validation
  → checklist, fold traversal, draft lifecycle (incl. dependent-clear
  computation, decision IDs, draft versions). Unit tests + proptest random
  walk over the slot graph.
- [x] **4. `ruleset-pf2e`**: mechanics module (boost math, proficiency
  arithmetic, HP, AC, saves, attacks, Bulk); kind modules (ancestry,
  background, class, feats, skills, equipment) with registration-only public
  surface; rules-data record parsing (records passed in, no file access);
  PF2e Fighter slot definitions; sheet derivation via the fold. Golden sheet
  tests (Torvald the Dwarf Fighter + 2 more hand-verified builds),
  `checks/replay.rs` (golden + property), fold benchmark in `checks/perf.rs`.
- [x] **5. `rules-data`**: versioned JSON (Dwarf/Human/Elf/Goblin + Player
  Core heritages + L1 ancestry feats; Field Medic/Warrior/Blacksmith/Hunter/
  Street Urchin; Fighter class + L1 class feats incl. one with prerequisite;
  skills; starting kit + small gear list). Stable IDs, per-record license
  metadata, ORC notice string. `checks/rules_data.rs` lint. Verified against
  Archives of Nethys (agent research notes in `run/` dir).
- [x] **6. `server` + persistence**: axum routes (roster, create draft,
  confirm decision, unconfirm/change with dependent-clear, finalize, view,
  delete-to-trash, resume); persistence module (private storage docs, temp →
  fsync → rename, schema v1 + unknown-version refusal, quarantine, `trash/`
  timestamped, data-dir lockfile pid-checked, port-walk, temp-file sweep);
  `verify` subcommand. Static file serving of built UI. Checks:
  `persistence.rs`, `crash_harness.rs`, `confirm_idempotency.rs`,
  `no_rewrite_on_load.rs`, `api_authority.rs`.
- [x] **7. `wasm` crate + TS façade**: one request enum in, one response enum
  out via tsify `Ts<T>`; panic hook; committed generated bindings; CI
  bindings-freshness step green; WASM↔native parity smoke on fixture logs.
- [x] **8. `ui`**: roster (create/resume/view/delete w/ confirm), 7-step
  wizard (concept → ancestry+heritage+ancestry feat → background → class →
  boosts → equipment → details), non-linear nav with badges, live checklist
  (incomplete vs illegal, jump-to-step), summary sidebar w/ live recompute,
  change-confirmed-choice flow with clear-list confirmation, finalize, sheet
  view, ORC notice. Component tests (checklist, counters).
- [x] **9. Playwright e2e**: first run (hand-checkable numbers), the mistake
  (incl. clearing), the crash (real server kill), jumping ahead,
  change-ancestry dependent clearing, delete-to-trash.
- [x] **10. Full verification + report**: entire CI matrix green locally;
  `--timings` artifact; spot-check data records vs AoN; write
  `.checkpoints/run/chargen-fighter/report.md`, commit, present. Ping Ben's
  phone (he asked 2026-08-27).

## Decisions made in-bounds (report these)

All 13 recorded in report.md ("Decisions made inside the contract").

## Complaints logged

(none yet)
