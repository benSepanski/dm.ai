---
slug: chargen-content
status: approved
---

# Chargen slice 2: full Player Core breadth + reference pipeline + quick build

> Drafted overnight 2026-08-28, research verified against AoN index
> aon-20260802-141253. **[call]** decisions were ratified at review.

## Problem

The chargen-fighter slice shipped a working PF2e Fighter wizard over a thin
subset: 111 rules-data records, verified entirely by hand against a 520-line
Archives of Nethys dossier. That does not scale — full Player Core breadth
is ~4x the records, each one a chance to silently poison trust in derived
numbers. The wizard also has no fast path: every character is a full walk.

This slice makes the Fighter wizard *complete* for Player Core: all common
Player Core content a level-1 Fighter can select, flowing into the existing
slots; a mechanical reference-check pipeline replacing hand verification as
the primary trust mechanism; the app's first rules-data version bump over
live characters, forcing the review-flags-never-silent-mutation machinery
the vision promises; and a quick-build fast path. Research reframes the
vision's wording there: PF2e has never published per-class quick-build
choices in any edition (only the class kit and key attribute), so the fast
path ships as an explicitly app-authored suggested build, not a
"rules-published" one.

## Requirements

1. **Content breadth — all common Player Core content for the Fighter
   wizard, with per-file counts as acceptance criteria.** The rarity line
   **[call]**: common ships; uncommon and rare do not (no access-gating
   machinery exists; records may carry a rarity field). Counts below are
   research-pass numbers; the implement report records the finalized counts
   against the pinned AoN snapshot so the criterion stays auditable:
   - Ancestries: all 8 core (adds Gnome, Halfling, Leshy, Orc) with complete
     Player Core stats, heritages, and level-1 ancestry feats (~27 new
     heritages → 45 total; ~33 new feats → 63 total).
   - Versatile heritages **[call]**: the two common ones, Aiuvarin and
     Dromaar, selectable at the heritage step for any ancestry, with their
     level-1 feats (~5). Changeling, Nephilim, and Jinxed Halfling
     (uncommon) are excluded — deferring Jinxed's feat-exclusion rule too.
   - Backgrounds: 39 of 40. Raised by Belief is excluded by name **[call]**:
     its mechanics are parameterized on a deity catalog whose canonical
     names are ORC-reserved. The ~15 backgrounds with in-background choices
     (skill pick, player-named Lore, choice-dependent skill feat — Scholar,
     Guard, Nomad, Martial Disciple…) ship with those choices working, not
     flattened.
   - Fighter level-1 class feats: already complete (all 8 shipped) — a
     no-op, restated so "full breadth" is auditable.
   - General feats: all 14 common level-1 general feats. Skill feats
     **[call]**: the full 53-record level-1 catalog ships as real records —
     backgrounds reference 35, and a general-feat slot legally reaches all.
   - Equipment: all common Player Core weapons (~65, incl. ammunition), all
     13 armors, all 4 shields (adds Buckler, Tower Shield), and the common
     adventuring-gear and assistive-items tables (~140). Services do not
     ship; the 23 uncommon weapons are excluded (Unconventional Weaponry
     stays greyed, per precedent).
2. **Bounded machinery growth.** "Pure data entry" is the norm; the
   complete list of mechanics additions: versatile-heritage support
   (heritage unbound from ancestry; ancestry-feat catalog becomes a union);
   background sub-choice and player-named-Lore slots; choice-dependent
   grants landing as real skill/Lore training (Hold Mark, Gnome Obsession,
   Scholar-pattern backgrounds); two evaluable prerequisite kinds
   (attribute threshold, trained-in-skill); a save/Perception
   proficiency-override effect (Canny Acumen shows expert at level 1 —
   text-only would render a wrong sheet); a ranged unarmed attack field
   (Seedpod); a fist-replacement convention (Iron Fists); language
   selection (req 3). Anything else is out of scope until spec'd.
3. **Language selection** (deferred from slice 1, now forced by three
   Player Core mechanics): per-ancestry additional-language lists ship as
   data; a chooser grants Int-modifier bonus languages (dynamic count, like
   trained skills); Nomadic Halfling's +2 and the Multilingual skill feat
   feed the same chooser; languages render on the sheet.
