# chargen-wizard — review findings (gathering before fixing)

Reported by Ben while walking the report's verification stories; fixes land
together on this branch once gathering is done.

2. **Prep tray overflows and hides its remove buttons.** The picked-items
   list in List slots (prep cantrips/rank-1) renders each item's full
   summary text unwrapped; long spell texts overflow the card horizontally
   and push the per-item "remove" buttons out of view — making overfill
   easy to enter and hard to leave. Fix: the tray should show name (+ a
   clamped/wrapped summary or none at all) and keep remove always visible.
   **Testing gap this exposes (the core property):** nothing asserts that
   arbitrarily long content never breaks layout. Remedy: an e2e layout
   invariant — after rendering the wordiest records, every `.slot` card
   satisfies `scrollWidth <= clientWidth` (no horizontal overflow) and its
   action buttons are within the viewport-visible card box; run it over
   the wizard walk (spells are the longest strings shipped).

3. **Duplicate preparation.** Same spell can be Added repeatedly.
   Rank-1 slots: rules-legal (same spell in multiple slots) — keep, but
   the UX should make the count/duplicates visible (tray grouping "×2"
   instead of repeated rows would also shrink the tray). Cantrips:
   duplicates are pointless and read as a bug — make prepared cantrips
   distinct (validator flags duplicates as Illegal, or the Add button
   greys once picked). Decide: distinct-for-cantrips, repeatable with
   visible grouping for rank-1.

