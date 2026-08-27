---
slug: chargen-fighter
status: approved
---

# Chargen slice 1 — architecture

> Drafted preemptively while the spec is itself still a draft; if spec
> approval changes requirements, this doc gets a delta pass before its own
> approval. The language choice was decided with Ben in review dialogue
> (2026-08-28): Rust engine + WASM, TS presentation layer.

## Situations

- **The same rules engine must run in two places.** The wizard validates and
  recomputes the sheet live on every choice (sub-50ms, no network), and the
  server is the authority for what gets persisted and finalized. What must
  hold: one implementation of slots/validation/derivation — compiled to WASM
  for the browser, native on the server. What must never happen: two
  divergent implementations of the rules, or the client trusted as
  authority, or game semantics accreting in the presentation layer because
  calling the engine feels heavy.
- **Derivation is a pure fold.** Sheet = fold(decision log, pinned rules-data
  version). What must never happen: wall-clock, randomness, I/O, or ambient
  config reaching derivation or validation code — replay run next year must
  reproduce today's sheet byte-for-byte.
- **The process dies whenever it dies.** Laptop lid, battery, kill -9 — at
  any instant. What must hold: every confirmed wizard step was already
  durably on disk before the UI advanced; restart shows the roster and
  resumes the draft at the exact step. What must never happen: a torn or
  half-written character file, or one corrupt file preventing the roster
  from loading.
- **The data directory is a user artifact.** Ben will open, read, diff, back
  up, and occasionally hand-edit these files. What must hold: one JSON file
  per character (materialized sheet + ordered decision log + schema version +
  rules-data pin); hand-tampering is detected by `verify`, reported, and
  never blocks loading. What must never happen: state hidden in an opaque
  store, or a silent overwrite of a file the app didn't write.
- **Rules content is versioned data, not code.** Adding the Wizard class (or
  ten more backgrounds) later must be data files plus slot definitions —
  no core changes. Every record carries a stable ID and license metadata;
  the app displays the ORC notice. What must never happen: a rules-data edit
  silently changing an existing character's stored sheet — divergence is
  surfaced by `verify`, resolved deliberately.
- **The boundary that matters is core vs ruleset.** The core knows
  characters, slots, decisions, drafts, and a presentation contract. The
  PF2e module knows boosts, heritages, and proficiency ranks. What must
  never happen: PF2e vocabulary in core types, or core reaching into
  ruleset internals. This is enforced by tooling from the first commit, not
  by review vigilance.

## Boundaries

Language: **Rust engine + Rust server, TypeScript presentation layer**
(decided with Ben after codegen research). The engine — slots, validation,
the fold — is Rust compiled twice: WASM for the browser, native in the axum
server — one engine, two runtimes, no duplication. Types are defined once,
in Rust: serde governs the wire format, **tsify** welds the generated TS
declarations into the wasm-bindgen `.d.ts`, so every exported function has
a real TS signature (never `JsValue`/`any`). The WASM surface is narrow,
Graphite-style: one serde-tagged request enum in, one response enum out,
behind a thin hand-written TS façade. Rust's compiler is a standing
reviewer over agent-written code; accepted costs: two-toolchain repo,
slower engine iteration (budgeted below), Chromium-only source-level WASM
debugging — mitigated by debugging the pure engine natively and treating
the browser copy as a black box with a panic hook.

```
              browser                            server process (Rust)
     ┌─────────────────────────┐         ┌─────────────────────────────┐
     │ ui (TS: wizard, roster  │──HTTP───▶  api (axum routes,          │
     │  — renders, never       │  JSON   │   authority)                │
     │  computes game values)  │         └──────┬───────────────┬──────┘
     └──────┬──────────────────┘                │ native        │
            │ typed WASM calls                  │               ▼
            ▼ (tsify-generated .d.ts,           │        ┌──────────────┐
     ┌──────────────────┐  narrow msg enums)    │        │ persistence  │
     │ wasm façade (TS) │                       │        │ (Rust; only  │
     └──────┬───────────┘                       │        │ fs user)     │
            ▼                                   ▼        └──────┬───────┘
     ┌──────────────────────────────────────────────┐           ▼
     │  engine (Rust crates, compiled twice:        │       data dir
     │  WASM for browser, native for server)        │    (JSON files,
     │    ruleset-pf2e ──▶ engine-core ──▶ types    │    lock, trash/)
     └──────────────────────┬───────────────────────┘
                            ▼
                 rules-data (versioned JSON,
                 stable IDs, license metadata)
```

