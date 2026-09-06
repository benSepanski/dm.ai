# chargen-dnd — the D&D 5.5e Champion Fighter, 1 to 3 — report

Checkpoint: `chargen-dnd` · Branch: `checkpoint/chargen-dnd` · Status: delivered

## What changed and why

The app now plays two games. A campaign directory declares which one
(`campaign.json`, written once when the campaign is empty), and the
server, the browser engine, and the checks resolve that game to one of
two rulesets behind a single trait. The D&D 5.5e Fighter (SRD 5.2.1, CC BY
4.0) is created at level 1 through the same guided dialog Pathfinder uses
— class, origin (background with its ability-score distribution, then
species with its own choices), ability scores by Standard Array or Point
Buy, class choices, equipment, details — and leveled to 3 through the
same level-up machinery: level 2 is the machinery's first empty level
(gains only, finalize at once), level 3 opens the Fighter Subclass slot
whose catalog is the subclass records, with the Champion shipped.

The cross-system stress test the roadmap planned came out this way:

- **The core held.** engine-core and the wire types gained no game word.
  The PF2e ruleset crate changed by addition only: the trait
  implementation and its embedded data (`crates/ruleset-pf2e/src/ruleset.rs`,
  two lines in `lib.rs`). Every PF2e golden, fixture, and story is
  untouched and green.
- **The ruleset boundary became a contract.** `engine_core::Ruleset` (log
  in, views out) with `EngineOps` implemented once over the generic engine;
  each ruleset answers only the escape hatches the server used to get from
  PF2e free functions (name and class slots, level of a log, next level,
  advance slot and option, suggested builds, mint fill-ins, name-pool key,
  and a mint pin). Server and WASM hold a two-arm selector; no registry.
- **Files know their game.** Character documents are schema v5 with a
  `system` field; older files infer it from a registered pin prefix, else
  PF2e, and gain it on their next write. A file from another game is
  refused in place — reported on the roster, never loaded, written, or
  moved. Known versions are per ruleset; the system check runs first.
- **Rules data is per system**: `rules-data/pf2e/` (moved byte-identical)
  and `rules-data/dnd5e/` (103 records: 4 species, 4 backgrounds, 8
  feats, the Fighter, the Champion, 18 skills, 2 score methods, 65
  equipment records covering every weapon and armor in the SRD). Every
  shipped license paragraph shows on every campaign — attribution follows
  the binary.
- **The UI learned two things and no game**: a campaign view fetched
  first (choose-game screen, roster label, license lines) and one new
  presentation hint, `one-per-group`, rendering a select per option group
  for the ability-score assignment. The boost editor's PF2e copy became
  generic. No system id or ability name appears in shipped UI source.

Rolled ability scores were split into the next slice (`dnd-dice`) at spec
time; this slice makes one claim, the boundary holds, and the ability-
score method slot is data so a third method appends without redesign.

## Where the boundary bent (spec req 7)

Every "one system" assumption the survey found, and what replaced it:

| Assumption | Where it lived | What replaced it |
|---|---|---|
| One engine type, `Engine<Pf2eState>`, held by concrete type | `server::App`, `wasm`, `version.rs`, every check | `Arc<dyn Ruleset>` resolved per request from the campaign; `EngineOps` blanket impl; per-system checks |
| PF2e free functions as the server's escape hatches (`next_level`, `slot_level_advance`, `advance_level_of`, `CLASS_SLOT_ID`, `NAME_SLOT_ID`, `ANCESTRY_SLOT_ID`, `suggested_builds`) | `routes.rs`, `main.rs` | Trait queries: `level_of`, `next_level`, `advance_slot`, `advance_option`, `is_advance_slot`, `class_slot`, `name_slot`, `name_pool_key`, `suggested_builds`, `mint_pin` |
| The advance-slot string parsed by the server; the advance option id minted server-side | `routes.rs` (five sites), `main.rs` verify | `is_advance_slot` / `advance_option`; a scan bans slot-id literals and crate paths in routes |
| A bare `"pf2e.details.name"` literal | `routes.rs` (two sites) | `name_slot()` |
| `LORE_TOPICS` and ancestry-keyed name pools in the server | `routes.rs` | `text_fill_candidates` / `name_pool_key`; pools keyed by record id (ancestry or species) |
| One flat `rules-data/` with eleven hard-coded file names in four places | `main.rs`, `wasm`, `checks/lib.rs`, `data.rs` | `embedded()` per ruleset crate; `rules-data/<system>/`; lints iterate directories |
| One `KnownVersions`, one current version; extras file unkeyed | `version.rs` | Per-ruleset sets keyed by system; extras keyed by system; an unshipped key is a startup error |
| No system on any file; the campaign had no game | `CharacterDoc`, data dir | `campaign.json` declaration; schema v5 `system`; refuse-in-place |
| `RosterView.license_notice` = the PF2e manifest's notice | roster | `CampaignView.license_lines` = every shipped ruleset's paragraphs |
| "Quick build a Fighter" hard-coded | `Roster.tsx` | `RosterView.quick_build: Option<ClassOption>`; absent where the rules publish no build |
| The boost editor's "Boost" copy | `SlotCard.tsx` | Generic "Pick N" / "— choose —" copy; the ruleset's labels carry the game words |
| `ALLOWED_SOURCE_BOOKS`, `RECORD_FILES`, the ORC-only license tag, the denylist non-empty rule | `checks/rules_data.rs` | A per-system table (book allowlist, license tag, notice text); record files discovered per directory; an empty denylist is allowed for a license that reserves nothing |
| Attestation at `rules-data/attestation.json` with Foundry keys at the top level | `checks/attestation.rs`, `reference-check` | Per-directory attestations under one schema with a `source` block (`kind`, `sha256`, …); the PF2e file restructured by hand, no regeneration |
| Kind-module list, purity list, `const LEVEL` scan, class-isolation names — all PF2e's | `checks/crate_layering.rs`, `class_isolation.rs` | Per-crate lists; per-system name sets |
| Random mint's sampling: a flat shuffle over every option | `routes.rs` | Group-aware candidate order (one per group, distinct labels first) plus a ruleset `mint_pin` (5.5e pins the standard array) |

Two bends deliberately not taken: the PF2e boosts editor keeps its
positional selection encoding (a finalized-fixture fact), and PF2e keeps
its own kind-module taxonomy rather than sharing 5.5e's.

## How to verify

Two data directories: your existing PF2e campaign, and a fresh one.

```bash
cargo run --release -p server -- --data-dir ./campaign
```

1. **Two campaigns, one app — the PF2e side first.** Open your existing
   campaign. No question is asked; the roster header says it plays
   Pathfinder 2e "by default" (the directory predates declarations), and
   `campaign.json` is NOT written. Torvald and Sylvenne open unchanged;
   create a fresh character through the unchanged wizard; level a PF2e
   character to 3. The footer shows both notices (ORC and the SRD 5.2.1
   attribution).
2. **The second campaign.** Stop the server and start it on a fresh
   directory:

```bash
cargo run --release -p server -- --data-dir ./campaign-5e
```

   The app asks which game the campaign plays; pick D&D 5.5e. The roster
   says so. Tap Create, name "Brannock", and walk the sequence: Fighter;
   Soldier — distribute its increase (+2 Strength, +1 Constitution) and
   watch the sidebar; Human — pick Perception and the Alert feat;
   Standard Array — one select per ability (15 Str, 14 Con, 13 Dex, 12
   Wis, 10 Cha, 8 Int); Acrobatics and Insight; Defense; greatsword,
   flail, javelin masteries; the Soldier's package and package A;
   finalize. Hand-check the sheet against the SRD: HP 12 (10 + Con 15 →
   +2), AC 17 (chain mail 16 + Defense), Strength save +5, Athletics +5,
   Perception proficient from the Human, initiative +3 (Dex +1 + Alert's
   proficiency bonus), passive Perception, weight 148 lb of 255 lb, 18 GP.
