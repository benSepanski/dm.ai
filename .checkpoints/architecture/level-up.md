---
slug: level-up
status: approved
---

# Chargen slice 5 — architecture

> Delta on the chargen-fighter/-content/-wizard/roster-ergonomics
> architectures: every boundary, failure mode, and constraint there
> remains in force. This slice makes level a fact derived from the log,
> gives the character file a pending-level tail, and proves the one
> dialog machine. Design calls were made by the agent against the spec's
> requirements and risks (Ben asked for best calls first, review after —
> 2026-09-01); each call names what forced it.

## Situations

- **Level is derived, never stored.** Today the ruleset derives at a
  compile-time level constant. What must hold (spec req 5: replay
  reproduces the leveled sheet from the log alone): advancing to a level
  is itself a decision in the log — a level-advance slot per level,
  whose presence unlocks that level's slots and whose count the fold
  reads as the character's level. Every level-dependent number
  (proficiency bonus, HP, spell slots, cantrip rank) derives from that.
  Advance decisions enter the log only through the start-level route:
  the engine refuses an advance while another advance is pending, and a
  raw confirm naming an advance slot is rejected. What must never
  happen: a level field in storage or state the fold does not compute;
  a level constant in derivation; two advances in one pending tail.
- **A level's slots are distinct slots.** Level-2's class feat is its
  own registration, unlocked by the level-2 advance, offering feats of
  level ≤ 2 whose prerequisites the *leveled* state meets (spec req 6);
  the fold accumulates per level (a list of class feats, not one). The
  Wizard's spellbook growth is likewise one `level-N spellbook` slot
  (two picks, mixed-rank options grouped by rank in the existing
  option-group vocabulary) — never a grown count on the level-1 picker,
  which would amend a finalized decision, and never two cards to
  reconcile. What must never happen: a slot re-used across levels, or a
  prerequisite judged against the level-1 state.
- **The pending level is the log's un-finalized tail** (chosen over a
  sidecar file or a temporary clone: spec req 2 demands finalize and
  abandon each be one atomic transition, and req 8 demands clone carry a
  pending level — trivial with one file, hard with two). The document
  records `finalized_through`: how many decisions of the log the stored
  sheet reflects. On a creation draft it is 0; creation finalize sets it
  to the log length; on read it is optional and fixed up to those values
  for pre-slice files. Decisions past it are the pending tail, whose
  first decision is always a level-advance. A "leveling" character is a
  finalized character whose log is longer than its marker — no third
  document state. **Finalize-pending** = re-derive from the full log,
  advance the marker, write once (on a finalized document with no tail
  it is an idempotent no-op returning current state — the
  crash-between-save-and-ack retry lands here). **Abandon** = truncate
  to the marker, write once, returning the discarded decisions in the
  existing clear-preview shape so the existing confirm dialog renders
  the list. Draft versions are monotonic across both transitions —
  never reset by abandon, so a tab stale from a first attempt can never
  land in a second. What must hold: `stored sheet == fold(finalized
  prefix)` always, and the full log folds cleanly — that pair IS the
  verify contract for leveled characters. One accessor yields the
  finalized prefix, and it is the only thing `verify`, version status,
  version accept, and clone ever fold. What must never happen: the
  stored sheet reflecting pending decisions; a write that moves the
  marker without re-deriving or re-derives without moving it; any
  write that alters a decision below the marker (raw confirm, amend,
  clear — cascades are bounded by the marker; the server refuses,
  `verify` is the backstop, not the guard).
- **The future's undo is a replay prefix** (Ben, 2026-09-01: eventual
  "view prior levels / jump back", not this epoch). With level
  boundaries as log decisions, "the sheet as of level N" is the fold up
  to the level-N boundary — history costs no new storage, and jump-back
  would be a marker move plus a re-derive, the transition abandon
  already performs. Reserved, not built: no history UI, no as-of API.
  What must never happen: a representation that would give prior-level
  sheets their own storage.
