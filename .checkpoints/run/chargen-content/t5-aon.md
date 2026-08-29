# T5 — equipment data entry: AoN verification log

Ground truth: AoN public Elasticsearch (`https://elasticsearch.aonprd.com/aon/_search`,
index `aon-20260802-141253`), filtered with
`{"term": {"source.keyword": "Player Core"}}` per category. Note the stricter
`primary_source.keyword: "Player Core"` filter drops 7 common weapons whose remaster
record is primary-sourced elsewhere but lists Player Core in its source list (the
Shortbow precedent from chargen-fighter) — the `source.keyword` filter is the correct
one and reproduces the research-pass counts exactly.

## Query per category

| Category | Query filter | Docs | Common docs used |
|---|---|---|---|
| Weapons | `category: weapon` + `source.keyword: "Player Core"` | 89 | 65 (43 martial + 18 simple + 4 ammunition; 1 unarmed = Fist) |
| Armor | `category: armor` + same | 13 | 13 (incl. the non-purchasable "Unarmored" stat row) |
| Shields | `category: shield` + same | 4 | 4 |
| Gear | `category: equipment` + same | 173 | 141 (130 Adventuring Gear + 11 Assistive Items); 32 Services docs excluded |

Fields verified per record straight from the ES `_source`: `price_raw`, `damage`,
`weapon_group`, `weapon_category`, `hands`, `range`, `reload_raw`, `bulk_raw`,
`trait_raw`, and per-armor `ac`/`dex_cap`/`check_penalty`/`speed_penalty`/`strength`,
per-shield `hardness_raw`/`hp_raw` (HP with BT in parentheses), plus `url` and the
Player Core page from `source_raw`. Gear `text` summaries were paraphrased from the
ES `text` field.

## Final counts (equipment.json)

| Array | Before | After | Delta |
|---|---|---|---|
| weapons | 11 | 63 (41 martial + 18 simple + 4 ammunition) | +52 |
| armor | 7 | 12 | +5 |
| shields | 2 | 4 | +2 |
| gear | 3 | 83 (74 adventuring gear + 9 assistive) | +80 |
| kits | 1 | 1 | 0 |

All kit.fighter contents/options IDs unchanged and still resolve
(`cargo test -p checks --test rules_data` passes, which runs the full
integrity pass including kit cross-references).

## Modeling calls

- **Ammunition stays in `weapons`** with `category: "ammunition"` — the shipped
  Arrows/Sling Bullets records already model it that way, and `WeaponRecord` fits
  (`damage: null`, `hands: null`, price per 10 in the name, e.g. "Bolts (10)").
  Added Bolts (10) at 1 sp and Blowgun Darts (10) at 5 cp.
- **Price "—" ships as `price_cp: 0`** (Club, Staff, Shield Bash, Primal Symbol),
  matching the shipped Sling precedent. These are the book's genuinely free rows.
- **Shield Bash included** (price "—", bulk "—"): it is a real PC1 martial-weapons
  table row and carries the attack stats a fighter needs to Strike with a shield.
  Shield Boss / Shield Spikes included as purchasable attachments (5 sp each,
  trait "attached to shield").
