# T3 AoN verification record — ancestries / heritages / ancestry feats

Verified against Archives of Nethys public Elasticsearch
(`https://elasticsearch.aonprd.com/aon/_search`) on 2026-08-29, filtered to
`primary_source.keyword == "Player Core"` (strict PC1; legacy Core
Rulebook / APG / Character Guide duplicates identified by primary_source and
excluded). Query pattern per `.checkpoints/run/chargen-fighter/aon-reference.md`:
`category` term + `primary_source.keyword` term + `name.keyword`/`trait`/`level`
terms; values read from the record's `markdown`/`text`, `attribute`,
`attribute_flaw`, `language`, `trait`, `vision`, `hp`, `size`, `speed`,
`rarity`, `source_raw`, `url` fields.

## ancestries.json (4 → 8)

New records, all rarity common on the PC record:

| Record | AoN | Pg | Verified values |
|---|---|---|---|
| ancestry.gnome | /Ancestries.aspx?ID=61 | 50 | HP 8; Small; 25 ft; boosts Con, Cha + 1 free; flaw Str; languages Common, Fey, Gnomish; traits gnome, humanoid; low-light vision |
| ancestry.halfling | /Ancestries.aspx?ID=63 | 58 | HP 6; Small; 25 ft; boosts Dex, Wis + 1 free; flaw Str; languages Common, Halfling; traits halfling, humanoid; no vision sense; special Keen Eyes (+2 circ. Seek within 30 ft; flat check 3/9 vs concealed/hidden) |
| ancestry.leshy | /Ancestries.aspx?ID=65 | 66 | HP 8; Small; 25 ft; boosts Con, Wis + 1 free; flaw Int; languages Common, Fey; traits leshy, plant (NOT humanoid); low-light vision; special Plant Nourishment |
| ancestry.orc | /Ancestries.aspx?ID=66 | 70 | HP 10; Medium; 25 ft; two free boosts, no flaws; languages Common, Orcish; traits humanoid, orc; darkvision |

`additional_languages` added to all 8 ancestries, read verbatim from each PC
ancestry page's "Additional languages" sentence:

| Ancestry | List shipped |
|---|---|
| dwarf | Gnomish, Goblin, Jotun, Orcish, Petran, Sakvroth |
| elf | Draconic, Empyrean, Fey, Gnomish, Goblin, Kholo, Orcish |
| gnome | Draconic, Dwarven, Elven, Goblin, Jotun, Orcish |
| goblin | Draconic, Dwarven, Gnomish, Halfling, Kholo, Orcish |
| halfling | Dwarven, Elven, Gnomish, Goblin |
| human | Draconic, Dwarven, Elven, Fey, Gnomish, Goblin, Halfling, Jotun, Orcish, Sakvroth |
| leshy | Draconic, Elven, Gnomish, Goblin, Halfling, Sakvroth |
| orc | Goblin, Jotun, Petran, Sakvroth |

Language-list notes:

- No reserved nouns appear in any PC list (no "Varisian"-style regional
  demonyms; Kholo, Petran, Sakvroth, Empyrean, Fey, Jotun are remaster
  rulebook language names and are not on the denylist), so nothing was
  omitted for scrub reasons.
- The RAW catch-all "and any other languages to which you have access (such
  as the languages prevalent in your region)" is not representable as a
  fixed list and is omitted by design on every ancestry.
- Human's list is RAW "the list of common languages": the PC common
  languages minus Common itself (verified via `category: language`,
  `rarity: common`, PC records — Languages.aspx?ID=155–163 plus Fey ID=119
  and Sakvroth ID=118). Wildsong (ID=116, the secret druidic language) is
  rarity-common on AoN but is not a general pick and was excluded.
- Known gap: human RAW grants "1 + Int modifier" picks; the engine computes
  max(0, Int) + bonus_languages effects and AncestryRecord carries no
  effects, so the +1 is not representable this version. Shipped as-is;
  flagged for a future `bonus_languages`-on-ancestry or similar.

## heritages.json (18 → 46: +26 ancestry-bound, +2 versatile)

All shipped records verified rarity common, source Player Core. Effects noted
only where the engine interprets them; resistances/reactions/riders stay
annotation text (Forge Dwarf precedent).

