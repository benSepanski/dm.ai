# T8 — quick build: implementation notes

## The authored suggested build (dm.ai content, spec req 7 [call])

Lives as a `suggested_build` block on `class.fighter` in
`rules-data/classes.json` — ordered candidate option IDs per slot, plus one
text entry. Published anchors honored: the class kit (sword-and-board
option) and key attribute (Strength). Everything else is app-authored;
never presented as Paizo-published. No Paizo sample-build text was
consulted or copied.

The classic sword-and-board human fighter:

| Slot | Suggestion (first legal wins) |
|---|---|
| Ancestry | Human |
| Heritage | Skilled Human |
| Heritage skill chooser | Diplomacy (then Society, Stealth) |
| Ancestry feat | Cooperative Nature (then Haughty Obstinacy) |
| Ancestry free boosts (2) | Str, Con (list continues Wis, Dex) |
| Additional languages | Dwarven, Orcish, Goblin, Jotun (count is Int-driven; 0 for this build — slot hidden, candidates future-proof the block) |
| Background | Warrior (fixed skill/lore/feat — no sub-choices) |
| Background boost (choice) | Str (of Str/Con) |
| Background boost (free) | Wis (then Con, Dex) |
| Class | Fighter |
| Key attribute | **Strength** (published anchor) |
| Class feat | Sudden Charge (then Reactive Shield) |
| Class skill | Athletics (then Acrobatics) |
| Trained skills (3 + Int) | Acrobatics, Medicine, Survival (list continues Society, Stealth, Crafting, Nature) |
| Free boosts (4) | Str, Dex, Con, Wis (list continues Cha, Int) |
| Kit | **Fighter Kit + longsword and steel shield** (published anchor; falls back to the bare kit) |
| Equipment extras | none (empty candidates — legal) |
| Name | "Garrek Ironvale" (seeded only when the request carries no name) |

Final modifiers: Str +4, Con +2, Wis +2, Dex +1, Int 0, Cha 0.

