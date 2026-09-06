---
slug: dnd-dice
status: approved
---

# Chargen slice 7 — architecture

> Delta on the chargen-fighter through chargen-dnd architectures: every
> boundary, failure mode, and constraint there remains in force. This
> slice adds one thing to the decision log — a recorded input — and one
> place where entropy enters the system. Design calls were made by the
> agent against the spec (best calls first, review after — Ben's
> standing preference); each call names what forced it. Review reshaped
> two calls: roll inputs are *appended*, never round-tripped, and rolled
> hit points are one slot, not two (see Review record).

## Situations

- **A recorded input is a selection, not a source.** The log already
  distinguishes *what* was chosen (`Selection`) from *who* chose it
  (`DecisionSource`). A roll is a new kind of *what*: a history of
  rolled sets, each set the faces that came up, grouped as the die
  shape groups them (six groups of four d6; one group of one d10), each
  set tagged with its origin — rolled by the app or entered by hand.
  The tag is a second, two-variant provenance mark beside the decision
  source, and exists only because one decision holds sets of both
  origins; the source stays the player, who asked for the roll or typed
  the dice. The shape (sides, dice per group, group count) is declared
  by the slot's view kind, so the UI can lay out an entry grid without
  knowing what the groups mean, and one game-free shape check beside
  the type is what every consumer's apply calls. Totals, dropped dice,
  and what a total is *for* are the ruleset's, derived from faces in the
  fold. What must never happen: a game word in the recorded-input
  shape; a total stored where a face should be; the UI adding two dice
  together; a third origin.
- **The history is the decision, and inputs only append.** The engine's
  amend replaces a slot's decision (clear, then append) and the log
  keeps no superseded entries, so "every rolled set kept" cannot ride
  on the log's own history. It rides on the selection: a roll slot
  holds one decision whose selection is the ordered list of every set
  so far, the last one live. For a roll slot, a *submitted* selection
  means "sets to append": the engine's append, amend, and preview
  compose the stored history plus the incoming sets, so dropping or
  reordering a set is inexpressible — there is no diff to check and
  nothing for a client to round-trip. This is the one variant whose
  input meaning differs from its stored meaning, named as such. A
  reroll is an amend of one appended set; the dependents machinery
  clears the assignment as for any amend, and the card asks first
  through the existing clear preview when an assignment exists. What
  must never happen: a set dropped or reordered; a second decision for
  the same slot; history kept anywhere but the log.
