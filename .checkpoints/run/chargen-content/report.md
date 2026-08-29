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

Then start the server and open the URL it prints (usually
`http://localhost:8000`). Leave it running for all the walks.

```bash
cargo run --release -p server -- --data-dir ./campaign
```

**Walk 9 — the bump, on your real roster (do this first).**
1. The roster loads with your slice-1 characters. Each one now carries a
   version note: either an amber review flag ("Rules data changed" /
   "Review: replay failed") or the quiet "Data updated — re-pin
   available".
2. Click a *flagged* character. A panel shows every changed value as an
   old → new row. Read it, then click **Accept new values**. The sheet
   updates; nothing else changes.
3. If you have a second flagged character, open it and click **Keep old
   derivation** instead — the flag clears, the sheet stays as it was.
4. If a character shows the quiet state, open it and click **Re-pin to
   pf2e-pc.0.2.0** (its replay was identical; this just records the pin).
5. Open the character files in an editor (`campaign/characters/*.json`):
   each action you took is recorded under `version_history`, with the
   superseded values preserved on any accept. Nothing was lost.
6. If you had a half-finished draft, click its "Resume creating…" entry:
   it explains the data changed and walks you through resolving before
   the wizard continues; anything now illegal reopens on the checklist.

**Walk 1 — linear breadth (Leshy, front to back).**
1. Type a name, click **Create character**. Go in step order.
2. Ancestry step: eight ancestries now. Pick **Leshy**, then a heritage
   (try **Root Leshy**), then an ancestry feat, then assign the boosts.
3. Background step: 39 entries — type in the filter box to find
   **Nomad**. Confirm it, then in the Lore box it opens, type `Steppe` —
   the sheet's skill list shows **Steppe Lore (trained)**, your word.
4. If your Int is positive, a "Languages" chooser appears on the ancestry
   step — pick from the leshy list and watch the sheet's Languages line.
5. Class → Fighter, key attribute, class feat, skills as usual.
6. Equipment: the shop is grouped (Weapons / Armor / Shields / Gear) with
   one filter across all groups. Buy a couple of items by filtering.
7. Finalize. Hand-verify the sheet against Archives of Nethys: Root Leshy
   HP is 10 (so total 20 + Con), Small size, low-light vision, speed 25,
   the typed Lore, the Languages line, Bulk.

**Walk 2 — backwards (Gnome, checklist-driven).**
1. Create a character and jump straight to the **equipment** step (the
   step tabs are all clickable). Buy something. Jump to **details**, name
   them.
2. Now let the checklist drive: click each red/amber entry — it jumps you
   to the right step. Pick class Fighter, then background **Scholar**:
   inside the background a skill picker opens (Arcana / Nature /
   Occultism / Religion). Pick one and watch **Assurance** follow that
   choice on the sheet.
3. Finish boosts and ancestry last. The moment the final checklist entry
   clears, Finalize unblocks.

**Walk 3 — the cascade (Halfling → Orc).**
1. Create a character; take **Halfling**, a heritage, a feat, boosts.
2. Go back to the ancestry step and change ancestry to **Orc**. A
   confirmation lists exactly which decisions will be cleared.
3. Confirm it: those slots reopen on the checklist; re-pick them and
   check nothing halfling-flavored survived on the sheet.

**Walk 4 — versatile heritage (Dwarf + Aiuvarin).**
1. Create a **Dwarf**; at the heritage step, **Aiuvarin** appears
   alongside the dwarf heritages. Pick it.
2. Open the ancestry-feat list: it is now the union — dwarf feats plus
   aiuvarin and elf feats (filter for "Earned Glory" or an elf feat name
   to see both sides).

**Walk 5 — the chooser chain (Canny Acumen).**
1. Create a **Human**, heritage **Versatile Human**. A "General feat"
   slot opens with the full 67-entry catalog — use the filter.
2. Notice a skill feat you lack the training for (e.g. **Battle
   Medicine** before training Medicine) is greyed with the rule named.
3. Pick **Canny Acumen**. A "Proficiency choice" slot opens: choose
   **Will**. The sheet's Will save jumps to expert (+5 at level 1).

**Walk 6 — quick build.**
1. Back on the roster, click **Quick build a Fighter** (name optional).
2. You land on a completed wizard: every slot filled, each decision
   badged *suggested*, checklist empty.
3. Swap one suggestion (e.g. change the class feat) — the badge on that
   slot flips to a normal player decision.
4. Rename if you like, Finalize. Ask yourself: would you hand this to a
   player whose session starts in five minutes?

**Walk 7 — fill the rest.**
1. Create a character by hand: pick only ancestry and background.
2. Click **Fill remaining with suggestions** (in the wizard header).
3. Confirm your two hand-picked choices did not move (no *suggested*
   badge on them); everything else filled in. Finish and finalize.

**Walk 8 — the stubborn draft.**
1. Create a character; confirm class Fighter and key attribute
   **Dexterity** first, nothing else.
2. Click **Fill remaining with suggestions**: the fill adapts around your
   Dex choice where legal; anything it could not resolve stays on the
   checklist. Your Dex decision is untouched.

**Walk 10 — the greyed shelf.**
1. Create a **Gnome**; at the heritage step find **Fey-touched** and
   **Wellspring** — visible but unpickable, each explaining that cantrip
   choices arrive with the spellcaster slice.
2. Filter the general/ancestry lists for **Unconventional Weaponry** —
   same pattern (uncommon weapons not shipped). Judge whether each reason
   tells a player the truth.

**The attestation, as a skeptic.**
1. Open [rules-data/attestation.json](../../../rules-data/attestation.json).
   Pick three record IDs at random; each shows which fields were
   machine-checked against the Foundry snapshot, or a waiver with a
   reason.
2. Spot-check the scrubbed records against AoN: search AoN for "First
   World Magic" and compare it to our **Fey World Magic** — same
   mechanics, reserved nouns gone. Same for the Fey-touched Gnome text.
3. Replay-verify every character on disk:

```bash
cargo run --release -p server -- --data-dir ./campaign verify
```

   Characters you re-pinned or accepted report clean; anything you left
   on keep-old reports as pinned to the older known version.

**Intent check.** After the walks: is the sentence "a table can build any
common Player Core Fighter without the book open" now true?

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
