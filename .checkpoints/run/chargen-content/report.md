# chargen-content — report

Checkpoint: `chargen-content` · Branch: `checkpoint/chargen-content` · Status: delivered

## What changed and why

The Fighter wizard is now complete for common Player Core content, and the
numbers are machine-trusted. Rules data grew from 111 to **415 records**
(version `pf2e-pc.0.2.0`): all 8 ancestries with heritages, level-1 feats,
and per-ancestry bonus-language lists; the versatile heritages Aiuvarin and
Dromaar working under any ancestry; 39 of 40 backgrounds with their
in-background choices working (skill picks, player-named Lores,
choice-dependent feats) rather than flattened; all 14 common general feats
plus the full 53-record level-1 skill-feat catalog; and the common
weapon/armor/shield/gear tables. Excluded by name, per the spec: uncommon
and rare content, Raised by Belief, and everything cantrip-shaped (those
records ship greyed with reasons).

Trust is mechanical now: a `reference-check` tool compares every record
field-by-field against a pinned, hash-verified Foundry snapshot
(verification only — no Foundry bytes anywhere in the repo) and writes a
committed attestation CI verifies offline. Final tally: **385 match / 30
reasoned waivers / 0 mismatches**, completeness both directions. The
pipeline found **zero transcription errors** in the new records; it did
force fixes to two things hand-review missed in slice 1 (a wrong AoN URL)
and this slice's own drafts (the versatile-heritage vision encoding, a
heritage skill-grant fold gap — both also caught by the golden builds).

Because the data version bumped over your live characters, the
review-flag machinery now exists: on first launch your slice-1 roster
computes each character's status, flags divergent or failing replays with
old-vs-new values, and mutates nothing until you explicitly accept,
keep-old, or re-pin. Quick build landed as the app-authored suggested
build (PF2e publishes none): one roster tap yields a complete, legal,
reviewable — not auto-finalized — sword-and-board human Fighter, every
choice badged as suggested until you edit it; "fill remaining" completes a
stalled draft without moving anything confirmed. Long option lists gained
a text filter and the shop is category-grouped; ten Playwright scenarios
automate the spec's ten walks.

## How to verify

First, the one-command insurance:

```bash
cp -R campaign campaign.backup-pre-0.2.0
```

Then start the server and follow the spec's ten walks
([What Ben checks](../../specs/chargen-content.md)):

```bash
cargo run --release -p server -- --data-dir ./campaign
```

1. **Walk 9 first — the bump on your real roster.** Open the roster: your
   slice-1 characters show version flags or quiet re-pin states. Read a
   diff, accept one, keep-old another; open the character files afterward
   and confirm prior values are recorded, nothing lost.
2. **Walk 1 — linear breadth.** Leshy Fighter, Nomad with a typed "Steppe"
   Lore, languages, filtered gear, finalize; hand-verify against AoN.
3. **Walks 2–5** — backwards Gnome with Scholar's in-background skill
   pick; the Halfling→Orc cascade; Dwarf + Aiuvarin's widened feat list;
   Versatile Human → Canny Acumen showing expert on the sheet and a
   trained-gated skill feat greying with its rule.
4. **Walks 6–8 — quick build.** Roster tap → read badges → swap one →
   rename → finalize (the five-minute-player test); half-build by hand
   then "fill remaining"; confirm a Dex key attribute survives a fill.
5. **Walk 10 — the greyed shelf.** Fey-touched/Wellspring Gnome and
   Unconventional Weaponry: judge whether the reasons tell the truth.
6. **The attestation, as a skeptic.** Open
   [rules-data/attestation.json](../../../rules-data/attestation.json):
   pick three records, see what was checked vs waived; spot-check the
   scrubbed gnome records (Fey World Magic née First World Magic) against
   AoN — mechanics intact, nouns gone. Replay-verify everything:

```bash
cargo run --release -p server -- --data-dir ./campaign verify
```

7. **Intent check:** is "a table can build any common Player Core Fighter
   without the book open" now true?

## Constraints now enforced

All slice-1 rows still run; the new rows (architecture table → repo tooling):