4. **Mechanical fidelity is machine-checked.** A reference-check pipeline
   compares every record's mechanical fields (existence, names, levels,
   numeric stats, boost patterns, prerequisites, traits, prices, bulk,
   proficiency ranks) against a pinned, content-addressed snapshot of the
   Foundry PF2e open data — verification only: no Foundry file, text, or
   value is ever committed, vendored, or embedded in any artifact; match
   verdicts, field names, and hashes only. Completeness runs both ways:
   every in-scope Player Core record exists in our data, and every shipped
   record matches or carries a reviewed, reasoned waiver. The tool runs as
   a deliberate invocation; CI stays offline and asserts the
   committed attestation covers every record with zero unwaived mismatches
   — and is bound to the data by content hash, so no rules-data byte
   changes without regenerating it. Errata arrive by deliberately
   re-pinning the snapshot and reviewing the diff, never by silent data
   edits. Prose fidelity, page numbers, kit semantics, and rules
   interpretation remain human-verified: golden builds plus a stated
   sampling quota (all scrubbed records + a sample per file).
5. **License scrub is tooling, not vigilance.** No ORC-reserved proper noun
   appears in any shipped record name or text: the four "First World" gnome
   records are renamed/paraphrased per the ORC AxE deletion pattern,
   Golarion example nouns dropped (Street Urchin precedent), a
   reserved-noun denylist lint over record names and text enforcing it.
   Scrubbed records are flagged in the data and appear as named waivers in
   the attestation; the lint's config and those waivers may contain the
   nouns they police (repo tooling, never served content), exempt from
   their own scan. The lint also pins the source-book set to exactly
   {Pathfinder Player Core}.
6. **The first data version bump is survivable and honest.** Shipping this
   content bumps the rules-data version while slice-1 characters exist
   pinned to the old one:
   - An older-known-version character or draft is detected at load; the
     server replays its log against current data. Identical sheet →
     eligible for re-pin, done only by an explicit action recording a note
     in the file. Divergent → a review flag names old and new values; the
     stored sheet is untouched until Ben accepts (accept re-pins and
     records prior values — nothing the table saw is lost). A log that
     *errors* on replay gets the same flag naming the failing decision;
     accept waits until resolved. Not accepting is first-class: the
     character stays usable on its stored sheet with a standing flag, or
     Ben keeps the old derivation, recorded, un-flagged until data changes
     again.
   - A draft mid-wizard cannot continue against mismatched data without
     resolving first; resolving re-pins and re-validates, and any decision
     now illegal reopens its slot through the existing cascade and
     checklist machinery with the change named — never silently dropped.
   - `verify` distinguishes "older known version" from "unknown version".
   - Record IDs are immutable once shipped — errata and renames change
     display names, never IDs — and never deleted: a wrong record is
     deprecated (unselectable in new drafts, resolvable by old logs). No
     wizard operation replays an old log against new data outside this
     flow.
7. **Quick build** — one tap to a complete, legal, reviewable character:
   - From the roster, "Quick build a Fighter" creates a draft and fills
     every required slot with the app's suggested build: an app-authored
     **[call]** choice set (published anchors: class kit, key attribute;
     exact choices pinned at implement by a golden test), labeled as dm.ai
     suggestions, never Paizo-published. It lands on the completed wizard
     in review state with an empty checklist — the player confirms name
     and finalizes.
   - In-wizard, "fill remaining with suggestions" completes only the open
     slots of a partial draft, adapting to confirmed choices (dependent
     counts and options resolve against actual draft state, never a static
     list). It never overwrites a confirmed choice; if one makes a
     suggestion inapplicable, the fill completes as far as legality allows
     and the checklist shows the remainder — never all-or-nothing rollback.
     (Fill-remaining is the designated first cut if scope must shed.)
   - Suggested decisions are ordinary decision-log entries — same fold,
     replay, validation, and crash rules — carrying a distinct provenance
     source ("suggested") visible on hand-inspection; editing one later
     records the player as the new source. A suggested build that fails to
     fold to a finalizable character is a data-lint failure, not a runtime
     surprise.
8. **Full breadth is usable at the table.** Any option list past a small
   threshold gets a text filter; the equipment step groups by category and
   its shopping list is filterable. The 39-background step and 53-entry
   skill-feat chooser must be scannable without endless scrolling. No
   other wizard redesign.
