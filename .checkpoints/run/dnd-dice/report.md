# dnd-dice — rolled ability scores and hit points as recorded inputs — report

Checkpoint: `dnd-dice` · Branch: `checkpoint/dnd-dice` · Status: delivered (reissued after review feedback)

## Review feedback and the iteration

Ben's review of the first report (2026-09-06) raised three things, all
in the ability-score step:

1. **The assignment after rolling was confusing**: two equal totals
   showed as one value, and a value already assigned could be picked
   again. He asked for something closer to drag and drop.
2. **On a narrow window the screen jumped** when picking options at the
   Origin step.
3. **Standard Array was hard to use through the same selects, and Point
   Buy never showed what each score costs.**
4. **Rolling a hit die changed nothing in the level-up table** (2026-09-07),
   and nothing in the table said the Hit Points row was provisional.
5. **The hit point breakdown was a bare formula** ("10 + 0 Con + 1 × (6 +
   0 Con)") that needed the rule to read, and its rolled form was no
   clearer.
6. **The dice-entry copy read oddly for one die** ("1 set of 1, each from
   1 to 10").
7. **Past three sets the earlier rolls vanished** behind a "Show all"
   link too quiet to notice, with no scroll bar.
8. **Taking the fixed hit points should be an explicit option**, not a
   default buried in text; and the breakdown text still read poorly.
9. **The gains table's third column did not wrap; it showed the fixed
   value before any choice** (preferring one decision over the other for
   no reason); and its Why column replayed every earlier level instead of
   the rule for this level's change. Reviewed with a design pass and a
   reviewer subagent before building.
10. **"Unreachable code should not be executed" on Change after choosing
    Roll a d10** — a WASM panic. Ben asked whether the flows had been
    driven by hand in a browser; they had not (Playwright and unit tests
    only), and the browser copy of the engine committed in the roll-card
    step predated the hit point choice slot, so the Change dialog's
    engine call met an unknown slot. The wizard's preview fallbacks had
    masked the stale engine in every automated walk.
12. **Every pre-slice character was flagged "Review: values changed" with
    an empty diff** (found by the by-hand plan below, on files written by
    main's build). The guard judged identical replays by comparing whole
    sheets, breakdown text included, so the reworded Hit Points breakdown
    read as a divergence. Identical is now judged by values; the explicit
    re-pin stores the replayed sheet so today's wording enters the file
    with the same numbers. My earlier "quiet re-pin" claim was also wrong:
    the established flow flags an identical replay mildly and re-pins by
    one explicit action — the report now says so.
11. **After a roll on an existing character, the Why still listed the
    level-1 line.** The character had been finalized by an earlier build,
    so its stored sheet carried the old one-line wording; the scoping
    compared the new bullets against that text and kept them all. Every
    test had used characters created by the current build. Explanations
    are now scoped against a fresh fold of the finalized prefix under
    today's rules, and a check rewrites a stored sheet to the old wording
    before leveling and asserts the level-1 line stays out.

Found by the by-hand plan (below) on 2026-09-07 and fixed on the same
branch:

13. **A hand-speed double tap on Roll recorded two sets.** The in-flight
    guard only spans the request, and on localhost the roll answers in a
    few milliseconds, so a second tap 120 ms later was an honest "Roll
    again". My earlier "double tap → one set" claim came from a
    synchronous double-dispatch, not a hand-speed tap. The Roll button
    now rests for 400 ms after a roll answers — only that button; dice
    entry and every other control stay live — and a unit test pins it.
    Retested by hand: the second tap finds the button disabled, one set.
14. **At phone width the gains table's level columns wrapped letter by
    letter** ("Hu ma n Fig hte r"): the fixed 24 / 15 / 15 column shares
    squeezed them. Under 600 px the table now sizes columns by content
    with a minimum width on the value columns.
15. **The point-buy meter read "Points 0 of 27"** on a fully spent buy,
    which reads as "spent 0". It is the points-left meter; it now says
    "Points left 0 of 27".
16. **A fractional face ("3.5") was refused with "Enter every die"**,
    which does not say why. It now says "Faces are whole numbers from 1
    to 10."

Reproduced in the browser at phone width, then fixed on the same branch:

- **Tap-to-place assignment** for the array and the roll. The values to
  place are a tray of chips — one chip per offered listing, so a total
  rolled twice is two chips — and every ability is a row. Tap a chip,
  then the row; tap a placed value to take it back; tap a filled row
  while holding a chip to swap. A placed chip greys out, so a value can
  never be picked twice by accident. Chips match rows by position and
  the editor reads no id and adds nothing up.
- **A cost stepper for Point Buy**: each ability row steps through the
  published scores with that score's cost beside it ("9 points"); the
  always-on Points meter shows what is left, and an overspend is still
  the checklist's verdict.
- **The gains table follows the roll.** The "At level N you gain…" table
  was computed from the advance alone, deliberately before any choice —
  but a rolled die is a recorded input, not a choice, and the row stayed
  on the fixed value. The fold behind the gains now includes any roll in
  the pending level, so Hit Points updates in place with "rolled 8" in
  the Why column; "Changes so far" then shows only choice-driven changes.
  Before a roll, any gains row that a roll card in the step can still
  change carries a marker ("🎲 fixed value — or roll below"), matched to
  the card by label so the UI still learns no game word.
- **An explicit fixed-or-roll choice on every pending level.** The Hit
  Points card offers two options with the numbers spelled out — "Take the
  fixed value: 6 + Constitution modifier (+2) = 8 hit points" and "Roll a
  d10" — as an unrequired choice (absent still means the fixed value, so
  level 2 finalizes at once and every existing file is untouched).
  Choosing to roll opens the die card, required while open, so a
  chosen-but-unrolled die is a checklist gap ("Roll your hit die, or take
  the fixed value instead"). This reinstates the two-slot shape the
  architecture review had folded into one; the boundary is unchanged.
  The gains-table marker reads "fixed value unless you choose to roll
  below" before a choice and "waiting for your roll below" after.
- **The browser engine is fresh, and staleness fails loudly.** The
  bindings and bundle are rebuilt; the WASM/native parity smoke now runs
  every fixture of both games, including a new `ysolde-3` golden that
  uses the hit point choice, the die, and a roll history, so a committed
  binary that lacks a slot fails the unit suite (verified: the stale
  binary fails five of eight parity cases, the fresh one passes).
- **A dead engine is loud.** When the in-browser engine throws during a
  preview, the wizard says so once at the top of the step instead of
  silently degrading to the server's projection. Making it loud exposed
  a second, older defect: during a level-up the browser rebuilt its log
  from the projection's live steps only, so every level-up preview had
  been folding a log without its finalized prefix or the advance and
  failing quietly. The draft view now carries the whole decision log the
  projection derives from, and the browser previews and clears against
  that; the reconstruction helper is gone from the wizard.
- **A double tap cannot race itself.** Two synchronous clicks on Roll
  (found by hand: a JavaScript double-dispatch got the second request
  out before the disabled button re-rendered, and it came back as a
  stale-version "changed from another tab" notice — one set was still
  recorded, but the notice lied) are now stopped by an in-flight guard
  in the wizard; the double-tap walk asserts no notice. A hand-speed
  double tap (item 13) is a second matter: the request had already
  answered, so the guard let it through as a reroll. The Roll button
  now rests for 400 ms after every answer, so one intended tap is one
  set; Playwright waits for the button to re-enable, so the walks that
  roll twice on purpose are unchanged.
- **The sidebar sheet honours undecided values too**: entries a card the
  player has not decided will set render "?" with the pointer as their
  title, matching the gains table.
- **Undecided rows show no value.** A gains row that an undecided card in
  the level will set (matched by label; the projection carries only the
  level's live cards) renders "?" with a pointer — "🎲 decide below", or
  "🎲 roll below" once rolling is chosen — and only the rule line of its
  explanation, so no default the player has not chosen is displayed. The
  fold still needs a number underneath; the table refuses to show it.
  "Changes so far" takes the same markers. Once the choice is confirmed
  (fixed, or roll and rolled) the value and its bullet appear.
- **Explanations are scoped to the change.** The server's diff keeps a
  multi-line explanation's first line (the rule) and only the bullets new
  against the old entry — a game-free string shape documented on the wire
  type — so at level 2 the Why reads the rule plus "• Level 2: rolled 8 +
  2 = 10", never the level-1 line; version-review diffs get the same
  scoping. The sheet's own breakdown keeps the full per-level list. Each
  bullet is now complete on its own (the species bonus rides in each
  level's line; no "Total" bullet — the value column has the total).
- **The table wraps**: fixed layout with column widths (24 / 15 / 15 /
  remainder), wrapping in every cell, the pointer on its own line.
- **The hit point breakdown is a rule line and bullets, third pass** (Ben:
  the run-on sentences were the problem). Rendered as separate lines:
  "Fighter: 10 hit points at level 1, then each level adds a d10 roll (or
  the fixed value 6) plus your Constitution modifier (+2)." then
  "• Level 1: 10 + 2 = 12", "• Level 2: fixed value 6 + 2 = 8" (or
  "rolled 8 + 2 = 10", "entered 7 + 2 = 9", "rolled 1 − 1 = 0, minimum
  1 → 1"), "• Dwarf: +1 per level = +2" when it applies, "• Total: 20".
  Sheet breakdowns and the gains table's Why column render line breaks.
  Values unchanged; the four 5.5e golden sheets were regenerated for the
  wording. The "?" for a die not yet decided lives in the gains table's
  marker beside the row, not in the breakdown (a finalized level that
  never rolled and a pending one look the same to the fold).
- **Dice entry copy per shape**: "Type the face you rolled (1 to 10)." for
  one die; "Type the faces you rolled: 6 sets of 4 dice, each face 1 to
  6." for the ability scores.
- **The roll history scrolls instead of hiding.** Every set stays visible
  in a list that scrolls past a few entries, with a count line ("5 sets
  recorded — every one stays in your record; the last is live") and the
  live set scrolled into view as the history grows. This replaces the
  architecture's "collapse behind show all" presentation detail on
  review feedback; the boundary (history rendered from engine-described
  entries, nothing computed) is unchanged.
- **A steady step nav on narrow screens.** The cause was the
  "Unconfirmed changes" chip: on a phone the step nav sits above the
  cards, and the chip appearing grew it by 39 px the moment a tentative
  pick landed. The nav's finalize status region now keeps a fixed height
  on narrow screens (measured: 475 px before and after a pick, scroll
  position unchanged).

Under the hood the presentation hint became state-dependent (the same
assignment slot renders as `assign-pool` under the array or a roll and
as `assign-budget` under a point buy), and a value offered more than
once is one option per listing with an instance-suffixed id
(`score.str.12`, `score.str.12.2`); the fold ignores the suffix, so every
existing log and fixture is unchanged.

## What changed and why

The app rolls dice now, and every roll is a recorded input in the decision
log: the faces that came up, grouped as the die shape groups them, tagged
with whether the app rolled them or the player entered physical dice.
Replay reads faces and never regenerates a roll; derivation (drop the
lowest, sum, assign) stays a pure fold. Every rolled set is kept — a
reroll appends to the slot's history, the most recent set is live, and
nothing ever removes or rewrites an earlier set.

Two consumers ship on the same shape:

- **Rolled ability scores** for 5.5e — the SRD's third method, "Random
  Generation" (4d6, keep the highest three, six times; SRD 5.2.1 p. 21),
  as a data record beside Standard Array and Point Cost. Choosing it
  opens a roll card: the app rolls, or the player enters twenty-four
  faces by hand. The assignment then offers the live set's six totals
  under every ability, each total as often as it was rolled (duplicate
  totals are legal); 18 plus the Soldier's +2 reads 20, the cap.
- **Rolled hit points** at levels 2 and 3 — one unrequired roll card per
  pending level. Absent, the class's fixed value applies exactly as
  before (the SRD's "instead of rolling"); present, the live face
  replaces that level's value under the published minimum of 1 (SRD
  5.2.1 p. 23). Level 2 still finalizes at once; the abandon list names
  the die; the sheet's breakdown says rolled, entered, or fixed per level.

The design that makes it hold:

- **Inputs only append.** A submitted roll means "sets to append"; the
  engine composes it onto the stored history on amend and preview, so a
  request cannot drop or reorder a set. Origin is stamped by the server:
  entered on the ordinary confirm/amend path, app-rolled only by the roll
  route (a client claiming the app's tag is refused, typed).
- **Entropy enters in one place.** `server::dice` draws the operating
  system's bytes by rejection sampling, behind the one clippy-sanctioned
  call; nothing else in the workspace can reach an entropy crate (a
  whole-workspace dependency scan enforces it, plus token scans over
  the WASM and UI sources). The roll route reads the slot's shape under
  the store lock, draws with the lock released, and records through the
  write body it now shares with confirm and amend.
- **Reproducibility is the log; seeds exist only at draw time.** A
  testing-only `--dice-seed` flag swaps in a keyed SplitMix64 mixer
  (seed × character id × decision id), so the same seed, character, and
  decision id reproduce the same faces across copies of a campaign and
  different decisions are independent streams. The campaign view says
  `seeded_dice` and the roster wears a badge whenever it is set; no seed
  reaches any file.
- **The UI knows no die.** The roll card renders the engine's history
  entries (totals, faces with the dropped die named, the tag, which set
  is live), sizes its entry grid from the slot's kind, and adds nothing
  up. A scan bans die literals and browser entropy from shipped UI code.

PF2e is untouched: no roll slot, no data change, every golden byte-identical.
The 5.5e rules version moved to `dnd5e-srd.0.2.0` for the new record; the
established older-known flag covers existing characters: identical values,
one explicit re-pin. Character files are
schema v6 (the selection enum grew); v1–v5 read and never rewrite on load.

## How to verify

Your existing 5.5e directory works as before after one explicit re-pin per
character (the flag reads "identical") on first
open; a fresh directory is cleanest for the walks:

```bash
cargo run --release -p server -- --data-dir ./campaign-dice
```

The binary embeds `ui/dist`, which is committed; if you touch a ruleset,
rebuild the browser engine before the UI (`wasm-pack build crates/wasm
--target web --out-dir ../../ui/src/engine/pkg --no-pack`, then `npm run
build` in `ui/`) — the tentative previews come from that binding, and a
stale one disagrees with the server quietly.

1. **The roll.** Declare D&D 5.5e, create "Ysolde", walk Class (Fighter)
   and Origin (Soldier, +2 Strength / +1 Constitution, Human, Perception,
   Alert). At Ability Scores pick **Random Generation**: a "Roll ability
   scores" card says nothing is rolled yet and the assignment waits on it.
   Tap **Roll**: six sets of four faces appear, the dropped die named per
   set ("6, 5, 3, 1 → 14 (dropped 1)"), the badge says *rolled*, and the
   assignment card shows the six totals as chips — a total rolled twice
   is two chips. Tap a chip, then the ability row it goes to; a placed
   chip greys out, and tapping a placed value returns it. Hand-check each
   total from its faces and the sidebar scores from totals plus the
   Soldier's increases. Try it at phone width too: the cards stay put as
   you pick.
2. **The reroll.** Tap **Roll again**: the dialog says every earlier set
   stays and names the assignment it clears. Confirm: two sets listed in
   order, the first greyed as superseded, the second live; the assignment
   card is empty again. Open `campaign-dice/characters/<id>.json`: the
   roll decision holds both sets, faces and `"origin": "app"`, in order.
3. **The physical dice.** Create "Marrow" the same way, but tap **Enter
   dice**: twenty-four boxes. Type two identical sets and one 6, 6, 6, 1;
   put a 7 in one box — the card says every face must be 1 to 6 and
   Confirm stays disabled. Fix it, confirm: the set is tagged *entered*
   and its totals read 18, 12, 12, 10, 9, 8 — the tray shows two 12
   chips. Place 18 on Strength and the twelves on two abilities: the
   sidebar reads Strength **20 (+5)**, the cap, with the Ability Scores
   step complete. Then tap Roll again: a *rolled* set lands live above
   the entered one.
4. **The double tap.** Tap Roll again twice as fast as you can: one new
   set. (The button is busy after the first tap.)
5. **The hit die.** Finish and finalize Ysolde (skills, style, masteries,
   packages). Level up to 2: the gains panel lists the fixed hit points;
   the one card is **Hit Points (optional)** and Finalize is enabled at
   once; the card offers "Take the fixed value (… = 8 hit points)" and
   "Roll a d10", and the Hit Points row in the gains table shows "?" with
   "🎲 decide below" and only the rule in its Why column — no number until
   you decide. Pick Roll: a die card opens, Finalize waits on it, the
   pointer says "🎲 roll below". Tap Roll — a face — and the row shows the
   value with "• Level 2: rolled N + …" as its Why; Roll again: both kept,
   the second live, the row follows the live one.
   **Abandon level 2**: the dialog names
   Hit Points among what it discards; afterwards the file holds no hit-die
   decision. Level up again, roll once, finalize: the sheet's Hit Points
   breakdown lists "• Level 2: rolled N + 2 = …" (or "fixed value 6 + 2"
   when you took the fixed value).
   At level 3 pick the
   Champion and **Enter dice** on the hit die: 11 is refused with the rule
   named, 7 is accepted and tagged entered; finalize and the breakdown
   lists "• Level 3: entered 7 + 2 = 9". Open Brannock in your existing campaign:
   his hit points and his file are unchanged.
6. **The crash.** `kill -9` the server the instant after tapping Roll, a
   few times; restart on the same directory: the history holds either no
   new set or exactly one, never a torn file; resume lands on the card.
   Close the tab after a roll and reopen: same card, same sets.
7. **The skeptical inspection.** Read Ysolde's roll decision in the file:
   sets in order, four faces each, tagged. Run

```bash
cargo run --release -p server -- --data-dir ./campaign-dice verify
```

   Then edit one live face (a 3 to a 6) and verify again: it reports
   **BROKEN** — the assignment no longer replays because the tampered
   total is not among the rolled ones — naming the decision. (An edit that
   keeps every total but moves which faces stand behind a score reports
   DIVERGED instead; both leave the file untouched.)
8. **The clone.** Clone Ysolde mid-wizard: the clone's file carries both
   sets and the assignment.
9. **The seeded server.** Start with the flag and the roster wears a red
   "Seeded dice — testing only" banner; the file records faces only.

```bash
cargo run --release -p server -- --data-dir ./campaign-dice --dice-seed 7
```

   To see reproduction by hand, copy the directory twice, start each copy
   with the same seed, and roll the same character through the API with
   the same decision id — identical faces (the UI mints a fresh decision
   id per tap, so two taps in the browser are two different rolls; see
   the decisions below).

10. **Nothing else moved.** Torvald, Sylvenne, Brannock, and Nell open
    unchanged; a fresh PF2e character meets no roll card; a fresh 5.5e
    character choosing Standard Array or Point Cost meets none either;
    random mint still pins the array. Standard Array now places by tap
    from six chips; Point Cost steps each ability with its cost shown
    ("15 — 9 points") and the meter draining.
11. **Intent checks.** Read a rolled set in the file: is it obviously how
    an attack roll or a saving throw would be recorded later — faces on a
    die, grouped, tagged — or is it ability-score-shaped? Does keeping
    every reroll visibly feel like the right relationship between player
    and DM? Would a future redo of a roll need anything but this file?

## Constraints now enforced

| Row | Lives at |
|---|---|
| Entropy reaches the server only: whole-workspace normal-dependency walk (`rand*`, `getrandom` only under `server`; `reference-check`'s TLS stack exempted as the non-shipped network tool); purity tokens `getrandom`, `rand::`, `Math::random` in engine crates; entropy tokens absent from `crates/wasm/src` | `checks/crate_layering.rs::only_the_server_reaches_an_entropy_crate`, `engine_sources_are_pure`, `wasm_sources_draw_no_entropy` |
| Entropy is drawn at one call site: `getrandom::getrandom`/`fill`, `rand::random`/`thread_rng`/`rng` disallowed workspace-wide, one scoped allow in `server::dice`; the app-rolled origin is constructed (`origin: RollOrigin::App`) in exactly one server module and nowhere in engine crates or wasm | `clippy.toml`, `crate_layering.rs::app_rolled_origin_is_minted_in_one_server_module` |
| Recorded-input types are game-free: no system id, ability, or hit-point word in `crates/types/src` or `crates/engine-core/src` | `crate_layering.rs::engine_core_and_types_name_no_system` |
| UI is dice-blind: no `Math.random`, `getRandomValues`, `randomUUID` (outside the id minter), no word-bounded die literal, no drop-lowest phrase in shipped `ui/src` | `crate_layering.rs::ui_is_dice_blind` |
| Shape is checked at every roll slot: the shared `check_roll_shape` refuses wrong group count, dice per group, a face off the die, zero sets; engine-core tests over a toy roll slot; both 5.5e roll slots refuse out-of-shape sets at apply | `crates/types/src/roll.rs` tests, `crates/engine-core/src/tests.rs::rolls`, `crates/ruleset-dnd5e/src/tests.rs::dice`, `::hit_dice` |
| Roll inputs append by construction: amend and preview compose stored ++ incoming (M + N); the roll route appends exactly one app-rolled set; a claimed app origin is refused typed with the file byte-identical; the route refuses a non-roll slot, a hidden slot, a stale version (conflict), a finalized character | `engine-core tests::rolls`, `checks/api_authority.rs::roll_route_records_app_dice_and_refuses_forged_origins` |
| Roll idempotency: one decision id → one set, equal views; retry after SIGKILL between roll and write records exactly one set | `checks/confirm_idempotency.rs::a_replayed_roll_id_records_one_set`, `checks/crash_harness.rs::rolls_under_sigkill_are_prior_or_next_state` |
| Atomic transitions: SIGKILL during the roll route, an entered-dice amend, and a hit-die roll on a pending level leaves the prior or next state | `crash_harness.rs::rolls_under_sigkill_are_prior_or_next_state` |
| Seeds stay at draw time: equal (seed, character, decision) → equal faces across two copies; different seed or the OS differ; a second decision id is a different stream; `seeded_dice` true iff the flag; no `seed` in any written file; a seeded campaign verifies clean; the mixer's streams cover every face without obvious correlation | `api_authority.rs::seeded_dice_reproduce_across_copies_and_wear_the_badge`, `crates/server/src/dice.rs` tests, `ui/e2e/dice.spec.ts` |
| Schema v6: v1–v5 fixtures load byte-identical (existing rows, bumped to 6); v7 refused; a v6 roll history round-trips byte-identical through a fresh server; a tampered face is BROKEN/DIVERGED under `verify` | `checks/persistence.rs::rolled_histories_round_trip_and_a_tampered_face_diverges`, `checks/campaign.rs::v7_files_are_refused` |
| Rolled scores golden: Ysolde (an app roll superseded by an entered set with duplicate twelves and an 18 reaching the cap) folds to hand-computed scores; the fixture shows faces, tags, order | `checks/dnd5e.rs::ysolde_golden_keeps_the_history_and_reaches_the_cap`, `checks/fixtures/ysolde.*.json` |
| Assignment multiplicity over swept histories with repeats; one use too many is Illegal with the rule named; the array's rule untouched | `checks/dnd5e.rs::rolled_totals_assign_as_often_as_rolled_across_a_seed_sweep`, `ability_score_machinery_holds_across_a_seed_sweep` |
| Rolled hit points: no decision → fixed values (Brannock's goldens byte-identical); a face replaces one level only under the minimum; the slot is unrequired and level 2 finalizes at once; gains, deltas, and the abandon list carry the roll; abandon discards it | `crates/ruleset-dnd5e/src/tests.rs::hit_dice`, `checks/dnd5e.rs::hit_dice_ride_the_level_up_views_and_abandon_discards_them`, `goldens_brannock_1_and_3_and_the_gold_alternative` |
| PF2e untouched: no roll slot, kind, or constructing form in the PF2e crate; every PF2e golden, fixture, and story byte-identical | `crate_layering.rs::pf2e_registers_no_roll_slot`, `checks/replay.rs`, the PF2e Playwright specs |
| Rules data: `method.roll` attested against the SRD by name and shape; version 0.2.0 supersedes 0.1.0 in shipped-versions; the version-guard rows re-pin | `checks/rules_data.rs`, `checks/attestation.rs`, `checks/version_guard.rs`, `crates/reference-check` (`--system dnd5e`) |
| Stories walk under the layout sweep: the roll and the reroll with its confirm; entered dice with a bad face, duplicates, the cap, a roll on top, the double tap; the hit die with a kept reroll, the abandoned level, an entered d10; the seeded badge and the array path's absent card | `ui/e2e/dice.spec.ts` (4 walks) |
| Budgets: a 1,000-set fold < 5 ms; WASM ≤ 2.5 MB, one module | `checks/dnd5e.rs::fold_with_a_thousand_set_history_is_under_5ms`, `.github/workflows/ci.yml` |

## Decisions made inside the contract

- **The method record is named as the SRD names it**, "Random Generation",
  so it attests by name with no waiver; the spec's stories say "Roll".
  The card and its button say Roll; the method option says Random
  Generation.
- **The roll key is (character id, decision id)** as the architecture
  says. The UI mints a fresh decision id per tap, so seeded reproduction
  is a property of scripted (API-driven) sessions over a copied campaign,
  which is what the checks assert — not of two browser taps or of two
  clone characters (clones have new ids). The spec's manual check ("roll
  Ysolde twice on two fresh clones") cannot pass as written under this
  keying; verify step 9 above is the walk that does. A keying by
  (character, slot, history position) would make browser-driven
  reproduction work too; noted as a follow-up choice, not taken here.
- **A tampered live face reports BROKEN, not DIVERGED**, when it changes
  a total the assignment relies on: the assignment's apply refuses the
  now-unoffered value, so the log stops replaying. That is a stronger
  catch than the spec's DIVERGED; a face edit that keeps totals but moves
  which faces back a score is what DIVERGED reports. Both are asserted.
- **Multiplicity replaced the array's by-value "taken" test** with a
  by-count one that the array also satisfies; the array's checklist
  message is unchanged, the roll's names the count ("12 assigned 3 times,
  rolled 2").
- **History entries ride the option list** with `available` marking the
  live set and `badge` the tag, as the architecture chose; the roll card
  collapses beyond three sets behind "Show all".
- **The hit-die card is always open**: a roll slot never shows a
  "Change…" affordance, because rolling again or entering more dice
  appends rather than replaces.
- **Entropy dependency**: `getrandom` 0.2, the version `rust-embed`
  already pulls, so the dependency-hygiene ban on duplicate versions
  holds; the 0.3 line stays dev-only under proptest as before.
- **The `--dice-seed` flag is visible** in `--help` (not hidden like the
  extra-known-versions test flag): the badge is the safeguard, and the
  Epoch 6 harness will want to find it.
- **Sheet composition under rolling** names faces and tag per ability
  ("18 (Random Generation: 6, 6, 6, 1 → 18, entered) +2 (Soldier)"); two
  equal totals each name their own group.
- **The cut to `dnd-hp-dice` was not needed**: the score stories were
  green before the hit-dice tickets started.
- **Presentation hints are now a function of state** in engine-core (a
  boxed closure like `kind`), the smallest change that lets one slot
  render two ways; every registration site updated mechanically.
- **Chips match rows by position, not by id**: the k-th option of every
  ability group is the same listing, so the tray never parses an id;
  the engine keeps availability and legality by count as before.

## By-hand test plan and results

Ben asked (2026-09-07) what my testing plan had been, after a roll on
his existing character still listed the level-1 line. The honest answer:
the automated walks and my earlier hand runs all used characters created
by the current build, so nothing exercised a file written by the
pre-slice build — the shape of his real data. This plan was written
first, then executed case by case in the Browser pane against a debug
server built from the branch, with the console and the engine-failure
notice checked after every case. Two campaigns:

**Campaign A** — files written by main's build (a separate worktree
running main's server), then opened with the branch. Every character
Ben has is one of these.

| Case | What I did | Result |
|---|---|---|
| A1 | Open Brannock (finalized at level 1 by main) with the branch | **FAIL, then fixed** (item 12): every pre-slice character was flagged "values changed" with an empty diff. After the fix: "Data updated — re-pin available", values unchanged (HP 12), the stored breakdown keeps the old wording until the explicit re-pin, then reads the new lines; `verify` clean |
| A2 | Level Brannock to 2, choose Roll, roll, finalize | "?" + "decide below", Why = rule only; after the roll Why = rule + "• Level 2: rolled 1 + 2 = 3", no level-1 line; sheet breakdown lists levels 1 and 2 |
| A3 | Sylvenne (leveled to 2 by main with the fixed value): re-pin, level to 3 with the fixed value | HP 20 → 28, Why = rule + "• Level 3: fixed value 6 + 2 = 8" only |
| A4 | A main-built draft parked at the array step with no assignment | Re-pin resumes at Class; the assignment is the tray; Change to Random Generation names only the method; roll → three 16s are three chips; paced taps place them (Dexterity 16, Constitution 17) |
| A5 | A main-built point-buy draft (27 points spent) | Stepper shows costs, values unchanged; the meter read "Points 0 of 27" (item 15) |
| A6 | `verify` on campaign A after all of the above | OK ×4 |

**Campaign B** — fresh under the branch.

| Case | What I did | Result |
|---|---|---|
| B1 | Ysolde: Random Generation → Roll → assign → finalize | Six groups with the dropped die named; hand-checked 5, 3, 6, 5 → 16; Strength 16 + 2 = 18 (+4) |
| B2 | Twelve rerolls with an assignment in place | The first reroll's dialog names the sets kept and the assignment cleared; then no dialog; 13 sets, count line, list scrolls to the live set |
| B3 | Entered dice: 0, 7, −2, 1e1, blank, "06", 3.5, then a valid set | Each off-die face refused with the rule, no tentative preview; "06" reads as 6; 3.5 got the wrong hint (item 16); the valid set confirms as "entered" with the right totals |
| B4 | Switch methods with 14 sets and an assignment | Change lists the method, the live set ("set 14 of 14"), and the assignment; Standard Array shows no roll card; back to Random Generation starts empty (the accepted rule: history leaves the live log with the method) |
| B5 | Two tabs, one stale, both rolling and entering | The stale tab gets "changed from another tab — reloaded" and no second set; reload-and-stop, never an auto-retry; the file holds exactly the two sets (app, entered) |
| B6 | Close the tab mid-roll; stop and restart the server | Resumes at Ability Scores with both sets intact; `verify` OK |
| B7 | Clone Ysolde mid-wizard | The clone carries both sets and resumes at the same card |
| B8 | Marrow's level-up: Change with a die, Change without one, three rolls then Abandon, level again with the fixed value, level 3 with an entered die (11 refused, 7 taken), finalize | Every dialog names what it clears; a tentative pick of the fixed value still shows "?"; the file after Abandon has no level-2 trace; the finalized breakdown reads levels 1, 2 (fixed) and 3 (entered) on their own lines |
| B9 | Double tap Roll 120 ms apart | **FAIL, then fixed** (item 13): two sets. After the fix: one set, the second tap finds the button disabled |
| B10 | Marrow's level-up at 375 px | No horizontal overflow, the "?" row, the die card and the entry grid fit, the nav grows 6 px on a tentative pick (scroll position unchanged); the level columns wrapped letter by letter (item 14, fixed) |
| B11 | Two servers with `--dice-seed 7`, one without | Identical faces on the seeded pair, different on the third; the badge follows the flag; no file mentions a seed |
| B12 | A PF2e campaign: random mint, all seven steps, finalize, level up | 21 cards, no roll UI, no dice glyph, no "?" and no marker; the gains table's Why stays one line |
| B13 | 5.5e random mint | Pins Standard Array (no roll set in the log); level 2 with a roll then reads "• Level 2: rolled 2 + 2 = 4"; the breakdown lists both levels |
| B14 | `verify`; then a face edited in a copy of Marrow's file | Clean; the tampered copy: "BROKEN … decision 9 on slot 'dnd5e.scores.assign' is invalid: Random Generation does not offer a score of 11"; `verify` writes nothing |

Two things I measured rather than assumed: the "5 of 6 left" I first saw
in A4 was my own script placing chips faster than React re-rendered
(paced taps are right), and the "live set out of view" I first saw in B2
was a rect-padding artifact (the list is scrolled to its bottom).

## Agent evidence

Final run on the branch head (2026-09-07, after the by-hand plan's fixes):

| Check | Result |
|---|---|
| `cargo fmt --all -- --check` | clean |
| `cargo clippy --workspace --all-targets -- -D warnings` | clean |
| `cargo deny check` | advisories, bans, licenses, sources ok |
| `cargo test --workspace --no-fail-fast` | 232 passed, 0 failed, 2 ignored (fixture regenerators); the new `compat` check replays four pre-slice files written by main's build |
| `reference-check --system dnd5e attest` | 104 records: 103 match, 1 waived (the pre-existing Point Cost naming waiver), 0 mismatch |
| WASM bundle (both rulesets) | 1,743,451 bytes, one module (budget 2,621,440); bindings rebuilt after the last ruleset edit — a stale binding surfaced once more by hand (the point-buy meter's tentative preview still said "Points" while the server said "Points left"); sheet parity cannot see a label-only drift, so rebuilding the bindings is a listed step in How to verify |
| `npm run typecheck`, `npm run lint` | clean |
| `npm test` (vitest) | 11 files, 75 tests passed — parity covers every fixture of both games (a stale engine binary fails five of them; verified by swapping the old binary in); the roll card's rest after a roll and the whole-number hint are pinned |
| `npm run e2e` (Playwright, full suite) | 53 passed, 0 failed (1.2 min), rerun after the last fix; the level-up walk presses Change on the choice card, switches fixed↔roll, and asserts no engine-failure notice; the double-tap walk waits for the rested button first |
| Driven by hand in a browser (2026-09-07) | The plan above: 20 cases over two campaigns, three failures found and fixed (items 12–14), two wording findings fixed (items 15–16); no console errors from the current bundle, no engine-failure notice in any case |

Test-suite wall time: on this machine the whole suite measures 33 s idle
against main's 39 s measured the same way minutes apart — the noise floor
here (other servers running) exceeds the delta. Timed individually the
new server-backed rows add about 7 s locally (roll route 1.0, seeded 1.2,
idempotency 1.1, persistence 1.3, hit-dice 1.7, crash 1.5); two rows were
trimmed after a first cut (crash cycles halved, the hit-dice character
built through confirms instead of a mint). CI's 20 s gate is the arbiter;
if it trips, the seeded and crash rows are the candidates to move behind
a slow tag.

Branch: 18 commits on `checkpoint/dnd-dice`; 91 files changed against `main`.

## Complaints logged

None.
