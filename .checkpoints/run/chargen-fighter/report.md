# Chargen slice 1: PF2e Fighter level-1 creation wizard — report

Checkpoint: `chargen-fighter` · Branch: `checkpoint/chargen-fighter` · Status: delivered

## What changed and why

The repo went from empty to the full walking skeleton the spec asked for: a
Rust engine (generic decision-log core + PF2e ruleset) compiled both native
and to WASM, an axum server with crash-safe JSON persistence, versioned
ORC-tagged rules data verified against Archives of Nethys, and a React
wizard that renders what the engine computes and never computes anything
itself. You can create a PF2e level-1 Fighter through a guided seven-step
wizard, watch validation explain itself live, kill the server at any moment
and resume at the exact step, read and hand-audit the character file, and
catch tampering with `verify`.

The three governing structures all exist as tooling, not intentions: the
crate-layering allowlist, the wire≠storage visibility split, and the
kinds→mechanics→engine-core separation inside the ruleset are enforced by
`checks/` and fail the build (twice during this run they failed **my own**
in-progress code — they work).

## How to verify

Every command below is your normal loop, on your own machine, in the
`checkpoint/chargen-fighter` branch checkout.

**1. First run — build Torvald and check his math.**

```bash
cargo run --release -p server -- --data-dir ./campaign
```

Open the printed localhost URL. You should see an empty roster with the ORC
notice at the bottom. Create "Torvald", then walk the steps: Ancestry →
Dwarf, Rock Dwarf, Rock Runner, free boost Strength. Background → Warrior,
constrained boost Strength, free boost Constitution. Class → Fighter, key
attribute Strength, Sudden Charge, Athletics, then Survival + Religion +
Crafting. Attribute Boosts → Str/Dex/Con/Wis. Equipment → "Fighter Kit +
add a longsword and steel shield". Finalize. Hand-check against Player
Core: **Str +4 Dex +1 Con +3 Int +0 Wis +2 Cha −1 · HP 23 · AC 17 ·
Fort +8 Ref +6 Will +5 · Perception +7 · longsword +9, 1d8+4 S ·
Athletics +7 · 6 gp 2 sp left · 5 Bulk, 2 L** (every number has a "+"
breakdown toggle on the sheet). Note the spec's illustrative "HP 20"
assumed Con +0, which no Dwarf can have — 23 = 10 ancestry + 10 class +
3 Con is the Player Core answer.

**2. The mistake, caught.** Mid-wizard, go to Attribute Boosts and set
boost 1 and boost 2 both to Strength. The checklist should immediately show
"Boosts gained at the same time must go to different attributes" under
*Against the rules* — before you confirm anything. Navigate to another step,
click the entry, confirm it returns you to the boosts; change boost 2 to
Constitution and watch the entry disappear.

**3. The crash.** Mid-wizard (say after Background), type into a Details
text field *without* confirming, then:

```bash
kill -9 $(pgrep -f "target/release/server")
```

```bash
cargo run --release -p server -- --data-dir ./campaign
```

Reload the browser: the roster offers "Resume creating Torvald (step N of
7 — …)". Open it — every confirmed choice intact, the half-typed field
gone, and you land on the step you left.

**4. The skeptical inspection.** Open the file and judge its legibility
yourself, then tamper and verify:

```bash
cat ./campaign/characters/*.json
```

Edit the stored sheet's Hit Points by hand, then:

```bash
cargo run --release -p server -- --data-dir ./campaign verify
```

Expect `DIVERGED … Defense / Hit Points: stored '99', replay '23'` and exit
code 1; the app still loads the stored sheet.

