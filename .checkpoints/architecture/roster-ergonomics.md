---
slug: roster-ergonomics
status: approved
---

# Chargen slice 4 — architecture

> Delta on the chargen-fighter/-content/-wizard architectures: every
> boundary, failure mode, and constraint there remains in force. This
> slice adds two roster features (random mint, clone) whose design is
> almost entirely forced by existing disciplines; the doc records how,
> and the two places something genuinely new is sanctioned.

## Situations

- **Randomness is data, never a dependency.** The pure crates
  (engine-core, ruleset, types) ban `rand`, clock, and env transitively
  and always will. A random mint draws entropy in the server and hands
  it to the planner as an input; given the same entropy, the engine's
  picks are a pure deterministic function. Entropy-draw failure takes
  the same contract as every mint failure: a typed error, nothing
  written. What must never happen: an RNG, clock, or entropy source
  inside a pure crate; a random pick that cannot be reproduced in a
  test by fixing the seed.
- **Random picks ride the existing planner and the existing oracle.**
  The suggestion planner (`expand_suggestions`) already walks open
  required slots in registration order and appends through the normal
  validated path. A random mint is the same walk with a different
  suggestion source: one that samples candidate selections from the
  slot's legal options and validates whole selections through the
  engine's **existing** append/validation oracle — bounded
  rejection-resampling on refusal, never a new constraint-exposure API.
  The sanctioned engine-core delta is exactly the suggestion-source
  seam: the source becomes state-aware (the planner hands it the folded
  state / option catalog, a signature change to `expand_suggestions`),
  and the planner may retry a slot with a fresh sample instead of
  reporting it unresolved on the first refusal. What must never happen:
  a second planner; a random path that bypasses `append` validation;
  speculative constraint-introspection machinery.