- **Entropy enters in one place, and it is the server.** The pure crates
  ban randomness and always will; the browser is not trusted to say
  "the app rolled". Origin is stamped by the route, never taken from
  the client: confirm and amend stamp appended sets *entered* (a client
  that claims app-rolled is refused typed — cheap and loud), and one
  roll route stamps *app-rolled*. The roll route is the amend handler
  with a server-composed input, sharing one body with confirm and amend
  rather than a third copy: it takes the slot, the draft version, and a
  client decision id; draws its faces from an entropy source it
  receives as an argument (the operating system's bytes via `getrandom`
  in production — the server's first and only entropy dependency, no
  `rand` — a fixed or failing source in checks, the same shape as the
  sampler's caller-supplied seed) **before** taking the store lock, so a
  slow draw stalls nothing; then checks the version like every confirm,
  checks the projected slot is an open roll slot, and amends through the
  normal validated path under the lock. Faces come from rejection-
  sampled bytes, never a modulo. Idempotency is the existing rule: the
  decision id is the key, and an id already in the log returns the
  recorded roll. The app-rolled origin is constructed in exactly one
  server module. What must never happen: `rand` or `getrandom` reachable
  from any crate but the server; a roll drawn in WASM or in the browser
  (no `Math.random`, no `getRandomValues`); an app-rolled set whose
  bytes the server did not produce; the same decision id yielding two
  different rolls.
- **Reproducibility is the log; seeds exist only at draw time** (raised
  by Ben, 2026-09-06). Undo removes a roll decision and redo re-appends
  it with its recorded faces — Epoch 8's journaled play-state events
  will redo a rolled action the same way. No read path — fold, preview,
  `verify`, clone, a future redo — ever reconstructs a roll from a seed;
  a seed that could regenerate a roll would make the mixer a schema
  and the file no longer the record. Seeding is for checks and Epoch
  6's scripted sessions. The entropy source's draw call carries a
  **key** — the character id and the decision id — and has two
  implementations: the production source ignores the key and returns
  operating-system bytes; the deterministic source derives each draw
  by mixing a root seed with the key through a proper splittable mixer
  (not the mint sampler's FNV), so streams are independent across
  characters and rolls with no shared mutable state, parallel checks
  cannot interfere, and a retried decision id yields the same faces by
  construction. The deterministic source reaches the real binary
  through a testing-only `--dice-seed` flag; whenever it is set the
  campaign view carries a `seeded_dice` fact and the roster shows a
  badge, so a seeded server can never pass for a real one. The seed is
  never written to a character file, the campaign declaration, or a
  log. What must never happen: a seed on any read path; production
  dice from anything but the operating system; a seeded server without
  the badge; a seed persisted anywhere.
- **Shape is validated at apply, meaning by the ruleset.** Each roll
  slot's apply calls the shared shape check — group count, dice per
  group, each face in 1..=sides, at least one set — and a bad entry is
  an apply error the preview surfaces as illegal with the rule named,
  under WASM and under the server alike (the existing count-legality
  home is the ruleset's own validate, not a generic engine pass, and
  that stays true). The 5.5e scores kind then reads the live set, drops
  the lowest face per group, sums, and exposes six totals; the
  assignment slot offers those totals under every ability with
  multiplicity — a total is available for another ability while its
  rolled count is not exhausted — replacing the array path's by-value
  "taken" test with a by-count one that the array path also satisfies.
  What must never happen: a duplicate total refused; the scores kind
  reading any set but the live one; a roll slot whose apply skips the
  check.
- **The UI renders a roll slot from render-ready data.** A new slot view
  kind carries the shape (a presentation hint cannot carry counts).
  The slot's history is the ruleset's own option list — one entry per
  set: faces as the label, the total as the summary, the struck die in
  the details, the tag as the badge, the live set marked available —
  because what is struck and what a total means are ruleset semantics
  (a hit die drops nothing). The card offers two acts: roll (the
  server route) and enter dice (a faces grid sized from the shape,
  previewed through the existing candidate path, then the existing
  amend with the new set only); sets beyond the most recent few
  collapse behind "show all". What must never happen: a system or
  ability word in the UI; die arithmetic in the UI; a client-side roll.
- **Rolled hit points are one unrequired roll slot per level.** The 5.5e
  class kind registers, for levels 2 and 3, one unrequired roll slot
  of one group, one die of the class hit die, in the pending level's
  step. Absent, the fold applies the fixed value — exactly what it
  derives today; present, the live face replaces the fixed value for
  that level, under the published per-level minimum. No fixed-or-roll
  chooser: "take the fixed value" is the absence of a roll, so nothing
  writes a default into a log and nothing can be chosen-but-unrolled.
  Level 2 still finalizes at once. Abandon names the slot among what it
  discards, as it names every pending pick. What must never happen: a
  level's hit points as a stored number; a fixed default in a log; a
  hit-point slot that blocks finalize.
- **Storage moves to schema v6** because the selection enum grew. v1–v5
  files load byte-identical and gain nothing on load; a v6 file holding
  a roll selection is refused by an older binary as a newer schema, as
  today. The 5.5e rules-data version bumps for the new method record;
  the established quiet re-pin covers existing characters.
- **Budgets hold under history.** Only new sets travel; the history
  lives on disk and grows one set per tap, a few tens of bytes each.
  The fold budget is asserted over a thousand-set history. No cap is
  imposed on rerolls (a decision the spec accepts); a single request is
  bounded by the server's default body limit.

## Boundaries

```
ui ── roll card: "Roll" → POST roll route; "Enter dice" → faces grid
 │    → Preview (WASM, new set as candidate) → amend (new set only);
 │    history rendered from the slot's option list; shape read from
 │    the slot kind; clear preview before a reroll; nothing computed
 ▼
wasm ── Project / Preview unchanged in kind; compose stored ++ incoming
 │      for roll slots; apply-time shape errors surface as illegal
 │
server ── roll route = amend with a server-composed input (shared body);
 │        entropy source keyed by (character, decision): OS bytes via
 │        getrandom, or the --dice-seed mixer (campaign view says so);
 │        drawn before the lock; origin stamped by route; schema v6
 ├─▶ ruleset-dnd5e ── method.roll record; scores kind: faces → totals,
 │                    multiplicity-aware assignment, history as options;
 │                    class kind: one unrequired hit-die roll slot per
 │                    level; HP fold reads live face or fixed value
 ├─▶ ruleset-pf2e ──── unchanged
 └─▶ engine-core ──── append/amend/preview compose roll histories
        └─▶ types ── Selection::Rolled { sets }, RolledSet { groups,
                     origin }, SlotViewKind::Roll { sides, dice, groups },
                     one shape-check fn beside them
```

Forbidden: `rand*` or `getrandom` in the resolved normal-dependency
tree of any crate but `server`; a die-arithmetic, die-literal, or
browser-entropy call in `ui/src`; an app-rolled origin constructed
anywhere but one server module; a game word on the recorded-input
types; a roll slot in the PF2e crate; a seed or the entropy source
reachable from anything but the roll route's draw; a `seed` key in any
persisted file.

## Failure modes

- **Entropy unavailable or failing:** the roll route returns a typed
  error and writes nothing (drawn before the lock, so nothing is held);
  the card shows the error and the tap can be retried with the same id.
- **Entropy slow:** the draw happens outside the store lock; other
  routes on the campaign proceed; the tap waits.
- **kill -9 during a roll:** the file holds the prior decision or the
  extended history — temp, fsync, rename as for every write; a retry
  with the same id after restart either finds the roll or rolls fresh,
  and in both cases exactly one set is recorded for that id.
- **Retried roll after a successful write:** the id is in the log; the
  route returns the recorded draft view, no new set.
- **Stale draft version on the roll route (another tab rolled):** the
  existing conflict rule — reload and stop; the user sees the other
  tab's set and taps again if they mean to. Never an automatic retry.
- **Stale version on an entered-dice amend:** the same reload-and-stop;
  the grid's unsent faces are the only thing lost, and the reloaded card
  shows the history as stored.
- **Roll route on a slot that is not a roll slot, is locked, on a
  finalized character, or in another system's campaign:** typed refusal
  naming the slot; nothing written.
- **A client claims an app-rolled origin:** typed refusal naming the
  rule; nothing written. (Dropping or reordering sets is not a request
  the wire can express.)
- **Entered faces out of shape:** an apply error in the preview, illegal
  on the checklist with the rule named; the amend refuses the same way
  if forced.
- **Method changed away from rolling:** the confirm names the history
  and assignment as cleared; they leave the live log (existing rule).
- **Abandon after a rolled hit die:** the abandon confirm names the
  hit-die pick; the history leaves with the level (existing rule).
- **A file whose roll selection fails the shape check at load** (a hand
  edit): the fold fails typed; the roster reports it like any file that
  does not replay; `verify` names the decision.
- **A hand edit to a superseded set or a tag:** the sheet is unchanged
  and `verify` passes — provenance is as trustworthy as the disk, the
  spec's accepted risk; the app itself can never make such an edit.
- **Older binary meets a v6 file:** refused as newer schema, in place.
- **Server started with `--dice-seed` on a real campaign:** it runs, the
  roster wears the badge on every load, and the file records faces
  only — a seeded session's data is indistinguishable in kind from a
  real one and needs no cleanup; the badge is the whole warning.
- **Redo (a later epoch) of a roll:** the recorded decision is
  re-appended; entropy is not consulted; the badge state at redo time
  is irrelevant.
- **Hit-die slot absent on a pending or finalized level:** the fixed
  value applies; nothing is flagged.
- Everything else inherited unchanged.

## Performance budgets

| Budget | Value | Asserted where |
|---|---|---|
| Fold of a 5.5e level-3 log whose roll slot holds 1,000 sets | < 5 ms | `checks/dnd5e.rs` |
| Default test suite wall time | < 20 s (unchanged) | CI timing gate |
| WASM bundle | ≤ 2.5 MB raw, one module (unchanged) | CI WASM step |

Design target, hand-checked: tap to rendered set with no perceptible
delay on the dev machine.

## Constraints emitted

All prior rows remain in force. New or amended rows:

| Rule | Enforced by | Config lives at |
|---|---|---|
| Entropy reaches the server only: walking every workspace crate's resolved normal-dependency tree, `rand*` and `getrandom` appear only under `server` (the existing scan's `starts_with("rand")` misses `getrandom` today and is widened); the purity token scan gains `getrandom` and `Math::random` and covers `crates/wasm/src` | dependency-tree scan + source scan | `checks/crate_layering.rs` |
| Entropy is drawn at one call site: `getrandom::getrandom` (and `rand::random`, `rand::thread_rng` for the future) disallowed workspace-wide with one scoped allow in the server's entropy helper (the `server::clock` precedent); the app-rolled origin constructor appears in exactly one `crates/server/src` module and nowhere in engine-core, the rulesets, or wasm | clippy `disallowed-methods` + source scan | `clippy.toml`, `checks/crate_layering.rs` |
| Recorded-input types are game-free: no `pf2e`/`dnd5e`/ability/hit-point literal in `crates/types/src` (existing scan, now also covering the new module); the roll shape lives on the slot view kind only; the origin enum has exactly two variants | source scan + type test | `checks/crate_layering.rs`, `checks/persistence.rs` |
| UI is dice-blind: no `Math.random` or `getRandomValues`, no arithmetic over faces, and no word-bounded die literal (`d4`, `d6`, `d8`, `d10`, `d12`, `d20`) or drop-lowest phrase in `ui/src` outside `*.test.tsx`; the roll card reads counts from the slot kind only | source scan (word-bounded regex over code lines) | `checks/crate_layering.rs` |
| Shape is checked at every roll slot: the shared check refuses wrong group count, dice per group, a face outside 1..=sides, or zero sets over generated shapes; and for every registered roll slot in either ruleset, an append or amend of an out-of-shape set is an apply error | property test over the helper + a sweep over registered roll slots | `checks/replay.rs` |
| Roll inputs append by construction: an amend carrying N sets to a roll slot with a stored history of M yields M+N sets in stored order under server and WASM alike; the roll route appends exactly one app-rolled set; a confirm or amend claiming an app-rolled origin is refused typed, file byte-identical; the roll route refuses typed, file byte-identical, on a stale version, a non-roll slot, a locked slot, and a finalized character; an injected failing entropy source yields a typed error and no write | standalone tests via the real server + engine test | `checks/api_authority.rs`, `checks/replay.rs` |
| Roll idempotency: two roll requests with one decision id record one set and return equal views; a retry after SIGKILL between roll and write records exactly one set | idempotency + crash harness rows | `checks/confirm_idempotency.rs`, `checks/crash_harness.rs` |
| Seeds stay at draw time: the deterministic source yields equal faces for an equal (seed, character, decision) key and different faces across decision ids and across characters over a swept key space (no run-length or lag correlation on a bounded sample); the same binary with `--dice-seed` reproduces a scripted session's every roll byte-identical, and without the flag two runs differ; `seeded_dice` is true on the campaign view and the badge renders iff the flag is set; no `seed` key and no seed value appears in any character file, campaign declaration, or fixture written by a seeded run; the entropy-source type is named only in the roll route's module and the server's boot | property test + standalone tests via the real server + fixture and source scans | `checks/api_authority.rs`, `checks/persistence.rs`, `checks/crate_layering.rs`, `ui/e2e/dice.spec.ts` |
| Atomic transitions: SIGKILL during the roll route, an entered-dice amend, and a hit-die roll on a pending level leaves the prior or next state | crash harness rows | `checks/crash_harness.rs` |
| Schema v6: v1–v5 fixtures load byte-identical; a v6 fixture with a roll history round-trips byte-identical; v7 refused; a hand-edited live face fails replay and `verify` names the decision | persistence fixtures | `checks/persistence.rs`, `checks/no_rewrite_on_load.rs` |
| Rolled scores golden: Ysolde at 1 from a fixed roll history (a reroll, an entered set, duplicate totals, an 18 reaching the cap with the background increase) folds to hand-computed scores; the file fixture shows faces, tags, order | golden test | `checks/dnd5e.rs`, `checks/fixtures/ysolde*.json` |
| Assignment multiplicity: over swept histories with repeats, each total is assignable exactly as often as rolled, one per ability; the array path's by-count test equals its old by-value behaviour on distinct values | property test | `checks/dnd5e.rs` |
| Rolled hit points: a level-2 log with no hit-die decision derives today's fixed values (Brannock's goldens byte-identical); a rolled face replaces the fixed value for that level only, under the published minimum; the slot is unrequired and level 2 finalizes with an empty checklist; the gains and finalize deltas carry the rolled value and tag; abandon lists the slot | golden + fixture tests | `checks/dnd5e.rs`, `checks/fixtures/brannock*.json` |
| PF2e untouched: no roll slot in any PF2e registration; every PF2e golden, fixture, and story byte-identical; `rules-data/pf2e/` unchanged | existing goldens + a registration scan | `checks/replay.rs`, `checks/class_isolation.rs` |
| Rules data: `method.roll` attested against the SRD like every record; the 5.5e version bumps and the old version joins shipped-versions; every existing 5.5e fixture quietly re-pins | data lint + attestation + version fixtures | `checks/rules_data.rs`, `checks/attestation.rs`, `checks/version_guard.rs` |
| Stories walk: the roll with the clearing confirm on reroll and the history visible; entered dice with an out-of-shape face, forced duplicates, and the cap; the double tap; the hit die with a kept reroll and an entered d10; the abandoned level; nothing-else-moved on both campaigns — under the layout sweep | Playwright specs | `ui/e2e/dice.spec.ts` |
| Budget: 1,000-set fold < 5 ms | asserting test | `checks/dnd5e.rs` |