4. **Prep-at-chargen feels wrong** ("shouldn't I just be choosing my
   spellbook?"). The data model already separates prep from the log; the
   friction is that the wizard REQUIRES initial prep before finalize (the
   spec's "table-ready" decision) and renders prep slots inline with build
   choices. Options: (a) keep required but visually distinct pencil
   section; (b) prep optional at chargen — finalize with a blank prepared
   column, fill later from the sheet's existing picker; (c) no prep at
   chargen at all. NOTE: (b)/(c) revise approved spec req 3 (frozen-doc
   flow, diff-sized re-approval) — Ben to decide when gathering is done.

5. **Spellbook-change cascade is disproportionate (weird UX).** Changing
   the curriculum picks (or any spellbook slot) clears ALL dependent
   rank-1/cantrip preparation wholesale — even entries still legal under
   the new book. Proposal: drop the spellbook→prep dependent edges;
   because prep is validated state (not replayed history), a book change
   simply leaves any now-unbacked prep entry flagged Illegal on the
   checklist ("no longer in your spellbook") to fix in the picker —
   guardrails, not walls. Keep the school→school-prep clearing edges (the
   architecture's cascade row mandates those, and they're the cascade the
   spec's story wants). Sub-item: "Change…" on a complete Multi slot
   should reopen the editor preloaded with current picks (amend-in-place)
   instead of the clear-everything ceremony. NOTE: the implemented
   spellbook→prep edges were an implement-stage choice, not an
   architecture mandate — removing them stays inside the contract; the
   cascade-exactness check keeps covering the school edges.

6. **Curriculum slot can become unsatisfiable (diagnosed from screenshot).**
   Free rank-1 picks overlapping the school curriculum grey those
   curriculum options ("already in your spellbook"); with a 3-spell
   curriculum and 2 overlaps, only 1 legal pick exists for a 2-pick
   requirement — Confirm partial-saves forever, reads as "nothing
   happens", and the draft can never finalize. Fix: the slot's required
   count adapts to min(spellbook_curriculum_rank1, curriculum spells not
   already in the free book), with the meter/checklist explaining the
   shrink ("2 curriculum spells are already in your book"); alternatively
   surface an explicit conflict entry steering the player to change free
   picks. Also: partial-confirm feedback ("Saved — 1 left") is a 5-second
   ack that reads as nothing — persist the saved-partial state at the
   card.

7. **Spellbook split across three slots forces player-side bookkeeping.**
   Free rank-1 picks and curriculum additions as separate cards make the
   player track which spells are curriculum, with clear-and-change loops
   when they guess wrong. Fix: ONE spellbook slot per rank — rank-1 is
   Multi{5 or 7 (school-dependent)} with a validator "at least 2 from the
   curriculum once a school is chosen", curriculum options badged, second
   meter for the minimum. Subsumes the #6 dead-end (any 7 with ≥2
   curriculum is legal) and shrinks #5's cascade surface (one slot).
   Note: slot restructure invalidates in-flight wizard DRAFTS from this
   branch (Ben's test characters) — the existing repair/resolve flow or
   deletion covers them; nothing merged is affected.

1. **Class-skill source label hardcoded "Fighter".** A Wizard's Arcana
   shows "already trained (from Fighter)" in the Trained skills card.
   Cause: `Pf2eState::skill_resolution` pushes the class skill choice with
   the literal source `"Fighter"` (slice-1 leftover); it should be the
   chosen class's name. Also affects the sheet's per-skill detail line
   ("from Fighter"). Fix: resolve the class record's name (state has only
   the id — thread the class name through state or resolve in callers).

---

# Resolutions (rework landed 2026-08-30, commit series through this branch)

The findings triggered a contract revision: spec + architecture rewritten
and re-approved (spec 5a2924b1, arch 4d89c0b2), preparation moved out of
the epoch entirely (vision: Epoch 8 rung 5 owns it), and the wizard rebuilt
to build-decisions-only. Per-finding outcome:

1. **"from Fighter" label** — fixed. `Pf2eState.class_name` is resolved
   from the chosen class record at apply; both hardcoded literals (skill
   resolution + trained-skills apply) removed, plus a "Choose Acrobatics or
   Athletics" message that named Fighter's choices. Now structural: the
   `checks/class_isolation.rs` lint fails the build on any shipped record
   name appearing as a ruleset source literal, and the contamination sweep
   builds a complete character per class and asserts other classes'
   vocabulary is absent from projection and sheet.

2. **Tray overflow / hidden removes** — fixed and generalized. Tray rows
   are grouped with clamped text and always-visible removes; the core
   property is now enforced: `ui/e2e/layout.ts` (`expectSaneLayout`) checks
   page overflow, element overflow, starved columns, and clipped/offscreen
   enabled controls — wired into the shared helpers so EVERY step visit in
   every e2e walk sweeps the screen, plus a wordiest-content stress spec at
   desktop and tablet widths (`ui/e2e/layout.spec.ts`). The sweep also
   caught a real tablet-width bug during hands-on testing (main column
   starved to a sliver), fixed with a responsive single-column stack.

3. **Duplicate picks** — resolved by the set/bag rule (architecture):
   checkbox sets make duplicates unrepresentable (spellbook is a set);
   bag trays (equipment) group as "×N" with per-group removes. A UI unit
   suite pins kind→control mapping. Prepared-slot duplicates left with
   preparation (Epoch 8).

4. **Prep at chargen feels wrong** — Ben chose (c): no preparation in
   character creation at all. The sheet states "Preparation: at the table".
   The validated scoped-choice design is recorded in the vision for
   Epoch 8; the engine machinery for it was fully reverted.

5. **Disproportionate cascade** — moot for prep (gone); for the school:
   the school slot has NO dependents. Changing school destroys nothing;
   the curriculum validator simply re-judges the standing book (checklist
   entry, fix in place). Pinned by `changing_school_rejudges_instead_of_
   clearing` and the changed-mind e2e story.

6. **Unsatisfiable curriculum slot** — impossible by construction: the
   unified picker never greys curriculum options; the requirement is a
   validator over the one slot ("at least 2 of these 7 from the
   curriculum"), so any full book with ≥2 curriculum picks is legal.
   `every_school_has_a_satisfiable_spellbook_and_no_dead_ends` proves it
   for every shipped school. Partial/illegal confirms now persist at the
   card (`slot-error`), not as a 5-second ack.

7. **Three-slot bookkeeping** — the spellbook is ONE slot per rank:
   cantrips Multi{10}, rank-1 Multi{5 or 7, school-dependent} with
   curriculum options sorted first and badged, a Curriculum meter, and the
   minimum enforced in place. No player-side tracking of which pick "is
   curriculum".
