# roster-ergonomics — ticket plan

Docs: `.checkpoints/specs/roster-ergonomics.md`,
`.checkpoints/architecture/roster-ergonomics.md`. Branch
`checkpoint/roster-ergonomics`. Tickets in order; `[x]` = done, `[~]` = in
progress. Constraints (ticket 1) are wired first as check scaffolding and
turn green as their feature tickets land — every row green before the
report.

## Key design decisions (bound by the docs; details agent-decided)

- Entropy = a 64-bit seed derived by hashing the client `request_id`
  (FNV-1a → SplitMix64 mixing). Pure data, deterministic, no rand dep
  anywhere; distinct taps (UUIDs) give distinct builds; same request ⇒
  same character, which also strengthens idempotency.
- `Sampler` (SplitMix64 PRNG, plain arithmetic, caller-seeded) lives in
  engine-core as the standalone pick source; the legality filter is the
  caller choosing which options to hand it (`available`-only vs all) —
  separable by construction.
- The planner's suggestion source becomes state-aware:
  `FnMut(&SuggestionContext) -> Option<SlotSuggestion>` where the context
  carries slot ID, kind, and the option views; `expand_suggestions` gains
  bounded per-slot resampling (re-ask the source on append refusal, cap
  64) before reporting unresolved.
- Random mint route: seed typed name (Player) if given → expand with the
  random source (skips the name slot) → sample name from ancestry pool
  (Random source) if none → save once. Chosen class seeds as Player
  decision; "any" samples the class (Random).
- Clone route: load source, refuse trashed/quarantined/pin-unloadable/
  replay-divergent; copy doc verbatim except id/file + name decision
  (re-minted, `DecisionSource::Clone`, clone-time name; appended if the
  source had none); sheet re-derived by replay under the source pin.
- ID prefixes: mint `c-rn-`, clone `c-cl-` (quick build keeps `c-qb-`).
- Name pools: `app-data/name-pools.json` (default pool + per-ancestry
  pools, ≥12 names each), read at mint time; malformed ⇒ typed error.
- Schema v3 = v2 + `random`/`clone` decision sources. MIN stays 1.

## Tickets

- [ ] 1. Constraints wiring: register `checks/random_mint.rs` and
  `checks/clone.rs` in the checks crate; name-pool lint section in
  `checks/rules_data.rs`; note rows carried by existing tooling
  (layering, quick-build-unchanged) — each later ticket lists the rows it
  turns green.
- [ ] 2. types + storage: `DecisionSource::{Random, Clone}`; mint/clone
  API types; `RosterView.classes` catalog for the picker; schema v3
  (persistence fixtures updated; v1/v2 load fixtures kept byte-identical).
- [ ] 3. engine-core: `Sampler`; `SuggestionContext`; state-aware
  source signature + bounded resampling in `expand_suggestions` /
  `unresolved_suggestions`; migrate existing callers (quick-build route,
  fill-remaining, engine tests). Quick-build behavior byte-identical
  (goldens in `checks/quick_build.rs`, `checks/replay.rs` untouched and
  green).
- [ ] 4. server: `app-data/name-pools.json` + loader; random-mint route
  (idempotent, crash-safe, typed failures, no partial writes); classes in
  roster response.
- [ ] 5. server: clone route (idempotent, creation-only, refusals:
  trashed/quarantined/divergent/pin-unloadable; first-write-wins on
  retried name).
- [ ] 6. checks: `random_mint.rs` (seed-sweep soundness, determinism,
  variety, pool failure fixtures); `clone.rs` (fidelity for draft/
  finalized/old-pin, refusal fixtures); extend `confirm_idempotency.rs`
  (both routes, per-route prefixes), `crash_harness.rs` (both write
  paths), `persistence.rs` (v3 + old-file fixtures),
  `no_rewrite_on_load.rs` (creation-only sweep over new routes).
- [ ] 7. `pf2e_random_walk` in `checks/replay.rs` consumes the Sampler
  with the legality filter off (fuzz-seam proof row).
- [ ] 8. perf: mint benchmark < 250 ms in `checks/perf.rs` driving the
  route in-process; fold budget unchanged.
- [ ] 9. UI: roster Random button + class picker ("any" default), Clone
  dialog (prefilled "<name> (copy)"), pending-state button disable,
  provenance badges on decided cards at review; unit tests.
- [ ] 10. e2e `ui/e2e/roster.spec.ts`: mint walk (variety visible),
  typed-name preserved, clone dialog walk, badges — under the generic
  layout sweep.
- [ ] 11. All gates green: `cargo fmt --check`, clippy, full checks
  suite, UI unit tests, e2e, suite-time ceiling.
- [ ] 12. Report `.checkpoints/run/roster-ergonomics/report.md`; commit.