| Record | AoN | Pg | Mechanics shipped |
|---|---|---|---|
| heritage.gnome.chameleon | /Heritages.aspx?ID=245 | 51 | text only (Stealth rider annotation); SCRUBBED |
| heritage.gnome.fey-touched | /Heritages.aspx?ID=246 | 51 | choose_from_catalog primal_cantrips ×1 (absent catalog → greys with reason, Otherworldly Magic pattern); SCRUBBED |
| heritage.gnome.sensate | /Heritages.aspx?ID=247 | 51 | sense "scent (imprecise) 30 feet" |
| heritage.gnome.umbral | /Heritages.aspx?ID=248 | 51 | sense darkvision |
| heritage.gnome.wellspring | /Heritages.aspx?ID=249 | 51 | choose_from_catalog wellspring_cantrips ×1 (absent catalog → greys) |
| heritage.halfling.gutsy | /Heritages.aspx?ID=255 | 59 | text only |
| heritage.halfling.hillock | /Heritages.aspx?ID=256 | 59 | text only |
| heritage.halfling.nomadic | /Heritages.aspx?ID=258 | 59 | bonus_languages count 2 |
| heritage.halfling.twilight | /Heritages.aspx?ID=259 | 59 | sense low-light vision |
| heritage.halfling.wildwood | /Heritages.aspx?ID=260 | 59 | text only |
| heritage.leshy.cactus | /Heritages.aspx?ID=263 | 67 | unarmed_attack Spine 1d6 P (finesse, unarmed) |
| heritage.leshy.fruit | /Heritages.aspx?ID=264 | 67 | text only (healing fruit annotation) |
| heritage.leshy.fungus | /Heritages.aspx?ID=265 | 67 | sense darkvision (plant→fungus trait swap is annotation) |
| heritage.leshy.gourd | /Heritages.aspx?ID=266 | 67 | text only |
| heritage.leshy.leaf | /Heritages.aspx?ID=267 | 67 | text only |
| heritage.leshy.lotus | /Heritages.aspx?ID=268 | 67 | text only |
| heritage.leshy.root | /Heritages.aspx?ID=269 | 67 | ancestry_hp_override 10 (save-DC rider annotation) |
| heritage.leshy.seaweed | /Heritages.aspx?ID=270 | 67 | speed_bonus −5 (land Speed reduction; swim Speed 20 ft is annotation) |
| heritage.leshy.vine | /Heritages.aspx?ID=271 | 68 | text only |
| heritage.orc.badlands | /Heritages.aspx?ID=272 | 71 | text only |
| heritage.orc.battle-ready | /Heritages.aspx?ID=273 | 71 | grant_skills [skill.intimidation] (Intimidating Glare feat grant is annotation — no grant-feat effect exists) |
| heritage.orc.deep | /Heritages.aspx?ID=274 | 71 | text only (skill-feat grants annotation) |
| heritage.orc.grave | /Heritages.aspx?ID=275 | 71 | text only |
| heritage.orc.hold-scarred | /Heritages.aspx?ID=276 | 71 | ancestry_hp_override 12 (Diehard feat grant is annotation) |
| heritage.orc.rainfall | /Heritages.aspx?ID=277 | 71 | text only |
| heritage.orc.winter | /Heritages.aspx?ID=278 | 71 | grant_skills [skill.survival] |
| heritage.versatile.aiuvarin | /Heritages.aspx?ID=281 | 82 | ancestry null; feat_ancestries ["aiuvarin", "ancestry.elf"]; sense_upgrade darkvision/low-light vision |
| heritage.versatile.dromaar | /Heritages.aspx?ID=282 | 83 | ancestry null; feat_ancestries ["dromaar", "ancestry.orc"]; sense_upgrade darkvision/low-light vision |

Versatile-heritage vision RAW note: the PC Aiuvarin and Dromaar pages say
only "you gain … low-light vision"; the explicit "or darkvision if your
ancestry already has low-light vision" clause appears on the sibling PC
versatile heritages (Changeling /Heritages.aspx?ID=279 pg. 76, Nephilim
/Heritages.aspx?ID=280 pg. 78). Shipped both records with the sense_upgrade
effect (which degrades to plain low-light for ancestries without it) per the
task direction and the sibling-heritage precedent; the record text carries the
parenthetical so the sheet matches the effect.

### Heritage exclusions and count discrepancy

- **Jinxed Halfling** (/Heritages.aspx?ID=257) — EXCLUDED: rarity uncommon.
- **Changeling, Nephilim** — EXCLUDED per contract (uncommon versatile).
- **Count discrepancy vs data-scope**: the contract table says "halfling 6
  incl. NO jinxed"; strict PC1 has exactly 6 halfling heritages *including*
  Jinxed, so common-only = **5** (Gutsy, Hillock, Nomadic, Twilight,
  Wildwood — there is no PC "Observant Halfling"; that heritage is
  legacy-only). Shipped ancestry-bound heritage total is therefore 44, not
  45. All other counts match (gnome 5, leshy 9, orc 7).

## ancestry-feats.json (30 → 67)

