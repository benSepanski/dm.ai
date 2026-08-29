---
slug: chargen-wizard
status: approved
---

# Chargen slice 3: PF2e Wizard — spellcasting enters the wizard

## Problem

The creation wizard handles the Fighter with full Player Core breadth, but
nothing in the system knows what a spell is. Per the vision roadmap, the PF2e
Wizard is the slice that forces the spellcasting shape — tradition, spellbook,
daily preparation, slot ranks and heightening, focus pools — inside one system
before any cross-system abstraction of it, and it is the first test of the
claim the architecture was built on: adding a class is rules data plus slot
definitions in the ruleset crate, not core code.

This slice also owns a decision the vision explicitly delegates to it: where
"prepared today" lives. Daily preparation is a recurring, revisable choice —
it must reuse the slot/validation machinery without becoming a permanent
decision-log entry, the first exercise of Epoch 8's scope-agnostic-choice
commitment.

## Requirements

1. "Create character" offers the Wizard alongside the Fighter. The guided
   wizard follows the same creation sequence; the Wizard's class step covers
   the class's decisions: arcane thesis, arcane school (curriculum), the
   arcane bond / level-1 class feature choices, the class feat slot,
   spellbook selection, and initial preparation — with the rules-published
   counts and constraints (spellbook size, prepared cantrips, rank-1 slots,
   the school's curriculum-restricted extra slot), finalized against
   Archives of Nethys at implement.
2. The finalized sheet derives and displays the spellcasting block: spell
   attack and spell DC, spell slots by rank, the spellbook, prepared spells
   (distinct from the book), focus pool with the school's focus spell, and
   cantrips at their auto-heightened rank. All values derived, never
   hand-entered.
3. Prepared spells live in a **play-scoped preparation section** of the
   character file — alongside, never inside, the decision log. It is bound
   to the class's slot structure, validated by the same engine machinery
   ("only spells in your book, only as many as you have slots per rank,
   curriculum slots only from the curriculum"), and replaceable wholesale
   without appending to or rewriting the log. Chargen's final class step
   fills the initial preparation, so the finalized sheet is table-ready.
   The finalized sheet view carries one affordance — "change prepared
   spells" — that reopens just the prep picker, saved with the same
   durability **and stale-view/retry** discipline as wizard confirms: a
   retried save appends nothing twice, and a save from a stale view is
   rejected with a reload prompt, never silently interleaved. Build choices
   stay locked.
   (Decided 2026-08-29 — the first exercise of the vision's
   scope-agnostic-choice commitment, proven end-to-end rather than only
   structurally.)
4. Class addition is data + slot definitions: engine-core is unchanged, and
   any engine-core diff that proves necessary is listed and justified in the
   implement report — that list is a first-class deliverable of the slice,
   since this is the experiment the slice runs. All Wizard semantics live in
   `ruleset-pf2e` modules and rules-data records.
5. Content breadth is a **representative subset** chosen to exercise every
   mechanism, mirroring the Fighter slice: two arcane theses, 2–3 schools
   with their curricula and focus spells, and a cantrip/rank-1 spell list
   covering an attack-roll spell, a save spell, a non-damaging utility
   spell, and cantrip heightening display. Full Player Core wizard breadth
   is a follow-up data-only slice (`wizard-content`) through the existing
   content pipeline, which also owns the Wizard's quick build.
6. Heightening ships at the depth level 1 requires: cantrips display at
   their auto-heightened rank, and spell records transcribe their
   heightening entries as structured data even though nothing casts at a
   higher rank yet — an accepted speculative cost, bounded by the
   transcribe-only rule: the heightening schema captures exactly what the
   printed entries state, nothing designed beyond them.
7. Spell and class records carry the mechanical fields the printed rules
   state discretely (per the vision's transcribe-mechanics commitment):
   action cost, components/traits, range/area/targets, duration, defense,
   heightening — structured, transcription never invention, even where this
   slice only displays them. License metadata and reference checks flow
   through the existing content pipeline.
8. Existing characters and flows are untouched: every pre-slice character
   file loads unchanged, the Fighter path through the wizard is unchanged,
   and any character-file schema change follows the established
   version-and-migrate discipline. `verify` still replays every character
   cleanly, including wizards whose preparation has been revised — replay
   covers the decision log; the prep section is validated state, not
   replayed history, and `verify` re-validates it against the engine rules,
   reporting a hand-tampered or illegal preparation the same way it reports
   sheet divergence. Absence of a prep section is valid (non-preparing
   classes, every pre-slice file). Since this slice's data ships as a new
   rules-data version, existing characters land in the established
   quiet-re-pin state on first open — no review flags from purely additive
   data.

## User stories & flows

- **First wizard.** Ben creates "Maribel", a Gnome Wizard: ancestry through
  details as before, and at the class step picks a thesis, a school, her
  arcane bond, a class feat, her spellbook (watching the count constraints
  tick), and her initial prepared spells — the prep picker showing only her
  book, per-rank slot counts, and the curriculum restriction on the school
  slot. The finalized sheet shows spell DC and attack, slots by rank, book
  vs prepared clearly distinguished, her focus spell and pool, and cantrips
  at rank 1 — all matching a hand calculation.
- **The pencil edit.** A session later, Maribel swaps a prepared spell from
  the sheet view's "change prepared spells": the picker enforces the same
  rules, the change survives a server restart, and the character file shows
  a byte-identical decision log with only the preparation section changed.
- **Illegal prep, caught.** Ben tries to prepare a spell not in the book,
  then to overfill rank 1, then to put a non-curriculum spell in the school
  slot: each shows a checklist entry naming the rule, and finalize (or prep
  save) stays blocked until the prep is legal. He swaps in a legal spell and
  watches the entry clear and finalize unblock.
- **The changed mind, cascaded.** Mid-wizard, with spellbook and prep
  already set, Ben changes Maribel's arcane school: the confirmation lists
  exactly what will be cleared (the curriculum slot's preparation, the
  school's focus spell), the checklist reopens those decisions, and
  everything school-independent — spellbook entries, other prepared slots —
  survives untouched.
- **The crash.** kill -9 between confirming the spellbook and finishing
  prep; restart; resume lands exactly at the prep step with the spellbook
  and every earlier class-step choice (thesis, school, bond, class feat)
  intact.
- **Nothing else moved.** Torvald (the Fighter) still opens unchanged; a new
  Fighter runs through the same wizard as before, no spell steps anywhere.
- **The skeptical inspection.** The wizard's file reads like the Fighter's:
  a recognizable sheet, an ordered decision list, and a small separate
  "prepared" section a human can read; hand-tampering the sheet is still
  caught by `verify`, and revising prep never trips it.

## Risks

- **Prepared-today modeled wrong** poisons both Epoch 8 (daily prep flows)
  and the 5.5e slice (a different preparation model). Mitigated: the
  play-scoped section was decided deliberately in dialogue; the 5.5e slice
  is budgeted to bend the shape, not assumed to fit it.
- **Spell records are the largest, most field-rich records yet**; both
  transcription errors and schema speculation scale with them. Mitigated:
  representative subset first, transcribe-only-discrete-fields rule, the
  existing reference-check pipeline, golden-sheet hand verification.
- **The class-addition claim fails** — the Wizard turns out to need
  engine-core changes (e.g. the prep-scope machinery itself). Accepted as
  the experiment's honest outcome: the change lands, listed and justified
  in the report, and the finding feeds the architecture rather than being
  hidden. (The prep section is new core-adjacent machinery by design;
  "unchanged engine-core" applies to the build/decision path.)
- **Scope creep via spell browsing**: a spell list invites search, filters,
  and a reader UX. Mitigated: a simple list with rank/school grouping is
  enough at subset size; real browsing UX is `wizard-content`'s problem.
- **Character-file schema change risk**: adding the prep section touches
  every file's schema envelope. Mitigated: additive change under the
  existing version discipline; req 8 makes old-file loading a requirement,
  and the first real migration lands here if one is needed.
- **The prep save is the first-ever write to a finalized character file** —
  until now those were write-once, and a bug here could corrupt a finished
  character's log. Mitigated: the crash harness covers the prep-save path,
  and a log-untouched assertion (decision log byte-identical across prep
  saves) is part of the slice's checks, not just manual inspection.
- **Later rules data can invalidate a stored preparation** (a
  `wizard-content` correction to a spell or curriculum record). Handled by
  the established divergence principle: surfaced via `verify` and the prep
  picker's checklist, the sheet still loads, nothing is auto-rewritten.
- **If implement stalls, the designated first cut** is the post-finalize
  "change prepared spells" affordance — the prep section itself and initial
  preparation at chargen are never severable, since they carry the slice's
  structural claim.
- **Accepted:** familiars (and the class feats that grant them) are excluded
  from the subset — a companion entity is its own scope; players who want
  one wait for a later slice.

## Out of scope

- Casting anything: no actuation, no slot expenditure at play, no rest or
  re-preparation flows beyond the sheet-view prep edit — Epoch 8 owns play.
- Full Player Core wizard breadth and the Wizard's quick build
  (`wizard-content` follow-up slice).
- Familiars and familiar-granting feats; rituals; scrolls, wands, staves,
  and magic-item mechanics beyond the basic gear list.
- Any second spellcasting class or tradition beyond what the Wizard needs;
  no cross-system spellcasting abstraction (the 5.5e slice owns that
  stress test).
- Learning new spells after creation (level-up slice); heighten-at-cast;
  spell slots above rank 1.
- Editing finalized build choices (later Epoch 1 slices) — only prepared
  spells are revisable post-finalize.

## What Ben checks

- Walk "first wizard" end to end and hand-verify the spellcasting block
  against the Player Core / Archives of Nethys: spell DC and attack, slots
  by rank (including the school's extra slot), prepared counts, focus pool,
  cantrip rank.
- Walk "the pencil edit": change prep from the sheet view, restart the
  server, confirm it stuck; open the character file and confirm the
  decision log is untouched with only the prep section changed; run
  `verify` and confirm it is clean. While there, confirm the finalized
  sheet offers no way to change any build choice — only prepared spells.
- Walk "the changed mind": mid-wizard with spellbook and prep set, change
  the arcane school; confirm the prompt lists exactly what will clear (the
  curriculum slot's prep, the focus spell) and the checklist reopens those
  decisions while everything school-independent survives.
- Walk "illegal prep": not-in-book, overfilled rank, non-curriculum in the
  school slot — confirm each checklist entry names the rule and clears when
  fixed.
- Walk "the crash" at the class step: kill -9 between spellbook and prep,
  restart, confirm resume lands at prep with the book intact.
- Open a pre-slice Fighter and create a new one: confirm nothing about the
  Fighter path changed.
- Spot-check three spell records (a heightening cantrip, a save spell, the
  school focus spell) against Archives of Nethys — including the structured
  mechanical fields (action cost, defense, duration, heightening), not just
  display text.
- Intent check on the experiment: read the implement report's engine-core
  diff statement — does "adding a class is data + slot definitions" feel
  true, and if the engine did change, do the reasons read as honest
  findings rather than quiet scope creep?
- Intent check on the class step feel: is the spellbook-then-prep flow
  something you'd hand a new wizard player at a table?

## Review record

| Role | Verdict | Folded in |
|---|---|---|
| risk-reviewer | advice | stale-view/retry discipline on prep saves (req 3); first-write-to-finalized-file risk with log-untouched assertion; `verify` re-validates prep, absent-section validity (req 8); stored-prep-invalidated-by-data risk |
| user-advocate | advice | "changed mind" cascade story + check; illegal-prep story closed to resolution; locked-build-choices check; crash resume asserts all class-step choices |
| scope-warden | advice | designated-first-cut line (sheet-view prep edit); heightening transcription owned as bounded speculative cost (req 6); quiet-re-pin clause for existing characters (req 8) |