- **Set-level constraints survive sampling.** Where a slot group
  carries a remaining minimum (the Wizard's curriculum floor), bounded
  resampling against the oracle must land a satisfying selection — the
  same satisfiability discipline the wizard slice asserted for pickers,
  now exercised by a seed sweep instead of one player. What must never
  happen: a seed that strands a satisfiable constraint or lands an
  illegal decision; for shipped data, a seed that leaves a required
  slot unfilled.
- **The sampler is a fuzzer with its safety on (decided 2026-08-30).**
  The pick source is a standalone component with two separable stages:
  candidate sampling and the legality filter. The mint feature composes
  both and drives the engine; tests may compose them differently — the
  existing engine random-walk property tests (`pf2e_random_walk`)
  adopt the sampler, filter off, as their operation source, and a
  future test surface may drive the same sampled decisions through the
  UI instead of the engine (a Playwright random walk — explicitly
  deferred, not built this slice). What must never happen: the legality
  filter fused into sampling so unfiltered sampling is unreachable, or
  the sampler coupled to the planner so no other driver can consume it.
- **Random is not quick build.** The published-suggestion path and the
  random path are two suggestion sources over one planner; repeated
  random mints of the same class genuinely vary. What must never
  happen: the random path pinning any slot to the published suggestion
  (beyond coincidence), or the quick-build button's behavior changing
  at all.
- **Clone is a copy that must prove itself.** Clone reads an atomic
  snapshot of the source (which side of a concurrent draft append it
  lands on is indifferent — it clones what it read), copies the
  decision log verbatim except the name decision (re-minted with clone
  provenance and the clone-time name), re-derives the sheet by replay
  under the source's rules-data pin — the pin must be loadable, else a
  clean refusal — and writes a new character file through the existing
  crash-safe path. A source whose stored sheet diverges from replay
  refuses to clone; so do trashed and quarantined sources. This is the
  first sanctioned path that writes a *finalized* file the wizard never
  walked — bounded by being creation-only: no path mutates an existing
  finalized file. What must never happen: a clone born
  verify-divergent; a clone sharing identity, file, or link with its
  source; corruption propagating from a tampered source.
- **New provenance is schema vocabulary.** Decision sources grow
  (random, clone) beside player/suggested, so the character schema
  version bumps (v2 → v3) under the established
  version-plus-migration discipline: every v1/v2 file loads unchanged,
  `verify` replays both vocabularies, no file is rewritten on load.
  What must never happen: a pre-slice file failing to load, or loading
  differently.
- **Name pools are app data, not rules content.** Own-authored pools
  live in their own directory outside `rules-data/` — which excludes
  them from attestation and reference-check by construction (those
  scan `rules-data/` only) — keyed by ancestry record ID with an
  ancestry-agnostic default pool, loaded server-side. Editing a pool is
  a data edit. A malformed pool file — the default pool included —
  fails the mint with a typed error naming the file; a missing or empty
  ancestry pool falls back to the default. What must never happen: name
  pools acquiring license machinery, or a pool failure crashing the
  server or writing a partial draft.
- **No partial writes, ever.** Any mint or clone failure — pool parse,
  entropy draw, planner error, refusal — writes nothing; the character
  either exists complete or not at all. Crash mid-write is the existing
  crash-safe story.
- **Idempotency is inherited, not reinvented.** Mint and clone both use
  the quick-build scheme: the character ID derives from a
  client-generated request ID under a per-route prefix (so IDs can
  never collide across routes), and a retry — even one carrying
  different parameters, e.g. an edited clone name — returns the
  already-created character and appends nothing: first write wins.
  What must never happen: a crash-retry pair yielding two characters,
  or a novel idempotency mechanism.

## Boundaries

Slice-1/2/3 diagrams unchanged. Additions:

```
ui (roster: Random button + class picker, Clone dialog, provenance badges)
 │  existing API boundary only
 ▼
server ─ new routes: random mint, clone
 │   ├─ entropy drawn here (server-only), passed down as data
 │   └─ name pools loaded here (own app-data dir, outside rules-data/)
 ▼
engine-core ─ the one delta: state-aware suggestion-source seam on
 │            expand_suggestions (+ bounded per-slot resampling);
 │            append, fold, replay, suggested_selection: unchanged
 ▼
ruleset-pf2e ─ unchanged (legality/satisfiability already lives in slot
               definitions and validators)
types ─ new DecisionSource variants + mint/clone API types (additive)
rules-data ─ untouched (no version bump)
```

Forbidden: `rand`/clock/env in pure crates (existing tooling); UI
reaching storage except through the API; name pools inside rules-data;
any write to an existing finalized file.

## Failure modes

- **kill -9 mid-mint or mid-clone:** the write is crash-safe and the
  route idempotent; on restart the retried request (same ID) returns
  the saved character or creates it — exactly one exists either way.
  The human sees the retry affordance, then one new roster entry. While
  a mint is pending, the UI disables the button; a deliberate fresh tap
  after completion is a legitimate second mint.
- **Malformed name pool file (default pool included):** the mint fails
  with a typed error naming the file; no draft is written; the server
  keeps serving. Missing or empty ancestry pool: silent fallback to the
  default pool.
- **Clone of a verify-divergent source:** refusal with a message
  pointing at `verify`; nothing is written.
- **Clone of a trashed or quarantined source (e.g. from a stale roster
  tab):** refusal (not-found / not-cloneable); the UI surfaces it;
  nothing is written.
- **Clone of a source whose pinned rules-data version cannot be
  loaded:** clean refusal naming the pin; nothing is written; the
  established quiet-re-pin still happens only on first *open*, never
  at clone time.
- **Mint request naming an unknown or no-longer-shipped class ID:**
  typed refusal; nothing written.
- **A seed that cannot complete a build (future data, not shipped):**
  after bounded resampling, the planner's existing behavior — legal
  prefix kept, unfilled slots reported unresolved and landing on the
  checklist; never a rollback, never an illegal decision.
- Everything else (quarantine, version guard, re-pin on old pins,
  trash-only deletes) is inherited unchanged.

## Performance budgets

| Budget | Value | Asserted where |
|---|---|---|
| Derivation fold of a complete level-1 log | < 5 ms (unchanged) | `checks/perf.rs` |
| Random mint, request to saved draft, over shipped data | < 250 ms | asserting benchmark in `checks/perf.rs`, driving the route in-process the way `checks/confirm_idempotency.rs` already does — no new bench rig |
| Default test suite wall time | < 20 s (unchanged; seed sweeps fit via bounded proptest case counts — the repo's existing mechanism — never a new tagging scheme) | CI timing gate |

Clone is a copy plus one replay of a level-1 log — covered by the fold
budget; reported, not separately asserted.

## Constraints emitted

All prior rows remain in force. New or amended rows:

| Rule | Enforced by | Config lives at |
|---|---|---|
| Random mint soundness: for every shipped class and a seed sweep, the mint fills every required slot, yields an empty checklist, finalizes, and replays verify-clean; no seed lands an illegal decision or strands a set-level constraint | property test through the real engine over shipped data (bounded case counts) | `checks/random_mint.rs` |
| Mint determinism: same entropy + same data ⇒ identical character (name included) | property test | `checks/random_mint.rs` |
| Mint variety: across a seed sweep per class, picks are not constant on any slot with >1 legal option (guards accidental pinning to the published suggestion) | statistical assertion in the seed sweep | `checks/random_mint.rs` |
| Randomness, clock, and env stay out of pure crates | existing source scan + transitive dependency ban (unchanged; listed because this slice is the first to lean on the rand half) | `checks/crate_layering.rs` |
| Quick build unchanged: published-suggestion expansion and its goldens byte-identical to slice 3 | existing rows, no config change (listed so review checks nothing crept in) | `checks/quick_build.rs`, `checks/replay.rs` |
| Clone fidelity: for draft, finalized, and old-pin fixtures, the clone differs from its source exactly in character ID, file identity, and the name decision (clone provenance, clone-time name) — and replays verify-clean; divergent, trashed, and quarantined sources refuse with nothing written | fixture test through server persistence + engine replay | `checks/clone.rs` |
| Creation-only finalized writes: no code path opens an existing finalized file for write (clone creates, never mutates) | extend the no-rewrite-on-load / persistence sweep to the new routes | `checks/no_rewrite_on_load.rs`, `checks/persistence.rs` |
| Mint & clone idempotency: crash-retry with the same request ID yields exactly one character; a retried clone's differing name is ignored; per-route ID prefixes never collide | extend the confirm-idempotency harness to both routes | `checks/confirm_idempotency.rs` |
| Schema v3 migration: v1/v2 fixture files load byte-identically (no rewrite), `verify` passes over old and new provenance vocabularies | persistence fixtures | `checks/persistence.rs` |
| Name pools: live outside `rules-data/`; parse; ≥ 12 names per shipped ancestry; no empty strings | data lint over the pool files | `checks/rules_data.rs` (names section) |
| Pool failure modes: malformed pool (default included) ⇒ typed error, nothing written, server continues; absent/empty ancestry pool ⇒ mint succeeds with a default-pool name | fixture tests beside the mint property tests | `checks/random_mint.rs` |
| Roster stories walk: random mint (variety visible), typed-name preserved, clone dialog, provenance badges at review — under the generic layout sweep | Playwright specs | `ui/e2e/roster.spec.ts` |
| Crash-safety of the two new write paths | crash harness rows extended to mint and clone | `checks/crash_harness.rs` |
| Sampler reuse is real, not aspirational: the engine random-walk property tests consume the sampler with the legality filter off | `pf2e_random_walk` rewired to the sampler | `checks/replay.rs` |

Deliberately unenforced, with reasons: **sampler/filter separability
and driver-pluggability** are structural — the row above (fuzz walks
consuming the unfiltered sampler) is the living proof, and the
UI-driver seam stays unexercised until its slice arrives.
**single-planner / no-append-
bypass / no-novel-idempotency-mechanism** are structural sameness
claims — their observable consequences are enforced above (verify-clean
soundness, one-character idempotency), and the structural halves are
review-checked in the implement report, per the chargen-content
precedent for "never a client-side planner". Name *flavor* (pools
fitting their ancestry) is human-reviewed data. "Mint feels fast and
pleasant" is review-judged beyond the asserted latency row. Sampler
uniformity is not statistically asserted beyond the variety row (bias
that keeps all outcomes reachable is acceptable this slice).

## Review record

| Role | Verdict | Folded in |
|---|---|---|
| constraint-auditor | advice | quick-build-unchanged row; fallback-pool fixture; trashed/quarantined-clone refusals into the fidelity row; old-pin fixture; rand-row wording widened to clock/env; structural clauses parked in deliberately-unenforced with the content-slice precedent |
| failure-mode-reviewer | advice | default-pool failure path; quarantined-source clone; pin-unloadable clone refusal; entropy-draw failure contract; per-route ID prefixes + first-write-wins on parameter mismatch; no-partial-write generalized to all failures; atomic-snapshot clone vs a moving log; unknown-class refusal; pending-mint double-tap wording |
| simplicity-warden | advice | sampling mechanism named (rejection-resampling through the existing oracle, signature change sanctioned, no constraint-exposure API); "slow tag" replaced with bounded case counts; malformed-pool row moved to `checks/random_mint.rs`; attestation-exclusion-by-construction wording; perf row reuses the in-process route harness |
| Ben (dialogue, 2026-08-30) | fold | fuzz seam reserved: sampler standalone with separable legality filter and pluggable driver; engine fuzz walks adopt it now; UI-driven random walk named as deferred future test surface |
