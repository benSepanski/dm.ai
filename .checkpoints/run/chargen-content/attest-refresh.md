# Attestation refresh after T3–T5 breadth (chargen-content)

Run: 2026-08-29, pin `pf2e-8.4.1` (cache verified against the baked sha256),
rules-data `pf2e-pc.0.1.0`, 415 shipped records. End state:
`cargo run -p reference-check -- attest` exits 0, **385 match / 30 waived /
0 mismatch**, `claims_full_breadth: true` with `missing_from_data` empty in
every category.

## Tool changes (crates/reference-check)

The first attest over the new data produced 143 problems; every one traced
to a tool-shape gap, a name-bridge, or a legitimate divergence — **zero
our-data errors**. Comparator changes keep the values-free rule (field
names, hashes, counts only):

- **Skill-feat routing by ID prefix** (attest.rs, compare.rs): T6 expected
  a record-level `category: "skill"`; T4 shipped the T2 convention instead
  (IDs `feat.skill.<slug>` in general-feats.json, no category field). The
  partition router and the feat comparator's category argument now key on
  the `feat.skill.` prefix. This resolved all 53 skill-feat existence
  mismatches and the 53-name `skill_feats_l1` sweep block.
- **Background sub-choices** (compare.rs): `skill: "" + skill_choice` and
  `lore: "" + lore_player_named` compare as emptiness agreement — Foundry
  encodes choice-based training as an empty trainedSkills/lore list, so
  the checkable projection is "our record declares a choice ⇔ ground truth
  encodes no fixed pick". Verified against all 39 pairs before coding.
- **Background skill_feat ID resolution** (compare.rs, attest.rs): the
  field now holds shipped feat IDs; a `Ctx { feat_names }` map (shipped
  data only) resolves them to names for the granted-item membership test.
  Parameterized grants (`skill_feat_display`, e.g. "Assurance (Survival)")
  and choice-dependent grants (`skill_feat_by_choice`) accept an empty
  Foundry grant list — Foundry omits parameterized grants (verified:
  Farmhand/Nomad/Scholar/Martial Disciple empty; Miner grants the plain
  base feat). Resolved 39 background mismatches.
- **Trait dice-notation bridge** (norm_trait): the book prints "Two-Hand
  1d8" / "Fatal 1d12" / "Jousting 1d6" (AoN trait_raw confirmed); Foundry
  drops the die count. "1dN" tokens normalize to "dN". Resolved staff,
  bastard sword, greatpick, lance, light pick, pick.
- **Ranged-thrown range** (weapon comparator): dart/javelin/bola carry the
  plain "thrown" trait and the increment in Foundry's range field, unlike
  melee-thrown (dagger) where the increment lives in the thrown-N trait.
  The range projection now keys on whether our traits carry an
  incremented thrown trait.
- **Negligible-bulk bridge** (bulk_str): Foundry bulk 0 ↔ the book's "—"
  (the tables have no "0" row). Resolved 20+ gear/weapon bulk mismatches
  (all AoN-confirmed "—" or inherited-negligible rows).
- **Armor strength bridge**: the book's "—" Strength entry ships as
  `str_req: 0`; Foundry encodes null. Resolved Explorer's Clothing.
- **Name normalizer folds hyphens to spaces** (foundry.rs): bridges
  "Lantern (Bull's-Eye)" ↔ Foundry "Lantern (Bull's Eye)".
- **Foundry `consumable` items index into the Gear partition**
  (foundry.rs): Foundry types four PC1 adventuring-gear rows as
  consumable — Candle, Chalk, Oil (1 pint), Rations — exactly our four
  records and nothing else at PC1/common/level-0 (enumerated before the
  change; the gear sweep gains zero stray names).

## Overrides added (name bridges, overrides.json)

| Our record | Why |
|---|---|
| feat.ancestry.gnome.fey-world-magic | req-5 rename ("Fey World Magic"); Foundry keeps the book name First World Magic |
| feat.ancestry.orc.tusks | Foundry disambiguates as "Tusks (Orc)" |
| weapon.bolts, weapon.blowgun-darts | bundle suffix "(10)" absent upstream (arrows precedent) |
| gear.chalk, gear.rations, gear.rope | bundle/quantity suffixes "(10)" / "(1 week)" / "(50 feet)" absent upstream |
| gear.clothing-explorers | book lists it in both the armor table and the clothing family; Foundry ships only the armor-typed record (same physical item; price+bulk match) |
| gear.wheelchair-travelers-chair, gear.wheelchair-chair-storage | Foundry names the variants standalone ("Traveler's Chair", "Chair Storage") |
| gear.hearing-aid-magical | Foundry word order "Magical Hearing Aid" |
| gear.barding-light-small-or-medium | Foundry collapses light barding into one armor-typed record "Light Barding" (values match the Small/Medium row) |

## Mismatch triage (all remaining = waived; zero record fixes needed)

