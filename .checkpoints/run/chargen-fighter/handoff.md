# Handoff: implement `chargen-fighter`

Written 2026-08-28 at the end of the design sessions. Both governing docs are
approved and committed on `main`; you are the implementing agent.

## Where things stand

- `.checkpoints/specs/chargen-fighter.md` — approved (hash ba13d2a4498d)
- `.checkpoints/architecture/chargen-fighter.md` — approved (b4e01fd3e3b3)
- `docs/VISION.md` — landed via the `vision` checkpoint; read it first for
  the roadmap and standing disciplines. The vision checkpoint is complete
  (doc-only; its architecture stage was deliberately skipped, complaint
  logged).
- The repo is otherwise empty — you are writing the first code since the
  fresh-start reset. Nothing in git history is design input.

## How to start

Invoke the `checkpoints:implement` skill for `chargen-fighter`. It cuts the
implementation branch, keeps resumable run state in this directory, and ends
in a report Ben accepts before the mechanical tail (PR → CI → merge).

**Ticket 1 is the architecture doc's Constraints emitted table**, verbatim:
workspace layout, `checks/` suite, clippy/cargo-deny/eslint/tsconfig config,
CI workflow. The constraints exist before the features they constrain.

## Decisions you must not relitigate (all recorded in the docs)

- Rust engine (`types` / `engine-core` / `ruleset-pf2e` crates) compiled
  native for the axum server and to WASM for the browser; TS (Vite + React)
  presentation layer that computes no game values.
- tsify welds TS declarations into the wasm-bindgen `.d.ts`; use the
  `Ts<T>` wrapper (tsify ≥ 0.5.7 — NOT the unmaintained `tsify-next` fork).
  Narrow boundary: one request enum, one response enum, thin TS façade.
  ts-rs is the fallback if tsify disappoints; schemars only if runtime
  validation of API responses proves needed.
- Wire ≠ storage: storage structs non-`pub` to persistence; responses built
  from view types only. Horizontal kind separation: ancestry / background /
  class / feats / skills / equipment modules never reference each other —
  kinds → mechanics → engine-core. No crate named common/utils/helpers/
  shared; the dependency graph is an allowlist in `checks/crate_layering.rs`.
- Characters: decision log + materialized sheet in one JSON file; replay is
  `verify`, never the load path. Atomic writes, schema v1, quarantine,
  `trash/` (timestamped names), data-dir lockfile.
- Content: the spec's candidate set (Dwarf/Human/Elf/Goblin; Field Medic/
  Warrior/Blacksmith/Hunter/Street Urchin) — verify every record against
  Archives of Nethys before shipping; Foundry PF2e data is ground truth for
  *verification only, never bulk import*. ORC notice in the served app.

## Testing expectations beyond the constraints table

Golden-sheet tests hand-verified against Player Core; proptest random walks
over the slot graph; a WASM↔native parity smoke on fixture logs; Playwright
walking each spec user story (first run, the mistake incl. clearing, the
crash with a real server kill, jumping ahead, change-ancestry dependent
clearing, delete-to-trash); component tests for checklist/counters.

## Ben's working preferences (from memory, honor these)

- Docs for review go to the side panel via SendUserFile — never dumped
  inline.
- Design discussion runs depth-first: keep a visible queue of open points,
  resolve one at a time; batch-list anything already future-scoped.
- Ben runs the app as: `cargo run --release -p server -- --data-dir ./campaign`
  then a browser at the printed localhost URL — the server serves the built
  UI; Node must not appear in his loop. The report's verify section must
  carry exact commands.
- Git push over SSH fails here; the origin is scp-style, so use
  `git -c url.https://github.com/.insteadOf=git@github.com: push`.

## If the architecture turns out wrong

Do not silently diverge. The sanctioned flow: say so, edit the doc
deliberately (hash invalidates), delta dialogue with Ben, diff-sized
re-approval. Expected bend points are documented (effects representation,
the 5.5e slice) — slice 1 should not need them.