- **One dialog machine, proven by construction.** The projection is the
  wizard's only input; steps now carry a *liveness* predicate over the
  folded state (the step-level twin of a slot's unlock), and the
  projection emits only live steps: the seven creation steps while
  creating, the pending level's steps (a gains step, then its choice
  slots) while leveling. A dead step's slots are appendable but never
  rendered — which is exactly what lets the next level's advance slot be
  open to the start route without appearing as a card on a finished
  character. Step counts, resume labels, and the step cursor all index
  live steps. Resume, per-confirm durability, versions, cascades, the
  checklist: inherited, because leveling *is* wizard writes on the same
  log. The roster and character views gain a leveling state (old sheet
  beside a resume); the app-level router — which already branches on
  draft / flagged / finalized — routes it to the unchanged wizard. What
  must never happen: a phase or level branch inside the wizard
  component, a level-specific component, or the UI computing which
  slots belong to a level (the litmus test stands: a TUI needs zero
  Rust changes).
- **Gains are a derived diff, not authored text.** The gains step (spec
  req 4) is the existing `SheetDiff` vocabulary (the version-accept
  flow's before/after) between the finalized sheet and the fold through
  the advance decision alone — the fixed features the level grants land
  on the derived sheet, so the diff carries them (no separate clause,
  no double count). The finalize step's deltas are the same diff against
  the whole tail. Both ride as an additive field on the draft view,
  computed server-side per view. What must never happen: gains text
  hand-authored per level, or a number in the panel absent from the
  derived sheet.
- **Advancement is data, minimally.** Class records gain an advancement
  block listing, per level, the fixed features granted — as record IDs,
  cross-referenced, so a feature name hardcoded in a kind module fails
  the existing class-isolation scan. Which slot kinds a level grants is
  the same for both shipped classes (spec req 3) and stays a ruleset
  registration, not per-class config, until a class differs. The
  shipped cap is data too: the highest level a class's advancement block
  defines; the data lint requires every shipped class to define every
  level through the shipped cap. Level-2/3 feats and rank-2 spells are
  records through the existing pipeline, shipped as a new rules-data
  version. What must never happen: a level's grants hardcoded in a kind
  module; a per-class "granted slot kinds" table nobody needs.
- **Leveling under the version guard.** Leveling is a wizard write:
  start-level, confirms into the tail, finalize-pending are refused with
  the flag on a character whose pin is not current. A pending tail can
  resume only once the pin is current again (quiet re-pin or accept);
  re-pin, accept, and keep-old remain sanctioned writes that move the
  pin (and, on accept, the sheet — as the fold of the *prefix*) but
  never the marker or the log, re-judging the tail like any log.
  Keep-old with a pending tail leaves view and abandon only; a
  character kept on a pre-slice pin has no level-up (typed refusal
  naming the pin). Abandon is always permitted on a flagged character —
  the exit from a tail whose replay errors — and afterwards the guard
  re-judges the prefix alone. What must never happen: mixed-pin logs;
  a stuck "leveling up" with no exit.
- **Old characters are level 1 by construction.** A pre-slice log has
  no advance decisions, so it folds to level 1 exactly as before; its
  stored sheet matches; the marker is fixed up on read. Schema bumps
  v3 → v4 for the marker field (read old, never rewrite on load,
  upgrade on first write). What must never happen: a pre-slice sheet
  changing because level became derived.
- **Random leveling is test machinery.** The seed-sweep harness extends
  to leveled builds (mint → start → sample the level's slots → finalize
  → repeat to the cap) through the same sampler and planner — it is the
  spec's satisfiability proof (req 7) and its cross-level-prerequisite
  watch. No route, no UI.

## Boundaries

Prior diagrams unchanged. Additions:

```
ui ─ App router: leveling state → the unchanged <Wizard>; gains and
 │   deltas rendered by the existing SheetDiff list (version-flag view)
 ▼
server ─ new routes: start-level (idempotent; refuses drafts, the cap,
 │       non-current pins, kept-old), abandon (truncate to marker,
 │       returns a clear-preview); finalize reuses the finalize route
 │       ("finalize what is pending"); every wizard write refuses
 │       anything below the marker; roster/character views gain the
 │       leveling state; one finalized-prefix accessor on the loaded doc
 ▼
engine-core ─ step liveness predicate; per-level slot registrations;
 │            fold/append/replay/clear unchanged in kind (clear and
 │            cascades bounded by a caller-supplied floor)
 ▼
ruleset-pf2e ─ level-advance slots; per-level feat / skill-increase /
 │             spellbook-growth slots; level derived in the fold;
 │             advancement blocks read from class records
 ▼
types ─ additive: leveling roster/character view variants, gains and
        deltas on the draft view (SheetDiff reused); no marker, no
        level field (storage-private / derived)
rules-data ─ next version: advancement blocks (fixed-feature record
             IDs), level-2/3 feats, rank-2 spells; lineage, attestation
             partitions, cross-refs extend
```

Forbidden: level or phase logic in `ui`; a level constant in
derivation; "level" vocabulary in engine-core (it knows step liveness
and unlock-by-decision, never "class feat at 2"); any write to
finalized state beyond finalize-pending and abandon, other than the
pre-existing version-guard writes (pin and sheet only, never marker or
log); the marker or a level field on the wire.

## Failure modes

- **kill -9 mid-finalize or mid-abandon:** one temp-file → fsync →
  rename write; the file holds either the prior state (marker + tail
  intact) or the next — never a moved marker with a stale sheet. Ben
  sees the roster still saying "leveling up — resume", or the new
  level.
- **kill -9 mid-choice:** identical to creation — confirmed decisions
  are on disk; resume lands on the pending level's current step; every
  view shows the old level until finalize.
- **Second "Level up" (second tab, retry):** idempotent — returns the
  existing pending level, never a second advance (spec req 1). Start on
  a creation draft, on a kept-old or otherwise non-current pin, or at
  the cap: typed refusal, nothing written. Trashed or quarantined:
  not-found / not-writable, as everywhere.
- **Stale tab confirms into a finalized or abandoned tail:** the
  draft-version conflict machinery rejects it with current state; a
  retried tail confirm after the level finalized hits the
  "finalized, no tail" refusal *before* the decision-ID-present success
  path, so it can never answer "confirmed" against a finished document.
- **A raw write naming a decision below the marker** (amend, clear, a
  confirm whose cascade would cross it): refused at the server, typed;
  nothing written.
- **Fill-remaining or quick-build replay during a pending level:**
  suggested builds cover creation only this slice — typed refusal
  naming that, nothing written (the button's click surfaces the
  message; the shell is unchanged).
- **A pending tail that no longer folds** (rules-data correction under
  a re-pin, or hand-tampering): `verify` reports it per character; the
  version flag's resolve-replay-error path applies to the tail as it
  does to drafts; abandon always remains available as the exit.
- **Malformed marker or tail on read:** a marker past the log's end is
  schema-invalid → quarantine, like any structural corruption; a tail
  whose head is not an advance, or that holds two advances, loads (the
  finalized prefix is intact and authoritative) as a `verify` finding —
  the roster shows leveling, but resume and finalize refuse typed until
  the tail is abandoned.
- **Clone of a leveling character:** the clone copies log and marker;
  its sheet is the fold of the prefix under the source pin; the tail is
  folded for cleanliness only; the fidelity contract is unchanged (id,
  file, name decision) and a confirm into the clone's tail never
  touches the source.
- **Subset dead end** (no legal option for a slot at some build): the
  leveled seed sweep fails the build — it cannot ship; runtime never
  sees it.
- Everything else (quarantine, version guard, trash-only deletes,
  stale views) inherited unchanged.

## Performance budgets

| Budget | Value | Asserted where |
|---|---|---|
| Derivation fold of a complete **level-3** log (both classes) | < 5 ms (the level-1 budget, now over the longest logs the slice produces) | `checks/perf.rs` |
| Default test suite wall time | < 20 s (unchanged; the leveled seed sweep fits via bounded case counts) | CI timing gate |
| Warm incremental rebuild | < 10 s (unchanged) | timed CI step |

Design targets, hand-checked: the gains step renders with no
perceptible delay (two folds + a diff per view); projection payload
delta reported in the implement report.

## Constraints emitted

All prior rows remain in force, with one amendment: roster-ergonomics'
"creation-only finalized writes" row becomes the prefix-immutability row
below (this slice is the first to open a finalized file for write). New
or amended rows:

| Rule | Enforced by | Config lives at |
|---|---|---|
| Level is derived: the tokens `const LEVEL` / `LEVEL:` are absent from `crates/ruleset-pf2e/src`; the fold's level equals the count of advance decisions in the log (property over fixture and swept logs); `finalized_through` and any `level` field are absent from `crates/types/src` (wire≠storage banned-name list) | source token scans + property test | `checks/crate_layering.rs`, `checks/replay.rs` |
| Prefix invariant + verify: for every fixture and swept file, `stored sheet == fold(log[..finalized_through])` and the full log folds; every non-empty tail's head is an advance decision and holds exactly one; `verify` exits nonzero naming the character for a hand-edited pending decision, a moved marker with a stale sheet, and a malformed tail | persistence + replay tests; `verify` over negative fixtures | `checks/persistence.rs`, `checks/replay.rs` |
| Prefix immutability: across start-level, every pending confirm/clear/amend, clone, load, and every version-guard action, `log[..finalized_through]` and `sheet` bytes are unchanged; after abandon the file equals the pre-start file except the (monotonic) version counter and the v4 schema stamp; only finalize-pending moves marker and sheet, together | standalone test | `checks/persistence.rs` |
| Pre-slice logs fold to level 1 byte-identically: every slice 1–4 golden still matches under the level-derived fold | existing golden tests (untouched, must stay green) | `checks/replay.rs` |
| Atomic transitions: SIGKILL during start-level, confirms into a tail, finalize-pending, and abandon leaves a loadable file in exactly the prior or the next state | crash harness extension | `checks/crash_harness.rs` |
| Route authority for leveling: a second start returns the existing tail; start on a draft / at the cap / on a non-current or kept-old pin → typed refusal, nothing written; stale-version confirm/finalize/abandon conflict; a confirm after abandon or finalize is rejected (ID-present success never precedes the finalized-no-tail refusal); a raw confirm of an advance slot, a second advance in a tail, any amend/clear/cascade below the marker, and fill-remaining/quick-build replay during a tail are all refused, nothing written; draft versions never reused across abandon | standalone tests | `checks/api_authority.rs`, `checks/confirm_idempotency.rs` |
| Leveling under the version guard: start / tail confirms / finalize-pending on a flagged character → 409 with the flag, nothing written; a leveling file pinned to an older known version flags on load, byte-identical; re-pin / accept / keep-old / resolve-replay-error over a pending tail (identical, divergent, tail-replay-error fixtures) move only pin (and sheet = fold of prefix, on accept), never marker or log, and preserve the prefix invariant; abandon succeeds on a flagged character and the guard re-judges the prefix; start on a pre-slice pin refuses naming the pin | fixture tests via `--extra-known-versions` | `checks/version_guard.rs`, `checks/api_authority.rs`, `checks/no_rewrite_on_load.rs` |
| Old sheet authoritative: while a tail is pending, roster and character views carry the finalized sheet and the leveling state; the file's `sheet` bytes are identical across pending confirms | standalone test | `checks/persistence.rs` |
| Schema v4: v1–v3 fixtures (finalized AND a v3 mid-wizard draft) load untouched with the marker fixed up (log length / 0), resume at the same step, upgrade on first write; v5 refused | persistence fixtures | `checks/persistence.rs` |
| Clone of a leveling source: document-equality fidelity (id, file, name decision only), marker equal, clone sheet = fold of prefix, clone verify-clean, a confirm into the clone's tail leaves the source byte-identical | fixture test (extends the existing fidelity harness) | `checks/clone.rs` |
| Leveled seed sweep (test-only random leveling): for every shipped class and a seed sweep, a minted character levels to the cap with every level's slots fillable, an empty checklist at each finalize, and a verify-clean file; at least one seed takes the prerequisite-bearing level-2 feat — the satisfiability and cross-level-prerequisite rows in one | property test through the real engine and planner (bounded case counts) | `checks/random_mint.rs` (leveled section) |
| Gains are derived: the gains step's entries equal the `SheetDiff` between the finalized sheet and the fold through the advance decision; finalize deltas equal the diff against the full tail | property test over swept builds | `checks/replay.rs` |
| Golden coverage: hand-verified Fighter 3 (taking the prerequisite feat) and Wizard 3 (Torvald and Sylvenne leveled), plus one mid-level pending fixture | golden tests | `checks/replay.rs` |
| One dialog machine (structural half): no `LevelUp` identifier in any `ui/src` filename or export; `Wizard.tsx` contains no phase/level comparison token (`phase`, `level ===`, `isLeveling`); gains and deltas render through the existing SheetDiff list component, no new diff component | source scan over `ui/src` beside the existing source scans | `checks/crate_layering.rs` |
| Level-up stories walk: first level-up with gains and deltas, straight-to-cap with the note, wizard's new rank, crash resume, changed mind, illegal picks at the card, abandon via the existing clear dialog, pending-level clone — asserting the same step nav, checklist, slot cards, and confirm affordances by their existing test IDs, under the generic layout sweep | Playwright specs | `ui/e2e/level-up.spec.ts` |
| Advancement data: advancement blocks schema-valid with fixed features as cross-referenced record IDs; every shipped class defines every level through the shipped cap; level-2/3 feat and spell records license-tagged, attested, denylisted; lineage extended; a fixed feature's name as a source literal fails class isolation | data lint + attestation + existing class-isolation scan | `checks/rules_data.rs`, `checks/attestation.rs`, `checks/class_isolation.rs` |
| Level-3 fold < 5 ms | asserting benchmark | `checks/perf.rs` |

Deliberately unenforced, with reasons: **no "level" vocabulary in
engine-core** stays at the dependency-and-review level like every prior
vocabulary claim (engine-core knows step liveness and unlock-by-
decision — generic; whether a name leaks is review). **Only two
functions write finalized state** is structural (the prefix-immutability
row asserts the observable half; the structural half is the implement
report's route table). **Random leveling never reaches the product** is
review of that same route table plus the sampler living only under
`checks/`. **Gains readability** and **"leveling feels like the same
dialog"** are the spec's intent checks. The **undo/history seam** is a
property of the representation, demonstrated by the prefix-invariant
row, not by a history feature.

## Review record

| Role | Verdict | Folded in |
|---|---|---|
| constraint-auditor | block, resolved | version-guard row added (the block); prefix-immutability row replaces roster-ergonomics' creation-only row; UI scan re-homed to the source-scan check with named tokens and the SheetDiff-reuse clause; level-constant tokens and the storage-half (types banned names) named; cap/draft/kept-old refusals in the authority row; leveling clone fidelity case; negative verify fixtures + tail-head rule; v3 draft fixture; random-leveling-stays-in-tests parked in deliberately-unenforced; Fighter-3 golden takes the prerequisite feat; class-isolation scan cited for fixed features |
| failure-mode-reviewer | advice | monotonic versions across abandon (byte-identical claim narrowed); abandon permitted on flagged characters; tail resumes only under a current pin, keep-old leaves view+abandon, pre-slice pins cannot level; version-guard writes sanctioned as pin/sheet-only; clone sheet = fold of prefix; marker floor for amend/clear/cascade; advance only via the start route; malformed marker/tail behaviors; marker on drafts and creation finalize; start on a draft refused; cap is data with a lint; fill-remaining refused during a tail |
| simplicity-warden | advice | phase tag dropped for a step-liveness predicate (nothing on the wire); abandon returns the existing clear-preview shape so the existing dialog renders it; one finalized-prefix accessor named as the only thing verify/status/accept/clone fold; every wizard route's refusal becomes "finalized and no tail", refusal ordered before ID-present success; gains double-count clause removed, gains ride the draft view server-side; advancement blocks reduced to fixed features; spellbook growth as one mixed-rank slot; marker as optional-with-fixup; leveling view variants with the app router branch sanctioned; UI scan re-homed |
