# Level-up — Fighter and Wizard through level 3 — report

Checkpoint: `level-up` · Branch: `checkpoint/level-up` · Status: delivered

## What changed and why

Characters can now level. A finalized Fighter or Wizard's sheet offers
**Level up to N** (to 2, then 3 — the level-3 world's cap; at 3 the button
gives way to "Higher levels are coming"). Tapping it opens the same guided
dialog you already know — checklist, cards, confirm-per-choice durability,
resume — showing only the pending level: an **"At level N you gain…"**
panel (HP, proficiency changes, fixed features like the Fighter's Bravery,
derived as a before/after diff — nothing hand-authored), the level's choice
slots (level 2: class feat + skill feat; level 3: general feat + skill
increase; a Wizard also adds two spells per level and opens rank-2 spells at
3), a **"Changes so far"** sidebar, **Finalize level N**, and **Abandon
level N** (through the existing clear dialog, listing exactly what it
discards). Mid-level-up the character is still its old level everywhere —
roster, sheet, clone — until the level finalizes in one atomic write.

The mechanics, per the architecture:

- **Level is derived, never stored.** Advancing is itself a decision in the
  log (`pf2e.level.N.advance`); the fold counts advances. The ruleset's
  compile-time level constant is gone; every level-dependent number
  (proficiency bonus, HP per level, spell slots, cantrip rank) reads the
  derived level. Every pre-slice log has zero advances and folds to
  byte-identical level-1 sheets (all prior goldens untouched, green).
- **The pending level is the log's un-finalized tail** behind a storage-
  private `finalized_through` marker (schema v3 → v4; v1–v3 files load
  untouched, the marker fixed up on read). One accessor — the part of the
  log the stored sheet reflects — is the only thing `verify`, version
  status, version accept, and clone ever fold. Finalize moves marker and
  sheet together; abandon truncates to the marker; versions stay monotonic
  across abandon.