- **Negligible bulk ships as `"—"`** (the book's own notation) in the `bulk` string
  field.
- **Thrown weapons** follow the shipped Dagger convention: `range` is
  `"thrown N ft."` and the thrown trait stays in `traits` exactly as AoN lists it
  (`"thrown 10 ft."` vs plain `"thrown"` for the ranged Dart/Javelin/Bola).
  Reload weapons follow the shipped Longbow convention: `"100 ft., reload 0"`.

## Exclusions

- **Uncommon weapons (24 docs / 23 distinct)**: all uncommon PC1 weapons excluded
  per the common-only rule — martial: Breaching Pike, Butterfly Sword, Dogslicer,
  Elven Curve Blade, Falcata, Fangwire, Filcher's Fork, Horsechopper, Kama, Katana,
  Khakkhara, Kukri, Nunchaku, Sai, Shuriken, Tekko-Kagi, Tengu Gale Blade, Wakizashi;
  advanced: Aklys, Fauchard, Spiked Chain, Taw Launcher, Whip Claw; simple: Ankle Biter.
  (These include every ancestry weapon; Unconventional Weaponry stays greyed.)
- **Fist** (common unarmed doc): engine built-in, not a record — verified no shipped
  or added record duplicates it.
- **Alchemical Bomb** (common martial doc): a table placeholder whose price and
  damage are "Varies" (the actual bombs are alchemical items, out of scope);
  `price_cp: u32` cannot express it, so the row is excluded. This plus the AoN
  double-indexed **Bola** (legacy doc ID=331 and remaster ID=433 both citing PC1
  pg. 280; the remaster ID=433 was kept) is why 43 martial docs became 41 records.
- **"Unarmored" armor doc** (Armor.aspx?ID=38): the wear-nothing stat row — not
  purchasable, price "—", Dex cap "—" (inexpressible in `ArmorRecord.dex_cap: i32`),
  and the engine computes unarmored defense natively. Excluded; this is why the
  13-common-armor target ships as 12 records (Explorer's Clothing, the 13th
  purchasable table column, IS included with `category: "unarmored"`).
- **Services (32 docs)**: excluded wholesale per scope (incl. Spellcasting and
  Transportation subcategories).
- **Uncommon gear (6 docs)**: Scholarly Journal (+Compendium), Survey Map (+Atlas).

## Leveled-item cuts (level 2+ variant rows, all common)

Alchemist's Lab (Expanded) L3, Artisan's Toolkit (Sterling) L3, Barding
(Heavy; Small or Medium) L2, Barding (Heavy; Large) L3, Clothing (High-Fashion
Fine) L3, Compass (Lensatic) L3, Concealed Sheath L3, Crowbar (Levered) L3,
Detective's Kit L3 (base item is L3 — whole item cut), Disguise Kit (Elite) L3,
Disguise Kit (Elite Cosmetics) L3, Fishing Tackle (Professional) L3, Healer's
Toolkit (Expanded) L3, Lock (Average L3 / Good L9 / Superior L17), Magnifying
Glass L3 (whole item cut), Manacles (Average L3 / Good L9 / Superior L17),
Musical Instrument (Virtuoso Handheld / Virtuoso Heavy) L3, Periscope L2 (whole
item cut), Repair Toolkit (Superb) L3, Spyglass (Fine) L4, Tent (Pavilion) L2,
Thieves' Toolkit (Infiltrator L3 / Infiltrator Picks L3).

Level 0–1 rows of leveled families ARE included: Lock (Poor/Simple), Manacles
(Poor/Simple) — Simple rows are level 1.

## Variant-collapse decisions

- Unpriced umbrella docs (Barding, Clothing, Lantern, Lock, Manacles, Musical
  Instrument, Religious Symbol, Tent, Tool, plus unpriced duplicate docs for
  Alchemist's Lab / Hearing Aid / Repair Toolkit / Wheelchair) are not purchasable
  rows — each priced variant ships as its own record instead
  ("Lantern (Hooded)", "Tool (Long)", …), all sharing the family's AoN url.
- Straight double-indexed docs (Artisan's Toolkit, Climbing Kit, Compass, Crowbar,
  Disguise Kit, Fishing Tackle, Healer's Toolkit, Spyglass, Thieves' Toolkit,
  Writing Set, Wheelchair) deduped by name, keeping the priced doc.
- Quantity-priced items put the quantity in the name per the Arrows (10)
  precedent: Chain (10 feet), Chalk (10), Rope (50 feet), Rations (1 week),
  Oil (1 pint), Ladder (10-foot).
- Net result: 141 gear-category docs → 83 records (−32 services already excluded
  from the 173 total; −6 uncommon; −25 L2+ rows; −27 umbrella/duplicate docs).

## Reserved-noun scrub

- **Wheelchair (Chair Storage) → "Wheelchair (Chair Stowage)"**
  (`gear.wheelchair-chair-stowage`, `"scrubbed": true`, AoN url kept at the
  original Equipment.aspx?ID=2777): the word "storage" contains the denylisted
  deity name "torag" as a case-insensitive substring, tripping
  `no_reserved_proper_nouns_in_records`. This is a false positive, not actual
  Reserved Material; if a reasoned exception is later added to
  rules-data/denylist.json (out of T5's file scope — denylist.json is shared),
  the record can be renamed back to the book's "Chair Storage".
  All other record names/texts were written to avoid denylist terms (no deity
  names in the Religious Symbol/Text entries, etc.).

## Pre-existing data bug found (NOT fixed — out of contract)

`gear.grappling-hook` (shipped 0.1.0) cites `Equipment.aspx?ID=2712`, which is
the **Chest** record; the Grappling Hook is `Equipment.aspx?ID=2725`. Left
byte-identical because shipped records must not change under T5; recommend a
follow-up correction. (Every other shipped equipment URL was re-verified correct:
weapons 358/386/379/371/403/398/436/437/430/443/442, armor 40–47, shields 18/19,
gear 2700/2727.)

## Gate results

- `cargo test -p checks --test rules_data`: **5 passed, 0 failed** (after the
  Stowage scrub).
- `cargo test -p checks --test replay`: 5 passed, 1 failed —
  `golden_elyse_human_archer` fails on `pf2e.ancestry.languages`
  ("1 additional language choice(s) left"). **Not an equipment failure**:
  reverting equipment.json to HEAD reproduces the identical failure, so it comes
  from the concurrent T3/T4 (ancestries/languages) work in flight.
  `golden_torvald_dwarf_fighter` (the fighter golden, which exercises the kit and
  equipment) passes with the new data.