**5. Jumping ahead + change-ancestry.** On a fresh character go straight to
Equipment: the kit slot explains its lock ("choose a class first — kits are
class-specific"), the item list still works, Finalize is disabled and the
checklist lists every gap. Then on a dwarf with heritage+feat chosen, hit
"Change…" on Ancestry: the prompt must list exactly Ancestry, Heritage,
Ancestry feat, and the ancestry free boost — nothing else — and clearing
reopens those slots.

**6. Delete to trash.** Delete a draft from the roster (it asks once), then:

```bash
ls ./campaign/trash/
```

The file sits there under a timestamped name; the roster is clean.

**7. Second instance + port walk (hand-checks from the architecture doc).**
With the server running, start a second one on the same data dir — it must
refuse with "already being served at <url>". Then stop both, occupy 8080
with anything, start the server: it walks to 8081 and prints the URL.

**Intent checks.**
- Is this the "good character creation dialog through a nice web UI" you
  meant — would you hand a player this wizard at a table tomorrow?
- Open `campaign/characters/torvald.json`: is it genuinely the file you'd
  want to diff and back up?
- Spot-check three records against Archives of Nethys (all URLs are in the
  data files themselves): e.g. `rules-data/ancestries.json` (Dwarf),
  `rules-data/backgrounds.json` (Field Medic),
  `rules-data/class-feats.json` (Sudden Charge).

## Constraints now enforced

Every row of the architecture table runs in the repo's own tooling; all
green at [f70b13e](../../..):

| Rule | Lives at | Proof |
|---|---|---|
| Crate-layering edge allowlist, banned crate names, engine purity (no fs/net/clock/env/rand), wasm-bindgen only in `wasm`, kind-module import scan, storage-doc export scan | [crate_layering.rs](../../../checks/crate_layering.rs) | 7 tests; caught a real violation twice during implementation (cross-kind slot refs; a bare `pub enum` in persistence) |
| No I/O/clock/env bans + no `remove_file` anywhere | [clippy.toml](../../../clippy.toml) + layering scan | `cargo clippy --workspace --all-targets -- -D warnings` clean; the server's one clock helper carries the visible `#[allow]` |
| `#![forbid(unsafe_code)]` engine crates; workspace lints | crate roots + [Cargo.toml](../../../Cargo.toml) | compiles |
| cargo-deny license allowlist, duplicate/yanked bans | [deny.toml](../../../deny.toml) | `advisories ok, bans ok, licenses ok, sources ok` |
| Wire ≠ storage | [storage.rs](../../../crates/server/src/persistence/storage.rs) (`pub(crate)` max) + layering spot-check | compile-visibility + test |
| Kind modules don't bleed | ruleset layout + module scan | test green over the real six kind modules |
| TS strictness, no `any`, façade-only wasm access, no rules-data import | [tsconfig.json](../../../ui/tsconfig.json), [eslint.config.js](../../../ui/eslint.config.js) | `tsc --noEmit` + `eslint .` clean |
| Bindings never stale | committed [pkg](../../../ui/src/engine/pkg) + CI regen-diff | local regen produced zero diff |
| Persistence contract (schema v1, newer-version refusal, quarantine, trash) | [persistence.rs](../../../checks/persistence.rs) | 5 tests incl. real second-instance refusal |
| Crash safety under SIGKILL | [crash_harness.rs](../../../checks/crash_harness.rs) | 4 kill cycles/run against the real binary; asserts durable state = acked or acked+in-flight |
| Confirm idempotency + stale-tab conflict | [confirm_idempotency.rs](../../../checks/confirm_idempotency.rs) | incl. the stale-version retry case |
| Load is read-only | [no_rewrite_on_load.rs](../../../checks/no_rewrite_on_load.rs) | byte-hash equality |
| Server authority over raw HTTP | [api_authority.rs](../../../checks/api_authority.rs) | locked-slot, cross-catalog, unknown-option, unavailable-option, finalize-blocked |
| Replay determinism + golden sheets | [replay.rs](../../../checks/replay.rs) | 3 hand-verified goldens (Player Core page refs inline) + fixture freshness + proptest random walk over the real slot graph |
| Rules-data integrity + ORC notice | [rules_data.rs](../../../checks/rules_data.rs) | unique IDs, per-record license metadata, resolvable cross-refs, notice text |
| Fold < 5 ms; suite < 20 s; warm incremental < 10 s | [perf.rs](../../../checks/perf.rs) + CI timing steps | fold ~µs; suite 16 s local; warm engine→wasm+server 9 s (wasm-opt capped at ‑O1 to make it) |
| All of the above on every push | [ci.yml](../../../.github/workflows/ci.yml) | wired; will get its first cloud run on the PR |

## Decisions made inside the contract

1. **"Blacksmith" → Artisan.** No Blacksmith background exists in Player
   Core (AoN-verified); Artisan (Str/Int, Crafting, Guild Lore, Specialty
   Crafting — flavor text literally names a blacksmith's apprentice) ships
   instead, per the spec's "finalized against Archives of Nethys" clause.
2. **Prerequisite machinery exercised by Adapted Cantrip.** No level-1
   fighter class feat has a formal prerequisite (AoN-verified; four have
   use-time *requirements*, shipped as annotation text). The evaluable
   prerequisite path is exercised by Human's Adapted Cantrip ("requires a
   spellcasting class feature") — greyed with the reason in the UI and
   rejected server-side, both tested. Elf's Ancestral Longevity ("100+
   years old") is selectable — age isn't tracked, so the prerequisite shows
   as an annotation.
3. **Choosers with empty catalogs are unavailable, uniformly.** Ancient Elf
   (needs other classes' dedications), Otherworldly Magic (needs a cantrip
   catalog), and Unconventional Weaponry (needs uncommon weapons) ship as
   real records whose options grey out with "no entries in this rules-data
   version". `chargen-content`/`chargen-wizard` un-grey them by adding data.
4. **A small general-feat catalog (5 records)** so Versatile Human and
   General Training work: Toughness, Fleet, Incredible Initiative, Diehard,
   Ride (all AoN-verified). Natural Ambition grants a second fighter-feat
   slot; Natural Skill and Skilled Human grant skill choosers.
5. **The skill replacement rule** is three statically-registered slots that
   exist only while grant collisions exist (background/Lore-feat grants
   landing on an already-trained skill). Collisions resolve in a canonical
   order (choices, then background grant, then feat grants) so replay is
   order-independent. Golden #3 (Krivvy) builds out of order to force it.
6. **Boost widgets allow the illegal state.** Per-boost dropdowns can put
   two boosts on Strength; the engine flags it live and finalize blocks.
   The UI never pre-blocks what validation should explain (spec's mistake
   story).
7. **Rules data is embedded in both binaries** (`include_str!`), so client
   and server data cannot diverge, Ben's loop needs no data path, and
   "rules data absent at start" is impossible by construction (corrupt data
   still refuses to start with a clear message).
8. **The UI build is committed** (`ui/dist`) and embedded via rust-embed —
   `cargo run --release -p server` is the whole loop, Node never appears.
9. **Bulk is the literal Player Core sum**: listed values (worn armor as
   listed; a second suit +1 as carried), 10 L = 1 Bulk rounded down. The
   backpack's "first 2 Bulk in the pack don't count" exemption is *not*
   modeled (AoN's kit line uses it; our per-item breakdown shows the
   arithmetic so a hand-check matches).
10. **Modifier-only attributes** (remaster style): sheet shows `+4`, not
    18; the level-1 +4 cap is structurally unreachable (four batches, each
    distinct), so no partial-boost machinery this slice.
11. **Deferred content** (report-worthy scope lines): language selection
    beyond ancestry defaults, itemized-shopping quantity UI beyond
    add/remove rows, and Lore-skill sheet modifiers (Lores render as
    trained lines without invented Int math). All natural
    `chargen-content` follow-ups.
12. **Spec nit:** the first-run story's "HP 20" is unreachable for any
    Dwarf (Con is a fixed boost); the correct hand calculation is 23 and
    the golden test pins it.
13. **The `verify` exit code** is 0 clean / 1 divergence-or-corruption, so
    it can script.

## Agent evidence

- `cargo test --workspace`: 20/20 test targets green, 16 s wall (budget
  20 s) — includes the SIGKILL crash harness (4 kill cycles per run,
  repeated ×3 in this session), persistence, idempotency, authority,
  read-only-load, layering, rules-data lint, perf, engine unit +
  proptest, and the three golden sheets.
- `cargo clippy --workspace --all-targets -- -D warnings`: clean.
  `cargo fmt --check`: clean. `cargo deny check`: all four gates ok.
- UI: `tsc --noEmit`, `eslint .` clean under `strict` +
  `noUncheckedIndexedAccess` + `exactOptionalPropertyTypes`; vitest 11/11
  (checklist, boost counters, WASM↔native parity on all three fixture
  logs — sheets byte-identical after null/undefined canonicalization).
- Playwright: 6/6 stories against the real binary — first run with
  hand-checked numbers, the mistake, the crash (real `kill -9`), jumping
  ahead, change-ancestry clearing, delete-to-trash.
- Release-binary walkthrough of the verify/tamper story reproduced the
  DIVERGED report shown in step 4 above.
- Budgets: fold ≪ 5 ms (µs range, asserted); warm engine→wasm+server 9 s.
- AoN verification record: [aon-reference.md](aon-reference.md) — every
  shipped record checked against the Archives of Nethys remaster index
  (2026-08-02 snapshot), with the two find-and-fix notes (Blacksmith→
  Artisan, no-prereq fighter feats) folded into the data.

## Review round (2026-08-27, pre-acceptance)

Ben's hands-on review surfaced three UX defects, fixed together as one
generalized change (full ledger: [review-notes.md](review-notes.md)):

1. **Step badges overclaimed** — a step whose required slots were merely
   locked showed ✓. Now: per-slot `SlotStatus` (locked/empty/partial/
   complete/illegal) computed by the engine, step badges a pure fold over
   it, with a hollow `Waiting` badge for "nothing to do yet".
2. **Half-confirmed multi slots looked done** — 2-of-4 skills rendered as a
   closed card. Now: Partial slots keep their editor open, preloaded, and
   Confirm amends via a new atomic engine op + `/amend` route (idempotent,
   version-checked; cascades exactly like clear, dialog only when other
   slots' decisions are actually taken along).
3. **The equipment budget was invisible until violated** — now slots carry
   always-on engine meters ("Spent 8 gp of 15 gp", "Chosen 2 of 4"); the
   budget rule derives its violation entry from the same computation, so a
   violation without a visible gauge is unrepresentable.

Guarding the class of bug: property-walk coherence invariants (every
Partial/Illegal slot has a checklist entry; every entry targets a
non-Complete slot; finalize-ready means nothing required is unfinished) run
in both the toy-ruleset and full-PF2e random walks; a component test
asserts the five statuses render distinguishably. Two e2e stories added
(finish-partial-in-place; live budget meter). Sheets are untouched, so all
goldens, fixtures, and the parity smoke stand unchanged. Dropped by Ben:
the Adapted Cantrip copy nit (future spellcasting slices supersede it).

A harness complaint was logged this round (no channel for iterative
review feedback; see complaints.jsonl). The original "Complaints logged"
statement below still covers the implementation run itself.

## Complaints logged

None during implementation — the gate, ACTIVE hook, and stage flow behaved
throughout the build. One complaint logged during report review (iterative
feedback channel), recorded 2026-08-27 in complaints.jsonl.
