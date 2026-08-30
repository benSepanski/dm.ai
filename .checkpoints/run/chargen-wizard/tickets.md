# chargen-wizard — ticket plan (revised contract)

Contract: spec 5a2924b1, architecture 4d89c0b2 (the post-review revision:
build decisions only, preparation out of the epoch). Branch
`checkpoint/chargen-wizard`. All tickets complete; report at report.md.

The first implementation round (prep-era tickets, preserved in git history
through commit 729b7bf) was reviewed by Ben; findings 1–7 (findings.md)
revised the contract. This plan is the rework to the revised contract.

## R1 — Constraints emitted table applied  [x]

- [x] engine-core byte-identical (report diff listing; layering/purity rows guard) — verified: `git diff main...` over engine-core/types/persistence/routes/version.rs is empty
- [x] spellbook satisfiability, every school, no dead ends — `checks/replay.rs`
- [x] school change destroys nothing, re-judges — `checks/replay.rs`
- [x] class-feat slot hidden for Wizard; class-named skill sources — goldens (Sylvenne + Torvald)
- [x] spell-record lint: bounded heightening, stable IDs, license, cross-refs — `checks/rules_data.rs` + ruleset integrity
- [x] attestation covers spell + class-feature partitions, zero unwaived — `checks/attestation.rs`
- [x] layout sweep on every step visit + wordiest-content stress at 2 widths — `ui/e2e/layout.ts`, `layout.spec.ts`, helpers wiring
- [x] card-local confirm feedback — `ui/e2e/wizard-class.spec.ts` illegal-picks story
- [x] no shipped-record name as ruleset source literal — `checks/class_isolation.rs`
- [x] cross-class contamination sweep (complete character per class) — `checks/class_isolation.rs`
- [x] kind→control mapping total and exclusive — `ui/src/SlotCard.test.tsx`
- [x] storage untouched (schema v2, no new write paths) — `checks/persistence.rs` unchanged from slice 2
- [x] goldens per shipped school + re-judge fixture — `checks/replay.rs`
- [x] wizard projection < 5 ms — `checks/perf.rs`

## R2 — revert the detour  [x]
engine-core, types, persistence, routes, version.rs restored byte-identical
to the branch point; `scoped.rs` deleted; prep checks deleted.

## R3 — ruleset: unified spellbook  [x]
thesis slot; school slot with no dependents; cantrips Multi{10}; rank-1
Multi{5|7} with curriculum-first ordering, badge prefix, minimum validator,
Curriculum meter; `class_name` threaded through state.

## R4 — UI: set/bag controls, card feedback, responsive layout  [x]
grouped bag trays; `slot-error` card feedback incl. illegal-saved;
illegal slots editable preloaded; responsive stack ≤68rem.

## R5 — hands-on browser passes + fixes  [x]
Playwright-driven visual review (scratch scripts, screenshots read back):
found + fixed tablet column starvation, illegal-slot collapse, green ack
carrying an illegal save.

## R6 — tests green, feature map, report  [x]
cargo workspace 116 passed / clippy 0 / fmt clean; UI 36 unit, tsc, eslint
clean; e2e 26 passed (~36 s). `docs/feature-map.md` added. Report rewritten.
