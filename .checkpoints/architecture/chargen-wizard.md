---
slug: chargen-wizard
status: approved
---

# Chargen slice 3 — architecture

> Delta on the chargen-fighter and chargen-content architectures: every
> boundary, failure mode, and constraint there remains in force. This doc
> adds only what spellcasting, the play-scoped preparation section, and the
> first write path to finalized files introduce. The prep-engine decision
> (engine-core gains one scoped-choice operation) was made with Ben in
> dialogue (2026-08-29).

## Situations

- **Choices now live in two scopes; the engine owns both with one driver.**
  Preparation is a choice set bound to ruleset-defined prep slots, validated
  against the folded build sheet, replaceable wholesale. engine-core gains
  exactly one game-word-free operation: validate a **scoped choice set**
  (slot definitions + choices + folded base → checklist entries). PF2e
  defines the prep slots (per-rank counts, in-book option source, the
  curriculum restriction); Epoch 8's daily prep and the 5.5e slice call the
  same operation. What must never happen: a second, ruleset-private
  validation driver; prep entries in the decision log or replay; engine-core
  learning "spell", "spellbook", or "preparation" vocabulary — the operation
  sees slots, choices, and a base state.
- **The stored sheet stays a pure function of the log.** Sheet =
  fold(decision log, data version), byte-for-byte as before — the
  spellcasting block the fold adds (spell attack/DC, slots by rank, focus
  pool, cantrip rank) derives from build decisions only. Prepared spells are
  presentation: the projection layer (engine, both runtimes) combines the
  materialized sheet with the prep section into the view. What must never
  happen: prep contaminating the stored sheet or replay; the UI computing
  legality, slot counts, or heightened ranks.
