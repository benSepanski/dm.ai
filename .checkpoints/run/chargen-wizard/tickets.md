# chargen-wizard — ticket plan

Contract: spec e90d35d5, architecture 94ee856e. Branch `checkpoint/chargen-wizard`.
All tickets complete; report at report.md.

## T1 — Constraints emitted table applied  [x]

- [x] replay ignores prep — `checks/replay.rs` (stored_sheet_is_pure_over_prep)
- [x] prep-save writes only prep (+ v2-envelope fixture) — `checks/prep.rs`
- [x] prep-save idempotency + stale + lifecycle rejection — `checks/prep.rs`
- [x] crash harness: draft-prep, finalized-prep, school-cascade cycles — `checks/crash_harness.rs`
- [x] finalized writers don't race — `checks/prep.rs` (finalized_writers_serialize)
- [x] prep routes respect version guard — `checks/version_guard.rs`
- [x] server authority over prep — `checks/api_authority.rs`
- [x] verify re-validates prep — `checks/prep.rs` (verify_revalidates_prep)
- [x] one-driver parity (route = verify; WASM structural) — `checks/prep.rs`
- [x] cascade clears exactly the listed dependents — `checks/replay.rs`
- [x] storage v3 rows — `checks/persistence.rs`
- [x] broken prep degrades, never quarantines — `checks/persistence.rs`
- [x] spell-record data lint + bounded heightening — ruleset integrity + `checks/rules_data.rs`
- [x] attestation covers the spell partition — `checks/attestation.rs` (zero unwaived)
- [x] engine purity + kind isolation over new code — existing checks, green
- [x] goldens: Sylvenne (Battle Magic) + Protean swap + cascade + revised-prep — `checks/replay.rs`
- [x] perf: wizard projection with prep < 5 ms — `checks/perf.rs`

## T2 — types  [x]  ## T3/T4 — engine-core diffs  [x]  ## T5 — ruleset  [x]
## T6 — rules-data 0.3.0 + reference pipeline  [x]  ## T7 — persistence v3  [x]
## T8 — server routes  [x]  ## T9 — wasm + bindings  [x]  ## T10 — ui  [x]
## T11 — goldens, perf, e2e  [x]  ## T12 — report  [x]