- **One dialog machine, by construction.** Steps carry a liveness
  predicate; the projection emits only live steps (creation steps at level
  1, the pending level's step while leveling). The wizard component has no
  phase or level branch — a source scan enforces it — and the app router
  simply hands the pending level's draft view to the unchanged wizard.
- **Every wizard write is guarded**: a finalized character with no pending
  level refuses (before any idempotency shortcut, so a stale retry can never
  answer "confirmed" against a finished level); nothing below the marker
  can be confirmed, amended, or cleared (cascades included); an advance
  enters only via the level-up route; fill-remaining refuses during a level.
  Leveling is a wizard write under the version guard: a flagged character
  resolves first; abandon is always permitted; kept-old and pre-slice pins
  cannot level.
- **Rules data 0.4.0**: class advancement blocks (Fighter 3 → Bravery, Will
  to expert), the Wizard's spells-per-day table, Fighter and Wizard level-2
  class feats, level-2 skill feats (expert-gated), level-3 general feats,
  and a rank-2 arcane spell subset (attack, saves, utility, per-rank and
  fixed-rank heightening) — attested against the pinned Foundry snapshot
  with zero mismatches. The reference-check tool had hardcoded "fighter" as
  every class feat's required trait; it now derives the trait from the
  record's own class.
- **The random-mint sampler levels characters in the test harness**
  (mint → advance → sample the level's slots → finalize, to the cap, across
  a seed sweep) — the spec's satisfiability proof and cross-level
  prerequisite watch. No route, no UI.

Also in this branch, at your request: `campaign/` and
`campaign.backup-pre-0.2.0/` are gitignored and the three tracked campaign
files untracked (they stay on disk).

## How to verify

```bash
cargo run --release -p server -- --data-dir ./campaign
```

1. **The first level-up.** Open Torvald (or quick-build a Fighter and
   finalize him), tap **Level up to 2**. The gains panel lists what level 2
   brings — hand-check: HP grows by class HP + Con, every proficiency-based
   number by +1, Class DC +1. The checklist shows the two open slots. Pick a
   class feat and a skill feat, watch "Changes so far", **Finalize level 2**:
   the sheet reads Fighter 2 and offers **Level up to 3**.
2. **Straight to 3.** Mint a random Fighter, finalize, level twice
   back-to-back. At 3 the button is gone; the note says higher levels are
   coming. Hand-check Fighter 3 against Archives of Nethys: Will save now
   expert (Bravery listed under Features), the skill increase's skill at
   expert (+7 + attribute), HP = ancestry + (class + Con) × 3.
3. **The wizard's new rank.** Level Sylvenne to 2, then 3: each level adds
   two spells through the familiar picker (rank-2 spells pickable at 3,
   grouped by rank); the sheet shows Rank 1 slots 4 and Rank 2 slots 3
   (table + school slot), cantrips heightened to rank 2, spell DC/attack
   +2 from level 1; the prepared column still points at the table.
4. **Illegal picks at the card.** In the level-2 skill-feat card, Powerful
   Leap / Nimble Crawl / Intimidating Prowess are greyed with "requires
   expert in …" — nobody is expert at 2. Leave the skill-feat slot empty:
   Finalize level 2 stays disabled with the gap on the checklist. Then take
   the level-3 skill increase to expert in Athletics and see the sheet's
   Athletics line say so.
5. **The changed mind.** Mid-level, Change… the confirmed class feat: the
   cascade prompt names only level-2 choices; nothing outside the level
   moves.
6. **The retreat.** Abandon level 2: the dialog lists "Advance to level 2"
   and the picks so far; afterwards the sheet is Fighter 1 and the file
   shows no trace beyond a bumped version counter.
7. **The crash.** `kill -9` mid-level-up, restart: the roster says
   "Leveling up — resume (level 2 — step 1 of 1 — Level 2)" and still shows
   Fighter 1; resume lands with every confirmed pick intact.
8. **The fork first.** Clone Torvald mid-level-up: the clone resumes the
   pending level at the same spot; level the clone down another path; the
   original never moves. Clone a finalized Fighter 2 and level the clone to
   3 — the original stays at 2.
9. **Nothing else moved.** Open a pre-slice character (sheet unchanged, a
   Level-up button now offered); create a fresh level-1 character through
   the unchanged wizard; quick build, random mint, and clone behave as
   before at level 1.
10. **The skeptical inspection.** Open a leveled file: `finalized_through`
    plus the level's decisions appended in order, the advance first. Set
    `finalized_through` to the log length by hand mid-level and run:

```bash
cargo run --release -p server -- --data-dir ./campaign verify
```

    It reports DIVERGED; hand-edit a pending decision and it reports
    TAIL-BROKE; abandoning the level recovers.
11. **Intent checks.** Does leveling *feel* like the same dialog — same
    nav, cards, confirm, resume — rather than a second UI? Is "At level N
    you gain…" the at-the-table moment you wanted?

## Constraints now enforced

Every row of the architecture's table is green in the repo's own tooling:

| Rule | Lives at |
|---|---|
| Level is derived: no `const LEVEL`/`LEVEL:` in the ruleset; `finalized_through` absent from the wire types; fold level = 1 + advances (fixtures + leveled goldens); every level boundary is a finalizable prefix | `checks/crate_layering.rs::level_is_derived_and_the_marker_is_storage_private`, `checks/replay.rs::level_equals_one_plus_the_advance_decisions` |
| Prefix invariant + verify: stored sheet = fold(prefix); tail folds; tail head is exactly one advance; tampered pending decision / moved marker / malformed tail are `verify` findings (marker past the log = quarantine) | `checks/persistence.rs::verify_reports_tampered_pending_levels_and_malformed_tails` |
| Prefix immutability: prefix + sheet bytes unchanged across start, tail confirms, load, abandon; abandon = pre-start file modulo version; finalize moves marker + sheet together; old sheet authoritative on roster and views | `checks/persistence.rs::pending_levels_never_touch_the_finalized_prefix_or_sheet` |
| Pre-slice logs fold to level 1 byte-identically | all slice 1–4 goldens in `checks/replay.rs` (untouched, green) |
| Atomic transitions under SIGKILL (start, tail confirm, abandon, finalize-pending) | `checks/crash_harness.rs::level_transitions_under_sigkill_are_prior_or_next_state` |
| Route authority: idempotent second start; start on draft / at cap refused; raw advance, second advance, below-marker confirm/amend/clear, fill-remaining during a tail refused; confirm after abandon/finalize refused before the ID-present path; versions monotonic | `checks/api_authority.rs::level_up_routes_refuse_everything_below_the_marker_and_out_of_order`, `checks/confirm_idempotency.rs::replayed_level_starts_and_finalizes_append_nothing` |
| Leveling under the version guard: flagged → 409 with the flag, nothing written; leveling file pinned older flags on load byte-identical; re-pin over a tail moves only the pin; abandon on flagged succeeds; kept-old cannot level | `checks/version_guard.rs::leveling_is_a_wizard_write_under_the_version_guard` |
| Schema v4: v3 finalized AND v3 draft fixtures load untouched, marker fixed up, upgrade on first write | `checks/persistence.rs::v3_documents_read_untouched_with_the_marker_fixed_up` (+ existing v1/v5 rows) |
| Clone of a leveling source: fidelity, marker equal, sheet = fold of prefix, verify-clean, independent tail | `checks/clone.rs::cloned_leveling_character_keeps_its_pending_level_independently` |
| Leveled seed sweep (test-only random leveling): every class levels to the cap, empty checklist per level, a prerequisite-bearing level-up feat taken | `checks/random_mint.rs::minted_characters_level_randomly_to_the_cap_across_seeds` |
| Gains are derived: gains = diff(stored, fold through the advance); deltas = diff(stored, fold of the whole tail) — judged against the checks' own diff | `checks/replay.rs::gains_and_deltas_are_the_sheet_diff_between_folds` |
| Golden coverage: Fighter 3 (Torvald: Lunge, Titan Wrestler, Toughness, Athletics increase) and Wizard 3 (Sylvenne: Conceal Spell, Arcane Sense, Fleet, Arcana increase, rank-2 spells), hand-verified | `checks/replay.rs::golden_torvald_fighter_3`, `golden_sylvenne_wizard_3` |
| One dialog machine (structural): no LevelUp* file/export in `ui/src`; `Wizard.tsx` free of phase/level branch tokens; gains render via the shared `SheetDiffTable` | `checks/crate_layering.rs::ui_has_no_level_specific_wizard` |
| Level-up story walks under the layout sweep | `ui/e2e/level-up.spec.ts` (6 walks) |
| Advancement data: contiguous 2..=3 for every class; feature IDs namespaced; caster slot table through the cap; level-2/3 catalogs present; feature names join the class-isolation literal scan | `checks/rules_data.rs::advancement_tables_reach_the_shipped_cap`, ruleset integrity, `checks/class_isolation.rs`, `checks/attestation.rs` |
| Level-3 fold < 5 ms | `checks/perf.rs::fold_of_level_3_logs_is_under_5ms` |

Deliberately unenforced items stand as the architecture recorded them.
The structural "only two functions write finalized state" claim is visible
in the route table: `finalize` (marker + sheet together) and
`abandon_level` (truncate); the version-guard routes touch pin and sheet
only, through the prefix accessor.

## Decisions made inside the contract

- **Marker on read**: absent (pre-v4) → 0 for drafts, log length for
  finalized; a marker of **0 on a finalized file reads as unset** (the
  creation prefix is never empty, so 0 can only be a hand-flipped draft —
  the version-guard fixtures do exactly that). A marker past the log's end
  is quarantined as structural corruption.
- **"Finalized prefix" accessor semantics**: for a creation draft it is the
  whole log (a draft's stored sheet tracks every confirm); for a finalized
  character, the prefix. Clone and verify judge exactly that.
- **The advance slot lives in a step that is never live** — appendable by
  the route, never a card. The gains panel therefore rides above the
  level's step rather than as a separate "gains step": same content, one
  fewer nav entry (the architecture described a gains step; the panel is
  the presentation of it).
- **Level rhythm is code, features are data**: which slots a level grants
  (class+skill feat at even levels, general feat + skill increase at odd)
  is the published class-progression shape, registered once in the ruleset;
  the class-specific part (fixed features, spell slots) is data.
- **Skill feats** are the general-feat records whose IDs start with
  `feat.skill.` (the catalog's existing convention); a `skill_rank`
  prerequisite kind ("expert in Athletics") was added because every
  level-2 skill feat in Player Core requires expert — so at level 2 they
  all show greyed with the reason, and only level-1 skill feats are
  takeable (which is the printed rule).
- **No Fighter level-2 class feat in Player Core has a prerequisite** (the
  Foundry ground truth says so for all eleven). The spec's "at least one
  with a prerequisite" is satisfied by the level-2 *skill-feat* slot
  (trained-in / expert-in prerequisites, judged against the leveled state)
  and the level-3 general-feat slot (Feather Step: Dex +2; Fast Recovery:
  Con +2); the goldens take Titan Wrestler (trained Athletics) and Arcane
  Sense (trained Arcana). A level-2 pick that *enables* a level-3 pick does
  not exist in this content — the cross-level interaction that does exist
  is creation → level-2 (skill prerequisites) and boosts → level-3
  (attribute prerequisites). Noted so the What-Ben-checks walk expects the
  right thing.
- **Fill-remaining is hidden during a pending level** (rather than a
  visible button that always refuses): the existing rule "a dead control
  the player can't explain is a banned state" won; the route still refuses
  typed if called.
- **Spellbook growth** is one `pf2e.level.N.spellbook` slot (two picks,
  mixed-rank options grouped by rank), never a grown count on the level-1
  picker; the sheet merges the book per rank.
- Source references for the new records carry Player Core page numbers
  from memory and Archives of Nethys *search* URLs (not record IDs): the
  mechanical fields are what the attestation verifies against Foundry; the
  URLs are working links, not fabricated IDs.
- Two `clippy` style items and one over-strict clone check (drafts) were
  caught by the suite and fixed; the reference-check tool's hardcoded
  "fighter" trait was a latent slice-2 bug this slice's data exposed.

## Review feedback folded

- **Ben (first review, 2026-09-05): "the table at the top is confusing — no
  explanations for why."** Folded: every sheet diff now carries the changed
  entry's own detail line as a `why` (an additive, optional field on
  `SheetDiff` — the version-review table gains it for free), the gains
  table shows it as a **Why** column ("8 ancestry + (10 class + 2 Con) × 2
  levels", "6 expert + 2 Con", "4 trained + 2 Wis"), the panel opens with
  one sentence saying these change on their own before any choice, and the
  "Changes so far" sidebar only appears once a choice changed something
  beyond the automatic gains (until then it merely repeated the panel).
  The gains property row compares the four value fields and treats `why`
  as presentation.

## Agent evidence

- Full workspace suite green: 27 test targets, 0 failures; warm wall time
  18 s against the 20 s ceiling (execution only, CI's measurement; the
  crash cycles were trimmed to hold it).
- `cargo fmt --check`, `cargo clippy --workspace --all-targets -D warnings`,
  `cargo deny check`: clean. `tsc`, `eslint`: clean; 44 UI unit tests green.
- All 39 Playwright e2e specs green (6 new level-up walks; every prior walk
  untouched except the version-bump fixture, which now fabricates a
  consistent v4 marker when it flips a draft to finalized).
- WASM bindings regenerated; parity test green.
- Attestation: 450 → 471 records, zero unwaived mismatches, zero stale
  waivers (four overrides added for shared-class wizard feats).
- Live visual verification: quick-built Fighter finalized, Level up to 2
  opened the gains panel (HP 20→32, all proficiency-based values +1, each
  with its formula in the Why column after the review fold), the single
  Level 2 step with class-feat and skill-feat cards, Finalize gated by the
  checklist, Abandon offered.
- HTTP smoke of the full flow before the check rows were written: level 1 →
  2 → 3 with the gains diff, guard refusals (below-marker, raw advance,
  fill-remaining), abandon, cap refusal, and a v4 file with marker = log
  length at the end.

## Complaints logged

None — no harness friction this checkpoint.
