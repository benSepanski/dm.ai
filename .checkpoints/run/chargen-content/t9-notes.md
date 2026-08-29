# T9 — UI breadth (spec req 8, walks 1–10)

## What shipped

Zero Rust changes — the architecture's litmus test held. Everything is
presentation over the existing render-ready option arrays.

- **Text filter** (`ui/src/SlotCard.tsx`): any option list with more than
  `FILTER_THRESHOLD = 15` entries gets a case-insensitive text filter
  matching name + summary, with a shown/total count and a "No options
  match" state. It lives in the shared slot editors (single/radio, multi/
  checkbox, and list/add-row pickers), so every step gets it without
  per-step forks: 39 backgrounds, the 16-entry trained-skill list, the
  16-entry Aiuvarin feat union, the 67-entry general-feat chooser, and the
  162-item shop. The boost `<select>` editors top out at 6 attribute
  options and can never cross the threshold. Filter state is ephemeral
  editor state: `SlotEditor` is keyed by slot id, so the query clears on
  slot change (and greyed options stay visible, with reasons, under
  filtering — the filter narrows by text, never by availability).
- **Equipment grouping**: the shopping list (`presentation_hint:
  "shopping-list"`) groups its add-rows under Weapons / Armor / Shields /
  Adventuring gear headers. The data already arrives categorized — every
  equipment option ID is namespaced (`weapon.`, `armor.`, `shield.`,
  `gear.`) — so grouping is a pure ID-prefix partition in the UI. The one
  filter spans all groups; emptied groups drop their headers. The kit slot
  is untouched.
- **CSS**: `.option-filter`, `.option-filter-count`,
  `.option-group-heading` in `app.css`.

## Tests

- **Vitest** (`ui/src/SlotCard.filter.test.tsx`, 11 tests): threshold
  boundary (15 no / 16 yes) across all three editor kinds;
  case-insensitive name and summary matching with the shown count;
  no-match state; greyed-remains-visible-with-reason under filtering;
  clear-on-slot-change; shop grouping headers; filter-across-groups
  dropping emptied headers; plain lists stay ungrouped.
  Whole ui suite: 31 passed.
- **Playwright** (`ui/e2e/walks1|2|3.spec.ts` + shared `e2e/helpers.ts`,
  same real-server harness as `stories.spec.ts`): all ten walks
  automated. Suite total 20 passed (10 slice-1 stories + 10 walks).
  - Walk 1: linear Leshy — Leaf Leshy, Seedpod, Nomad with typed "Steppe"
    Lore, Int-driven language chooser (leshy list), background filter,
    grouped+filtered gear purchase; finalized sheet asserts HP 21, AC 17,
    Fort +8, Small/Speed 25/low-light line, "Languages = Common, Fey,
    Elven", "Steppe Lore = trained", Coins 5 gp 7 sp.
  - Walk 2: backwards Gnome — shop before anything, checklist-driven
    completion by clicking entries (each jump asserted), Scholar
    in-background skill pick with Assurance (Nature) following on the live
    sheet, kit demand appearing once a class exists, finalize unblocking
    the moment the checklist clears.
  - Walk 3: Halfling→Orc cascade — the prompt lists exactly the four
    ancestry-dependent clears (and not the free boosts), checklist
    reopens, re-pick leaves no halfling residue.
  - Walk 4: Dwarf + Aiuvarin — offered beside dwarf heritages; feat list
    is the dwarf+elf+Aiuvarin union (filter finds both sides); greyed
    Otherworldly Magic keeps its reason under filtering.
  - Walk 5: chooser chain — Versatile Human → 67-entry chooser → Battle
    Medicine greyed "requires trained in Medicine" → Canny Acumen → save
    chooser → Will +3 → +5 (expert) on the live sheet.
  - Walk 6: quick build — checklist empty, suggested badges on, swap the
    class feat (badge flips off, neighbours keep theirs), rename,
    finalize.
  - Walk 7: fill-remaining — hand-built Leshy/Nomad choices byte-stable
    and badge-free after the fill; filled slots badged; finalizes.
  - Walk 8: stubborn draft — Dexterity key attribute confirmed first
    stays a player decision; fill adapts (with the
    remainder-on-checklist branch also asserted structurally).
  - Walk 9 (UI leg): replicates the `checks/version_guard.rs` fixture in
    the harness — real characters doctored to a fabricated prior version,
    server restarted with the hidden `--extra-known-versions` flag
    (`TestServer.extraArgs`). Asserts both roster badges, the divergent
    old-vs-new diff table (stored sheet untouched until accept), accept
    clearing the flag, and the identical-case quiet re-pin. Server-side
    behavior remains covered by `checks/version_guard.rs`.
  - Walk 10: greyed shelf — Fey-touched and Wellspring Gnome and
    Unconventional Weaponry visible, disabled, with their full
    "no entries in this rules-data version" reasons.

## Gates

- `npx tsc --noEmit` ✔, `npx eslint .` ✔, `npx vitest run` 31 passed.
- `npx playwright test` 20 passed (~30 s).
- `cargo test -p checks` green (61 passed) — no crates/rules-data
  changes in this ticket. Note: the first post-checkout run showed a
  stale-binary attestation failure that vanished on rebuild; nothing in
  this ticket touches attested data.
- `ui/dist` rebuilt from the final sources.

## Notes / deviations

- `ui/e2e/server.ts` gained an `extraArgs` field (test-support only) so
  the Walk 9 UI leg could pass the hidden flag; no production surface
  changed.
- Dynamic multi-slot counts (trained skills growing with Int, language
  counts) are handled by a fill-until-the-counter-says-full helper in
  `e2e/helpers.ts` rather than hard-coded counts, so data corrections
  don't brittle the walks.
- No new testids beyond `option-filter` were needed; existing
  class/testid hooks covered the assertions.
