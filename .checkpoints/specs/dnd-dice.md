---
slug: dnd-dice
status: approved
---

# Chargen slice 7: dnd-dice — rolled ability scores and hit points as recorded inputs

## Problem

The app has never rolled a die. Every number on every sheet is a pure
function of choices from a catalog, which is exactly why replay and
`verify` work — and exactly why the 5.5e ability-score step offers only
Standard Array and Point Buy, with rolling split out of `chargen-dnd`
on 2026-09-06 so that slice made one claim. Rolling is the published
first method in the SRD, most tables use it, and it is the app's first
encounter with an input that is neither a choice nor derivable.

This slice adds **rolled ability scores** (4d6, drop the lowest, six
times) as the third method, and **rolled hit points** at level-up as a
second consumer of the same shape. Rolls land in the decision log as
**recorded inputs**: the faces that came up, tagged with whether the app
rolled them or the player entered physical dice. Replay replays the
recorded faces; derivation (drop the lowest, sum, assign) stays pure.
Every rolled set is kept — rerolls are allowed and visible, never
overwritten — because the vision's reroll policy is table policy for a
later epoch, and the log is what that policy will read. The recorded-
input shape this slice lands is the substrate Epoch 8's rolled actions
reuse, so it is designed to carry any die, not just d6s.

## Requirements

1. **Rolling is the third score method**, a data record beside the array
   and the buy, chosen at the same Generation method card with no
   redesign of the step. Choosing it opens a **roll slot** for the six
   sets, and the existing assignment slot then offers the six totals
   under every ability, exactly as the array does — with the one
   difference rolling forces: duplicate totals are legal and each total
   may be assigned as many times as it was rolled, never more. The
   background's increases stack on top through derivation as before; the
   published cap (20) is enforced by the validator and is now reachable
   (18 + 2) though not exceedable at level 1.
2. **The app rolls.** One tap rolls all six sets (twenty-four d6) on the
   server with real entropy — or, when the server was started with the
   testing-only seed flag, from that seed, in which case the roster
   wears a visible "seeded dice" badge on every load and the seed is
   never written to any file — records the faces, and lands the result as
   a decision the player sees at once: each set's four faces, the
   dropped die, and the total. The tap is idempotent on a client
   decision id: a retried request returns the roll already recorded,
   never a second one (an id cleared by a later method change is simply
   gone, and a late retry rolls fresh — harmless and visible). The roll
   request carries the draft version like every confirm, so two tabs
   cannot silently overwrite each other's set. A roll never happens in
   the browser and never in derivation. A rolled set the server did not
   produce is refused **at the server's routes** — the fold, the
   preview, and `verify` never judge origin, so every existing file
   replays whatever it recorded.
3. **The player may enter physical dice instead**: four faces per set,
   six sets, each face validated against the die shape (1–6, four per
   set, six sets) in the live preview before anything is confirmed and
   again on confirm — an out-of-shape entry is illegal on the checklist
   with the rule named, and a crafted request cannot land a 7. Entered
   sets are tagged as entered, app rolls as rolled, and the tag is
   visible everywhere a set is shown and in the file.
4. **Every rolled set is kept.** The history lives **inside the roll
   slot's one decision**: an ordered list of sets, the most recent live.
   Rerolling — by app or by hand — records the same list plus one set
   through the existing amend path, so no new log shape is needed;
   earlier sets stay, in order, with their tags. A client submits only
   the sets to append — the app composes them onto the stored history,
   so dropping, reordering, or rewriting a set is not something a
   request can say — and the app, not the client, tags each set:
   entered on the ordinary path, rolled on the roll path. A reroll clears the
   assignment through the existing dependents machinery (the confirm
   names what it clears). There is no reroll limit and no policy — the
   history is the record a later table-policy slice reads.
