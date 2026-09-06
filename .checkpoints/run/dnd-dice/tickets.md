# dnd-dice — ticket plan

Docs: `.checkpoints/specs/dnd-dice.md`, `.checkpoints/architecture/dnd-dice.md`.
Branch `checkpoint/dnd-dice`. `[x]` done, `[~]` in progress. Ticket 1 wires
the constraint scaffolding first; behavioural rows land with their feature
tickets — every row green before the report. Cut gate (spec, Risks): if the
score stories are not green by ticket 4's end, ticket 3b/5b/6b (rolled hit
points) split off as `dnd-hp-dice`.

## Key design decisions (bound by the docs; details agent-decided)

- **Wire types** (`crates/types/src/roll.rs`): `RollOrigin { App, Entered }`
  (exactly two variants, serde snake_case); `RolledSet { groups:
  Vec<Vec<u8>>, origin }`; `Selection::Rolled(Vec<RolledSet>)` (serde tag
  `rolled`); `SlotViewKind::Roll { sides: u8, dice: u8, groups: u8 }`; one
  game-free `check_roll_shape(sides, dice, groups, &[RolledSet]) ->
  Result<(), String>` beside them (group count, dice per group, faces in
  1..=sides, at least one set). No seed anywhere in types.
- **Stored vs submitted meaning**: a stored `Rolled` holds the whole
  history, last set live. A submitted `Rolled` (DecisionInput) means "sets
  to append". `Engine::amend` and `Engine::preview` compose `stored ++
  incoming` when the slot's existing decision is `Rolled`; `append` (no
  existing decision) takes the input as-is. Drop/reorder is inexpressible.
- **Shape check at apply**: each roll slot's `apply` calls
  `check_roll_shape` with its own declared shape; an out-of-shape set is an
  `ApplyError` (illegal in preview, refused on confirm). No generic engine
  pass.
- **5.5e scores**: rules-data `method.roll` record (`kind: "roll"`,
  `roll: {sides: 6, dice: 4, keep: 3, sets: 6}`), version bump
  `dnd5e-srd.0.1.0 → 0.2.0` (manifest supersedes, shipped-versions,
  attestation re-run offline against the cached mirror). New slot
  `dnd5e.scores.roll` (step scores, required, `Roll{6,4,6}`, Open iff the
  method is roll else Hidden, dependents → assign; the method slot's
  dependents → roll, assign). Its `options` are the history, one
  `OptionView` per set: label = totals, summary = live/superseded, details
  = each group's faces with the dropped die named, badge = rolled/entered,
  `available` = is live. Apply stores the full history in
  `state.rolled_sets`; live = last. Assignment offers the live set's
  totals with multiplicity (a value is available while its assigned count
  < its offered count); validate generalizes "each value once" to "at most
  as often as offered" for array and roll alike.
- **Rolled hit points**: per advancement level L, one unrequired slot
  `dnd5e.level.L.hit-die` in step `level-L`, `Roll{hit_die, 1, 1}`, Open
  iff `state.level() == L` and a class is chosen. Apply stores
  `state.hit_die_rolls[L] = sets`; HP fold: with no hit-die decisions the
  existing formula and detail text verbatim (Brannock's goldens
  byte-identical); with any, a per-level breakdown naming rolled / entered
  / fixed, each level's gain `max(1, value + Con)` (SRD minimum, verified
  against the cached SRD text at implement).
- **Server** (`crates/server/src/dice.rs`): `trait Entropy { fn faces(&self,
  key: &RollKey, sides: u8, n: usize) -> Result<Vec<u8>, EntropyError> }`;
  `OsEntropy` via `getrandom` (rejection sampling, never modulo);
  `SeededEntropy { seed }` mixing seed + character id + decision id
  through SplitMix64. `RollOrigin::App` is constructed only in `dice.rs`.
  CLI `--dice-seed <u64>`; `App { dice: Arc<dyn Entropy>, seeded_dice }`;
  `CampaignView.seeded_dice: bool` (serde default) → roster badge.
- **Roll route** `POST /api/characters/{id}/roll` `{ slot, version,
  decision_id }` → `ConfirmOutcome`. Phase 1 under the store lock: load,
  guards (wizard target/write, not an advance slot, above the marker),
  idempotency (id in log → Confirmed), version (≠ → Conflict), project and
  read the slot's `Roll` shape (not a roll slot / locked / hidden → 422).
  Phase 2, lock released: draw `groups × dice` faces. Phase 3 under the
  lock: reload, re-check id and version, compose one `Rolled` set tagged
  App, amend through the shared body, save. Confirm and amend share one
  body with the roll route (`write_decision`); confirm/amend refuse typed
  (422) any `Rolled` input carrying an `App` set — everything else they
  accept is `Entered` by construction (server re-stamps).
- **Schema v6** (`Selection` grew). v1–v5 read; v7 refused.
- **UI**: `case 'roll'` → `RollEditor`: history from `slot.options` (most
  recent 3 shown, "Show all N"), a Roll button (`rollDice` API, preceded
  by the existing clear dialog when the slot is occupied and the engine's
  clear preview lists dependents), and an Enter-dice grid (`groups × dice`
  numeric inputs, tentative `{kind:'rolled', value:[{groups, origin:
  'entered'}]}`, previewed through the existing candidate path, confirmed
  through the existing confirm/amend). No die literal, no arithmetic.
- **Checks**: scans in `crate_layering.rs` (entropy only under server —
  whole-workspace walk; `getrandom`/`Math::random` purity tokens incl.
  `crates/wasm/src`; `RollOrigin::App` constructor in exactly one server
  module; word-bounded die literals + `Math.random`/`getRandomValues` in
  `ui/src`); `clippy.toml` disallowed `getrandom::getrandom` with one
  allow in `dice.rs`; behavioural rows in `api_authority.rs`,
  `confirm_idempotency.rs`, `crash_harness.rs`, `persistence.rs`,
  `replay.rs`, `dnd5e.rs`, `ui/e2e/dice.spec.ts`.

## Tickets

- [x] 1. Constraints wiring: entropy dependency scan inverted to the whole
  workspace (only `server` reaches `rand*`/`getrandom`); purity tokens
  `getrandom`, `Math::random` + `crates/wasm/src` coverage; `clippy.toml`
  entropy bans; UI dice-blind scan (word-bounded `d4..d20`, `Math.random`,
  `getRandomValues`); single-module `RollOrigin::App` scan (skips until the
  type exists); `SelectionKind` exhaustiveness left to the compiler. All
  green on the unchanged tree.
- [x] 2. Types + engine-core + schema: `roll.rs` types, `Selection::Rolled`,
  `SlotViewKind::Roll`, `check_roll_shape`; amend/preview composition;
  every exhaustive `Selection` match gains an arm (server version.rs,
  routes.rs, both rulesets' describe/sel helpers); engine-core tests
  (composition, shape helper property test in `checks/replay.rs`); schema
  v6 + persistence rows (v5 reads, v7 refused, v6 round-trip fixture).
- [x] 3. ruleset-dnd5e scores: `method.roll` record + version bump 0.2.0 +
  shipped-versions + attestation re-run; `dnd5e.scores.roll` slot with
  history options; multiplicity-aware assignment; sheet ability entries
  name faces and tag; crate tests; every existing 5.5e golden unchanged.
- [~] 3b. ruleset-dnd5e hit dice: per-level unrequired `hit-die` slots; HP
  fold per-level with the published minimum; describe; gains/deltas/pending
  carry the roll; Brannock goldens byte-identical.
- [ ] 4. Server: `dice.rs` (OS + seeded, keyed), `--dice-seed`, `seeded_dice`
  on the campaign view, the roll route (three phases), shared
  `write_decision`, origin refusal on confirm/amend; checks:
  `api_authority.rs` (refusals, append-by-construction M+N, injected failing
  entropy via a seed-flag variant? — no: failing source is in-process; the
  real-binary row asserts typed refusals + no write), `confirm_idempotency.rs`
  (one id → one set), `crash_harness.rs` (roll, entered amend, hit-die roll),
  seeded rows (same seed → same faces across two clones; no flag → differ;
  badge iff flag; no `seed` key in any written file).
- [ ] 5. WASM bindings rebuild; UI `RollEditor`, `rollDice` API, clear-before-
  reroll, roster badge, ConfirmedSummary `rolled` arm, pending/prune
  handling; vitest rows; UI dice-blind scan green; `campaign.spec.ts`
  untouched.
- [ ] 6. Checks + stories: Ysolde golden (reroll, entered set, duplicate
  totals, 18+2 cap) + fixtures; multiplicity property; hit-point rows
  (absent = fixed, rolled replaces one level, unrequired, gains/deltas,
  abandon lists it); 1,000-set fold budget; PF2e registration scan;
  Playwright `ui/e2e/dice.spec.ts` (roll + reroll with confirm, entered
  dice with a bad face, duplicates and the cap, double tap, hit die with a
  kept reroll and an entered d10, abandoned level, nothing-else-moved).
- [ ] 7. Full gate run (fmt, clippy, deny, tests + budget, wasm size,
  bindings fresh, npm typecheck/lint/test/e2e) and the report
  `.checkpoints/run/dnd-dice/report.md`.
