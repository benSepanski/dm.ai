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

---

# Round 2 findings (Ben's interactive review, 2026-08-30 — gathering, not yet actioned)

8. **Curriculum marking too subtle.** The only in-list signals are sort
   order (invisible as a signal — nothing separates the curriculum group)
   and a plain-prose prefix at the head of the soft-gray summary line,
   easy to read past while scanning names. Direction: make curriculum
   spells stand out — a visible badge/chip next to the name and/or a
   labeled group header ("Battle Magic curriculum" / "Other arcane
   spells"); must survive filtering.

9. **Confirmed selections hide their details.** A confirmed slot collapses
   to name + "Change…"; the chosen option's details (school curriculum,
   thesis text, spell stats) are unreachable without undoing the
   selection. Direction: hovertip and/or an expand affordance on confirmed
   values so details stay readable after commitment.

10. **"Curriculum 3 of 2" reads as an error.** The meter shows the raw
    tally of curriculum spells in the book against the minimum, so
    exceeding the minimum renders as overfill ("3 of 2") and looks like an
    illegal selection. A requirement meter must cap at its target:
    min(count, need) of need ("2 of 2" once satisfied — generally N of N).
    Conceptually the first two curriculum picks fill the school's added
    slots; further curriculum spells are just free picks. Consider also
    marking which chosen spells count as the curriculum picks.

11. **Skill collision attribution is backwards.** With Acrobatics chosen
    as a free class skill, changing background to Acrobat left Acrobatics
    attributed "from Wizard" and spawned a fourth "replacement skill"
    card for the background's grant. Direction: fixed grants win ownership
    and attribution (sheet says "from Acrobat"); the player's free pick is
    what becomes redundant and re-judges in the trained-skills card they
    already know. Design note for actioning: fixed-vs-fixed collisions
    (background granting Arcana on a Wizard) have no free pick to hand
    back — the unified model is likely "any collision adds one to the free
    trained-skills count", dissolving the replacement-slot machinery
    rather than flipping its precedence. Mechanically identical to RAW's
    "select another skill".

12. **Finalize dead while the checklist says "ready" (blocker).** Repro:
    all slots confirmed, sidebar shows "Everything checks out — ready to
    finalize", Finalize disabled; going back to the roster and re-entering
    un-sticks it. Diagnosed root cause: the button gates on unconfirmed
    tentative edits — `disabled={!can_finalize || pending.length > 0 ||
    busy}` (Wizard.tsx) — and `pending` leaks: ANY interaction with an
    open editor (toggle a checkbox off and on, touch a preloaded picker,
    keystroke in a text field) records a pending entry that only a confirm
    of THAT slot clears. A no-op edit equal to the confirmed selection
    still counts, is visually indistinguishable from no edit, may live on
    another step, and nothing on screen explains the dead button. The
    roster roundtrip works because remounting the wizard resets the
    in-memory pending map. Fix directions: (a) clear a pending entry when
    the tentative selection equals the confirmed one; (b) when pending
    edits do block finalize, say so and where ("unconfirmed changes in
    Spellbook: rank-1 spells", click-to-jump) instead of a silently
    disabled button; (c) testing gap — no e2e story drives a no-op edit
    then finalizes; the layout sweep can't catch dead-control semantics.

    **Agreed design for 10 (Ben, 2026-08-30): abstract meter semantics
    into code, not just a test.** Two constructors on `MeterView` in the
    types crate — `requirement(label, have, need)` (progress toward a
    minimum: displays min(have,need) of need, Ok at threshold; over-
    satisfaction invisible — curriculum) and `capacity(label, used, cap)`
    (bounded resource: displays the true value, explicit Over state the
    UI styles as an error, never clamped — book size, budgets, counters).
    Rulesets stop hand-formatting; display and state can no longer
    disagree. Property test covers the constructors once; a checks/ lint
    bans raw `MeterView { … }` literals outside the types crate.

---

# Round 2 resolutions (landed 2026-08-30, same branch)

Root-cause classes from the post-assessment: goal-directed testing bias,
invisible state gating distant controls, presence≠salience, resting states
under-designed, implementation order as silent policy. Every fix below
pairs the visible change with the structural guard for its class.

8. **Curriculum visibility** — options carry structured `group` + `badge`
   fields (types crate); the rank-1 picker splits under labeled headers
   ("School of Battle Magic curriculum" / "Other arcane spells") with a
   CURRICULUM chip on each curriculum row. The chip rides the row, so it
   survives filtering; the prose prefix is gone. Pinned by the
   first-wizard story and `groupedRows` unit tests.

9. **Details after commitment** — confirmed cards grow a "Details ▼"
   expansion listing each chosen option's summary and full details (the
   school card shows its curriculum and focus spell in place). Pinned by
   the details-stay-readable story.

10. **Meter semantics in code** — `MeterView::requirement/exact/budget`
    constructors in the types crate compute display and state together
    ("3 of 2" is unrepresentable; capacity/budget overshoot always shows
    true numbers). All three call sites converted; a checks lint bans raw
    `MeterView` literals outside types; constructor property tests in the
    types crate. Pinned by the overshoot story ("8 of 7 — over the
    limit") and the capped "2 of 2" assert.

11. **Skill ownership policy** — `skill_resolution` now resolves fixed
    grants FIRST: grants own a skill and its attribution ("from
    Background: Street Urchin"); a redundant grant or class skill
    converts into one extra free trained pick (the printed "select
    another skill instead" rule); a free pick landing on an owned skill
    re-judges in its own card ("Thievery now comes from … — pick a
    different skill"). The replacement-slot machinery is deleted. Because
    stored logs could reference the removed slots, rules-data bumped to
    pf2e-pc.0.3.1 (supersedes 0.3.0; the version guard's repair flow
    covers older drafts — no live campaign log contained a replacement
    decision). Krivvy's golden rebuilt as the ownership story; ruleset
    unit tests cover grant-owns and redundant-class-skill, and the new
    owned-skill e2e story walks it in the UI.

12. **Finalize gate made honest** — three layers:
    (a) no-op edits are unrepresentable: option lists compare as sets and
        an emptied field on an unconfirmed slot is a no-op
        (`sameSelection`/`isRealEdit`, unit-tested), with pending entries
        pruned against every draft reload;
    (b) real unconfirmed edits are visible: an "Unconfirmed changes" chip
        under Finalize lists each slot with a jump link, the sidebar
        banner says "confirm your unconfirmed changes" instead of "ready
        to finalize", and leaving to the roster warns before discarding
        (a conflict reload now keeps in-progress edits too);
    (c) the class is banned: the layout sweep gained a dead-control
        invariant — a disabled action button with no visible explanation
        (aria-describedby → rendered text) fails every walk on every
        screen; every confirm button now renders its reason ("Pick one to
        continue."), and "Fill remaining" hides when moot instead of
        disabling silently.
    Pinned by the meander story (no-op → enabled; real edit → chip,
    banner, leave-guard; confirm → finalize).

    Bonus from the owned-skill story: a slot made illegal *indirectly*
    (school change, background grant) now shows its checklist message at
    the card, not only in the sidebar.

Predictions verified: (d) Int-shrink re-judge existed and is now pinned
(`shrinking_intelligence_rejudges_over_count_skill_picks`); (f) budget
meter shows negative remaining, never clamped; (g) quick-build is honest
("Quick build a Fighter"); (j) language duplicates blocked by data
integrity + dedup validator. Deferred to Epoch 8: sheet-side spell
details (same resting-state class as finding 9).