- Engine crates split for cache locality as much as layering: `types`
  (serde + Tsify derives incl. the presentation contract — the single
  source of truth for every boundary-crossing shape), `engine-core`, and
  `ruleset-pf2e`. Touching PF2e content must not rebuild the server;
  touching the UI rebuilds no Rust at all.
- `engine-core` depends only on `types`; no I/O, clock, randomness, or
  unsafe. Its contract is one concept — the choice slot (unlock condition,
  option source, validators, effects) — and five operations: slot-graph
  resolution, log append/replay, validation into the checklist, the fold
  traversal, draft lifecycle. Ancestry, background, class, heritage, feats
  are *not* engine concepts — each is a slot the ruleset defines, differing
  only in what its options unlock and contribute. Anything with a game word
  belongs in a ruleset crate; engine-core growing game vocabulary is the
  overfit smell reviews watch for. `ruleset-pf2e` depends on `engine-core`
  + `types` only; loads `rules-data` records passed in (no file access).
- **Horizontal separation inside a ruleset.** Each option kind (ancestry,
  background, class, feats, skills, equipment) is a module whose only
  public surface is the slot/option definitions it registers; kind modules
  never import each other. A rule needing another kind's outcome ("this
  feat requires a Strength boost") queries engine-core about the log or
  folded state — never a sibling module. Shared mechanics (boost math,
  proficiency arithmetic) live in the ruleset's mechanics module: kinds →
  mechanics → engine-core, a DAG with no kind↔kind edges. Enforced like
  wire≠storage: all but the registration surface is non-`pub`, so a
  cross-kind reference fails to compile. Future
  rulesets never depend on each other. Inside the ruleset the same split
  repeats one level down: *engine* (validation mechanics, the fold) is
  separate from *content* (slot definitions and option catalogs, which are
  data). That inner seam is what makes `chargen-content` a data-only slice,
  lets the wizard UI render steps from slot metadata instead of hand-coding
  them, and is where the shared PF2e/SF2e engine layer will sit.
- **Shared-infra discipline (anti-`common`-crate).** Crates named
  `common`/`utils`/`helpers`/`shared` are banned by the layering check.
  Shared functionality gets a purpose-named crate with one narrow contract,
  born only by extraction from a second concrete use — the same rule as the
  effects DSL — and rulesets opt in individually. The workspace dependency
  graph is an explicit allowlist in the layering check, so a new crate or
  edge is a reviewed edit, never silent accretion. Macros are syntax sugar
  expanding to ordinary hand-writable code — semantics never live inside a
  macro — and the first question before any generator is "should this be a
  rules-data record instead?" (content is already data-driven). The
  warm-incremental-build budget is the bulk tripwire: a crate everything
  rebuilds on touch shows in `--timings` and gets split. a serde-tagged request
  enum in, a response enum out, via tsify's `Ts<T>` (deserialization
  failures surface as catchable errors). A thin hand-written TS façade
  wraps it; generated bindings are committed, and the UI imports only the
  façade and the generated types.
- `ui` (TS, Vite + React) renders engine output and holds ephemeral form
  state; it computes no game values and talks to the server only via HTTP
  JSON using the generated types. Litmus test: a TUI against the same
  engine needs zero Rust changes.
- `server` (axum) re-validates and re-derives natively on every write — the
  client's fold is a preview, the server's is the record.
- `persistence` (Rust module or crate within the server, implement's
  discretion) is the only code touching the filesystem; every read parses
  through versioned serde schemas, every write is temp-file → fsync →
  atomic rename.
