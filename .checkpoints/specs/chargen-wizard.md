---
slug: chargen-wizard
status: approved
---

# Chargen slice 3: PF2e Wizard — spellcasting enters the wizard

> Revised 2026-08-30 after the first implementation was reviewed at the
> table. The original spec included the Wizard's daily preparation inside
> character creation; walking it taught the boundary: **the creation
> dialog is for durable build decisions only.** Preparation is session
> state and moved wholesale to Epoch 8's daily-maintenance rung (vision
> revised alongside). This spec is the slimmed slice; the review findings
> (`.checkpoints/run/chargen-wizard/findings.md`) drove the changes.

## Problem

The creation wizard handles the Fighter with full Player Core breadth, but
nothing in the system knows what a spell is. Per the vision roadmap, the
PF2e Wizard is the slice that forces the spellcasting *build* shape —
tradition, the spellbook with its curriculum rules, slots and heightening
as derived facts, the focus pool — inside one system before any
cross-system abstraction of it, and it is the first test of the claim the
architecture was built on: adding a class is rules data plus slot
definitions in the ruleset crate, not core code.

What this slice deliberately does NOT contain (the revision's lesson):
daily preparation. Prepared spells are about getting a player ready for —
or recovering from — a play session, not about creating a character. A
finished wizard's prepared column is empty, like a fresh paper sheet;
Epoch 8 owns every preparation flow, first fill included.

## Requirements

1. "Create character" offers the Wizard alongside the Fighter. The guided
   wizard follows the same creation sequence; the Wizard's class step
   covers the class's durable build decisions: arcane thesis, arcane
   school (curriculum), the arcane bond / level-1 class feature choices,
   and spellbook selection — with the rules-published counts and
   constraints, finalized against Archives of Nethys at implement. A class
   whose advancement table grants no level-1 class feat (the Wizard) shows
   no class-feat slot.
2. The spellbook is **one picker per rank**, never parallel cards the
   player must mentally partition: the cantrip picker asks for the full
   printed count; the rank-1 picker asks for the full count (free picks
   plus the school's curriculum additions) with "at least N from your
   school's curriculum" expressed inside the picker — curriculum spells
   badged in place, a second meter tracking the minimum. No combination of
   earlier picks may make a picker's requirement unsatisfiable.
3. The finalized sheet derives and displays the spellcasting block: spell
   attack and spell DC, spell slots by rank (including the school's
   curriculum-restricted extra slot) and prepared-cantrip counts as
   derived facts, the spellbook, and the focus pool with the school's
   focus spell. All values derived, never hand-entered. No prepared-spells
   section exists yet — the sheet states plainly that preparation happens
   at the table (Epoch 8).
4. Class addition is data + slot definitions: **engine-core is unchanged**
   — any engine-core diff that proves necessary is listed and justified in
   the implement report, and with preparation out of scope the expected
   listing is empty. All Wizard semantics live in `ruleset-pf2e` modules
   and rules-data records. Character storage is untouched (no schema
   change this slice).
5. Content breadth is a representative subset chosen to exercise every
   mechanism, mirroring the Fighter slice: two arcane theses, two schools
   with their curricula and focus spells, and a cantrip/rank-1 spell list
   covering an attack-roll spell, a save spell, a non-damaging utility
   spell, and cantrip heightening display. Full Player Core wizard breadth
   is a follow-up data-only slice (`wizard-content`) through the existing
   content pipeline, which also owns the Wizard's quick build.
6. Heightening ships at the depth level 1 requires: cantrips display at
   their auto-heightened rank, and spell records transcribe their
   heightening entries as structured data even though nothing casts at a
   higher rank yet — an accepted speculative cost, bounded by the
   transcribe-only rule.
7. Spell and class records carry the mechanical fields the printed rules
   state discretely (action cost, components/traits, range/area/targets,
   duration, defense, heightening) — structured, transcription never
   invention. License metadata and reference checks flow through the
   existing content pipeline.
8. The wizard's layout and feedback hold up under its wordiest content
   (spells are the longest prose the UI has ever rendered — the review's
   core lesson): no card ever overflows horizontally or hides its
   controls, and every confirm outcome is visible **at the card**, never
   only at the top of a long step. Both are enforced invariants, not
   review hopes.
9. Existing characters and flows are untouched: every pre-slice character
   file loads unchanged, the Fighter path through the wizard is unchanged
   (including its skill-source labels naming the right class), and
   `verify` still replays every character cleanly. This slice's data ships
   as a new rules-data version; existing characters land in the
   established quiet-re-pin state on first open — no review flags from
   purely additive data.

## User stories & flows

- **The first wizard.** Ben creates "Sylvenne", an Arctic Elf Artisan
  Wizard: ancestry through details as before, and at the class step picks
  a thesis, a school, and her spellbook — one cantrip picker, one rank-1
  picker whose curriculum spells are badged, with both meters ("chosen 6
  of 7", "curriculum 1 of 2") live as she picks. The finalized sheet shows
  spell DC and attack, slots by rank including the school slot, her book,
  and her focus spell — all matching a hand calculation — and a plain note
  that spell preparation happens at the table.
- **The wordy card.** Every spell option shows its full rules text; no
  card overflows, no control disappears, on the longest records shipped.
- **Illegal picks, caught at the card.** Ben overfills the rank-1 picker,
  then picks only one curriculum spell: each state is flagged at the card
  (meter + message), finalize stays blocked, and fixing the picks clears
  the flags where he is looking — never only in a notice scrolled out of
  view.
- **The changed mind.** Mid-wizard, Ben changes Sylvenne's arcane school:
  nothing is destroyed — his spellbook picks stand, and the rank-1
  picker's curriculum meter re-judges them against the new curriculum,
  flagging a shortfall if the new school's minimum isn't met. The focus
  spell follows the school automatically.
- **The crash.** kill -9 after the spellbook is confirmed; restart; resume
  lands at the class step with every confirmed choice intact.
- **Nothing else moved.** Torvald still opens unchanged; a new Fighter
  runs through the same wizard as before, no spell steps anywhere, and his
  Arcana says "from Fighter" while Sylvenne's says "from Wizard".
- **The skeptical inspection.** The wizard's file reads like the
  Fighter's: a recognizable sheet and an ordered decision list — nothing
  else. Hand-tampering the sheet is still caught by `verify`.

## Risks

- **The build/session boundary was learned the expensive way** — the
  first implementation shipped preparation inside chargen and was
  reverted. Accepted cost; the lesson is now vision language ("the
  creation dialog is for durable build decisions") and Epoch 8 inherits a
  validated engine design (scoped choice sets beside the log, in this
  branch's history) rather than a guess.
- **Spell records are the largest, most field-rich records yet**; both
  transcription errors and schema speculation scale with them. Mitigated:
  representative subset first, transcribe-only-discrete-fields rule, the
  reference-check pipeline, golden-sheet hand verification.
- **The class-addition claim fails** — the Wizard turns out to need
  engine-core changes. Accepted as the experiment's honest outcome: the
  change lands, listed and justified in the report.
- **Scope creep via spell browsing**: a spell list invites search,
  filters, and a reader UX. Mitigated: the existing filter-over-options
  machinery at subset size; real browsing UX is `wizard-content`'s
  problem.
- **Accepted:** familiars (and the class feats that grant them) are
  excluded from the subset — a companion entity is its own scope.
- **Accepted:** a finalized wizard is not playable-as-prepared until
  Epoch 8 ships preparation; the sheet says so plainly rather than
  pretending otherwise.

## Out of scope

- **Daily preparation, entirely** — no prep choices, storage, routes, or
  UI in this slice or this epoch; Epoch 8 owns first fill and revision
  alike. (The engine's scoped-choice design validated by the first
  implementation is recorded in the vision and recoverable from branch
  history.)
- Casting anything: no actuation, no slot expenditure at play — Epoch 8.
- Full Player Core wizard breadth and the Wizard's quick build
  (`wizard-content`).
- Familiars and familiar-granting feats; rituals; scrolls, wands, staves,
  and magic-item mechanics beyond the basic gear list.
- Any second spellcasting class or tradition; no cross-system
  spellcasting abstraction (the 5.5e slice owns that stress test).
- Learning new spells after creation (level-up slice); heighten-at-cast;
  spell slots above rank 1.
- Editing finalized characters in any way (later Epoch 1 slices).

## What Ben checks

- Walk "the first wizard" end to end and hand-verify the spellcasting
  block against the Player Core / Archives of Nethys: spell DC and
  attack, slots by rank (including the school's extra slot), focus pool,
  cantrip rank, and the spellbook counts (10 cantrips, 5+2 rank-1 with
  the curriculum minimum).
- Walk "the changed mind": with the book full, change the school; confirm
  nothing clears, the curriculum meter re-judges against the new school,
  and the focus spell follows.
- Walk "illegal picks": overfill the rank-1 picker and shortfall the
  curriculum minimum; confirm each is flagged at the card and clears in
  place when fixed.
- Squint test on wordiness: expand the longest spell descriptions in each
  picker; nothing overflows, every control stays reachable.
- Walk "the crash" at the class step: kill -9 after the spellbook,
  restart, confirm resume with everything intact.
- Open a pre-slice Fighter and create a new one: unchanged, and skill
  sources name the right class on both characters.
- Spot-check three spell records (a heightening cantrip, a save spell,
  the school focus spell) against Archives of Nethys — including the
  structured mechanical fields.
- Intent check on the experiment: read the implement report's engine-core
  diff statement — with preparation out, is it the zero it should be?
- Intent check on the boundary: does the finished wizard feel like a
  complete *character* whose *session* simply hasn't started — rather
  than an unfinished character?

## Review record

| Role | Verdict | Folded in |
|---|---|---|
| risk-reviewer | advice | (original round) stale-view/retry discipline; verify re-validation; superseded by the 2026-08-30 revision — prep rows removed with prep |
| user-advocate | advice | cascade story + locked-build check (original); revision keeps the cascade story in its gentler re-judge form |
| scope-warden | advice | designated-first-cut line; the revision executed a deeper cut than the designated one (prep removed entirely) |
| Ben (implementation review, 2026-08-30) | revision | findings 1–7: prep is session state → out of the epoch; unified per-rank spellbook picker; layout/feedback invariants (req 8); class-source label fix folded into req 9 |