All 37 new records verified: level 1, rarity common, source Player Core.
Rarity was checked per record — **no uncommon L1 feats exist in any of the
six catalogs**, so nothing was excluded. Prerequisites: none of these feats
has an attribute or trained-skill prerequisite RAW, so no evaluable prereq
kinds were needed; the only RAW prerequisite line is Orc Sight's.

| Record | AoN | Pg | Mechanics shipped |
|---|---|---|---|
| gnome.animal-accomplice | /Feats.aspx?ID=4422 | 52 | text only (familiar) |
| gnome.animal-elocutionist | /Feats.aspx?ID=4423 | 52 | text only |
| gnome.fey-fellowship | /Feats.aspx?ID=4424 | 52 | text only; SCRUBBED |
| gnome.fey-world-magic | /Feats.aspx?ID=4425 | 52 | choose_from_catalog primal_cantrips ×1 (greys); RENAMED + SCRUBBED |
| gnome.gnome-obsession | /Feats.aspx?ID=4426 | 52 | choose_lore "Gnome Obsession" (Assurance grant is annotation) |
| gnome.gnome-weapon-familiarity | /Feats.aspx?ID=4427 | 52 | text only |
| gnome.illusion-sense | /Feats.aspx?ID=4428 | 52 | text only |
| gnome.razzle-dazzle | /Feats.aspx?ID=4429 | 52 | text only (free action, 1/hour) |
| halfling.distracting-shadows | /Feats.aspx?ID=4455 | 60 | text only |
| halfling.folksy-patter | /Feats.aspx?ID=4456 | 60 | text only |
| halfling.halfling-lore | /Feats.aspx?ID=4457 | 60 | grant_skills [acrobatics, stealth] + grant_lore "Halfling Lore" |
| halfling.halfling-luck | /Feats.aspx?ID=4458 | 60 | text only (free action, 1/day) |
| halfling.halfling-weapon-familiarity | /Feats.aspx?ID=4459 | 60 | text only |
| halfling.prairie-rider | /Feats.aspx?ID=4460 | 60 | grant_skills [nature] |
| halfling.sure-feet | /Feats.aspx?ID=4461 | 60 | text only |
| halfling.titan-slinger | /Feats.aspx?ID=4462 | 60 | text only |
| halfling.unfettered-halfling | /Feats.aspx?ID=4463 | 60 | text only |
| halfling.watchful-halfling | /Feats.aspx?ID=4464 | 60 | text only |
| leshy.grasping-reach | /Feats.aspx?ID=4493 | 68 | text only |
| leshy.harmlessly-cute | /Feats.aspx?ID=4494 | 68 | text only (Shameless Request grant annotation) |
| leshy.leshy-lore | /Feats.aspx?ID=4495 | 68 | grant_skills [nature, stealth] + grant_lore "Leshy Lore" |
| leshy.leshy-superstition | /Feats.aspx?ID=4496 | 68 | text only (reaction) |
| leshy.seedpod | /Feats.aspx?ID=4497 | 68 | unarmed_attack Seedpod 1d4 B (unarmed), range "30 ft." — ranged unarmed |
| leshy.shadow-of-the-wilds | /Feats.aspx?ID=4498 | 68 | text only |
| leshy.undaunted | /Feats.aspx?ID=4499 | 68 | text only |
| orc.beast-trainer | /Feats.aspx?ID=4512 | 72 | grant_skills [nature] (Pet/Train Animal choice annotation) |
| orc.hold-mark | /Feats.aspx?ID=4517 | 72 | choose_skills count 1 from [diplomacy, survival, religion, intimidation] (per-emblem save rider stays annotation in text) |
| orc.iron-fists | /Feats.aspx?ID=4513 | 72 | unarmed_attack Fist 1d4 B (agile, finesse, shove, unarmed), replaces_fist — RAW drops nonlethal, adds shove |
| orc.orc-ferocity | /Feats.aspx?ID=4514 | 72 | text only (reaction, 1/day) |
| orc.orc-lore | /Feats.aspx?ID=4515 | 72 | grant_skills [athletics, survival] + grant_lore "Orc Lore" |
| orc.orc-superstition | /Feats.aspx?ID=4516 | 72 | text only (reaction) |
| orc.orc-weapon-familiarity | /Feats.aspx?ID=4518 | 72 | text only |
| orc.tusks | /Feats.aspx?ID=4519 | 72 | unarmed_attack Tusks 1d6 P (finesse, unarmed) — see Tusks call below |
| aiuvarin.earned-glory | /Feats.aspx?ID=4567 | 82 | grant_skills [performance] (Impressive Performance grant annotation) |
| aiuvarin.elf-atavism | /Feats.aspx?ID=4568 | 82 | text only |
| dromaar.monstrous-peacemaker | /Feats.aspx?ID=4571 | 83 | text only |
| dromaar.orc-sight | /Feats.aspx?ID=4572 | 83 | sense darkvision; prereq {kind: "special", text: "low-light vision"} (annotation-only kind — shown, never evaluated, so it cannot wrongly grey) |

