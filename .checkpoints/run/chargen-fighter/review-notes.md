# chargen-fighter — report-review notes (running)

Ben is hand-verifying the app; findings accumulate here one at a time
(depth-first). Accept/reject on the report is decided at the end of the
review conversation. Complaint about the missing iterative-feedback channel
logged to complaints.jsonl (2026-08-27).

States: `[ ]` open · `[d]` discussed, decision pending · `[f]` fix agreed · `[x]` resolved/no change

**2026-08-27 decision round:** #2 dropped (future spellcasting slices
un-grey it). #1/#3/#4 fixed together via the generalized design: per-slot
SlotStatus + Waiting step badge, engine meters (auto count meters for Multi
slots + ruleset budget meter deriving its own violation entry), atomic
`amend` op with editor-preloaded Partial slots (option (b)), plus
status/entry coherence proptest invariants. Amend cascades statically —
pure extensions with live replacement slots still prompt; selection-aware
cascades deferred to level-up/retraining.

## Findings

- [x] **1. (fixed) Step badges: green ✓ on Equipment before a class exists** conflates
  "nothing to do yet" with "done" (Details' ✓ was legitimate — working name
  already confirmed). Proposed: fourth `Waiting` StepStatus rendered as a
  hollow badge (types + projection + UI + e2e + fixtures). Awaiting
  end-of-review decision.
- [x] **2. (dropped by Ben) Adapted Cantrip unavailability copy** reads as if it checks the
  not-yet-chosen class; actually grounded as "no spellcasting class in this
  data version" (order-independent). Proposed copy: "requires a spellcasting
  class feature — no class in this rules-data version has one". Ben: "this
  is all fine then" — treat as optional polish unless bundled with #1.
  Slice-3 note: when Wizard ships, this prerequisite becomes state-dependent
  and the ancestry-feat-before-class ordering needs deliberate design
  (lock-until-class vs select-and-revalidate).

- [x] **5. (fixed) Live preview double-counted a partial slot's picks** —
  editing a Partial slot folded the confirmed decision AND the tentative
  replacement into the preview, producing phantom "6 skills selected" /
  "already trained" entries (server state was always correct; regression
  introduced by the amend round, found by Ben in the browser). Fix: the
  hypothetical log replaces, not stacks, a pending slot's decision — amend
  semantics client-side too. e2e now asserts no phantom entries while
  finishing a partial slot.

- [x] **6. (fixed) Select overflow** — disabled boost options embedded the
  full rule sentence; a <select> sizes to its longest option and overran the
  card (overlapping Confirm). Short in-option reasons at the source + CSS
  max-width/flex guard.
- [x] **7. (fixed) Budget meter shows remaining** — "Remaining 9 gp, 2 sp of
  15 gp" (red when over) instead of amount spent.
- [x] **8. (fixed) Silent partial saves** — Ben's "Confirm does nothing":
  the amend HAD saved (Tee hee: Int +2 -> 5 skills required, 4 picked), but
  a save that leaves the slot open was visually identical to a dead click.
  Now: transient in-card "Saved — N left" acknowledgment + sticky notice bar
  so rejections/conflicts can't land off-viewport. e2e asserts the ack.

- [x] **9. (fixed) e2e gaps for conflict + server-down** — closed under the
  adopted testing strategy: e2e samples mechanisms (suite stays ~1:1 with
  spec stories + one story per interaction mechanism), lower layers
  enumerate. Added: SlotStatus x SlotViewKind rendering grid (40 combos,
  jsdom — found and fixed a missing status class on locked cards on its
  first run), dual-tab conflict story (notice + self-reload, no interleave),
  server-down confirm story (explained failure, tentative preserved, clean
  retry on same port). Model-based UI walk parked for Epoch 6.

## Answered without change

- Details step ✓ at start: correct — the roster's working name is a real
  confirmed decision on the name slot.
- Unconventional Weaponry / Adapted Cantrip / Ancient Elf / Otherworldly
  Magic are intentionally visible-but-unavailable with reasons (report
  decisions 2–3); un-greyed by future data slices, never selectable here.

## Fix round outcome (2026-08-27)

All three agreed findings landed in one commit, generalized rather than
patched: per-slot `SlotStatus` + `Waiting` step badge (#1), Partial slots
stay editable and Confirm amends atomically (#3), engine meters with the
budget gauge deriving its own violation entry (#4). Coherence invariants
(test-only, property-walk assertions) pin the class of bug going forward.
New e2e stories: finish-partial-in-place, live budget meter. Full matrix
green; suite 7s warm. Process note: agent started implementing while the
design conversation was still open — Ben flagged it; future rounds hold
until an explicit go.
