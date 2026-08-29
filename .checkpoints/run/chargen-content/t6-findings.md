# T6 — reference-check findings

Run: 2026-08-29, pin `pf2e-8.4.1` (tarball sha256
`b0a649e6f9859350f7eca86e85082ac68b20309f4335c77bf6e1643aff009c8a`),
rules-data `pf2e-pc.0.1.0` (111 records).

## Suspected our-data errors

**None.** Every mechanically comparable record (91 of 111) matches the
Foundry ground truth on every checked field — the slice-1 hand
verification holds up. The three field-level divergences below were each
investigated and are legitimate differences, waived, not data errors.

## Waivers (20) — all bound to state hashes in crates/reference-check/overrides.json

| Records | Mismatch | Why waived |
|---|---|---|
| skill.* (16) | no counterpart | PF2e core skills are fixed game vocabulary, not Foundry compendium records; attribute pairings were AoN-verified in slice 1 |
| kit.fighter | no counterpart | Foundry ships no class-kit pack; kit contents/price hand-verified (slice-1 dossier §8.6) |
| background.street-urchin | lore | Book parameterizes the Lore on the character's home city with a Golarion example noun; we ship generic "City Lore" per the req-5 scrub, Foundry encodes an empty lore list |
| weapon.arrows, weapon.sling-bullets | traits | Foundry attaches its systemic `consumable` handling trait to ammunition records; the book's ammunition entries carry no trait line (PC1 p.280) |

## Slice-1 known quirks, resolved against Foundry

- **Shortbow source quirk** (AoN indexes it under Tian Xia Character
  Guide): does not surface — Foundry's shortbow record carries publication
  "Pathfinder Player Core". Clean match, no waiver.
- **Remaster renames** (Reactive Strike, Vicious Swing, Stonemason's Eye,
  Healer's Toolkit, Skilled/Versatile Human): Foundry uses remaster names
  throughout; all matched by normalized name.
- **Artisan-not-Blacksmith**: our data already ships Artisan; clean match.
- **Kit price semantics**: kit has no Foundry counterpart; waived (above).

## Match statistics (match/waived/mismatch)

ancestries 4/0/0 · heritages 18/0/0 · ancestry-feats 30/0/0 ·
backgrounds 4/1/0 · classes 1/0/0 · class-feats 8/0/0 ·
general-feats 5/0/0 · skills 0/16/0 · weapons 9/2/0 · armor 7/0/0 ·
shields 2/0/0 · gear 3/0/0 · kits 0/1/0 — **total 91/20/0, zero unwaived.**

Overrides used (2): `weapon.arrows` and `weapon.sling-bullets` → Foundry
names its ammo records without the "(10)" bundle suffix.

## Reverse completeness (informational — claims_full_breadth=false)

Missing from data, per attestation `missing_from_data` (counts): ancestries
4, heritages 28, backgrounds 34, ancestry_feats_l1 55, fighter_feats_l1 0,
general_feats_l1 9, skill_feats_l1 53, weapons 49, armor 3, shields 2,
gear 70. These are the T3–T5 workload as Foundry sees it. Notes for the
flag flip after T3–T5:

- **Raised by Belief** is common, so it would sit in `missing_from_data`
  forever; it is excluded by name via `spec_exclusions` in overrides.json
  (reasoned, per spec req 1 [call]). Add future by-name exclusions there.
- The `classes` pack is not swept (slice claims Fighter breadth only).
- Sweep filters are: publication == Pathfinder Player Core, rarity common;
  feats additionally level 1 (fighter trait for class feats); equipment
  additionally level 0. The gear sweep counts 73 PC common level-0 records
  vs the spec's ~140 estimate — when T5 lands, reconcile the filter (some
  adventuring gear may be level>0 or typed consumable) before flipping
  `CLAIMS_FULL_BREADTH` in crates/reference-check/src/attest.rs.
- Armor sweep shows 10 PC common armors (spec says 13; the remainder are
  presumably non-common in Foundry) — same reconciliation note.

## Mechanical notes for future runs

- If a new record file is added (e.g. skill-feats), extend three lockstep
  lists: `RECORD_FILES` (checks/rules_data.rs), `ATTESTED_RECORD_FILES`
  (checks/attestation.rs), `FLAT_FILES` (crates/reference-check/src/ours.rs).
  Skill feats inside general-feats.json already route correctly if records
  carry `"category": "skill"`.
- Foundry encodes neither fighter `class_dc` rank (null) nor the
  Acrobatics/Athletics class-skill choice; both stay human-verified and are
  deliberately absent from `fields_checked` on the class record.
- GitHub generates tag tarballs on the fly; the pinned sha256 held across
  two independent downloads on 2026-08-29. If GitHub ever changes
  compression, `fetch` fails against the pin — re-pinning is a deliberate
  edit to the consts in crates/reference-check/src/main.rs.

## Re-run after new data lands

```
cargo run -p reference-check -- fetch     # once per machine / after cache loss
cargo run -p reference-check -- attest    # writes rules-data/attestation.json
cargo test -p checks --test attestation   # offline gate CI runs
```

`attest` exits non-zero while unwaived mismatches or stale waivers exist,
printing each record's mismatched fields and the state_hash a waiver must
carry; fix the record (book wins) or add a reviewed waiver in
crates/reference-check/overrides.json, then re-run. Any rules-data edit or
manifest version bump stales the attestation until `attest` is re-run —
that is the forcing function, not an error.