3. **The buy.** A second character: choose Point Buy. Push a score past
   the budget: the meter shows the overshoot and the checklist names the
   Point Cost rule. Buy exactly 27 points (15, 14, 13, 12, 10, 8 costs 9 +
   7 + 5 + 4 + 2 + 0), take the gold alternative for both the class and the
   background, finalize: the sheet shows coin (155 + 50 GP), unarmored AC
   10 + Dex, an empty Attacks section, and six scores matching the buy
   plus the increases.
4. **The level 3 subclass.** Level Brannock up: the gains panel lists
   Action Surge and Tactical Mind, no cards, Finalize enabled at once (HP
   20). Level again: one card, Fighter Subclass, the Champion. Abandon
   once — the confirm lists the pick — then level again; close the tab
   mid-level and reopen: resume lands on the same step with the pick
   intact. Finalize: deltas list Improved Critical and Remarkable Athlete,
   HP 28, and the cap note appears.
5. **The crash.** `kill -9` the server mid-creation after the scores are
   confirmed; restart on the same directory: resume lands on the exact
   step with every confirmed choice intact.
6. **The wrong drawer.** Copy Brannock's file into the PF2e campaign's
   `characters/`, start the server there: the roster reports the file as
   belonging to a D&D 5.5e campaign, not loaded, file untouched — check
   the bytes and that no `quarantine/` entry appeared. Copy it back and it
   loads.
