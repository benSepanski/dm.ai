# Feature map — what the user sees → where it lives

A maintenance aid for UI work: each user-visible feature or flow, mapped to
the code that renders it, the engine/server code that decides it, and the
tests that pin it. Update this table when a feature moves or a new one
ships.

| Feature / flow (user-visible) | UI | Engine / server | Pinned by |
|---|---|---|---|
| Roster: list, create, quick build, delete-to-trash | `ui/src/Roster.tsx`, `App.tsx` | `server/src/routes.rs` (roster/create/quick_build/delete) | `ui/e2e/stories.spec.ts`, `checks/quick_build.rs` |
| Wizard shell: steps, badges, non-linear nav, resume cursor | `ui/src/Wizard.tsx` | `Engine::project` step folding; `routes.rs` set_step | `ui/e2e/walks*.spec.ts` |
| One choice card: options, filter, details, meters, confirm | `ui/src/SlotCard.tsx` | ruleset slot registrations (`crates/ruleset-pf2e/src/*`) | `ui/src/SlotCard*.test.tsx` |
| Set pickers (radios/checkboxes) vs bag trays (Add/×N/remove) | `SlotCard.tsx` `SlotEditor` (kind→control mapping) | `SlotViewKind` in `crates/types/src/wizard.rs` | `SlotCard.test.tsx` kind-mapping suite |
| Live preview while a pick is tentative | `Wizard.tsx` `displayed` memo → WASM engine | `crates/wasm/src/lib.rs` → same engine as the server | `ui/src/engine/parity.test.ts` |
| Confirm feedback at the card (saved-partial ack, refusals, offline) | `Wizard.tsx` `ack`/`cardError` → `SlotCard` | `ConfirmOutcome` in `crates/types/src/api.rs` | `wizard-class.spec.ts` illegal-picks story; `stories.spec.ts` server-down story |
| Change a confirmed choice (dependent-clearing prompt) | `SlotCard.tsx` `ClearConfirmDialog` | `Engine::clear_preview`/`clear` dependents graph | `stories.spec.ts` change-ancestry; `wizard-class.spec.ts` changed-mind |
| Checklist: incomplete vs against-the-rules, jump-to-slot | `ui/src/Checklist.tsx` | slot validators → `ChecklistEntry` | walk specs; engine goldens |
| Wizard class step: thesis, school, spellbook per rank, curriculum meter | `SlotCard.tsx` (generic) | `crates/ruleset-pf2e/src/spells.rs` | `checks/replay.rs` Sylvenne goldens; `wizard-class.spec.ts` |
| Curriculum badges + labeled group split in the rank-1 picker | `SlotCard.tsx` `groupedRows`/`OptionRow` (badge chip) | `spells.rs` `rank1_options` sets `group`/`badge` | first-wizard story; `pending.test.ts` groupedRows suite |
| Meters (requirement clamps; capacity/budget show true overshoot) | `SlotCard.tsx` `MetersRow` | `MeterView::requirement/exact/budget` in `crates/types/src/wizard.rs` | types constructor tests; overshoot story; `checks/class_isolation.rs` literal lint |
| Confirmed cards keep details readable ("Details ▼") | `SlotCard.tsx` `ConfirmedSummary` | option catalogs (render-ready) | details-stay-readable story |
| Finalize gate: unconfirmed-changes chip, no-op edit pruning, leave guard | `Wizard.tsx` (`sameSelection`/`isRealEdit`, pending chip) | server draft is the confirmed truth | meander story; `pending.test.ts` |
| Disabled actions always explain themselves | `SlotCard.tsx` `ConfirmButton`; finalize blockers | — | `ui/e2e/layout.ts` dead-control invariant (every walk) |
| Skill ownership: grants own skills/attribution; collisions add a free pick | `SlotCard.tsx` (generic; message at card) | `mechanics.rs` `skill_resolution`; `skills.rs` | Krivvy golden; ruleset unit tests; owned-skill story |
| School change re-judges the book (destroys nothing) | — (falls out of validators) | `spells.rs` (school has no dependents; validator re-judges) | `checks/replay.rs` re-judge test; changed-mind story |
| Class-conditional slots (class feat hidden for Wizard) | — | `feats.rs` unlock reads `level1_class_feat` | golden assertions |
| Skill source labels ("from Wizard") | — | `mechanics.rs` `skill_resolution` ← `state.class_name` | `checks/class_isolation.rs`; goldens |
| Sheet (draft sidebar + finalized page) | `ui/src/Sheet.tsx` | `mechanics.rs` `derive_sheet` | goldens; first-wizard story |
| "Preparation: at the table" note (no prep in chargen) | sheet entry (data-driven) | `derive_sheet` spellcasting block | first-wizard story; Sylvenne golden |
| Version flags & resolution actions | `ui/src/VersionFlag.tsx` | `server/src/version.rs`, version routes | `checks/version_guard.rs`; `walks*.spec.ts` |
| Layout integrity everywhere (overflow, hidden controls, starved columns) | `ui/src/app.css` (wrapping, responsive stack ≤68rem) | — | `ui/e2e/layout.ts` sweep in every step visit + `layout.spec.ts` stress |
| Class isolation (no cross-class vocabulary) | — | data lookups only, no name literals | `checks/class_isolation.rs` (lint + contamination sweep) |
