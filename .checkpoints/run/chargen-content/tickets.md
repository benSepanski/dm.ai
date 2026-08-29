# chargen-content — ticket plan

Contract: `.checkpoints/specs/chargen-content.md` (0ff34ff671f7) +
`.checkpoints/architecture/chargen-content.md` (42a98c4f6845). Work on
branch `checkpoint/chargen-content`. Update states here as work lands;
commit this file with the work. States: [ ] open, [~] in progress, [x] done.

- [x] **T1 — constraints base** (architecture table, rows that can be green
  now): layering-allowlist edit admitting the `reference-check` crate
  (skeleton bin, edges = ruleset-pf2e + types, nothing depends on it);
  reserved-noun denylist lint + `rules-data/denylist.json` (seeded from
  research: First World, Golarion deity/city nouns) with self-exemption;
  source-book allowlist = {Pathfinder Player Core};
  `rules-data/shipped-versions.json` seeded with pf2e-pc.0.1.0's 111 IDs +
  lint (current version present, prior IDs resolvable, lineage contiguous);
  storage schema v2 (DecisionSource::Suggested; v1 read-accepted, upgraded
  on write, never on load; v3 refused) + persistence-test rows; gitignored
  ground-truth cache path + absence test. CI stays green at this commit.
- [x] **T2 — engine/ruleset machinery** (spec req 2+3, bounded list): new
  Effect variants (save/Perception proficiency override; ranged unarmed
  attack field; fist replacement); prereq kinds attribute-threshold +
  trained-in-skill (evaluable, greying with reasons); versatile-heritage
  support (heritage `ancestry: null`, heritage-step union, ancestry-feat
  catalog union); background sub-choice slot + player-named-Lore slot +
  choice-dependent grants (Hold Mark, Gnome Obsession, Scholar pattern);
  language chooser (Int-modifier dynamic count + heritage/feat bonuses) +
  sheet languages line. Unit tests per validator/effect.
- [x] **T3 — data: ancestries + heritages + ancestry feats.** Gnome,
  Halfling, Leshy, Orc complete (stats, languages lists, heritages ×~27,
  L1 feats ×~33); Aiuvarin + Dromaar + their L1 feats (~5); language lists
  added for the four slice-1 ancestries. Greyed-with-reason records for
  cantrip-dependent options. Noun-scrub applied (4 gnome records; rename
  First World Magic). All records lint-clean.
- [x] **T4 — data: backgrounds + general/skill feats.** 34 new backgrounds
  (39 total; Raised by Belief excluded), sub-choices modeled not flattened;
  9 new general feats (14 total); 53 skill-feat records; background
  skill-feat grants become resolvable IDs.
- [x] **T5 — data: equipment.** All common PC1 weapons (~65 incl.
  ammunition), 13 armors, 4 shields (Buckler, Tower Shield added), common
  adventuring gear + assistive items (~140). Categories preserved for UI
  grouping. No uncommon weapons, no services.
- [x] **T6 — reference-check tool + attestation.** Fetch pinned Foundry
  pf2e tag (content-hash-verified cache, gitignored); match by
  publication-partition + normalized name + override map; per-record
  per-field verdicts; hash-bound waivers (scrubs, kit, known quirks);
  write `rules-data/attestation.json`; offline `checks/attestation.rs`
  (coverage both ways, zero unwaived, per-record hash recompute, schema
  admits no ground-truth values, CI-never-invokes-tool scan). Run tool,
  fix every real mismatch, commit attestation.
- [x] **T7 — version bump + guard.** Manifest → pf2e-pc.0.2.0 (+
  shipped-versions entry); load-time status (current/older-known/unknown),
  computed never written; replay compare (identical / divergent /
  replay-error); roster flags + explicit re-pin, accept (records prior
  values), keep-old routes; draft resolve → re-validate → cascade reopen;
  `verify` distinguishes older-known vs unknown; `checks/version_guard.rs`
  fixtures (all three cases); no-rewrite-on-load fixture with flag.
- [x] **T8 — quick build.** `suggested_build` block on class record
  (ordered candidate IDs; kit option + key attribute anchors); planner in
  engine-core (walk open slots in unlock order, resolve vs folded state,
  append); atomic server route (create-and-fill + fill-remaining),
  request-scoped idempotency, wizard-write under version guard;
  `checks/quick_build.rs` (folds clean + finalizable; fill-remaining
  preserves confirmed entries byte-identical, partial result names
  remaining slots); api_authority + crash-harness extensions; UI: roster
  action, fill-remaining action, "suggested" badges flipping on edit.
- [ ] **T9 — UI breadth.** Text filter on option lists ≥ threshold;
  equipment step category grouping + filterable shop; badge/greying
  affordances verified at 39-background/53-skill-feat/full-gear scale;
  Playwright scenarios for the spec's Walks 1–10 where automatable.
- [ ] **T10 — goldens + budgets + report.** One hand-verified golden per
  ancestry + versatile-heritage + background-sub-choice + quick-build
  goldens; fold/suite/warm-rebuild budgets green (levers per architecture
  if needed, ceiling 12s pre-authorized); measure + record suite/rebuild/
  WASM/projection-payload deltas; finalized per-file counts recorded;
  write `report.md`, commit, present.