7. **The skeptical inspection.** Read `campaign-5e/campaign.json` (two
   lines) and Brannock's file: `"system": "dnd5e"`, `"rules_version":
   "dnd5e-srd.0.1.0"`, the log in pick order. Tamper with the sheet's HP;
   `verify` reports DIVERGED:

```bash
cargo run --release -p server -- --data-dir ./campaign-5e verify
```

8. **Mint and clone in 5.5e.** Random character: a legal Standard-Array
   Fighter with a random species and origin, named from the species
   pool; the roster offers no quick build. Clone Brannock mid-level: the
   clone resumes the pending level; the original never moves.
9. **Spot-check three records** in `rules-data/dnd5e/` (a species, a
   background, a weapon with its mastery) against the SRD 5.2.1 for
   fidelity, page, and the CC BY tag; confirm the attribution paragraph in
   the footer is the SRD's own sentence.
10. **Intent checks.** Does creating a 5.5e character feel like the same
    app with different rules? Does the "Generation method" card read as
    the place a "Roll" option will slot in? Read the table above: does
    each bend read as a generalization you would defend?

## Constraints now enforced

| Row | Lives at |
|---|---|
| Layering: `ruleset-dnd5e` edges; server, wasm, checks → both rulesets; no ruleset↔ruleset edge; no `reqwest`/`ureq` in server's or wasm's normal tree | `checks/crate_layering.rs::internal_dependency_graph_matches_allowlist`, `server_and_wasm_carry_no_http_client` |
| Per-crate scans: purity, kind isolation (each crate's own module list), `const LEVEL`; no `pf2e`/`dnd5e` in engine-core or types code; no slot-id literal or advance-slot parsing in server/wasm; only the selectors name a ruleset crate | `crate_layering.rs::engine_sources_are_pure`, `ruleset_kind_modules_do_not_reference_each_other`, `level_is_derived…`, `engine_core_and_types_name_no_system`, `server_and_wasm_parse_no_slot_ids`, `only_the_selectors_name_a_ruleset_crate` |
| Class isolation per system: 5.5e shipped names scanned against its crate; cross-class check per system; `MeterView {` ban covers the new crate | `checks/class_isolation.rs` |
| Rules data per system: manifest `system` = directory = selector key; every version prefixed `<system>-`; book allowlist and license tag per system; CC BY attribution present; denylist, ID immutability, lineage per directory; 5.5e advancement 2..=3 and subclass cross-references | `checks/rules_data.rs` |
| Registry completeness: every `rules-data/<system>/` has a crate and selector arms | `crate_layering.rs::every_rules_data_directory_has_a_selector_arm_and_a_crate` |
| Attestation per system under one schema with a `source` block | `checks/attestation.rs` (both directories) |
| Schema v5: v4 loads byte-identical, `system` written on first write; v6 refused; system-vs-registered-prefix disagreement refused in place; unregistered prefix loads as PF2e, version-unknown | `checks/campaign.rs` |
| Campaign declaration: shell-only when undeclared; create-exclusive; SIGKILL-untorn; change only while empty (trash counts); never written into an undeclared dir with characters; corrupt → refusal with reason; foreign file → missing-declaration report naming the path | `checks/campaign.rs` |
| System before version: mismatched file present at its path, never in version status; per-ruleset known versions; extras keyed by system, unshipped key is a startup error | `checks/campaign.rs::wrong_drawer_is_refused_in_place`, `checks/version_guard.rs::known_versions_are_per_ruleset` |
| Attribution follows the binary | `checks/campaign.rs::attribution_follows_the_binary`, `ui/e2e/campaign.spec.ts` |
| System on the wire once (campaign view + declare request) | `crate_layering.rs::system_field_lives_only_on_the_campaign_view` |
| 5.5e goldens (Brannock 1 and 3, Nell's gold alternative); level 2 empty; level-3 slot = subclass records | `checks/dnd5e.rs`, `checks/fixtures/brannock*.json`, `nell-gold*.json` |
| 5.5e seed sweep to the cap; quick build refused in 5.5e | `checks/dnd5e.rs::minted_5e_characters_finalize_and_level_to_the_cap_across_seeds`, `checks/quick_build.rs::quick_build_is_absent_from_a_5e_campaign` |
| Clone in 5.5e (fidelity, pending level) | `checks/dnd5e.rs::clone_in_a_5e_campaign_keeps_fidelity_and_pending_levels` |
| Atomic transitions under SIGKILL (5.5e confirm, finalize-pending) | `checks/dnd5e.rs::confirm_and_finalize_pending_under_sigkill_are_prior_or_next_state` |
| Ability-score machinery property; method change cascades | `checks/dnd5e.rs::ability_score_machinery_holds_across_a_seed_sweep` |
| UI system-blind: no system id or ability name in shipped source; no system-named file; one `.wasm`, one init site | `crate_layering.rs::ui_has_no_level_specific_wizard` |
| Stories walk under the layout sweep | `ui/e2e/campaign.spec.ts`, `ui/e2e/dnd.spec.ts` |
| Budgets: 5.5e level-3 fold < 5 ms; WASM ≤ 2.5 MB, exactly one module | `checks/dnd5e.rs::fold_of_a_level_3_log_is_under_5ms`, `.github/workflows/ci.yml` "WASM bundle budget" |

## Decisions made inside the contract

- `EngineOps` is a separate trait from `Ruleset` (`fn engine(&self) -> &dyn
  EngineOps`), so each ruleset implements only its escape hatches.
- The declaration temp is unlinked after the hard link (a second directory
  entry for identical bytes), with a scoped allowance on the never-unlink
  lint; character data is never unlinked.
- A pre-declaration directory declares nothing on load; the test harness
  declares PF2e on a fresh directory so every existing check keeps its
  meaning, with `spawn_undeclared` for the declaration tests.
- The declare request carries `system`; every view except the campaign
  view stays system-free (the scan admits exactly those two).
- 5.5e content: Human, Dwarf, Goliath, Halfling (Human's Small option not
  modeled; Elf skipped — its lineages grant spells); all four SRD
  backgrounds; background equipment as its own Single slot (package or 50
  GP); score methods as data records; Magic Initiate shipped with a
  visible "spell choices not yet supported" note; the Skilled feat opens a
  three-pick chooser; repeatable feats simplified (a duplicate is Illegal).
- Random mint pins the standard array (`Ruleset::mint_pin`) and samples
  grouped options one per group with distinct labels.
- The spec's illustrative numbers assumed Con +3; with Soldier's +1 on Con
  14 the correct values are HP 12 / Con save +4 / +8 per level, and the
  goldens encode those.
- The reference-check tool: `--system` and a match, one attestation schema
  with a per-source block; the PF2e attestation was restructured in place.

## Agent evidence

(filled at the end of the checkpoint — see the commit log for the run)

## Complaints logged

None.
