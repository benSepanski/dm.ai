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

- [f] **1. Step badges: green ✓ on Equipment before a class exists** conflates
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

## Answered without change

- Details step ✓ at start: correct — the roster's working name is a real
  confirmed decision on the name slot.
- Unconventional Weaponry / Adapted Cantrip / Ancient Elf / Otherworldly
  Magic are intentionally visible-but-unavailable with reasons (report
  decisions 2–3); un-greyed by future data slices, never selectable here.
