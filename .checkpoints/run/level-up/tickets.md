# level-up — ticket plan

Docs: `.checkpoints/specs/level-up.md`, `.checkpoints/architecture/level-up.md`.
Branch `checkpoint/level-up`. `[x]` done, `[~]` in progress. Ticket 1 wires the
constraint scaffolding first; rows turn green as their feature tickets land —
every row green before the report.

## Key design decisions (bound by the docs; details agent-decided)

- Level lives in `Pf2eState.level` (default 1), set only by the advance
  slots' `apply` (which refuses out-of-order advances); every `LEVEL` use in
  derivation reads `state.level`. Advance slot IDs: `pf2e.level.{N}.advance`,
  registered in a new `advancement` kind module, in a step that is never
  live (appendable-but-unrendered). The pending level's rendered step is
  `level-{N}`, live iff `state.level == N`; creation steps live iff
  `state.level == 1`.
- Per-level slots by kind module: feats.rs `pf2e.level.{N}.class-feat`,
  `pf2e.level.{N}.skill-feat` (skill feats = general-feat records whose ID
  is `feat.skill.*`, the file's existing convention), `pf2e.level.3.general-feat`;
  skills.rs `pf2e.level.3.skill-increase`; spells.rs `pf2e.level.{N}.spellbook`
  (Multi{2}, mixed-rank options grouped by rank). Prerequisite kind `feat`
  added (has-feat-by-ID) for cross-level enablement.
- Storage: `finalized_through: Option<usize>` on the doc (v4), fixed up on
  read (draft → 0, finalized → log length); `Loaded::finalized_prefix()` is
  the only thing verify / status / accept / clone fold.
- Routes: `POST /api/characters/{id}/level-up` (start; idempotent),
  `POST /api/characters/{id}/level-up/abandon`; finalize reuses the finalize
  route. `DraftView.level_up: Option<LevelUpView{level, gains, deltas,
  pending}>` carries the gains diff, finalize deltas, and the abandon
  preview. `CharacterView::Leveling{id, sheet, draft}`;
  `CharacterView::Finalized.next_level: Option<u32>`;
  `RosterCharacterState::Leveling{resume_label}`.
- Cap = highest level in the class's advancement block (data); lint requires
  every shipped class to define levels 2..=3.
- UI: App router sends `leveling` to the unchanged `<Wizard>`; the wizard
  renders a gains panel and finalize deltas through a `SheetDiffTable`
  extracted from VersionFlag, and an Abandon button through the existing
  `ClearConfirmDialog` fed by `draft.level_up.pending`. No phase/level
  branch tokens in Wizard.tsx (scanned).

## Tickets

- [ ] 1. Constraints wiring: token scans in `checks/crate_layering.rs`
  (`const LEVEL`/`LEVEL:` absent from ruleset src; `finalized_through`/level
  fields absent from types; ui `LevelUp*`/phase tokens); leveled sections
  stubbed in `checks/random_mint.rs`, `checks/clone.rs`, `checks/persistence.rs`,
  `checks/version_guard.rs`, `checks/api_authority.rs`, `checks/crash_harness.rs`,
  `checks/replay.rs`, `checks/perf.rs`, `checks/rules_data.rs`; `ui/e2e/level-up.spec.ts`.
- [ ] 2. engine-core: `StepRegistration` with liveness; `live_steps`;
  project emits live steps only and skips dead-step slots; `describe_decision`.
- [ ] 3. ruleset: `state.level`; LEVEL removed; advancement kind module +
  advance slots; per-level feat/skill-feat/general-feat/skill-increase/
  spellbook slots; skill ranks with increases; spell slot table by level;
  advancement blocks + cap; `feat` prerequisite kind; exports
  (`advance_slot_id`, `advance_level_of`, `level_cap`, `is_advance_slot`).
- [ ] 4. rules-data 0.4.0: advancement blocks (Fighter L3 Bravery with
  Will→expert effect), wizard slot table, Fighter/Wizard level-2 class feats,
  level-2 skill feats, level-3 general feats, rank-2 spells; lineage;
  attestation regenerated; existing goldens unchanged.
- [ ] 5. types: leveling views, LevelUpView, requests/outcomes.
- [ ] 6. server: schema v4 + marker fixup + prefix accessor; verify/status/
  accept/clone on the prefix; start/abandon routes; finalize-pending; wizard
  write guards (finalized-no-tail, below-marker, advance-slot, fill-remaining
  during tail, ordering); live-step resume labels; views + gains.
- [ ] 7. checks green: all rows of ticket 1 implemented for real.
- [ ] 8. UI: api.ts, App router + sheet Level-up button/cap note, Wizard
  gains/deltas/abandon, SheetDiffTable extraction, unit tests; bindings.
- [ ] 9. e2e level-up.spec.ts walks.
- [ ] 10. Gates: fmt, clippy -D warnings, deny, full suite (< 20 s),
  ui tests, e2e, bindings fresh.
- [ ] 11. Report.
