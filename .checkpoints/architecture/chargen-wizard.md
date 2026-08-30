---
slug: chargen-wizard
status: approved
---

# Chargen slice 3 — architecture

> Delta on the chargen-fighter and chargen-content architectures: every
> boundary, failure mode, and constraint there remains in force. Revised
> 2026-08-30 with the spec: daily preparation left the epoch, so the
> scoped-choice engine machinery from the first implementation is
> reverted (its validated design is recorded for Epoch 8 in the vision
> and in this branch's history), storage is untouched, and the slice adds
> only what the Wizard's build decisions and spell data introduce.

## Situations

- **The engine must not change at all.** Every Wizard mechanism — the
  thesis and school slots, the unified per-rank spellbook pickers with
  the curriculum-minimum constraint, the hidden class-feat slot, the
  spellcasting block on the sheet — is expressible with the existing five
  operations: state-dependent Multi counts, validators over folded state,
  unlock conditions, meters, derivation. What must never happen:
  engine-core growing an operation, a field, or vocabulary for this
  slice; a "spell" appearing anywhere in core types.
- **One picker per rank; constraints live inside it.** The spellbook is
  one slot per rank. The rank-1 count is school-dependent (5, or 7 once a
  school is chosen) and the curriculum minimum is a validator + meter
  inside that slot, with curriculum options badged. What must never
  happen: a second card the player must reconcile against the first, or
  any reachable state whose requirement no combination of picks can
  satisfy (the constraint re-judges picks; it never greys options into a
  dead end).
- **Changing the school destroys nothing.** School is data the book
  validator reads: on a school change the existing picks stand and the
  curriculum meter re-judges them, flagging a shortfall as an ordinary
  checklist entry; the focus spell is derived and follows automatically.
  What must never happen: a school change clearing spellbook picks, or a
  cascade prompt listing losses this design no longer has.
- **Spells are the richest records, transcribed not designed.** The
  `spells` record kind carries the printed mechanical fields (action
  cost, traits, range/area/targets, duration, defense, heightening
  entries bounded to the two printed shapes). Data version bumps
  additively; the attestation pipeline covers spell records like any
  record. What must never happen: a heightening or effect DSL designed
  past what shipped records need; ground-truth bytes in the repo.
- **The wordiest content is a tested load, not a hope.** Spell texts are
  the longest prose the UI renders; layout integrity (no horizontal
  overflow, no hidden controls) and card-local feedback for every confirm
  outcome are enforced invariants — swept generically across every screen
  the story walks visit, not asserted on one curated page. What must
  never happen: feedback that renders only at the top of a long step, or
  a control pushed out of reach by content length.
- **A control's shape derives from the selection's semantics.** A
  selection is either a *set* (membership — picking twice is meaningless:
  rendered as toggles, duplicates unrepresentable) or a *bag* (each pick
  is an instance: rendered as an add/remove tray with grouped "×N" rows
  and always-visible removes). The presentation contract's slot kind
  declares which; the UI derives the control from the kind and never
  chooses by context. This slice ships only sets (spellbook, skills,
  boosts) and one open bag (the shopping list); the bounded-bag variant
  (count + repeats, engine-enforced distinctness on sets) is the sanctioned
  vocabulary extension for its first real consumer — Epoch 8's
  preparation slots — not built speculatively now.
- **Class identity never lives in shared code.** The Fighter's leak into
  the Wizard's skill labels came from a class name hardcoded in shared
  mechanics — a category the crate/module boundaries cannot catch. What
  must hold: anything class-specific is a data lookup on the chosen class
  record; class-conditional behavior keys on record fields, never names.
  What must never happen: a shipped record's display name as a source
  literal in ruleset code, or one class's vocabulary appearing in another
  class's projection or sheet.
- **Storage does not change.** No prep section, no schema bump — schema
  stays v2, and the no-rewrite-on-load / persistence rows run unchanged.
  What must never happen: any new write path to finalized files in this
  slice.

## Boundaries

Slice-1/2 diagrams unchanged. Additions are confined to two boxes:

- **`ruleset-pf2e`**: a `spells` kind module — spell/thesis/school record
  parsing and catalogs, the thesis and school slots, the two spellbook
  slots (cantrips Multi{10}; rank-1 Multi{5|7} with the curriculum-minimum
  validator and badged options) — plus a class-feat unlock that hides the
  slot for classes whose advancement table grants none, and the
  class-skill source label resolved from the chosen class record (never a
  literal class name). Kind isolation holds: school→curriculum references
  are record IDs resolved by data lint and folded state, never kind↔kind
  imports.
- **`rules-data`**: `spells.json` (spells, theses, schools), the Wizard
  class record with its printed spellcasting entry (slot and book counts
  as display/validation facts), the Wizard kit; manifest and
  shipped-versions bump additively. `reference-check` gains the spell and
  class-feature partitions.
- `types`, `engine-core`, `server`, `persistence`, `wasm` interfaces:
  **unchanged** (the wasm binary re-embeds the new data; bindings
  regenerate without shape changes). The UI renders the new slots through
  the existing SlotCard machinery; its two behavioral changes — wrapped/
  clamped tray content and card-local outcome feedback — are presentation.

## Failure modes

- **Curriculum shortfall after a school change or late picks:** an
  ordinary Illegal/Incomplete checklist entry on the rank-1 spellbook
  slot naming the school and the shortfall; finalize blocks; fixing picks
  clears it. Never a cleared slot, never a dead end.
- **A record with extreme text lengths:** wraps and clamps within its
  card; controls stay visible; the layout invariant check fails the build
  otherwise.
- **A confirm outcome on a card deep in a long step:** rendered at the
  card (rejection reasons, saved-partial state, conflicts); the top-level
  notice may repeat it but is never the only signal.
- **Rules-data corrections to spells** flow through the existing
  version-guard machinery exactly as any record correction (flag, resolve
  explicitly, never silent).
- Everything else — crash mid-confirm, stale tabs, quarantine, version
  guard, replay divergence — is inherited unchanged from slices 1–2.

## Performance budgets

| Budget | Value | Asserted where |
|---|---|---|
| Derivation fold of a complete level-1 log | < 5 ms (unchanged; now includes the spellcasting block over full spell data) | native benchmark in `checks/perf.rs` |
| Default test suite wall time | < 20 s (unchanged) | CI timing gate |
| Warm incremental rebuild | < 10 s (unchanged; slice-2 levers still pre-authorized) | timed CI step |

Design targets, hand-checked: picker feel at subset size; projection
payload delta reported in the implement report alongside suite/rebuild/
WASM-size deltas.

## Constraints emitted

All slice-1 and slice-2 rows remain in force. New or amended rows:

| Rule | Enforced by | Config lives at |
|---|---|---|
| engine-core is byte-identical to its pre-slice state (the experiment's zero) | review of the implement report's diff listing + the existing layering/purity rows over anything that would slip in | report; `checks/crate_layering.rs`, `clippy.toml` |
| Spellbook satisfiability: for every shipped school, a full legal spellbook exists and no pick order can dead-end the rank-1 requirement (the constraint re-judges; options are never greyed into unsatisfiability) | property test through the real engine over shipped data | `checks/replay.rs` |
| School change destroys nothing: on a fixture draft with a full book, amending the school leaves every spellbook decision byte-identical and re-judges the curriculum meter (shortfall = checklist entry, not a clear) | standalone test through the real engine | `checks/replay.rs` |
| Class-feat slot hidden for classes without a level-1 class feat; class-skill source labels name the chosen class | golden assertions (Sylvenne + Torvald) | `checks/replay.rs` |
| Spell records: schema-valid with the bounded heightening shape (per-rank-step delta or fixed-rank override only); IDs stable; license metadata present; curriculum and focus-spell cross-references resolve | data lint (extends existing rules) | `checks/rules_data.rs` + ruleset integrity |
| Attestation covers the spell and class-feature partitions: every record attested, hash-current, zero unwaived mismatches | offline attestation check (slice-2 machinery, wider) | `checks/attestation.rs` |
| Layout sweep, everywhere: a shared `expectSaneLayout` helper asserts (a) the document has no horizontal scroll, (b) no element with visible overflow-x has `scrollWidth > clientWidth`, (c) every enabled control lies inside its clipping ancestor's box — called on every step visit in the shared e2e helpers (so all story walks sweep every screen they reach) plus a dedicated stress spec: longest shipped descriptions expanded, at desktop AND narrow (tablet) viewports | Playwright helper wired into `ui/e2e/helpers.ts` + stress spec | `ui/e2e/layout.ts`, `ui/e2e/layout.spec.ts` |
| Card-local feedback: a refused or partial confirm renders its outcome inside the card (asserted in the illegal-picks walk) | Playwright story assertion | `ui/e2e/wizard-class.spec.ts` |
| No shipped-record display name as a source literal: every record name in the shipped data is scanned against `ruleset-pf2e` source (tests and data excluded); a match fails the build — class-specific anything must be a data lookup | source lint over shipped data × ruleset source | `checks/class_isolation.rs` |
| Cross-class contamination: for every shipped class, a complete character built through the real engine yields a projection + sheet that never mentions another class's name or class-scoped record IDs (sole sanctioned exception: the class-picker catalog); pairwise, automatic for every future class | sweep test through the real engine | `checks/class_isolation.rs` |
| Kind→control mapping is total and exclusive: set-kinds (single/multi) never render an add control; bag-kinds (list) always render grouped tray rows with visible removes | UI unit test over the slot editor | `ui/src/SlotCard.test.tsx` |
| Storage untouched: schema version and persistence fixtures unchanged from slice 2; no new write paths | existing persistence/no-rewrite rows (no config change; listed so review checks nothing crept in) | `checks/persistence.rs`, `checks/no_rewrite_on_load.rs` |
| Golden coverage: one hand-verified Wizard per shipped school; the school-change re-judge fixture | golden tests | `checks/replay.rs` |
| Wizard projection < 5 ms over full spell data | asserting benchmark | `checks/perf.rs` |

Deliberately unenforced, with reasons: "engine-core byte-identical" is
review-plus-report rather than a hash check (a hash row would fight every
future slice; the layering/purity rows bound what any change could be).
"The sheet's preparation note reads plainly" and picker feel are
review-judged. The WASM copy's agreement with the native engine remains
structural (same commit, bindings-freshness gate), as in slice 1.

## Review record

| Role | Verdict | Folded in |
|---|---|---|
| constraint-auditor | block, resolved | (original round) cascade-atomicity + parity rows — superseded: prep and its cascade left the slice; satisfiability and destroy-nothing rows replace them |
| failure-mode-reviewer | block, resolved | (original round) finalized-writer race + flagged-prep rules — superseded: no prep, no new finalized write path; wordy-content and shortfall failure modes added |
| simplicity-warden | advice | (original round) engine accounting honesty — the revision resolves it maximally: engine-core diff is zero |
| Ben (implementation review, 2026-08-30) | revision | findings 1–7 folded: preparation out of the epoch; unified per-rank picker with in-picker constraint; layout + card-feedback invariants promoted to enforced rows |
