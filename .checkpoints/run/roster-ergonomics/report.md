# Roster ergonomics — random character & clone — report

Checkpoint: `roster-ergonomics` · Branch: `checkpoint/roster-ergonomics` · Status: delivered

## What changed and why

The roster now mints and forks characters cheaply. **Random character** is
a one-tap button (with a class picker: Any / Fighter / Wizard): every slot
is rolled from its legal options — never pinned to the published suggested
build, so repeated Fighters genuinely differ — the character gets an
ancestry-flavored name from own-authored pools, and the draft lands at the
review step exactly like quick build: one more click finalizes. **Clone**
duplicates any character (draft or finalized) as a fully independent copy
under a name you choose in a small prefilled dialog; the clone's decision
log is identical to its source except the name decision, which records the
clone-time name with `clone` provenance.

Under the hood, per the architecture: randomness is data — the client
request ID is hashed into a seed, so the same request always mints the
same character (which also strengthens crash-retry idempotency), and no
`rand` dependency exists anywhere. The random picks ride the existing
suggestion planner through a new state-aware suggestion-source seam, and
every pick passes the same validation as a human confirm. The sampler is a
standalone component with the legality filter outside it — the engine's
fuzz property test now consumes it with the filter off, the reserved seam
from the architecture dialogue. Clone re-derives its sheet by replay, so
clones are born verify-clean, and a tampered source refuses to clone.
The character schema bumped v2 → v3 for the two new provenance sources;
every pre-slice file loads unchanged.

One design discovery the spec's "constraint-narrowing" idea turned into
code: sampled picks can invalidate *earlier* generated picks (boosting
Intelligence grows the language and trained-skill counts after those slots
filled; the Wizard's curriculum floor judges at the checklist, not at
append). The mint handles both with a bounded re-open-and-resample loop
over its own generated decisions only — player decisions are never
touched. The seed-sweep property test is what surfaced both cases.

## How to verify

Start the server as usual from the repo root (the name pools resolve
relative to it):

```bash
cargo run --release -p server -- --data-dir ./campaign
```

1. **Minting a test party.** On the roster, leave the class picker on
   "Any class" and tap **Random character** three times (it navigates into
   each draft — tap "← Roster" between mints). Each lands at the review
   step, fully filled, checklist clear, with `random` badges on the rolled
   cards. Finalize each with one click. Then:

```bash
cargo run --release -p server -- --data-dir ./campaign verify
```

2. **Variety is the feature.** Mint three or four random Fighters
   specifically (class picker → Fighter): confirm they differ from each
   other and from the quick-build Fighter — different ancestries,
   attribute lines, feats, names.
3. **The class with no quick build.** Mint a random Wizard: thesis,
   school, and a curriculum-legal spellbook all filled; hand-check the
   spellbook against the school's curriculum minimum and the spellcasting
   block numbers.
4. **A typed name stands.** Type a name into the working-name field, then
   tap Random character: the typed name is the character's name (no badge
   on the name card — it is your decision, not the generator's).
5. **Clone and delete.** On a finalized character, tap **Clone**; the
   dialog prefills "<name> (copy)" — rename it, clone, and compare the two
   sheets side by side: identical everywhere but the name. Delete the
   clone; the original is untouched.
6. **Forking a half-built draft.** Clone a mid-wizard draft: the clone
   resumes at the same step with the same choices; take the two drafts
   down different paths and confirm neither bleeds into the other.
7. **The crash.** Kill the server mid-mint (`kill -9`), restart, and tap
   retry on the failed action: exactly one new character exists. A fresh
   tap after that is a legitimate second mint.
8. **The skeptical inspection.** Open a random character's JSON file: the
   decision list reads like any other, each generated decision marked
   `"source": "random"` (a clone's name decision `"clone"`). Hand-edit the
   stored sheet, run `verify` — it catches it — and confirm the tampered
   character refuses to clone with a message pointing at verify.
9. **Names as data.** Read [app-data/name-pools.json](../../../app-data/name-pools.json):
   do a dozen names per ancestry fit the ancestry's flavor, and is this a
   file you'd happily edit by hand? (Edit + server restart is the whole
   change cycle.)
10. **Intent check.** Is minting a test subject fast and pleasant enough
    that you'd reach for it — both for level-up testing next slice and
    for a pregen at a real table?

## Constraints now enforced

Every row of the architecture's table is green in the repo's own tooling:

| Rule | Lives at |
|---|---|
| Random mint soundness (seed sweep: full fill, empty checklist, finalizable, verify-clean) | `checks/random_mint.rs::sampled_builds_are_sound_for_every_shipped_class_across_seeds` |
| Mint determinism (same entropy ⇒ byte-identical character) | `checks/random_mint.rs::same_request_mints_the_identical_character` |
| Mint variety (no slot pinned) | `checks/random_mint.rs::sampled_builds_vary_across_seeds` |
| Randomness/clock/env out of pure crates | `checks/crate_layering.rs` (unchanged; the `rand`-ban half now load-bearing) |
| Quick build unchanged | `checks/quick_build.rs`, `checks/replay.rs` goldens (untouched, green) |
| Clone fidelity + refusals (draft, finalized; divergent/trashed/quarantined refuse) | `checks/clone.rs` |
| Creation-only finalized writes (source bytes never change) | asserted inside `checks/clone.rs` fidelity tests + existing `checks/no_rewrite_on_load.rs` |
| Mint & clone idempotency (per-route prefixes, first-write-wins) | `checks/confirm_idempotency.rs::replayed_mint_and_clone_request_ids_append_nothing`, `checks/clone.rs::clone_retries_…` |
| Schema v3 migration (v1 loads untouched, upgrades on first write) | `checks/persistence.rs` |
| Name pools: outside rules-data, ≥12 per shipped ancestry, no blanks, no license keys | `checks/rules_data.rs::name_pools_cover_every_shipped_ancestry` |
| Pool failure modes (malformed ⇒ typed error + nothing written; absent ⇒ default) | `checks/random_mint.rs` fixtures |
| Roster story walks (mint variety, typed name, clone dialog, badges) under the layout sweep | `ui/e2e/roster.spec.ts` |
| Crash-safety of both new write paths | `checks/crash_harness.rs::random_mint_and_clone_under_sigkill_are_none_or_all` |
| Sampler reuse is real (fuzz walk, filter off) | `checks/replay.rs::pf2e_random_walk` (rewired to `Sampler`) |
| Random mint < 250 ms; fold < 5 ms unchanged | `checks/perf.rs::random_mint_is_under_250ms` |

Deliberately unenforced items (structural sameness claims, name flavor,
mint feel) stand as the architecture recorded them; the structural halves
are visible in this report's diff: one planner (`expand_suggestions`),
one idempotency scheme (request-ID-derived character IDs), no new
constraint-exposure API.

## Decisions made inside the contract

- **Entropy = hash of the client request ID** (FNV-1a → SplitMix64), not
  an OS entropy draw: pure data, deterministic, reproducible, and it makes
  "same request ⇒ same character" literal. UUIDs per tap give distinct
  builds. The architecture's entropy-draw failure mode is thereby
  unreachable (nothing to fail), noted here as the stronger form.
- **The refill loop** (re-open own generated decisions flagged on the
  checklist, resample at settled counts, bounded at 8 rounds): the
  concrete mechanism for the spec's "no combination of picks may strand a
  constraint" — pure orchestration of existing engine operations (clear +
  expand), no engine change beyond the sanctioned seam.
- **Required free-text slots** (a background's custom Lore) sample from a
  small server-side topic list ("Farming Lore", …); the name slot is
  filled from the ancestry pool after expansion, when the rolled ancestry
  is known.
- **Old-pin clones** copy the stored sheet with only the name field
  updated (replay under old data is impossible by design); they inherit
  the pin and meet the established version flag on first open. Divergence
  refusal therefore protects current-pin sources only — same blind spot
  `verify` itself has for old pins.
- **ID prefixes**: mint `c-rn-`, clone `c-cl-` (quick build keeps
  `c-qb-`).
- **Class provenance**: a picker-chosen class records as a `player`
  decision; "Any" records the sampled class as `random`.
- The clone dialog is inline on the roster row (mirroring the delete
  confirm), not a modal.

## Agent evidence

- Full workspace suite green: 25 test targets, 0 failures (includes the
  17 checks binaries); suite wall time 17 s against the 20 s CI ceiling
  (execution only, CI's measurement).
- `cargo fmt --check`, `cargo clippy --workspace --all-targets -D
  warnings`, `cargo deny check`: clean.
- UI: `tsc` clean, eslint clean, 44 unit tests green; all 33 Playwright
  e2e specs green (3 new roster walks; every prior walk untouched).
- WASM bindings regenerated (`wasm-pack build`), parity test green.
- Live visual verification: minted "Vimsy Copperkettle" (Sensate Gnome
  Fighter, gnome-pool name, RANDOM badge, empty checklist), finalized,
  cloned via the prefilled dialog; the clone opened as its own finalized
  sheet with identical stats.
- The seed-sweep test caught two real planner interactions during the
  build (count growth after fill; checklist-judged set constraints) —
  both now handled and pinned by the same test.

## Complaints logged

None — no harness friction this checkpoint.