5. **Replay, `verify`, clone, crash-resume, and resume-after-tab-close
   all hold** for rolled characters: the sheet is a pure function of the
   log's live recorded faces plus the pin; `verify` catches a tampered
   live face or total; a clone — mid-wizard or finalized — carries the
   full history; kill -9 during a roll leaves the prior state or the
   recorded roll, never a torn file; closing the tab after a roll and
   reopening lands on the same card with the same sets.
6. **Rolled hit points at level-up** for 5.5e, at levels 2 and 3 (the
   cap): each pending level offers the published choice — take the
   fixed value or roll the class hit die — as a slot on the pending
   level's checklist, unrequired: an absent decision means the fixed
   value (the rule the sheet applies today), so every existing leveled
   character's sheet and file are byte-identical and level 2 stays a
   level that can finalize at once. Choosing to roll opens a one-die
   roll slot with the same app-roll, physical-entry, history, and tag
   behaviour as the scores; a level's gain applies the published
   minimum (transcribed at implement, never invented) so a low roll
   with a negative Constitution modifier never subtracts. The gains
   panel and the finalize deltas show the rolled hit points and their
   origin; the sheet's hit-point breakdown names each level's value and
   whether it was rolled, entered, or fixed. Abandoning the pending
   level discards its hit-point history with everything else on that
   level; a clone taken mid-level copies it.
7. **The record is legible and game-free.** A rolled set in a character
   file reads as the faces, the die, and the tag; the shape of a
   recorded input (die sides, dice per group, group count, origin) is
   defined once in the wire types with no game vocabulary, and the
   ruleset alone turns faces into totals. PF2e is untouched: no roll
   slot, no rules-data change, every PF2e golden and fixture
   byte-identical.
8. **Everything that exists keeps working**: Standard Array and Point
   Buy unchanged; random mint still pins the array; the wizard, level-
   up, quick build, clone, version flags, and `verify` unchanged for
   both systems; a character file from before this slice loads
   byte-identical and gains nothing on load.

## User stories & flows

- **The roll.** Ben creates "Ysolde" in the 5.5e campaign, reaches the
  ability scores, and picks Roll. A card shows six empty sets and one
  button; he taps it and six sets appear — four faces each, the lowest
  struck through, the total beside — tagged "rolled". He assigns the six
  totals one per ability (two 12s go to two different abilities), adds
  the Soldier's +2/+1, finalizes, and the sheet's scores match a hand
  calculation from the faces.
- **The reroll.** Ysolde's first set is 9, 8, 8, 7, 11, 6. Ben taps roll
  again: the confirm says the assignment will be cleared; the new set
  is live, the old set stays listed above it in roll order, greyed.
  Ben opens the file: both sets are there, in order, faces and tags.
- **The physical dice.** For "Marrow", Ben chooses Roll and taps "Enter
  dice" instead: he types four faces for each of six sets, deliberately
  entering two identical sets and one 6, 6, 6, 1. A 7 in one box is
  illegal at once with the rule named; he fixes it, confirms, and the
  set is listed tagged "entered". He assigns the 18 to Strength and
  the two equal totals to two abilities, gives Marrow the Soldier's +2
  Strength — the sheet reads 20, the cap, and the checklist is clean —
  and finalizes; the sheet matches a hand calculation from the faces.
  Back in the wizard for a moment, he taps the app roll once: a second
  set, tagged "rolled", becomes live above the entered one, and the
  confirm names the assignment it clears.
- **The double tap.** Ben taps roll twice as fast as he can. One set
  appears on the card and one set is in the file.
- **The hit die.** Ben levels Ysolde to 2. The gains panel shows the
  fixed hit points, and the checklist offers one unrequired card: Hit
  Points — the fixed 6 unless he rolls the d10. He taps roll: a 3. He
  rolls again; the 3 is kept in the history, an 8 is live; the gains
  panel now shows the 8 and "rolled"; he finalizes and the sheet's HP
  breakdown reads "level 2: 8 (rolled) + Con". At level 3 he enters a
  physical d10 instead — an 11 is illegal with the rule named, a 7 is
  accepted and tagged "entered". Brannock, leveled last slice with no
  such card, still reads his fixed values and his file is unchanged.