9. **Slice-1 invariants hold at scale.** Options requiring machinery this
   slice excludes (cantrip choosers: Fey-touched and Wellspring Gnome,
   Otherworldly Magic, First World Magic's renamed successor) ship greyed
   with an explanatory reason, per the Ancient Elf precedent. Golden
   coverage grows to one hand-verified build per ancestry, plus a
   versatile-heritage, a background-sub-choice, and the quick-build
   character. Crash safety, idempotent confirms, read-only load, server
   authority, replay determinism, and the perf/test budgets hold with full
   data; the report states measured suite/rebuild/WASM-size deltas.

## User stories & flows

Creation-path flows live as Walks 1–10 in What Ben checks; beyond those:

- **The quick build.** One roster tap: a completed wizard, every slot
  filled, each suggestion badged, checklist empty. Rename, swap a feat
  (badge flips to player), finalize — under a minute. The same mechanism
  fills only the *open* slots of a half-built draft; a stalled player's
  confirmed choices never move.
- **The bump, flagged.** After upgrade, Torvald (slice-1 data) shows a
  review flag: a pipeline correction changed a record and his replay now
  differs. Old vs new values shown; sheet unchanged. Ben accepts on
  Torvald, keeps the old derivation on a second flagged character — both
  recorded in the files; a third replays identically and shows quiet
  re-pin availability. His half-finished slice-1 draft explains itself the
  same way: one now-illegal decision reopens on the checklist naming the
  change, he re-picks, the wizard continues.
- **The pipeline catches a typo** *(implement-time; its after-build twin
  is the attestation check)*: a transcribed heritage has HP 8 where the
  book says 10; the attestation shows the mismatch and CI refuses until
  the record is fixed or waived.
- **Unhappy path — greyed with reasons.** A player eyes Fey-touched Gnome;
  it is visible but unpickable, saying cantrip choices arrive with the
  spellcaster slice. The wizard never silently hides published content.

## Risks

- **Transcription error at 4x scale** — the headline risk. Mitigated: the
  pipeline closes slice 1's mechanical error classes (invented records,
  prereq conflation, legacy contamination); goldens and the sampling quota
  cover the rest. Accepted residual: the pipeline verifies agreement with
  Foundry, not the book — a shared error passes silently, and
  rule-semantics misinterpretation survives machine checking.
- **The denylist is a heuristic** — an unlisted reserved noun ships
  silently. Mitigated: seeded from the research pass's verified hits plus
  Paizo's reserved statement; scrubbed records hand-reviewed. Accepted:
  slice 1's posture, now with citable AxE authority.
- **The bump flow fires on Ben's real characters immediately** — pipeline
  corrections make first-open flags likely. The feature working, but a
  confusing diff reads as data loss. Mitigated: old-vs-new values side by
  side; nothing mutates without accept; Walk 9 covers it, after a backup.
- **Scope size.** The largest slice yet: ~370 records, four bounded
  mechanics areas, pipeline, version guard, quick build — but one
  deliverable. The sanctioned split, if implement stalls:
  {content + pipeline + scrub + languages + version guard} first, {quick
  build, fill-remaining first} second — the version guard travels with
  content because the bump forces it.
- **Budget pressure.** Embedded data grows ~6x against a warm-rebuild
  margin of ~1s and a suite margin of ~4s. The architecture doc settles
  the levers and a pre-authorized ceiling before implement starts; any
  further raise is a deliberate architecture revision.
- **Projection payload growth** (~10x option volume over the WASM boundary)
  could dull the live feel. Watched, not asserted: the report measures it.
- **Versatile heritages bend the heritage schema** (heritage unbound from
  ancestry; feat catalogs become unions). Bounded to two common heritages;
  the uncommon pair and cross-ancestry feat access stay out. Accepted:
  Adopted Ancestry ships selectable, its catalog-widening RAW effect a
  documented level-up-slice gap.
- **App-authored quick build carries editorial responsibility.** Mitigated:
  provenance labeling everywhere; the golden pins it; changes flow through
  req 6 as data-version changes. Also accepted: the upstream snapshot could
  vanish (the pin is a content hash, the committed attestation durable;
  re-pin to a successor flows through diff review).

## Out of scope

- Uncommon and rare content and any access/rarity gating: Changeling,
  Nephilim, Jinxed Halfling, the 23 uncommon weapons. Raised by Belief;
  any deity catalog or belief parameterization.
- Cantrips, spell records, every cantrip chooser — chargen-wizard owns the
  spellcasting shape. Multiclass dedication catalogs stay greyed.