- **Build decisions cast shadows into the prep scope.** Changing an
  upstream build choice (arcane school) invalidates dependent scoped
  choices (curriculum-slot prep, the school's focus spell). The existing
  dependent-clearing machinery extends across the scope boundary: the
  confirmation lists prep entries that will clear alongside log decisions,
  and the clear happens in the same durable write. What must never happen:
  a school change leaving stale curriculum prep behind, or clearing prep
  without listing it first.
- **Finalized files now have two writers; writes are serialized per file.**
  Slice 2's version actions (re-pin, accept-divergence, keep-old) were the
  first finalized-file writers; the prep save is the second, and they are
  independent surfaces. All finalized-file mutations for one character go
  through a per-character serialized write path: read-modify-write happens
  under the serialization, so the later write always operates on the
  earlier's result — a prep save that raced a version action is validated
  against the post-action state, and a version action never resurrects
  pre-prep-save content. What must never happen: two interleaved
  read-modify-writes where the loser's effect silently vanishes. The prep route may touch only the prep section: decision
  log and materialized sheet remain byte-identical across any prep save,
  crash included. The route carries the full confirm discipline — request
  idempotency ID, prep-section version, stale-view rejection, temp-file →
  fsync → rename. The one sanctioned exception: a v2 file's first prep
  save also bumps the schema-version envelope (the ordinary upgrade-on-
  write), with log and sheet bytes still identical. What must never
  happen: a prep save that rewrites, reorders, or re-serializes the log or
  sheet; a stale tab silently clobbering a preparation.
- **Spells are the richest records yet, transcribed not designed.** A new
  `spells` record kind carries the mechanical fields the printed rules
  state discretely (action cost, components/traits, range/area/targets,
  duration, defense, heightening entries). The heightening schema admits
  exactly the printed entry shapes — per-rank-step deltas and fixed-rank
  overrides — nothing more. Data version bumps (0.2.0 → 0.3.0, additive);
  the attestation pipeline covers spell records like any record. What must
  never happen: a heightening or effect DSL designed past what shipped
  records need; ground-truth bytes in the repo.
- **The experiment stays falsifiable.** The Wizard lands as ruleset kind
  modules (class features, spells) plus records; the engine-core diff is
  exactly two amendments — the scoped-choice operation and the widened
  projection input — listed and justified in the implement report. A
  bigger engine-core need is the sanctioned re-open of this doc, never a
  quiet extra operation.

## Boundaries

Slice-1/2 diagrams unchanged. Additions:

```
  character file (schema v3)
  ┌───────────────────────────────┐      engine-core (+1 operation)
  │ sheet  = fold(log)  ◀─replay──┼──┐   ┌─────────────────────────────┐
  │ log    (append-only)          │  ├──▶│ fold / validate / slots ... │
  │ prep   (replaceable section;  │  │   │ validate_scoped(slots,      │
  │         absent = valid)       │◀─┼───│   choices, folded base)     │
  └───────────────────────────────┘  │   └─────────────▲───────────────┘
        ▲ prep-save route            │                 │ prep-slot defs,
        │ (only writer of prep;      │                 │ spell catalogs
        │  log/sheet byte-identical) │   ┌─────────────┴───────────────┐
  ┌─────┴─────┐                      └───│ ruleset-pf2e                │
  │ server    │  projection = view(      │  + spells kind module       │
  │ (axum)    │   sheet, prep) — engine, │  + wizard class kind        │
  └───────────┘   native & WASM          │  (kinds → mechanics → core) │
                                         └─────────────────────────────┘
```

- **engine-core**: two listed diffs, and only these. (1) One new operation,
  `validate_scoped` in spirit (name is implement's): slot definitions + a
  choice set + a folded base state → checklist entries. Base-decision
  changes reporting and clearing dependent scoped choices is the *existing*
  slot-graph/dependent-clearing machinery reaching across the scope
  boundary — an extended reach of one mechanism, never a second dependency
  tracker. (2) The existing projection operation's inputs widen to accept
  an optional scoped-choice section, so the view combines sheet + prep in
  engine code on both runtimes. No new crates, no new dependencies, no
  game vocabulary.
- **ruleset-pf2e**: a `spells` kind module (record parsing, catalogs,
  option sources) and the Wizard's class kind (thesis, school, bond, class
  feat, spellbook and prep slot definitions). Kind isolation holds:
  school→curriculum and spellbook→prep references are record IDs resolved
  by data lint and engine queries, never kind↔kind imports.
- **types**: the prep-section shape, the scoped-choice request/response
  shapes, and the spellcasting presentation block (book vs prepared
  distinguished, cantrip rank precomputed) — render-ready, so the UI stays
  arithmetic-free and the TUI litmus test stands.
- **server**: the prep step inside the draft flow writes the draft's prep
  section through the ordinary confirm route machinery; one new route
  edits a finalized character's prep. Both are the only writers of the
  prep section; no route writes a finalized log or sheet.
- **persistence**: schema v3 adds the optional prep section. v2 (and
  read-accepted v1) files load unchanged, never rewritten on load, upgrade
  on their next ordinary write; v4 refused in place. Absence of the
  section is the valid state for non-preparing classes and all pre-slice
  files.
- **verify**: replay covers the log exactly as before; a new pass
  re-validates the prep section through the same scoped operation,
  reporting illegal or unresolvable prep the way sheet divergence is
  reported. Prep on a class with no prep slots is reported, not repaired.
- **reference-check**: the pinned ground truth grows the spell partition;
  attestation semantics unchanged.

## Failure modes

- **Crash mid-prep-save** (draft step or finalized edit): atomic-rename
  discipline — prior prep intact; a retried request ID returns the saved
  result and changes nothing; the crash harness gains three cycles: draft
  prep confirm, finalized prep edit, and the school-change cascade write.
- **Prep save racing a version action on the same finalized file**: the
  per-character write serialization orders them; the prep save is
  validated against the post-action state (or vice versa), both effects
  land, and neither writer's result silently vanishes.
- **Stale prep save** (second tab, either flow): rejected with the current
  prep state attached; the UI reloads the picker — never silently merged.
- **Hand-edited prep** — illegal picks, unknown spell IDs, prep on a
  Fighter: file loads, sheet renders, `verify` names each violation and the
  prep picker shows the same checklist entries; nothing is auto-repaired.
- **Rules-data correction invalidates stored prep** (a `wizard-content`
  fix): surfaces exactly like hand-edited prep after the re-pin — the
  version-guard flow is untouched, prep legality is recomputed against the
  current data after resolution, never persisted as a verdict.
- **Prep operations on a flagged or older-pinned character**: rejected
  until the version flag is resolved — the slice-2 "wizard writes on a
  flagged draft rejected" rule extended to the prep routes. Only current
  catalogs ship, so legality against an old pin is not computable: `verify`
  reports that character's prep as not evaluable under a non-current pin
  rather than validating it against the wrong catalogs, and the sheet view
  shows the flag, not a legality verdict.
- **Structurally unparseable prep section** (hand-mangled JSON in an
  otherwise valid file): the prep section parses independently of the
  file's log and sheet. The character loads, the prep is reported broken —
  in `verify` and in the picker, which offers wholesale replacement — and
  whole-file quarantine stays reserved for files whose log or sheet cannot
  be read. Consistent with "absent = valid": a broken replaceable section
  never takes the character down with it.
- **School changed with dependent prep** (draft flow): the confirmation
  lists the curriculum-slot prep and focus-spell entries that will clear;
  decline leaves everything; accept clears log dependents and prep
  dependents in one durable write. A crash between confirm and write loses
  the whole change, never half of it.
- **Raw illegal prep request** (bypassing the UI): server re-validates
  natively via the same operation and rejects; the file is untouched —
  the slice-1 authority pattern extended to the new route.
- **Prep route against a draft mid-wizard vs finalized character**: each
  route accepts only its own lifecycle state; a finalized-prep edit against
  a draft (or vice versa) is rejected, not coerced.
- **Projection bigger than the wire expects** (spell text in catalogs):
  same posture as slice 2 — payload growth measured and reported, filtering
  stays UI-side over render-ready options, no new engine queries.

## Performance budgets

| Budget | Value | Asserted where |
|---|---|---|
| Derivation fold of a complete level-1 log | < 5 ms (unchanged; now includes the spellcasting block) | native benchmark in `checks/perf.rs` |
| Scoped prep validation (full wizard prep) | rides the same benchmark, asserted within the fold budget's headroom — no separate ceiling unless it grows one | `checks/perf.rs` |
| Default test suite wall time | < 20 s (unchanged) | CI timing gate |
| Warm incremental rebuild | < 10 s (unchanged; slice-2 levers and their order still pre-authorized) | timed CI step |

Design targets, hand-checked: prep picker feels instant (in-memory options,
WASM preview validation); projection payload delta reported in the implement
report alongside suite/rebuild/WASM-size deltas.

## Constraints emitted

All slice-1 and slice-2 rows remain in force. New or amended rows:

| Rule | Enforced by | Config lives at |
|---|---|---|
| Prep never touches replay: for fixture characters with identical logs and different (or absent) prep sections, fold output and stored sheets are byte-identical; replay determinism ignores prep | property + golden tests | `checks/replay.rs` |
| Prep-save writes only prep: across any prep save (draft step or finalized edit), the file's decision log and materialized sheet are byte-identical before and after — including a v2 file's first prep save, where only the schema envelope may additionally change (fixture covers it) | standalone test | `checks/prep.rs` |
| Prep-save idempotency + concurrency: a replayed request ID changes nothing and returns the saved result; a save carrying a stale prep version is rejected with current state | standalone test reusing the slice-1 idempotency test helpers — one pattern, new surface | `checks/prep.rs` |
| Crash safety: SIGKILL during draft-prep confirms and finalized-prep edits leaves every file loadable, prior prep intact or new prep complete — never torn | crash harness extension | `checks/crash_harness.rs` |
| Cascade atomicity: SIGKILL between a school-change confirm and its durable write leaves either the full change (log dependents and prep dependents cleared together) or none — never a cleared log with surviving curriculum prep | crash harness extension (third prep cycle) | `checks/crash_harness.rs` |
| Finalized-file writers don't race: a prep save concurrent with a version action (re-pin / accept-divergence / keep-old) on the same character leaves both effects in the final file, in some serial order — neither write lost | standalone concurrency test | `checks/prep.rs` |
| Prep routes respect the version guard: a prep save on a flagged or older-pinned character is rejected until resolution | standalone test (extends the slice-2 version-guard rows) | `checks/version_guard.rs` |
| One validation driver, observable: a single illegal-prep fixture yields identical checklist entries from the native prep route, the `verify` pass, and the WASM preview — a private second driver diverges visibly | parity test | `checks/prep.rs` |
| Broken prep degrades, never quarantines: a fixture file with unparseable prep but valid log/sheet loads with prep reported broken; whole-file quarantine fires only when log or sheet is unreadable | persistence contract test extension | `checks/persistence.rs` |
| Server authority over prep: raw requests with not-in-book, overfilled-rank, non-curriculum-in-school-slot, wrong-lifecycle, or no-prep-class payloads are rejected natively and append/change nothing | standalone test | `checks/api_authority.rs` |
| `verify` re-validates prep: fixtures with illegal picks, unknown spell IDs, and prep-on-a-Fighter each produce a named report; absent prep section is silent; a legal revised prep is clean | standalone test | `checks/prep.rs` |
| Scoped dependents clear atomically and completely: changing a school on a fixture draft clears exactly the listed curriculum-slot prep and focus-spell entries — no stale curriculum prep survives, nothing unlisted clears | standalone test through the real engine | `checks/prep.rs` |
| Storage schema v3: v2 fixture reads, is not rewritten on load, upgrades on first ordinary write (incl. a finalized v2 file whose first write is a prep save); v4 refused in place; prep-section absence valid at every layer | persistence contract test (extends existing rows) | `checks/persistence.rs` |
| Spell records: schema-valid including the bounded heightening shape (per-rank-step delta or fixed-rank override, no other variants); IDs stable; license metadata present; school curriculum / focus-spell / spellbook-eligibility cross-references resolve to shipped spell records | data lint (extends existing rules) | `checks/rules_data.rs` |
| Attestation covers the spell partition: every spell record attested, hash-current, zero unwaived mismatches — the slice-2 machinery, wider | offline attestation check (unchanged code, more records) | `checks/attestation.rs` |
| Engine purity applies to the new operation: no I/O, clock, randomness, env in the scoped-validation path | existing clippy bans + layering test (no config change; listed so review checks the new code falls under them) | `clippy.toml`, `checks/crate_layering.rs` |
| Kind isolation: the `spells` kind module and the Wizard class kind have no kind↔kind imports | existing module-graph scan (crate layout extends) | `checks/crate_layering.rs` |
| Golden coverage: one hand-verified Wizard (sheet + initial prep) per shipped school; the changed-school cascade fixture; a revised-prep fixture | golden tests | `checks/replay.rs` |

Deliberately unenforced, with reasons: "engine-core gained exactly one
operation" is not mechanically checkable — the implement report's engine-core
diff listing plus review own it (the layering, purity, and vocabulary rules
still bound what any addition can be). "The heightening schema captures only
printed shapes" is enforced as schema strictness; whether a field was
*invented* is a transcription judgment left to the reference pipeline and
review. "The prep picker reuses the shared slot components" is UI structure,
review-judged like slice 2's filter placement. "Prep legality is never
persisted as a verdict" is structural — there is no field to store it in —
and the no-rewrite-on-load check already catches any load-path write. "The
prep routes are the only writers of the prep section" is likewise
structural (route layout), with the dangerous inverse direction — anything
else writing prep, or prep writing anything else — covered by the
byte-identity and no-rewrite-on-load rows. "No second validation driver"
is enforced observably via the parity row rather than by code inspection.

## Review record

| Role | Verdict | Folded in |
|---|---|---|
| constraint-auditor | block, resolved | cascade-atomicity crash row (third harness cycle); one-driver parity row (native route / verify / WASM preview agree on an illegal-prep fixture); only-writers-of-prep moved to deliberately-unenforced with the structural reason |
| failure-mode-reviewer | block, resolved | per-character serialization of finalized-file writes (prep save vs version actions — no lost update) + concurrency row; prep routes rejected on flagged/older-pinned characters, verify says not-evaluable under a non-current pin; v2-first-prep-save schema-envelope carve-out + fixture; unparseable prep degrades instead of quarantining the file |
| simplicity-warden | advice | dependency clearing reworded as the existing machinery's extended reach (never a second tracker); projection-input widening named as the second listed engine-core diff; prep idempotency test reuses slice-1 helpers |
