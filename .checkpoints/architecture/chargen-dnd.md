---
slug: chargen-dnd
status: approved
---

# Chargen slice 6 — architecture

> Delta on the chargen-fighter through level-up architectures: every
> boundary, failure mode, and constraint there remains in force. This
> slice turns "the ruleset" into "a ruleset", gives the campaign a game,
> and stands a second ruleset crate beside the first. Design calls were
> made by the agent against the spec (best calls first, review after —
> Ben's standing preference); each call names what forced it. Review
> removed a registry crate from the first draft (see Review record).

## Situations

- **A campaign plays one game, and the process serves one campaign.**
  Spec req 1 puts the system on the campaign, so the runtime fact is a
  single id in a declaration file at the data-dir root, beside
  `characters/` and `trash/`. The declaration is store state: read when
  the store opens, written through the store's existing primitives,
  under the store's single write lock; each route resolves `system →
  embedded ruleset` under that lock. No activation step, no mutable
  engine slot. Undeclared and empty: the roster shell and the declare
  route only; every character route refuses typed. Undeclared with
  characters: PF2e, inferred on every load, never written; a declare
  call (of either game) refuses typed. **Empty** means no `.json` in
  `characters/`, `trash/`, or `quarantine/` whose stem is not a swept
  temp — a swept temp never fixes the game; a trashed or quarantined
  character always does. Declare: a uniquely named temp at the root,
  fsync, hard-link to the declaration name (fails if one exists), unlink
  the temp; change-while-empty: temp → fsync → rename; stray root temps
  are swept to `trash/` at start like character temps. What must never
  happen: two engines answering for one campaign; a declaration written
  by a load; a route folding a log under a ruleset the file does not
  name.
- **The ruleset boundary becomes a contract, not a type.** The server,
  the WASM bundle, and the checks hold `Engine<Pf2eState>` by concrete
  type and call PF2e free functions for what the engine does not know.
  Two engines behind one runtime selector force one surface: engine-core
  gains an object-safe `Ruleset` trait — log in, views out. The engine
  operations get one blanket implementation over `Engine<S>`; each
  ruleset crate implements only the escape hatches (rules version,
  `level_of(log)`, `advance_slot(level)`, name and class slot ids,
  suggested builds, mint fill-ins, license notice, known-versions
  inputs) and exposes `embedded()` — its compile-time rules data,
  parsed once. Server and WASM each hold a two-arm selector, id →
  `embedded()`; no registry crate (review: a two-entry table is not a
  crate, and it would not shorten any rebuild path). What must never
  happen: a game word in the trait; a ruleset crate importing another;
  the server pattern-matching a slot-id string (the advance-slot string
  it parses today becomes a ruleset query).
- **The browser holds the same selector.** One WASM module embeds both
  rulesets; `engine_request(system, request)` takes the id as a second
  parameter — the wire enum stays a pure engine op, and the TS façade
  stamps the id once from the campaign view. What must never happen:
  two WASM modules, or a UI branch on the id beyond passing it.
- **The campaign is a view.** One `campaign` view — declared or not,
  the system id, the shipped games to choose from, every shipped
  license line — fetched first by the UI; the choose-game screen, the
  roster label, and the façade all read it. The storage `system` field
  appears on the wire only there. What must never happen: a character
  or wizard view carrying a system field.
- **Files know their game; the campaign's game is checked first.**
  Character documents gain a `system` field (schema v4 → v5; optional
  on read, written on the next write). Load order per file: parse →
  schema → system check → version guard. The file's system is its
  field, else its pin prefix **when that prefix is a registered
  system id**, else PF2e (spec req 8); an unregistered prefix is
  version-unknown at the guard, as today, never structural. A file
  whose system ≠ the campaign's, or whose explicit field ≠ a registered
  prefix, is **refused in place** like a newer-schema file: reported on
  the roster with the reason, never loaded, never written, never moved
  — a valid file in the wrong context, not corruption. Known versions
  are assembled per ruleset from its own manifest and shipped-versions
  file; the test-support extras file is keyed by system. Rules-version
  strings keep `<system>-<source>.<semver>`, now linted. What must
  never happen: a file reaching the guard under another system's
  current version; a mismatch moving a file.
- **Rules data is per system, one directory each.** `rules-data/pf2e/`
  (existing files moved byte-identical; lineage, attestation, and the
  reference-check paths follow) and `rules-data/dnd5e/` with its own
  manifest (`system` finally read: must equal the directory and the
  selector key), shipped-versions, attestation, license notice. Each
  ruleset crate defines its own file set and parser. Every shipped
  license line shows on every campaign's roster — attribution follows
  the binary. What must never happen: a flat directory with two
  systems' records; a notice that depends on the open campaign.
- **Attestation gets a second source under one top-level schema.** The
  reference-check tool takes a `--system` argument and a match — not a
  source trait: two sources, two comparators (the Foundry comparator is
  Foundry-JSON-shaped; the 5.5e source needs its own). Each system's
  `attestation.json` keeps the shared top level (version, tool, records,
  verdicts, no ground-truth values) with a per-source `source` block
  naming kind and hash; PF2e's existing keys live under that block
  without regenerating through the network tool. The 5.5e source is the
  spec's bounded choice. What must never happen: a network path outside
  the tool; ground-truth values in a committed file.
- **The 5.5e ruleset is the PF2e ruleset's shape with its own words.**
  Its own state, kind modules (class, background, species, scores,
  feats, equipment, details, advancement) under the same kinds →
  mechanics → engine-core DAG, its own sheet sections; the layering and
  isolation checks become per-crate. Advancement is data: class and
  subclass records carry per-level fixed features by id; the Fighter
  Subclass at 3 is a Single slot whose catalog **is** the subclass
  records; level 2 has no choice slot — the pending level is the gains
  step alone, finalize enabled at once (the machinery's first empty
  level). Quick build: the suggested-build route refuses typed in a
  5.5e campaign and the roster shows no affordance. What must never
  happen: a level's grants in a kind module; a subclass as hardcoded
  features.
- **The ability-score step in the existing slot vocabulary** (spec
  req 3; the one-dialog-machine risk). A *method* slot (Single:
  standard array | point buy; `dnd-dice` appends roll) whose dependents
  are an *assignment* slot and, for point buy, its budget meter; the
  background's *increase* slot is a Single over the seven legal
  distributions, enumerated as data. Assignment is `Multi{6}` whose
  options carry their ability as `OptionView.group` (the existing
  grouped rendering — no id-prefix parsing): the array method offers
  each array value under every ability and validates one-per-group and
  each-value-once; point buy offers the published range under every
  ability with a budget meter showing true overshoot. The UI adds one
  presentation hint — *one pick per group* — rendering the grouped
  Multi as a select per group with the group's label; the PF2e boosts
  editor stays (its positional encoding is a finalized-fixture fact),
  its "Boost" copy moving to the slot's label. Method change cascades
  through the existing dependents machinery. What must never happen: a
  system branch in the UI; a widget that knows what an ability is.
- **Checks run per system on the same harness.** Tests needing a 5.5e
  campaign write the declaration into their temp dir first; every PF2e
  test is unchanged; 5.5e rows mirror the stories with bounded case
  counts so the default-suite budget holds.

## Boundaries

```
ui ── campaign view first (choose-game, label, license lines); the
 │    per-group hint; façade stamps system id into engine_request
 ▼
wasm ── engine_request(system, req) → two-arm selector → embedded()
 │
server ── store owns the declaration (open/declare/change under its
 │        lock); two-arm selector; per-file system check before the
 │        version guard; per-ruleset KnownVersions; campaign view
 ├─▶ ruleset-pf2e ──▶ engine-core ──▶ types
 └─▶ ruleset-dnd5e ─▶ engine-core ──▶ types
engine-core ── `Ruleset` trait: blanket engine ops over Engine<S> +
               per-ruleset escape hatches; Engine<S> unchanged in kind
rules-data/pf2e, rules-data/dnd5e ── one directory per system
reference-check ── `--system`, second comparator, one attestation schema
checks ── depends on both ruleset crates (fixtures, goldens)
```

Forbidden: `ruleset-pf2e` ↔ `ruleset-dnd5e`; a game word in the trait;
a system branch, system-id literal, or ability-name literal in `ui/src`;
a slot-id string parsed in server or wasm; the storage `system` field on
any view but the campaign view; an HTTP client in server's or wasm's
normal dependency tree.

## Failure modes

- **Declaration corrupt or unrecognized:** every character route refuses
  typed; the roster shows the campaign quarantined with the reason and
  the path; `verify` says the same; nothing written or moved.
- **No declaration, but a file names 5.5e:** reported as a missing
  declaration; the roster and `verify` name the expected path and its
  one-line content so the hand fix is unambiguous; no inference.
- **Declare on an undeclared dir holding characters:** typed refusal,
  either game; the dir stays inferred PF2e.
- **Two tabs answer the game question:** the second hard-link fails;
  that tab receives the declared game and reloads.
- **Change-while-empty races a first create:** both take the store
  lock; the loser gets a typed refusal naming why.
- **kill -9 during declare or change:** the file is absent, old, or new
  — never torn (temp + fsync + link/rename); root temps are swept.
- **Wrong drawer / pin disagrees with an explicit system:** refused in
  place with the reason; the rest loads; copying the file into a
  campaign of its game makes it load. When every file disagrees, the
  roster names the declaration as the likely wrong side.
- **Embedded rules data for either system fails to parse at boot:**
  refuse to start naming the system (a build defect: both sets are
  lint-asserted parseable).
- **A WASM fold under the wrong or unknown system:** a log naming a
  slot the ruleset does not know is a typed engine error and the UI's
  explicit error state, never an empty sheet; the id comes from the
  campaign view fetched at boot, refetched on reload.
- **Level 2 in 5.5e (no slots):** gains step and an enabled finalize;
  abandon lists only the advance.
- **Subset dead end:** the 5.5e seed sweep fails the build.
- **The Magic Initiate gap:** a rendered feature with a visible note.
- Everything else inherited unchanged.

## Performance budgets

| Budget | Value | Asserted where |
|---|---|---|
| Fold of a complete 5.5e level-3 log | < 5 ms (existing budget, per system) | `checks/perf.rs` |
| WASM bundle with both rulesets | ≤ 2.5 MB raw, exactly one `.wasm` (today 1.1 MB with one) | CI WASM step |
| Default test suite wall time | < 20 s (unchanged; bounded 5.5e case counts) | CI timing gate |
| Warm incremental rebuild | < 10 s (unchanged) | timed CI step |

Design target, hand-checked: declare → first wizard view with no
restart and no perceptible delay.

## Constraints emitted

All prior rows remain in force. New or amended rows:

| Rule | Enforced by | Config lives at |
|---|---|---|
| Layering: edges allowlisted for `ruleset-dnd5e` (→ engine-core, types) and `server`, `wasm`, `checks` → both ruleset crates; no edge between ruleset crates; `reference-check` unchanged; no `reqwest`/`ureq`/`hyper` in the resolved normal-dependency tree of `server` or `wasm` (the wasm-bindgen row's shape) | edge allowlist + dependency-tree scan | `checks/crate_layering.rs` |
| Per-crate scans: purity, kind-module isolation (each ruleset crate names its own module list), and the `const LEVEL` scan cover `ruleset-dnd5e`; no `pf2e`/`dnd5e` literal in `crates/engine-core/src` or `crates/types/src`; the tokens `.advance`, `slot_level_advance`, `"pf2e.`, `"dnd5e.` absent from `crates/server/src` and `crates/wasm/src` | source token scans | `checks/crate_layering.rs` |
| Class isolation per system: shipped names from each system's own data scanned against its crate; the cross-class-vocabulary check runs per system; the `MeterView {` ban covers the new crate | existing scan, parameterized | `checks/class_isolation.rs` |
| Rules data per system: each `rules-data/<system>/manifest.json` has `system` = directory = a selector key (the literal appears in server's and wasm's selectors), and every embedded set parses; every version in a system's manifest and shipped-versions begins with `<system>-`; `source.book` in that manifest's allowlist; the 5.5e manifest carries the CC BY 4.0 attribution and every 5.5e record names SRD 5.2.1 + CC BY; denylist, ID immutability, lineage, and advancement-reaches-cap per system; subclass records cross-reference their class | data lint (existing, per directory) | `checks/rules_data.rs` |
| Attestation per system: shared top level + a `source` block with kind and hash; matches the manifest version, covers every record, zero unwaived mismatches, no ground-truth values; cache gitignored; CI never runs the tool | existing check, per directory | `checks/attestation.rs` |
| Schema v5: v1–v4 fixtures load byte-identical, `system` written on first write; v6 refused; explicit-system-vs-registered-prefix disagreement is refused in place; a no-system file with an unregistered prefix loads as PF2e and is version-unknown | persistence fixtures | `checks/persistence.rs`, `checks/no_rewrite_on_load.rs` |
| Campaign declaration: undeclared-empty serves only shell + declare, character routes refuse typed; declare is create-exclusive (second → typed refusal, file byte-identical) and survives SIGKILL untorn; declare on undeclared-with-characters (either game) refuses; change succeeds only when empty per the definition (swept temps ignored; trash and quarantine count), else typed refusal; no declaration file appears after any load or `verify` of an undeclared dir; corrupt declaration → campaign-level refusal with reason; undeclared dir holding a 5.5e file → missing-declaration report naming the path | standalone tests via the real server | `checks/api_authority.rs`, `checks/persistence.rs`, `checks/no_rewrite_on_load.rs`, `checks/crash_harness.rs` |
| System before version: a mismatched file is present at its original path after any load or `verify`, never in version status; per-ruleset KnownVersions — a 5.5e campaign's guard never names a PF2e version and vice versa; extras file keyed by system, an unregistered key is a startup error | fixture tests | `checks/version_guard.rs`, `checks/persistence.rs` |
| Attribution follows the binary: the campaign view of a PF2e campaign, a 5.5e campaign, and an undeclared dir carries both the ORC notice and the CC BY text, byte-identical | standalone test + Playwright assertion | `checks/api_authority.rs`, `ui/e2e/dnd.spec.ts` |
| System on the wire once: in `crates/types/src` a `system` field exists only on the campaign view; serialized character and wizard views carry no `system` key | source scan + fixture assertion | `checks/crate_layering.rs`, `checks/persistence.rs` |
| Atomic transitions: SIGKILL during a 5.5e confirm and finalize-pending leaves the prior or next state | crash harness rows | `checks/crash_harness.rs` |
| 5.5e goldens: Brannock at 1 (array, package A) and 3 (Champion); a point-buy gold-alternative build (unarmored AC, empty attacks, coin); the level-2 pending fixture folds with an empty checklist; the level-3 checklist holds exactly one Single slot whose option ids equal the Fighter's subclass record ids | golden tests | `checks/replay.rs` |
| 5.5e seed sweep: minted characters finalize with an empty checklist, verify-clean, then level to the cap; the suggested-build route refuses typed in a 5.5e campaign, unchanged in PF2e | property test (bounded) + route test | `checks/random_mint.rs`, `checks/quick_build.rs` |
| Clone in a 5.5e campaign: fidelity contract unchanged; a leveling source clones its pending level independently | fixture test | `checks/clone.rs` |
| Ability-score machinery: over swept selections, one pick per group, each array value once, point-buy cost equals the table and never exceeds the budget; method change clears the assignment via dependents | property test | `checks/replay.rs` |
| UI system-blind: no `pf2e`/`dnd5e` literal and no ability-name literal in `ui/src` outside `engine/pkg` and `*.test.tsx`; no file or export named for a system; exactly one `.wasm` under `engine/pkg` and one init site; existing LevelUp/Wizard scans unchanged | source scan | `checks/crate_layering.rs` |
| Stories walk: choose-game; the second campaign; the buy with the gold alternative; level 2's empty level and the level-3 subclass; abandon and mid-level resume; the PF2e dir never asked; wrong-drawer refusal shown — under the layout sweep | Playwright specs | `ui/e2e/dnd.spec.ts` |
| Budgets: WASM ≤ 2.5 MB raw; 5.5e level-3 fold < 5 ms | CI size check; benchmark | `.github/workflows/ci.yml`, `checks/perf.rs` |

Deliberately unenforced, with reasons: **no game word in the `Ruleset`
trait** stays at review (the literal scans catch names, not meaning).
**The boundary-bends list** is the report's section (spec req 7), judged
by Ben. **Attestation source choice** is recorded in the report and the
`source` block, not asserted. **Same-app feel** and **roll-ready method
step** are the spec's intent checks.

## Review record

| Role | Verdict | Folded in |
|---|---|---|
| constraint-auditor | block, resolved | attribution-follows-the-binary row and system-on-the-wire-once row (the blocks); subclass catalog = records in the goldens row; ability-name and engine-core literal scans; HTTP-client dependency-tree ban; version-prefix lint; quick-build refusal row; one-wasm-file clause |
| failure-mode-reviewer | block, resolved | mismatch refused in place, never moved (the block); hard-link declare + root temp sweep; "empty" defined against swept temps, trash, quarantine; declare on non-empty undeclared refused; missing-declaration message names the path; unregistered prefix stays version-unknown; wrong-system WASM fold typed; extras keyed by system |
| simplicity-warden | block, resolved | registry crate removed for per-crate `embedded()` + two-arm selectors (the block; rebuild claim deleted); blanket engine-ops impl, escape hatches only per ruleset; system id as a request parameter; grouping via `OptionView.group`; `--system` + match in reference-check with a second comparator and one attestation schema with a per-source block; declaration as store state under the existing lock |