- **The abandoned level.** Ben starts Ysolde's next level, rolls a hit
  die twice, then abandons: the confirm lists the hit-point pick and
  its history among what goes; after abandon the file holds neither.
- **The crash.** kill -9 the server the instant after the roll button is
  tapped, several times; restart each time: the log has either no new
  set or exactly the recorded one; resume lands on the same card.
  Separately, close the tab right after a roll and reopen: the same
  card, the same sets.
- **The skeptical inspection.** Ysolde's file lists her roll decision:
  each set as four faces and a tag, in order. `verify` passes. Ben
  edits one live face from 3 to 6; `verify` reports DIVERGED.
- **The clone.** Cloning Ysolde mid-wizard (clone already works on
  drafts) carries both her rolled sets and her assignment; the clone's
  file shows the same history.
- **Nothing else moved.** Torvald and Sylvenne open unchanged; Brannock
  and Nell open unchanged; a fresh PF2e character meets no roll card
  anywhere; a fresh 5.5e character choosing Point Buy meets none either.
- **Unhappy path — the method change.** Ben switches Ysolde's method from
  Roll to Standard Array: the confirm names the roll history and the
  assignment as cleared; he switches back to Roll and the card is empty
  — the earlier sets are gone from the live log, which is the existing
  method-change rule, and the reason the history within a method is what
  the log preserves.

## Risks

- **A recorded input is a new kind of log entry**, the first that is
  neither a catalog pick nor text. The risk is that it lands as a
  5.5e-shaped special case rather than a substrate. Mitigated: the shape
  (sides, dice per group, groups, origin) lives in the game-free wire
  types and two different consumers — twenty-four d6 at creation, one
  d10 at level-up — ship in the same slice.
- **The app-rolled tag can be forged** by a client that submits a set
  claiming "rolled" through the ordinary confirm path. Mitigated: tags
  are stamped by the app's own paths, never read from a request, and a
  request that claims the app's tag is refused. The threat model is the
  LAN's mischievous friend; the log is visible to the DM, who disposes.
- **Unlimited rerolls** let a player roll until the numbers please them.
  **Accepted** by design: the history is the record, reroll policy is
  the DM's and arrives as table policy in a later slice; nothing here
  hides a reroll.
- **Duplicate totals** break the array method's "each value once"
  bookkeeping if carried over naively. Mitigated: assignment counts
  multiplicity — a total may be used as often as it was rolled — and a
  property test sweeps rolled sets with repeats.
- **A method change discards the roll history**, because switching
  methods clears the method's dependents; **abandoning a pending level
  discards that level's hit-point history** with the level. **Accepted**:
  these are the existing rules for every slot, the confirm names what
  goes, and the history the vision protects is within a method, within
  a level that was kept.
- **`verify` sees only the live set.** It compares the stored sheet to a
  replay, so editing a superseded set or flipping a tag by hand leaves
  the sheet unchanged and passes. **Accepted**: the file is the trusted
  record and a tag is as trustworthy as the disk it sits on; a hand
  edit of history is a DM's own act on their own files.
- **Unbounded history** grows the file and the card one set per tap.
  **Accepted** with two guards: the fold budget is asserted over a
  thousand-set history, and the card collapses sets beyond the most
  recent few behind a "show all" control.
- **The 5.5e rules-data version bumps** (a new method record), so every
  existing 5.5e character meets the established quiet re-pin on next
  open. Mitigated: the flow exists and is tested; the report confirms
  Brannock and Nell re-pin quietly and their sheets are unchanged.
- **If the slice proves too big at implement**, the designated cut is
  rolled hit points (requirement 6 and its stories), which become
  `dnd-hp-dice`; ability-score rolling with history, entry, and tags is
  the first half and stands alone. The gate is explicit: if the score
  stories are not green by the midpoint of the ticket list, cut then,
  not at the end. Recorded, not executed.