- **Wire types are not storage types.** The structs serialized to disk
  (storage documents) are private to `persistence` — `pub(crate)` at most —
  and route handlers can only build responses from view types in `types`.
  Every API response is therefore an explicit allowlist of fields, never a
  serialization of the stored document. This is the Epoch 2 visibility seed:
  per-role filtering later means defining more view types at the route
  layer, and a secret can't leak by default because the compiler already
  prevents handing a storage struct to the wire.
- Nothing imports `ui`.

## Failure modes

- **Process killed mid-write:** atomic-rename discipline means the old file
  survives intact; a stray temp file is swept on startup. The confirmed-step
  API call only returns success after fsync, so the UI never advances past
  an undurable step. Ben sees: restart, resume at the last confirmed step.
- **Character file corrupt / hand-tampered:** parse or schema failure
  quarantines the file (renamed aside, reported on the roster: "torvald.json
  could not be read — quarantined"); the rest of the roster loads, and the
  report appears even when the rename-aside itself fails (read-only dir).
  `verify` distinguishes tamper (sheet ≠ replay) from corruption
  (unparseable) and says which.
- **Replay divergence** (rules-data corrected, or derivation bug fixed):
  `verify` reports per character; the materialized sheet remains the load
  path, divergence is a flag for deliberate resolution, never a silent
  rewrite.
- **Data dir schema newer than the binary:** refuse to open with a clear
  message (downgrade guard). This slice ships schema v1 only — version
  fields and unknown-version refusal are the whole migration discipline
  until a v2 exists; the first migration is built when the first schema
  change happens, not as a framework now.
- **Second server instance on the same data dir:** the data dir carries a
  lockfile (pid-checked); a second instance refuses to start with "already
  serving at <URL>" instead of becoming a silent second authority whose
  atomic renames would clobber the first's writes. Only with the lock held
  does port-walking apply: if the port is taken by an unrelated process,
  walk to the next free port and print the bound URL; never silently fail to
  serve.
- **Server unreachable mid-wizard** (crashed, restarting, fetch timeout): a
  confirm-in-flight blocks step advancement; the UI shows the unsaved state
  and retries idempotently (safe under the decision-ID rule); the rest of
  the wizard stays readable. The UI never advances past an unacknowledged
  step.
- **Rules data absent or corrupt at server start:** refuse to start with a
  clear message (parallel to the downgrade guard) — derivation without its
  data has no degraded mode worth having.
- **Character file pinning an unknown rules-data version** (hand-edit):
  parses fine, so no quarantine; the materialized sheet loads, and `verify`
  reports "unknown rules-data version — replay impossible" for that
  character.
- **Browser tab dies mid-step:** the step cursor lives server-side in the
  draft, so resume lands on the exact step from any tab. Loss window: the
  in-flight unconfirmed field, exactly the loss the spec accepts — no
  client-side mirror machinery to shrink it further.
- **Retried or stale confirm:** every confirm carries a client-generated
  decision ID and the draft version it was made against. A retry after a
  crash-between-save-and-ack appends nothing (ID already present); a confirm
  from a stale tab is rejected with the current draft state so the UI
  reloads — never silently interleaved.
- **Disk full / data dir unwritable:** the temp-file write fails before the
  rename, the prior file version is untouched, the API returns an error, and
  the UI says the step did not save. Deletes move files to `trash/` inside
  the data dir under a timestamp-suffixed name (recreate-then-delete never
  overwrites an earlier trashed copy) — the app never unlinks a character
  file.
- **Client and server derivation disagree** (should be impossible — same
  engine, same commit): server wins, the mismatch is logged loudly, and the
  response carries the server sheet so the UI self-corrects.
- **Engine panic in the browser:** a panic hook surfaces the Rust panic
  message to the console and the UI shows an explicit error state instead of
  a silently dead widget; the triggering request enum value is logged so the
  same input becomes a native `cargo test` repro.

## Performance budgets

| Budget | Value | Asserted where |
|---|---|---|
| Derivation fold of a complete level-1 log | < 5 ms | native benchmark test in checks (underwrites the spec's live-recompute feel; WASM copy is same-order and hand-checked; the rest of UI latency is design, verified by hand at review) |
| Default test suite wall time | < 20 s | CI timing gate in checks (vision standing discipline) |
| Warm incremental rebuild: engine change → new WASM + server binary | < 10 s | timed CI step with warm cache (generous threshold; cold builds excluded as cache-noisy). `cargo build --timings` kept as a CI artifact so a regression is attributable to the crate that got fat — this is the crate-split-for-cache-locality budget |

Design targets, hand-checked at review rather than asserted (the spec sets no
number on them, and the crash harness already proves the durability property
itself): confirmed step durably on disk well under perceptible latency
(~100 ms), server cold start to roster ~2 s. No throughput budgets: one user,
KB-scale data. Requests/sec work is explicitly refused.

## Constraints emitted

Everything in this table is programmatic and build-failing — CI runs every
row on every push. Anything *not* in the table (and anything in the
"deliberately unenforced" and "design targets" notes) is guidance verified
by humans at review time. There is no third category.

| Rule | Enforced by | Config lives at |
|---|---|---|
| Crate layering: the workspace dependency graph is an explicit edge allowlist — `engine-core` depends only on `types`; `ruleset-*` only on `engine-core` + `types`, never on each other; `wasm` and `server` never in each other's trees; only `wasm` uses wasm-bindgen; any new crate/edge is an edit to this check; crates named `common`/`utils`/`helpers`/`shared` are rejected | layering test over the workspace `Cargo.toml`s | `checks/crate_layering.rs` |
| No I/O, clock, randomness, or env in engine crates: `std::fs`, `std::net`, `SystemTime::now`/`Instant::now`, `std::env`, and any `rand` dependency banned in `types`/`engine-core`/`ruleset-*` | clippy `disallowed-methods`/`disallowed-types` + the layering test (dependency bans) | `clippy.toml`, `checks/crate_layering.rs` |
| `#![forbid(unsafe_code)]` in engine crates; workspace lint policy | `[workspace.lints]` + crate roots | `Cargo.toml` |
| No `std::fs::remove_file`/`remove_dir*` anywhere — deletes are renames into `trash/` | clippy `disallowed-methods` (workspace-wide) | `clippy.toml` |
| Dependency hygiene: license allowlist, duplicate/yanked-crate bans | cargo-deny | `deny.toml` |
| Wire ≠ storage: storage document structs are non-public to `persistence`, so route handlers cannot serialize them — responses are built only from view types in `types` | rustc module visibility (a reference from a route handler fails to compile) | server crate layout; spot-asserted by `checks/crate_layering.rs` (no storage-doc type names exported) |
| Option kinds don't bleed: within a ruleset, each kind module's only public surface is its slot/option registrations; no kind module references another (kinds → mechanics → engine-core, no kind↔kind edges) | rustc module visibility + a module-graph assertion | ruleset crate layout; `checks/crate_layering.rs` (module-level import scan for the ruleset crates) |
| TS strictness in `ui`: `strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`; no `any`; no raw wasm-bindgen imports outside the façade; no importing `rules-data` | tsconfig + eslint (`no-explicit-any`, `no-restricted-imports`) | `tsconfig.json`, `eslint.config.js` |
| Generated bindings never stale: CI regenerates the wasm package + exported types and fails on any diff against the committed copies | regen + `git diff --exit-code -- <generated dirs>` | CI step in `.github/workflows/ci.yml` |
| Every persisted document round-trips a versioned serde schema; unknown versions — including versions newer than the binary — rejected; a corrupted fixture file is quarantined while the rest of the roster loads; deletes land in `trash/` | persistence contract test | `checks/persistence.rs` |
| Crash safety: kill -9 during a write storm leaves every file loadable and every confirmed step present | crash harness (spawn server, hammer confirms, SIGKILL at random offsets, restart, assert) | `checks/crash_harness.rs` |
| Confirm idempotency + concurrency: a replayed decision ID appends nothing; a confirm against a stale draft version returns a conflict carrying current state | standalone test | `checks/confirm_idempotency.rs` |
| Load is read-only: data-dir bytes are hash-identical before/after roster load and character open | standalone test | `checks/no_rewrite_on_load.rs` |
| Server authority: a raw HTTP confirm of an illegal or incomplete decision (bypassing the wizard) is rejected and appends nothing | standalone test | `checks/api_authority.rs` |
| Replay determinism: fold(log) equals stored sheet for all fixture characters; golden sheets hand-verified against Player Core | golden + property tests (native) | `checks/replay.rs` |
| Rules-data integrity: IDs unique and stable, license metadata on every record, schema-valid, ORC notice string present in the served app | data lint test | `checks/rules_data.rs` |
| Asserted perf budgets above (fold benchmark, suite wall time, warm incremental build) | asserting tests + timed CI step | `checks/perf.rs`, `.github/workflows/ci.yml` |
| All of the above run on every push | GitHub Actions: clippy, cargo-deny, fmt, cargo test incl. `checks/`, wasm build, bindings-freshness, tsc, eslint | `.github/workflows/ci.yml` |

Implement stage applies this table as its first ticket; the repo's own
toolchain runs them forever, with checkpoints absent.

The table is the *invariant* layer, not the whole test surface. The implement
stage also writes ordinary feature tests as part of its tickets: unit tests
for every validator and the derivation fold (including golden sheets
hand-checked against the Player Core), API tests for the draft/confirm/
finalize routes, and — the UI's main verification — a browser-driven
end-to-end suite (Playwright) that walks each user story in the spec ("first
run", "the mistake, caught", "the crash", "jumping ahead") as an automated
scenario. The agent's report cites those story walkthroughs as its evidence;
Ben's own checks in the spec re-walk them by hand. Pixel-level look-and-feel
is not machine-judged — that is what the spec's intent check is for.

Deliberately unenforced, with reasons: "no PF2e vocabulary in core types" is
enforced only at the dependency level (crate layering) — hand-written ruleset
vocabulary in a `types`/`engine-core` type would pass tooling and is left to
review, since vocabulary policing is not mechanically checkable. "The UI
never computes game values" is enforced only at its edges (no `rules-data`
import, no raw wasm access, engine outputs are render-ready) — a convenience
game calculation hand-written in TS would pass tooling; review treats any
such helper as an engine API gap. "Client and server derivation never
diverge" is structural (one engine, compiled twice from one commit, with the
bindings-freshness gate), so the divergence handler is defensive logging
with no dedicated test. The
lockfile-refusal and port-walk-and-print behaviors are hand-verified at
review (start a second instance; occupy the default port) rather than
asserted — cheap to promote to a check later if they ever regress.

## Review record

| Role | Verdict | Folded in |
|---|---|---|
| constraint-auditor | block, resolved | four missing rows added (confirm idempotency, read-only load, server authority, no-unlink); `no-restricted-syntax` for `new Date()`; newer-version clause; deliberately-unenforced reasons paragraph |
| failure-mode-reviewer | block, resolved | data-dir lockfile against a silent second server instance; server-unreachable-mid-wizard, rules-data-absent-at-start, unknown-data-pin behaviors; timestamped trash names; quarantine reports despite failed rename |
| simplicity-warden | advice | vestigial journal cut from the diagram; localStorage mirror cut; migration framework deferred to first real v2; two unjustified asserted budgets demoted to hand-checked targets; persistence-as-directory option noted |
| Ben (review dialogue) | decision | stack: Rust engine (native server + WASM via tsify) with TS presentation layer, chosen over TS end-to-end after codegen/debugging research; hard JSON boundary as narrow message enums; build-cache budget added as a constraint |
| Ben (review dialogue) | decision | Epoch 2 identity/visibility not front-loaded; wire-≠-storage view-type split adopted (with constraint row) as the structural guarantee that identity/filtering attach at the route layer later |