### The Tusks call

The contract anticipated Tusks as dual-traited aiuvarin+dromaar. On AoN the
PC record (/Feats.aspx?ID=4519, Player Core pg. 72) is traited **Orc only**
— the remaster moved it into the core orc feat list (the legacy APG version
was the half-orc feat). Shipped as one record with
`ancestry: "ancestry.orc"`. Dromaar characters still reach it because the
Dromaar heritage's feat_ancestries opens the `ancestry.orc` catalog;
Aiuvarin correctly does NOT get it (matching AoN RAW, so there is no access
gap to note beyond this). Aiuvarin 2 + Dromaar 2 = 4 versatile feats, not
the contract's ~5 — the difference is exactly Tusks not being
versatile-traited in PC1.

## Scrubs applied (denylist: "First World")

`"scrubbed": true` is set on every scrubbed record — verified safe: the
record structs in `crates/ruleset-pf2e/src/data.rs` do not use
`serde(deny_unknown_fields)`, so unknown fields are ignored (parse gate
passes with the flag present).

| Record | Before (AoN RAW) | After (shipped) |
|---|---|---|
| heritage.gnome.chameleon | "possibly due to latent magic from First World influences or lingering illusion effects" | "possibly due to latent fey magic or lingering illusion effects" |
| heritage.gnome.fey-touched | "meditating to realign yourself with the First World" | "meditating to realign yourself with the fey realm" |
| feat gnome.fey-fellowship | "a warmer reception from creatures of the First World" | "a warmer reception from creatures of the fey realm" |
| feat gnome.fey-world-magic | name "First World Magic"; "Your connection to the First World grants you a primal innate spell" | name "Fey World Magic" (id feat.ancestry.gnome.fey-world-magic); "Your connection to the fey realm grants you a primal innate spell"; original AoN url kept (/Feats.aspx?ID=4425) |

Wellspring Gnome needed no scrub (its RAW text has no reserved nouns).
Denylist lint (`no_reserved_proper_nouns_in_records`) passes; no denylist
exceptions were needed (denylist.json untouched).

## Gate results

Run 2026-08-29. The shared working tree contains T4's in-flight background /
general-feats migration (data.rs now requires background skill_feat IDs to
resolve in general_feats; `background.field-medic` → "Battle Medicine"
doesn't resolve yet), which fails every data-loading check regardless of T3.
To isolate T3, the full suite was also run in a scratch worktree at HEAD
(fa9198a) + only the three T3 JSON files:

| Gate | Isolated (HEAD + T3 only) | Shared tree |
|---|---|---|
| cargo test -p checks --test rules_data | ok (5/5: parse+integrity, license, ORC notice, denylist, shipped-ID lineage) | FAILED — T4 in-flight (background.field-medic), not T3 |
| cargo test -p ruleset-pf2e | ok (28/28) | ok (28/28) |
| cargo test -p checks --test replay | **5/6 — golden_elyse_human_archer FAILED (see conflict below)**; torvald + krivvy goldens and both fixture-match tests byte-identical | FAILED (all, on the T4 load error) |
| cargo test -p checks (full) | all other binaries ok (api_authority, confirm_idempotency, crash_harness, crate_layering, no_rewrite_on_load, perf, persistence) except attestation — see below | — |
| cargo fmt --all -- --check | clean (T3 edits are JSON-only) | clean |

### STOP-reported conflict: golden_elyse_human_archer

Exactly the flagged scenario: Elyse's fixture has Int +1, so human's new
non-empty `additional_languages` opens the required
`pf2e.ancestry.languages` chooser (engine count = max(0, Int) +
bonus-language effects) with "1 additional language choice(s) left", and her
build is no longer complete → the golden fails its completeness assertion.
Torvald (dwarf) and Krivvy (goblin) fixtures have Int ≤ 0 and stay
byte-identical. Per T3 instructions the golden/fixture was NOT edited; the
fix belongs to whoever owns the goldens (either add a language pick to
Elyse's decision log + regen, or accept the derivation change deliberately).

### Attestation coverage

`cargo test -p checks --test attestation` fails with all 69 new T3 record
IDs "shipped but unattested" — the T6 attestation flow requires
`cargo run -p reference-check -- attest` to be re-run over the final data
files. rules-data/attestation.json and the reference-check tool are T6's;
not touched by T3. Mechanical follow-up once T3+T4+T5 data is final.