- Cross-ancestry feat widening (Adopted Ancestry's full effect) — the
  level-up slice owns retroactive catalog changes.
- Services from the equipment chapter; itemized encumbrance beyond Bulk.
- Multiple quick-build archetypes; AI suggestions and backstories (muse);
  any second class or system, level-up, retraining, editing finalized
  characters; retained cleared-decision history (edits-and-exceptions); a
  migration framework beyond req 6 (waits for a real v2, per precedent).

## What Ben checks

First, copy `campaign/` aside. Each walk takes a route the others don't.

- **Walk 1 — linear breadth.** A Leshy Fighter front-to-back in step order:
  heritage, ancestry feat, Nomad with a typed "Steppe" Lore, languages from
  the leshy list plus Int bonus, gear via the filtered, grouped shop,
  finalize. Hand-verify against AoN: ancestry HP, Small size, senses,
  speed, the typed Lore, languages, Bulk.
- **Walk 2 — backwards.** Start a Gnome at the equipment step, jump to
  details, and let the checklist pull you back through class, background
  (Scholar — make its in-background skill pick, watch Assurance follow),
  boosts, ancestry. Confirm every gap was listed, each entry jumps to its
  step, and finalize unblocks the moment the last one clears.
- **Walk 3 — the cascade.** Build a Halfling through boosts, then change
  ancestry to Orc. Confirm the prompt lists exactly what will clear, the
  checklist reopens those slots, and re-picking leaves no halfling residue.
- **Walk 4 — versatile heritage.** A Dwarf taking Aiuvarin at the heritage
  step: confirm it appears alongside the dwarf heritages and the
  ancestry-feat list becomes the dwarf+Aiuvarin union.
- **Walk 5 — the chooser chain.** A Human with Versatile Human: in the
  opened general-feat slot pick Canny Acumen, choose its save, confirm
  expert proficiency lands on the sheet; then browse to a skill feat whose
  trained-in prerequisite you lack and confirm the greying names the rule.
- **Walk 6 — quick build.** Roster tap: read every badge, swap one
  suggestion (badge flips to a player decision), rename, finalize — would
  you hand this to a player joining a session starting in five minutes?
- **Walk 7 — fill the rest.** Half-build by hand (ancestry + background
  only), "fill remaining", confirm nothing you chose moved, finish it.
- **Walk 8 — the stubborn draft.** Confirm key attribute Dexterity first,
  then fill remaining: suggestions adapt around Dex or land on the
  checklist as unresolved; nothing overwritten.
- **Walk 9 — the bump.** On your real slice-1 roster: read the flags,
  accept one, keep-old on another, confirm both land in the files with
  prior values preserved; confirm the quiet re-pin state where replay is
  identical (provoke a divergence on a copy if none fires). Resume the
  draft you left half-finished before upgrading; re-pick what reopened.
- **Walk 10 — the greyed shelf.** Visit Fey-touched Gnome, Wellspring
  Gnome, and Unconventional Weaponry; read each greyed reason and judge
  whether it tells a player the truth about what's missing and when.
- Sweep the new ancestries walks 1–5 didn't touch, far enough to see
  boosts, heritages, and one feat each; anything thinner than slice 1's?
- Read the attestation as a skeptic: three random records, what was
  machine-checked vs waived; spot-check the scrubbed gnome records and
  Street Urchin against AoN — mechanics intact, nouns gone.
- Use the background and equipment steps at real table distance: does
  filtering keep a new player from ever scrolling forty entries?
- Intent check: is the sentence "a table can build any common Player Core
  Fighter without the book open" now true?

## Review record

| Role | Verdict | Folded in |
|---|---|---|
| risk-reviewer | advice | replay-error branch + never-delete/deprecate IDs + draft-resolution semantics (req 6); content-hash-bound attestation + durable-pin/snapshot-loss posture (req 4, risks); both-wrong residual named; campaign backup check; denylist self-exemption (req 5) |
| user-advocate | advice | interrupted-draft story + check; explicit not-accept/keep-old state (req 6); fill-the-rest closed to finalize + its check; bump-check fallback + provoke-divergence note; versatile-heritage and typed-Lore folded into Ben's walks; pipeline story marked implement-time |
| scope-warden | advice | split line corrected (version guard travels with content, quick build severable, fill-remaining first cut); budget levers settled in architecture before implement; finalized counts recorded in implement report (req 1) |
| Ben (review) | decision | approved with one revision: What Ben checks expanded into ten explicitly path-diverse walkthroughs (backwards, cascade, chooser-chain, stubborn-draft routes); redundant stories trimmed to fund it; [call] decisions ratified |
