# chargen-dnd — ticket plan

Docs: `.checkpoints/specs/chargen-dnd.md`, `.checkpoints/architecture/chargen-dnd.md`.
Branch `checkpoint/chargen-dnd`. `[x]` done, `[~]` in progress. Ticket 1 wires
the constraint scaffolding first; rows turn green as their feature tickets land —
every row green before the report.

## Key design decisions (bound by the docs; details agent-decided)

- `engine_core::Ruleset` — object-safe trait, log in / views out. Blanket
  `impl<S> Ruleset for Engine<S>`? No: the escape hatches need ruleset data,
  so each ruleset crate implements `Ruleset` on a small newtype
  (`Pf2eRuleset { engine, data, suggested }`) and delegates the engine ops
  to `Engine<S>` through an `engine_core::EngineOps` blanket helper.
  Escape hatches: `system()`, `rules_version()`, `supersedes()`,
  `shipped_versions_json()`, `license_lines()`, `name_slot()`,
  `class_slot()`, `level_of(log)`, `next_level(log)`, `advance_slot(level)`,
  `advance_option(level)`, `is_advance_slot(slot)`, `suggested_builds()`,
  `text_fill(slot)` (mint fill-in for required text slots),
  `name_pool_key(log)` (the ancestry/species record id for name pools).
- Each ruleset crate exposes `pub fn embedded() -> Arc<dyn Ruleset>` (its
  `include_str!` rules data, parsed once via `OnceLock`).
- Server and WASM: two-arm selector `fn ruleset_for(system) ->
  Option<Arc<dyn Ruleset>>`; no registry crate.
- Rules data: `rules-data/pf2e/` (moved byte-identical) and
  `rules-data/dnd5e/`; each with manifest, shipped-versions, attestation,
  denylist. `manifest.system` read and asserted.
- Campaign declaration: `<data-dir>/campaign.json` `{schema_version:1,
  system}`; `Store` owns it (read at open; declare = temp + fsync +
  hard_link + unlink temp; change = temp + fsync + rename; only while
  empty per the architecture's definition). Routes: `GET /api/campaign`,
  `POST /api/campaign` (declare/change). `App` holds every embedded ruleset;
  `store.system()` picks. Undeclared + characters → PF2e inferred, never
  written; undeclared + a file naming another system → missing-declaration
  problem, no inference.
- Character doc schema v5: `system: Option<String>` (absent on pre-slice
  files → from a registered pin prefix, else PF2e). Mismatch vs campaign or
  vs registered prefix → `RosterProblem` "refused in place", file untouched,
  never loaded/written/moved (new `ParsedDoc::WrongSystem`-style branch in
  the store's load; `Store::load` returns a typed refusal).
- Per-ruleset `KnownVersions` (from the active ruleset's manifest +
  shipped-versions); `--extra-known-versions` file keyed by system.
- WASM: `engine_request(system, request)`.
- Campaign view: `CampaignView { declared: bool, system: Option<String>,
  games: Vec<GameOption{id,name}>, license_lines: Vec<String> }`. Roster view
  loses `license_notice` (moved to campaign view) — UI reads the campaign
  view first.
- 5.5e slots (crate `ruleset-dnd5e`, ids `dnd5e.*`): class, background,
  background.increase (Single, 7 enumerated distributions),
  species (+ species.skill, species.feat for Human), scores.method (Single),
  scores.assign (Multi{6}, options grouped per ability via OptionView.group,
  hint `one-per-group`), class.skills (Multi{2}), class.style (Single),
  class.masteries (Multi{3}), equipment (Single: package A / B / gold),
  details.name, details.description; level.N.advance; level.3.subclass.
  Steps: class, origin, scores, class-choices, equipment, details, level-2,
  level-3 (+ never-live advance steps).
- Sheet sections (5.5e): Ability Scores, Combat, Saving Throws, Skills,
  Attacks, Features, Equipment.

## Tickets

- [~] 1. Constraints wiring: DONE — layering allowlist (+ruleset-dnd5e edges,
  HTTP-client ban for server/wasm), per-crate purity/kind/LEVEL scans,
  engine-core/types no-system-literal scan, server/wasm no-slot-parsing scan,
  types `system` field only on the campaign view (+ declare request), UI
  system-blind scan (system ids, ability names, one wasm file), rules_data +
  attestation per system directory (PF2e attestation keys moved under
  `source`), `checks/campaign.rs` (declaration rows, system-before-version,
  v4/v6 schema, SIGKILL declare, attribution). PENDING (need the 5.5e crate):
  class_isolation per system, version_guard per-ruleset rows, 5.5e goldens /
  sweep / clone / crash / ability machinery / quick-build refusal / perf /
  bundle size / e2e.
- [x] 2. Boundary: `Ruleset` trait in engine-core; PF2e implements it +
  `embedded()`; rules-data moved to `rules-data/pf2e/`; server refactored to
  `Arc<dyn Ruleset>` (no `ruleset_pf2e::` in routes/version); per-ruleset
  KnownVersions (extras keyed by system); checks/reference-check paths updated;
  wasm selector + `engine_request(system, req)`; all existing tests green.
- [x] 3. Campaign declaration + schema v5: store-owned declaration (hard-link
  create-exclusive, rename change-while-empty, root temp sweep), declare /
  campaign routes, campaign view (+ `RosterView.quick_build: Option<ClassOption>`,
  `license_notice` moved to the campaign view), undeclared refusals and roster
  shell, `system` field + fixup from a registered pin prefix, refusal in place
  (`StoreError::Refused` → 422), verify prints CAMPAIGN problems.
- [x] 4. ruleset-dnd5e crate + rules-data/dnd5e (SRD 5.2.1 subset): species
  (Human, Dwarf, Goliath, Halfling), backgrounds (4), origin + fighting-style
  feats, Fighter (styles, masteries, packages A/B/gold), all SRD weapons and
  armor, advancement + Champion; derive_sheet; 13 crate tests. Random mint:
  `Ruleset::mint_pin` (5.5e pins the standard array) + group-aware shuffle.
- [~] 5. reference-check `--system dnd5e`: SRD source fetch (pinned sha256),
  5.5e comparator, per-system attestation with a `source` block; PF2e
  attestation re-shaped (keys moved under `source`) without regeneration.
  (subagent running)
- [~] 6. UI: DONE — campaign view fetch + choose-game screen; roster label +
  license lines; `one-per-group` editor; game-free boost copy; façade passes
  the system id; quick build only when the roster names a class;
  `campaign.spec.ts`. PENDING: `dnd.spec.ts` 5.5e walks (subagent running).
- [ ] 7. Checks: every 5.5e row green (goldens, sweep, clone, crash, api
  authority, persistence, version guard, ability machinery, perf, size).
- [ ] 8. Report `.checkpoints/run/chargen-dnd/report.md` with the
  boundary-bends section.