**Design rule (doc-commented on `SuggestedBuild` in data.rs):** prefer
options that open no chooser chains; when a chosen option does open a
sub-slot (Skilled Human's skill chooser is the one case here), the block
MUST carry a candidates entry for that sub-slot. A slot the block cannot
parameterize simply stays open on the checklist.

## Planner (engine-core, generic)

`Engine::expand_suggestions(log, suggest, mint_id, source)` in
`crates/engine-core/src/engine.rs`:

- `suggest: Fn(&SlotId) -> Option<SlotSuggestion>` — the ruleset supplies
  content as `SlotSuggestion::Candidates(Vec<OptionId>)` or `Text(String)`;
  engine-core stays free of game vocabulary.
- Loop: fold → walk registrations in order → first open, required,
  undecided slot whose suggestion resolves gets appended through the
  normal validated `append` path (with `DecisionSource::Suggested`) →
  break, refold, repeat. Fixpoint when a full pass appends nothing.
- Candidate resolution per slot kind: Single = first candidate available
  in `options(state)`; Multi{count} = first `count` distinct available
  (count read from the kind at plan time — 3+Int, free-boost counts adapt);
  Text = the block's text; List = all available candidates.
- Never overwrites (occupied slots skipped; `append` also rejects);
  deterministic (registration order × candidate order, no randomness).
- Cannot-complete: the legal prefix is KEPT; `SuggestionPlan.unresolved`
  (typed `types::UnresolvedSuggestion { slot, label, reason }`) names each
  remaining open required slot and why (no entry / no legal candidate /
  the engine's structural refusal via a dry probe append).
- `Engine::unresolved_suggestions` is the standalone remainder computation
  (used by the idempotent-replay path without appending).

## Routes + idempotency

Both in `crates/server/src/routes.rs`; both are wizard writes under the
version guard (flagged draft → 409 with the flag), one engine transaction,
one temp-file → fsync → rename write.

- `POST /api/characters/quick-build` `{ request_id, name? }` → 200
  `QuickBuildResult { draft, unresolved }`. The character ID is derived
  from the request ID (`c-qb-<request_id>`), so **the file's existence is
  the durable idempotency marker**: a re-tap after a crash between save
  and ack loads the same file, returns the saved result, and appends
  nothing — no side table. The optional name seeds the name slot as a
  Player decision before expansion (the planner never overwrites it);
  otherwise the block's name text lands as Suggested. Result is a normal
  draft view: review state (cursor on the last step), `can_finalize`
  true, NOT finalized. Malformed request IDs (charset/length) → 422,
  nothing written.
- `POST /api/characters/{id}/fill-remaining` `{ request_id, version }` →
  `FillRemainingOutcome::Filled { draft, unresolved } | Conflict`.
  Expansion decision IDs are `{request_id}.{slot}`; idempotency is checked
  BEFORE the version (like confirm): any log decision carrying this
  request's prefix means the expansion committed — return current state,
  append nothing, even under the now-stale version. Saves only when the
  planner appended something. Finalized → 422; flagged → 409.
- Suggestion source: per-class maps resolved at startup
  (`ruleset_pf2e::suggested_builds`), selected by the log's class decision
  (`CLASS_SLOT_ID` re-export), falling back to the first class with a
  block.

## Integrity (data lint, `RulesData::check_integrity`)

Every class must carry a block; every entry names a known slot
(`mechanics::known_slot_ids()`); no duplicate slots; text XOR candidates;
every candidate resolves (record IDs incl. kit options, `attr.*`,
`prof.*`, `lang.*` against ancestry language lists, the no-kit sentinel).
`checks/quick_build.rs` adds the folds-clean lint through the real engine.

## Checks

- `checks/quick_build.rs` (new): folds clean on an empty draft (zero
  illegal, empty checklist, finalizable, all-Suggested, deterministic);
  fill-remaining preserves confirmed entries byte-identical (file-level
  prefix compare); blocked suggestions keep the legal prefix and name the
  remainder (Dwarf draft → heritage + ancestry feat unresolved, rest
  filled, zero illegal).
- `checks/api_authority.rs`: malformed quick-build/fill rejected + append
  nothing; quick build lands as a draft (never self-finalizes); fill on
  finalized → 422 byte-identical; fill on version-flagged draft → 409
  byte-identical (--extra-known-versions fixture pattern).
- `checks/confirm_idempotency.rs`: replayed quick-build request ID —
  same character, same version, same log, roster stays at one; replayed
  fill request ID appends nothing.
- `checks/crash_harness.rs`: quick-build cycles under SIGKILL at varied
  delays — none-or-all (file present ⇒ complete, review-ready), no torn
  files, re-tap rebuilds/returns and a second tap appends nothing.

## Gate results (2026-08-29)

- `cargo test -p checks`: all green EXCEPT
  `attestation::attestation_covers_every_record_and_hashes_are_current`,
  which fails on `class.fighter` — the hash-recompute forcing function
  firing on this ticket's additive `suggested_build` edit to
  `rules-data/classes.json`, exactly as designed. The attestation
  regenerates (concurrent reference-check work) after T8 lands.
  version_guard 8/8, persistence 6/6, crash 2/2, idempotency 3/3,
  authority 4/4, no_rewrite 2/2, replay 6/6 (+1 ignored slow), rules_data
  5/5, quick_build 3/3, layering 7/7, perf 1/1.
- `cargo test -p engine-core` 17 passed (3 new planner unit tests);
  `-p ruleset-pf2e` 30 passed (new suggested-build integrity negatives;
  synthetic dataset gained a minimal block since integrity now requires
  one per class).
- `cargo fmt --all --check` clean; clippy `-D warnings` over engine-core,
  ruleset-pf2e, server, types, checks (all targets) clean.
- Bindings regenerated (`wasm-pack build … --no-pack`, pkg .gitignore
  removed); new wire types present in `wasm.d.ts`. `ui`: tsc clean,
  eslint clean, vitest 20/20 (2 new badge tests). `ui/dist` rebuilt
  (committed dist is what the server embeds).

## UI

Roster: "Quick build a Fighter" button beside create (optional working
name shared with the create field). Wizard: "Fill remaining with
suggestions" above Finalize (disabled once nothing is open); outcome
notice names unfilled slots, checklist carries the detail. SlotCard:
`suggested` badge driven purely by `decision.source`; editing re-confirms
through the existing confirm/amend path as Player, so the badge flips off
without new machinery.