| Record | Fields | Disposition |
|---|---|---|
| background.street-urchin | lore | waiver re-bound (new state: skill_feat now resolves; lore divergence unchanged — generic "City Lore" per req-5 scrub vs Foundry's empty lore) |
| background.entertainer | lore | WAIVED: book/AoN "Theater Lore" (PC1 pg. 86); Foundry uses the regional spelling variant |
| background.gladiator | lore | WAIVED: book/AoN "Gladiatorial Lore" (PC1 pg. 86); Foundry's record misspells it |
| weapon.shield-bash | existence | WAIVED: real PC1 martial table row (AoN Weapons.aspx?ID=395, pg. 278); Foundry models shield attacks on shield records, no weapon record |
| weapon.blowgun-darts | traits, bulk | WAIVED: Foundry systemic consumable trait + negligible bulk vs book's no-trait-line + Bulk L (AoN Weapons.aspx?ID=440, pg. 280) |
| weapon.bolts | traits | WAIVED: Foundry systemic consumable trait (arrows/sling-bullets precedent) |
| gear.barding-light-large | existence | WAIVED: Foundry ships no Large-size light barding row (single collapsed record carries Small/Medium) |
| gear.disguise-kit-replacement-cosmetics | bulk | WAIVED: AoN Bulk L (Equipment.aspx?ID=2720, pg. 288); Foundry negligible |
| gear.thieves-toolkit-replacement-picks | bulk | WAIVED: AoN Bulk L (Equipment.aspx?ID=2758, pg. 292); Foundry negligible |
| gear.writing-set-extra-ink-and-paper | bulk | WAIVED: AoN Bulk L (Equipment.aspx?ID=2762, pg. 292); Foundry negligible |
| gear.tack | bulk | WAIVED: AoN/book Bulk 1 (Equipment.aspx?ID=2755, pg. 292); Foundry encodes heavier |

Guard/Noble lore modeling (t4-aon call #1) needs **no waiver**: Foundry
also encodes no fixed Lore for them, so the lore_player_named emptiness
projection matches cleanly. The RAW two-option restriction remains a
data-modeling note only (record text carries it).

Pre-existing waivers (kit.fighter, 16 skills, weapon.arrows,
weapon.sling-bullets) all still bind — none went stale, none re-reviewed.

## Reverse sweep reconciliation → claims_full_breadth = TRUE

Post-fix sweep left exactly 20 ancestry-feat names; 2 were our records
under bridged names (First World Magic, Tusks (Orc) — now matched via
overrides), the other 18 are the Changeling/Nephilim heritage feats
(traits verified changeling/nephilim per record). Those heritages are
uncommon and excluded by name in the scope; their feats are excluded with
them via 18 reasoned `spec_exclusions` entries (`ancestry_feats_l1`) —
Foundry marks the feats themselves common, so a rarity filter cannot
exclude them. All other categories emptied through the matches above.
**No genuinely missing in-scope record surfaced — nothing was entered.**
`missing_from_data` is empty in all 11 categories and
`CLAIMS_FULL_BREADTH` is flipped to true in attest.rs (the offline check
now asserts sweep emptiness).

T6's gear-count reconciliation note resolved: the sweep's 73-gear estimate
vs the spec's ~140 was Foundry variant-collapsing plus its consumable
typing; with the consumable partition addition the sweep and shipped data
agree exactly.

## Data corrections

None required — every T3–T5 record survived the mechanical comparison or
was a documented legitimate divergence. `gear.grappling-hook`'s wrong AoN
URL (T5's flagged pre-existing bug) is already fixed in the committed data
(verified: cites Equipment.aspx?ID=2725, the Grappling Hook).

## Final verdict counts (match/waived/mismatch)

ancestries 8/0/0 · heritages 46/0/0 · ancestry-feats 67/0/0 ·
backgrounds 36/3/0 · classes 1/0/0 · class-feats 8/0/0 ·
general-feats 67/0/0 (incl. 53 skill feats) · skills 0/16/0 ·
weapons 58/5/0 · armor 12/0/0 · shields 4/0/0 · gear 78/5/0 ·
kits 0/1/0 — **total 385/30/0**. Overrides used: 14.

## Gates

- `cargo run -p reference-check -- attest`: exit 0, zero unwaived
  mismatches, zero stale waivers.
- `cargo test -p checks --test attestation`: 7/7 ok (breadth-claim
  emptiness assertion now active).
- `cargo test -p checks --test rules_data`: 5/5 ok.
- `cargo test -p checks --test replay`: 6/6 ok (+1 ignored regen);
  goldens untouched.
- `cargo fmt --all -- --check`: clean.
- `cargo clippy -p reference-check --all-targets -- -D warnings`: exit 0
  (three pre-existing clippy.toml config notices about unreachable tokio
  paths; not lints, not introduced here).

## For the orchestrator

- No decisions pending from this pass. The known sheet gaps T4 logged
  (Canny Acumen / Assurance / Skill Training choice-in-feat modeling) are
  engine-side calls, not attestation blockers — Foundry's feat records
  compare clean on the checked fields.
- If a future data pass ships Changeling/Nephilim, delete their 18
  `spec_exclusions` entries alongside the records.