- **Accepted:** rolled scores are not offered by random mint (it pins
  the array); a rolled character comes from the wizard.

## Out of scope

- Reroll policy of any kind (limits, "reroll if below", DM approval),
  DM-configured table rules — a later slice with a table.
- Rolling anything else: attacks, saves, checks, Second Wind — Epoch 8.
- Any dice in PF2e; PF2e hit points are fixed by rule.
- Rolled hit points at level 1 (the SRD fixes them); levels 4+.
- Rolling in random mint or quick build; a digital-dice animation.
- Editing or deleting a recorded set; retroactive tags; DM overrides —
  edits-and-exceptions.
- Anything on a recorded input beyond faces: modifiers, advantage,
  keep-highest rules, target numbers, timestamps. The shape is sides,
  dice per group, groups, origin — what Epoch 8 layers on top is Epoch
  8's.

## What Ben checks

- Walk "the roll" end to end and hand-verify every total from its four
  faces (drop the lowest, sum the rest), then the sheet's six scores
  from totals plus the background increases.
- Walk "the reroll" and confirm the old set is still visible in the card
  and in the file, the assignment was cleared with a confirm that said
  so, and the new set is the one the assignment offers.
- Walk "the physical dice" (entry is how you force the cases app dice
  leave to chance): an out-of-shape face is illegal with the rule named
  before confirm; two identical sets assign to two abilities; 18 plus
  the +2 reads 20 with a clean checklist; the entered set is tagged
  entered; an app roll after it is tagged rolled and both are listed in
  order. Walk "the double tap" and count the sets.
- Walk "the hit die" and hand-verify the sheet's HP breakdown at both
  levels; confirm the history kept the discarded 3 and the entered 7 is
  tagged; open Brannock and confirm his file bytes and his HP are
  unchanged. Walk "the abandoned level" and confirm the file holds no
  trace of the abandoned rolls.
- Walk "the crash" a few times and confirm the log never holds a torn or
  duplicated set; close and reopen the tab after a roll. Walk "the
  clone" and compare the two files' roll histories.
- Walk "the skeptical inspection": read the roll decision in the file —
  would a stranger understand what was rolled, by whom, and in what
  order? Tamper with a face; `verify` catches it.
- Walk "nothing else moved" on both campaigns, including a fresh
  Standard Array and a fresh Point Buy character.
- Start the server with the seed flag on the 5.5e campaign: the badge
  is there; roll Ysolde twice under the same flag on two fresh clones
  and compare — identical faces; restart without the flag: no badge,
  and a roll differs. Read a file written under the flag: faces only,
  no seed.
- Intent check on the substrate: read the recorded-input shape in the
  file — is it obviously how an attack roll or a saving throw would be
  recorded later, or is it ability-score-shaped? Would a future redo
  of this roll need anything but this file?
- Intent check on the record: does keeping every reroll, visibly, feel
  like the right relationship between player and DM — the log shows,
  the DM decides — rather than either a nag or a hiding place?

## Review record

| Role | Verdict | Folded in |
|---|---|---|
| risk-reviewer | advice | history inside the one decision with the server's extension rule (req 4); version guard, origin judged only at the routes, late retry (req 2); apply-time shape check (req 3); `verify` sees the live set, unbounded history, abandon discards (Risks, req 6); per-level minimum, levels 2–3 (req 6) |
| user-advocate | advice | physical dice carried to a finalized sheet with forced duplicates and the cap; the double tap replaces the network retry; hit-die physical entry; the abandoned level; tab close; clone check line; "ordered" not "dated" |
| scope-warden | advice | one checkpoint; cut gate at the midpoint (Risks); substrate bounded to faces (Out of scope); history location stated (req 4); levels 2–3 named (req 6) |
