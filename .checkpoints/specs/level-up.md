---
slug: level-up
status: approved
---

# Chargen slice 5: level-up — Fighter and Wizard through level 3

## Problem

Characters are born at level 1 and stay there. Per the revised vision
(2026-08-30), this slice ships the level-up wizard: appended decisions on
the slots a new level unlocks, for the PF2e Fighter and Wizard through
**level 3** — exercising every new slot type (class feat, skill feat,
general feat, skill increase) and the Wizard's new-spell-rank machinery.
It is also the proof of the **one dialog machine** claim: leveling reuses
the creation wizard's guided-dialog machinery (checklist, live
validation, per-confirm durability, resume) — a new view over newly
opened slots, not a new wizard. The roster-ergonomics tools (random
mint, clone) exist precisely so this slice's builds are cheap to test.

## Requirements

1. A finalized Fighter's or Wizard's sheet offers **Level up** (to 2,
   then to 3 — the level-3 world's cap). Starting it
   opens a pending level in the same guided dialog: the slots that level
   unlocks, with the familiar checklist, live validation, per-confirm
   durable saves, revisable choices, and exact resume after tab close or
   server kill. One level at a time — a character has at most one
   pending level, and a second "Level up" (a second tab, a retry) lands
   in the existing pending level rather than starting another. Leveling
   1→2→3 back-to-back works; at the cap the button gives way to a plain
   "higher levels are coming" note.
2. **Mid-level-up, the character is still its old level** (decided
   2026-08-31): the finalized sheet stays authoritative everywhere, the
   roster shows a "leveling up — resume" state, and opening the
   character offers the old sheet beside the resume. Finalizing the
   level appends the level's decisions to the decision log and commits
   the re-derived sheet as one atomic transition — a crash can never
   leave a character both leveled and "leveling up". **Abandoning** the
   level (offered in the dialog, after a confirm listing exactly what
   will be discarded) drops only the pending choices, atomically too: a
   crash mid-abandon leaves either the intact pending level or the
   clean prior state, and finalized state is never edited either way.
   Writes into a pending level carry versions like every wizard write:
   a stale tab's confirm — including one racing an abandon or finalize —
   is rejected with a reload, never interleaved.
3. The level's slot coverage, finalized against Archives of Nethys at
   implement: level 2 grants a class feat and a skill feat (both
   classes); level 3 grants a general feat and a skill increase, plus
   each class's fixed level-3 features. The Wizard's levels also grow
   the spellbook (the rules-published two spells per level, at any rank
   the wizard can cast) through the established per-rank picker, and
   level 3 opens rank-2 slots — slot counts and the spellcasting block
   update as derived facts, cantrips display at the new auto-heightened
   rank, and the prepared column stays empty with its Epoch-8 note.
4. **Gains summary** (decided 2026-08-31): the level-up dialog opens
   with a read-only "At level N you gain…" panel — HP increase,
   proficiency changes, fixed features, the new choice slots — and the
   finalize step shows before/after deltas for the values the level
   changed. Purely informative; every value is derived, never
   hand-entered.
5. A level-up is decisions in the same decision log: the leveled
   character remains one file with one ordered log, replay reproduces
   the leveled sheet from the log alone, and `verify` covers leveled
   characters — pending levels included (tampered pending choices are
   caught the same way tampered sheets are). The established
   schema-version-and-migration discipline holds (every pre-slice file
   loads unchanged). Levels obey the rules-data pin discipline: leveling
   is a wizard write, so a character whose pin is not current resolves
   its version flag first — one log, one pin, never mixed.
6. Validation is the creation wizard's: prerequisites are judged against
   the leveled state, illegal and incomplete entries land on the same
   checklist naming rule and slot, and finalizing the level requires a
   clean checklist. No combination of picks may make a level's
   requirement unsatisfiable.
7. Content breadth is a representative subset exercising every
   mechanism, mirroring prior slices: for the Fighter, level-2 class
   feats including at least one with a prerequisite, a skill-feat and
   general-feat subset, and skill-increase choices covering the
   trained→expert rule; for the Wizard, its level-2 class feat options
   and a rank-2 spell subset covering an attack-roll spell, a save
   spell, a utility spell, and a heightening entry. Every slot's subset
   must leave at least one legal option for every legal prior build —
   a subset can never strand a level at an unfinalizable dead end. Full
   breadth per level is the growth track's data work, not this slice.
8. Everything that exists keeps working: the creation wizard, quick
   build, random mint, and clone are unchanged for level-1 work; clone
   of a character with a pending level clones the pending level with it
   (the same way cloned drafts resume at the same step); every
   pre-slice character file loads and replays exactly as before.

## User stories & flows

- **The first level-up.** Ben opens Torvald (finalized Fighter 1), taps
  Level up: the gains panel says what level 2 brings, the checklist
  shows the two open slots, he picks a class feat and a skill feat,
  watches the finalize step's before/after deltas, finalizes, and the
  sheet now reads Fighter 2 — HP and every changed number matching a
  hand calculation.
- **Straight to 3.** Ben mints a random Fighter, finalizes it, and
  levels it twice back-to-back. At 3 the Level-up button is gone,
  replaced by the cap note.
- **The wizard's new rank.** Sylvenne to 2, then 3: her spellbook grows
  by two spells each level through the familiar picker; at 3 rank-2
  spells become pickable, the sheet's slots-by-rank shows the new rank,
  and her cantrips display at rank 2. The prepared column is still
  empty, still pointing at the table.
- **The crash.** kill -9 mid-level-up; restart; the roster shows
  "leveling up — resume"; resume lands exactly where he left off, every
  confirmed choice intact — and until he finalizes, every view of the
  character still shows level 1.
- **The changed mind, inside the level.** Before finalizing, Ben swaps
  the level-2 class feat; anything dependent within the pending level
  re-judges or clears with the usual cascade prompt — nothing outside
  the pending level moves.
- **Illegal picks, caught at the card.** Ben eyes a level-2 class feat
  whose prerequisite his build fails: it shows greyed with the reason.
  He leaves the skill-increase slot empty and tries to finalize the
  level: blocked, with the gap named on the checklist at the card.
- **Nothing else moved.** Torvald's pre-slice file opens unchanged; a
  new character runs through the unchanged creation wizard; quick
  build, random mint, and clone behave exactly as before at level 1.
- **The retreat.** Ben abandons a half-done level 2: the confirm lists
  the two picks being discarded, and afterwards the character is its
  clean level-1 self, the file showing no trace of the attempt.
- **The fork first.** Before experimenting, Ben clones Torvald and
  levels the clone down a different feat path; the original never
  moves. Cloning mid-level-up works too: the clone carries the pending
  level and resumes at the same spot, independently.
- **The skeptical inspection.** A leveled character's file is the same
  log grown by the level's decisions, in order, provenance intact.
  Hand-tampering the sheet is still caught by `verify`.

## Risks

- **The pending level is a new lifecycle state** — neither a creation
  draft nor a finalized character. The architecture dialogue owns how it
  is represented and crash-persisted; the risk is a third state leaking
  complexity everywhere. Mitigated by requirement 2's hard rule: the
  finalized sheet stays authoritative until an atomic level finalize.
- **The one-dialog-machine claim fails** — leveling turns out to need a
  second wizard. Honest outcome: the report lists what the machinery
  could not express and why; the vision's claim is revised deliberately.
- **Advancement data is the largest rules surface yet** (per-level
  grants, feat prerequisites, spell ranks). Mitigated: representative
  subsets, the reference-check pipeline, golden hand-verified level-3
  builds of both classes.
- **Prerequisite interactions across levels** (a level-2 pick enabling a
  level-3 pick) may surface planner/validator gaps. Mitigated by a
  test-only extension of the seed-sweep harness that makes random legal
  level-up picks — harness machinery only, deliberately not a UI
  feature (see Out of scope).
- **If the slice proves too big at implement**, the designated first
  cut is Fighter-first: machinery + Fighter through 3 exercises every
  new slot type and the pending-level lifecycle; Wizard leveling (book
  growth, rank-2 slots) follows as its own slice. Recorded, not
  executed.
- **Accepted:** no undo of a finalized level — retraining is
  edits-and-exceptions' scope; the escape hatch this slice is cloning
  before you level.
- **Accepted:** leveling is a free player action with no XP, milestone,
  or DM gate — advancement policy is table machinery for later epochs.
- **Accepted:** abandoning a level discards durably-saved picks without
  a trash entry or log event — the one deliberate gap in the
  nothing-is-silently-lost discipline, bounded by the explicit confirm
  that lists every discarded pick.

## Out of scope

- Levels 4+ (growth track), and any level-4+ rules data.
- Retraining, editing or undoing finalized levels, and any edit to
  finalized level-1 state (edits-and-exceptions).
- XP or milestone tracking, DM-gated or staged level-ups.
- Multiclassing, archetypes, dedications; any new class or ancestry
  content beyond the level-2/3 subsets.
- Daily preparation and anything cast-time (Epoch 8); familiars.
- Random level-up as a product feature (mint stays level-1; random
  leveled characters can be assembled by minting then leveling by
  hand). The seed-sweep test harness may level randomly — that is test
  machinery, not UI.
- Wizard quick build (wizard-content).

## What Ben checks

- Walk "the first level-up" on Torvald and hand-verify Fighter 2
  against Archives of Nethys: HP, the feat slots offered, proficiency
  numbers, and the finalize deltas.
- Walk "the wizard's new rank" to 3 and hand-verify the spellcasting
  block: rank-2 slots, spellbook counts (+2 per level), cantrip
  heightening at rank 2, spell DC/attack.
- Walk "the crash" mid-level and confirm exact resume — and that every
  view stayed level 1 until finalize.
- Walk "the changed mind": swap the confirmed level-2 class feat and
  confirm the cascade prompt scopes to the pending level only.
- Walk "illegal picks": see the prerequisite-failing feat greyed with
  its reason, and finalize blocked by the empty slot, flagged at the
  card. Then take the prerequisite-bearing level-2 feat on a build that
  qualifies and see what it enables (or gates) at level 3 — the
  cross-level interaction, walked by hand.
- Walk "nothing else moved": open a pre-slice character, create a fresh
  level-1 character, quick build, mint, and clone — all unchanged.
- Walk "the retreat" and confirm the discard list was exact and the
  file is clean afterwards.
- Walk "the fork first" and confirm the original never moved — then
  clone mid-level-up and confirm the clone resumes the pending level at
  the same spot, independently.
- Level a character to 3 and confirm the cap note replaced the button.
- Open a leveled character's file: is the level legible as appended
  decisions? Tamper with the sheet; `verify` catches it.
- Spot-check three level-2/3 records (a class feat with a prerequisite,
  a general feat, a rank-2 spell) against Archives of Nethys.
- Intent check on the one-dialog-machine claim: does leveling *feel*
  like the same dialog you already know — checklist, cards, confirm,
  resume — rather than a second UI to learn?
- Intent check on the gains summary: is "At level N you gain…" the
  at-the-table moment you wanted it to be?

## Review record

| Role | Verdict | Folded in |
|---|---|---|
| risk-reviewer | advice | pin discipline for levels (req 5); single-pending-level + stale-tab/race rules (reqs 1-2); abandon and finalize both atomic (req 2); `verify` over pending levels (req 5); subset-satisfiability rule (req 7); abandon-discard accepted-gap bullet |
| user-advocate | advice | illegal-picks and nothing-else-moved stories + checks; changed-mind check; cross-level prerequisite hand-walk; pending-clone walk; cap-note check |
| scope-warden | advice | Fighter-first designated contingency cut (Risks, recorded not executed); pending-clone kept with a walk; random leveling named as test-only harness (Risks + Out of scope); cap-note wording de-jargoned |
