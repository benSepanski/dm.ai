# chargen-wizard — ticket plan

Contract: spec e90d35d5, architecture 94ee856e. Branch `checkpoint/chargen-wizard`.
Rule: a ticket is done when its code, its tests, and its constraint rows are green
in the repo's own tooling. Constraint rows that need a feature land with that
feature's ticket; T1 tracks the full table.

## T1 — Constraints emitted table applied  [in progress]

Tracking checklist for the architecture's new rows (each lands with its enabling
ticket; all must be checked before the report):

- [ ] replay ignores prep (identical logs ± prep → byte-identical sheets) — `checks/replay.rs` (T3/T11)
- [ ] prep-save writes only prep (+ v2-envelope carve-out fixture) — `checks/prep.rs` (T8)
- [ ] prep-save idempotency + stale rejection (slice-1 helpers) — `checks/prep.rs` (T8)
- [ ] crash harness: draft-prep confirm cycle — `checks/crash_harness.rs` (T8)
- [ ] crash harness: finalized-prep edit cycle — `checks/crash_harness.rs` (T8)
- [ ] crash harness: school-change cascade cycle — `checks/crash_harness.rs` (T8)
- [ ] finalized writers don't race (prep save vs version action) — `checks/prep.rs` (T7/T8)
- [ ] prep routes respect version guard (flagged/older-pinned rejected) — `checks/version_guard.rs` (T8)
- [ ] server authority over prep (not-in-book / overfill / non-curriculum / wrong-lifecycle / no-prep-class) — `checks/api_authority.rs` (T8)
- [ ] verify re-validates prep (illegal / unknown-ID / prep-on-Fighter / absent-silent / legal-clean) — `checks/prep.rs` (T8)
- [ ] one-driver parity (native route = verify = WASM preview) — `checks/prep.rs` (T9)
- [ ] cascade clears exactly the listed dependents — `checks/prep.rs` (T5)
- [ ] storage v3 rows (v2 reads, no rewrite on load, upgrade on first write incl. prep-save path, v4 refused, absence valid) — `checks/persistence.rs` (T7)
- [ ] broken prep degrades, never quarantines — `checks/persistence.rs` (T7)
- [ ] spell-record data lint (bounded heightening shape, IDs, license, cross-refs) — `checks/rules_data.rs` (T6)
- [ ] attestation covers spell partition — `checks/attestation.rs` (T6)
- [ ] engine purity + kind isolation cover new code (no config change; verify green) — existing checks (T3–T5)
- [ ] goldens: one wizard per shipped school + cascade fixture + revised-prep fixture — `checks/replay.rs` (T11)
- [ ] perf: fold budget still <5ms incl. spellcasting block + scoped validation — `checks/perf.rs` (T11)

## T2 — types: boundary shapes  [ ]
Prep-section storage/view shapes, scoped-choice request/response enums (engine_msg),
spellcasting presentation block (book vs prepared, cantrip rank precomputed),
prep-section version + request-ID fields. No game logic.

## T3 — engine-core diff 1: validate_scoped  [ ]
Slot defs + choice set + folded base → checklist entries. Dependent clearing
reaches across the scope boundary via the existing slot-graph machinery (no second
tracker). Unit tests. Purity rules apply.

## T4 — engine-core diff 2: projection input widens  [ ]
Projection accepts optional scoped section; view combines sheet + prep on both
runtimes. Stored sheet untouched. Unit tests.

## T5 — ruleset-pf2e: spells kind + Wizard class kind  [ ]
`spells` kind module (record parsing, catalogs, option sources). Wizard class kind:
thesis, school (curriculum), arcane bond, class feat slot, spellbook slots, prep
slot definitions (per-rank counts, in-book source, curriculum restriction).
Mechanics: spell attack/DC, slots by rank, focus pool. Cascade: school change
lists+clears curriculum prep + focus spell. Kind isolation holds.

## T6 — rules-data v0.3.0 + reference pipeline  [ ]
Representative subset records: 2 theses, 2–3 schools (curricula + focus spells),
cantrips + rank-1 spells (attack / save / utility / heightening display), wizard
class record, kit. Structured mechanical fields (transcribe-only). shipped-versions
update, denylist pass, license metadata. reference-check spell partition +
attestation re-run + data lints.

## T7 — persistence: schema v3 + serialization  [ ]
Optional prep section (absent = valid); v2 read-accept, upgrade on first ordinary
write; v4 refused in place; prep parses independently (broken prep degrades);
per-character serialized write path for finalized-file mutations.

## T8 — server routes  [ ]
Draft prep step through ordinary confirm machinery (durable per confirm); finalized
prep-edit route (idempotency ID, prep version, stale rejection); version-guard
rejection on flagged/older-pinned; native re-validation authority; lifecycle
mismatch rejection.

## T9 — wasm + bindings  [ ]
Expose scoped validation + widened projection; regen committed bindings;
bindings-freshness gate green; parity fixture (native = verify = WASM).

## T10 — ui  [ ]
Wizard class step: thesis → school → bond → class feat → spellbook picker → prep
picker (shared slot components, live WASM preview). Sheet spellcasting block.
"Change prepared spells" on finalized sheet view. Cascade confirmation lists prep
dependents. No game arithmetic in TS.

## T11 — goldens, perf, e2e  [ ]
Hand-verified golden wizard per shipped school (AoN-checked); cascade + revised-prep
fixtures; fold benchmark re-run; Playwright scenarios: first wizard, pencil edit,
illegal prep, changed mind, crash, fighter regression, skeptical inspection.

## T12 — report  [ ]
`.checkpoints/run/chargen-wizard/report.md`: engine-core diff listing +
justification (the experiment's deliverable), payload/suite/rebuild/WASM deltas,
constraint table all green, user-story walkthroughs for Ben.