| Rule | Lives at |
|---|---|
| reference-check crate edges; nothing depends on it | `checks/crate_layering.rs` |
| Reserved-noun denylist (word-boundary) + exceptions with reasons | `checks/rules_data.rs`, `rules-data/denylist.json` |
| Source-book allowlist = {Pathfinder Player Core} | `checks/rules_data.rs` |
| All cross-refs resolve incl. background skill-feat IDs + suggested build | `checks/rules_data.rs`, `ruleset-pf2e::check_integrity` |
| Attestation current: two-way coverage, per-record hash recompute, zero unwaived, hash-bound waivers, values-free schema, full-breadth gate | `checks/attestation.rs` |
| Ground-truth cache ignored + untracked; CI never invokes the tool | `.gitignore`, `checks/attestation.rs` |
| ID immutability + lineage, one artifact | `checks/rules_data.rs`, `rules-data/shipped-versions.json` |
| Suggested build folds clean + finalizable | `checks/quick_build.rs` |
| Fill-remaining preserves confirmed work; partial names remainder | `checks/quick_build.rs` |
| Quick-build server authority + wizard-write under version guard | `checks/api_authority.rs`, `checks/version_guard.rs` |
| Quick-build atomicity (SIGKILL none-or-all) + request idempotency | `checks/crash_harness.rs`, `checks/confirm_idempotency.rs` |
| Version guard: flagged-byte-identical-until-explicit-action, all three replay outcomes, keep-old recorded | `checks/version_guard.rs` (8 tests) |
| Storage v2: v1 reads untouched, upgrades on write, v3 refused | `checks/persistence.rs` |
| Golden coverage: 10 hand-verified builds incl. versatile, sub-choice, quick-build | `checks/replay.rs` + fixtures |
| Warm-rebuild lever 1: wasm-opt skipped in the CI warm loop only | `.github/workflows/ci.yml` |

## Decisions made inside the contract

- **Skill feats live in `general-feats.json`** (`feat.skill.*`) — they are
  general feats RAW, so the chooser reaches them with zero new plumbing.
- **Counts corrected against AoN during entry**: common halfling heritages
  are 5 (Jinxed is uncommon), Tusks is orc-only in the remaster (Dromaar
  reaches it via the union; no Aiuvarin gap), ancestry-bound heritages
  total 44.
- **Aiuvarin/Dromaar encode `sense_upgrade`** — their record text carries
  the "(or darkvision…)" clause; an interim plain-`sense` reading of a
  truncated AoN summary was reverted when the goldens caught it.
- **Guard and Noble** model their two-option Lore as player-named with the
  options stated in text (no lore-choice mechanism exists) — documented
  divergence, waived in the attestation. **Street Urchin** keeps its
  shipped fixed "City Lore".
- **Canny Acumen is fully modeled** (target chooser → expert on the
  sheet); **Assurance and Skill Training stay annotation-only** under the
  existing choice-in-feat precedent — the one remaining known sheet gap.
- **Ammunition ships in `weapons`** as its own category; unpriced umbrella
  gear rows don't ship, priced variants do; L2+ variant rows cut.
- **Keep-old is finalized-only** — a draft cannot continue against old
  data, so drafts must resolve (spec's table-use reading).
- **Quick build's content**: Human / Skilled (Diplomacy) / Cooperative
  Nature / Warrior / Str-Con-Wis-Dex line / Sudden Charge /
  sword-and-board kit, default name "Garrek Ironvale" — original dm.ai
  choices on the published anchors, pinned by a golden.
- **Slice-1 fixes**: `gear.grappling-hook`'s AoN URL corrected; heritage
  `grant_skills`/`grant_lore` now fold into training (Battle-Ready Orc
  regression, found by golden work, unit-tested).
- Denylist matching is word-boundary ("torag" no longer matches
  "storage"); the test-support surface for version fixtures is a hidden,
  loudly-announced `--extra-known-versions` flag.

## Agent evidence

- `cargo test --workspace`: green — 61 checks-suite tests (13 test
  binaries) incl. crash harness, version guard, quick build, attestation;
  31 ruleset unit tests; engine-core planner tests. Suite wall time
  **13.2 s** (ceiling 20 s).
- Warm incremental rebuild (engine touch → WASM + server): **8.8 s** with
  lever 1, vs 11.2 s with wasm-opt (ceiling 10 s, pre-authorized 12 s
  untouched). WASM: **908 KB** (614 KB in slice 1). rules-data: 440 KB.
- Attestation: 385 match / 30 waived / 0 mismatch, `claims_full_breadth:
  true`, zero stale waivers, pinned `pf2e-8.4.1`
  (sha256 b0a649e6…); offline checks 7/7.
- UI: tsc, eslint clean; vitest **31**; Playwright **20** (10 slice-1
  stories + the 10 walks). fmt, clippy `-D warnings`, cargo-deny all
  clean.
- Verification records: `t3-aon.md`, `t4-aon.md`, `t5-aon.md`,
  `attest-refresh.md`, `t10-goldens.md` (per-build arithmetic) in this
  directory.

## Complaints logged

None — no checkpoints-harness friction this run (two transient
API-stream drops during subagent work were infrastructure, resumed
without loss).