Deliberately unenforced, with reasons: **legibility of the file** and
**the substrate intent** are the spec's checks for Ben. **Fairness of
the entropy source** is the operating system's claim, not tested. **The
absence of a reroll cap** is a decision, not a rule a tool can check.
**"History lives nowhere but the log"** stays at review — a cached list
has no distinctive token — and the behavioural rows catch the
consequence (a clone and a crash-resume reproduce the history from the
file alone). **Route latency** is a hand-checked target, not a CI
assertion.

## Review record

| Role | Verdict | Folded in |
|---|---|---|
| constraint-auditor | block, resolved | browser and WASM entropy scans (`Math.random`, `getRandomValues`, `Math::random`) — the block; inverted whole-workspace dependency scan; clippy call-site ban with one allow; single-module origin constructor; word-bounded die tokens; roll-route refusal rows; injected entropy source; unenforced list extended |
| failure-mode-reviewer | advice | roll-route conflict = reload and stop, never auto-retry; clear preview before a reroll; entropy drawn before the lock; hand edits to history accepted with `verify` scope named; entered-dice conflict; abandon names the hit die; body-limit sentence corrected — and the round-trip diff replaced by append semantics, which removes the prefix-comparison and recompose-after-reload cases |
| Ben (delta, 2026-09-06) | folded | reproducibility situation: redo replays recorded faces, no seed on any read path; keyed entropy draws (character, decision) with a splittable mixer for independent streams; testing-only `--dice-seed` flag with a `seeded_dice` badge; seed never persisted; rows and failure modes for each |
| simplicity-warden | advice | roll inputs append by construction (the diff rule and three refusals deleted); one unrequired hit-die slot, no fixed-or-roll chooser; history as the ruleset's option list, no engine describe step; shape check as one helper called from apply, false Multi-count precedent removed; roll route as the shared amend body; `getrandom` alone, no `rand`/`OsRng`; route latency demoted to a hand-checked target; origin enum bounded to two variants |
