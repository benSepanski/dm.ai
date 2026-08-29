# T4 AoN verification — backgrounds + general/skill feats

Verified 2026-08-29 against Archives of Nethys public Elasticsearch
(`https://elasticsearch.aonprd.com/aon/_search`, index snapshot
`aon-20260802-141253`), every query filtered `source.keyword == "Player
Core"` (strict PC1). Query shapes:

- Backgrounds: `{"bool":{"must":[{"term":{"category":"background"}},{"term":{"source.keyword":"Player Core"}}]}}`
  → exactly 40 hits, all rarity common. Excluding **Raised by Belief**
  (`background-438`, excluded by name per the data-scope brief: per-deity
  mechanics + deity example "Abadar Lore" in its text) leaves the 39 shipped.
- Feats: same bool query with `{"term":{"category":"feat"}},
  {"match":{"trait":"General"}},{"term":{"level":1}}` → exactly 67 hits:
  14 without the Skill trait (general feats), 53 with it (skill feats),
  all rarity common. (The naive unfiltered query returns 70 L1 skill
  feats; the 17 PC2-only ones are excluded by the strict source term.)

Fields checked per record: name, rarity, attribute boosts, trained
skill(s), Lore, granted skill feat (backgrounds); traits, level,
prerequisite line, mechanics text, source page, AoN ID (feats). Texts in
the shipped files are condensed paraphrases of the ORC-licensed
mechanics; "leads to" cross-references, PFS notes, and specialty tables
were dropped.

## Backgrounds (39 = 5 shipped + 34 added)

All follow the PC1 pattern: `boost_choice` of two attributes + one free
boost (free boost is engine-implicit), one trained skill, one Lore, one
skill feat. Boost order matches AoN's attribute order.

| Background | AoN ID | pg. | Boosts | Skill | Lore | Skill feat | Modeling |
|---|---|---|---|---|---|---|---|
| Acolyte | 406 | 84 | int/wis | Religion | Scribing Lore | Student of the Canon | fixed |
| Acrobat | 407 | 84 | str/dex | Acrobatics | Circus Lore | Steady Balance | fixed |
| Animal Whisperer | 408 | 84 | wis/cha | Nature | terrain of liked animals | Train Animal | lore_player_named |
| Artisan* | 409 | 84 | str/int | Crafting | Guild Lore | Specialty Crafting | fixed |
| Artist | 410 | 84 | dex/cha | Crafting | Art Lore | Specialty Crafting | fixed |
| Bandit | 411 | 84 | dex/cha | Intimidation | terrain worked in | Group Coercion | lore_player_named |
| Barkeep | 412 | 84 | con/cha | Diplomacy | Alcohol Lore | Hobnobber | fixed |
| Barrister | 413 | 85 | int/cha | Diplomacy | Legal Lore | Group Impression | fixed |
| Bounty Hunter | 414 | 85 | str/wis | Survival | Legal Lore | Experienced Tracker | fixed |
| Charlatan | 415 | 85 | int/cha | Deception | Underworld Lore | Charming Liar | fixed |
| Cook | 416 | 85 | con/int | Survival | Cooking Lore | Seasoned | fixed |
| Criminal | 417 | 85 | dex/int | Stealth | Underworld Lore | Experienced Smuggler | fixed |
| Cultist | 418 | 86 | int/cha | Occultism | deity or cult | Schooled in Secrets | lore_player_named |
| Detective | 419 | 86 | int/wis | Society | Underworld Lore | Streetwise | fixed |
| Emissary | 420 | 86 | int/cha | Society | a city visited often | Multilingual | lore_player_named |
| Entertainer | 421 | 86 | dex/cha | Performance | Theater Lore | Fascinating Performance | fixed |
| Farmhand | 422 | 86 | con/wis | Athletics | Farming Lore | Assurance (Athletics) | fixed + skill_feat_display |
| Field Medic* | 423 | 86 | con/wis | Medicine | Warfare Lore | Battle Medicine | fixed |
| Fortune Teller | 424 | 86 | int/cha | Occultism | Fortune-Telling Lore | Oddity Identification | fixed |
| Gambler | 425 | 86 | dex/cha | Deception | Games Lore | Lie to Me | fixed |
| Gladiator | 426 | 86 | str/cha | Performance | Gladiatorial Lore | Impressive Performance | fixed |
| Guard | 427 | 86 | str/cha | Intimidation | Legal Lore OR Warfare Lore | Quick Coercion | lore_player_named (divergence, see below) |
| Herbalist | 428 | 86 | con/wis | Nature | Herbalism Lore | Natural Medicine | fixed |
| Hermit | 429 | 87 | con/int | Nature OR Occultism | terrain lived in | Dubious Knowledge | skill_choice + lore_player_named |
| Hunter* | 430 | 87 | dex/wis | Survival | Tanning Lore | Survey Wildlife | fixed |
| Laborer | 431 | 87 | str/con | Athletics | Labor Lore | Hefty Hauler | fixed |
| Martial Disciple | 432 | 87 | str/dex | Acrobatics OR Athletics | Warfare Lore | Cat Fall / Quick Jump | skill_choice + skill_feat_by_choice |
| Merchant | 433 | 87 | int/cha | Diplomacy | Mercantile Lore | Bargain Hunter | fixed |
| Miner | 434 | 87 | str/wis | Survival | Mining Lore | Terrain Expertise (underground) | fixed + skill_feat_display |
| Noble | 435 | 87 | int/cha | Society | Genealogy Lore OR Heraldry Lore | Courtly Graces | lore_player_named (divergence, see below) |
| Nomad | 436 | 88 | con/wis | Survival | terrain traveled in | Assurance (Survival) | lore_player_named + skill_feat_display |
| Prisoner | 437 | 88 | str/con | Stealth | Underworld Lore | Experienced Smuggler | fixed |
| Sailor | 439 | 88 | str/dex | Athletics | Sailing Lore | Underwater Marauder | fixed |
| Scholar | 440 | 88 | int/wis | Arcana/Nature/Occultism/Religion | Academia Lore | Assurance (chosen skill) | skill_choice + skill_feat_by_choice + display map |
| Scout | 441 | 88 | dex/wis | Survival | terrain scouted in | Forager | lore_player_named |
| Street Urchin* | 442 | 88 | dex/con | Thievery | home-city Lore | Pickpocket | fixed "City Lore" (divergence, see below) |
| Teacher | 443 | 88 | int/wis | Performance OR Society | Academia Lore | Experienced Professional | skill_choice (fixed feat) |
| Tinker | 444 | 88 | dex/int | Crafting | Engineering Lore | Specialty Crafting | fixed |
| Warrior* | 445 | 88 | str/con | Intimidation | Warfare Lore | Intimidating Glare | fixed |

\* previously shipped in 0.1.0; only `skill_feat` changed (display string
→ feat ID). Excluded: **Raised by Belief** (438).

### Ticket-vs-AoN corrections (verified on AoN)

- The ticket predicted Guard, Noble, and Teacher-style **skill** choices
  for Guard and Noble. AoN says otherwise: Guard trains fixed
  Intimidation with a **Lore choice** (Legal or Warfare), Noble trains
  fixed Society with a **Lore choice** (Genealogy or Heraldry). The
  skill-choice backgrounds are exactly Hermit, Martial Disciple,
  Scholar, Teacher.
- Farmhand and Miner have **fixed** Lores on AoN (Farming Lore, Mining
  Lore) — not player-named.
- Scholar's option list is four skills (Arcana, Nature, Occultism,
  Religion), not three.

## Modeling calls (waiver candidates in bold)

1. **Guard + Noble lore choice → `lore_player_named`.** The schema has
   fixed `lore` or free-text `lore_player_named` and no two-option Lore
   chooser; inventing one is outside this ticket's bounded code change.
   Shipped as player-named with the RAW restriction stated in the record
   text ("Your Lore is Legal Lore or Warfare Lore." / "…Genealogy Lore
   or Heraldry Lore."). Divergence: the engine accepts any typed Lore.
   **Waiver candidate: RAW restricts to two named Lores; a `lore_choice`
   field would make it exact.**
2. **Street Urchin fixed "City Lore" kept.** RAW is a Lore for the city
   you lived in (player-named). The record shipped in 0.1.0 with fixed
   "City Lore"; converting to `lore_player_named` would change a shipped
   record's mechanics mid-lineage, so it stays. **Waiver candidate:
   convert to `lore_player_named` at the next data-version bump.**
3. **Canny Acumen ships annotation-only (no effect).** The engine has
   `proficiency_override {target, rank}` but no chooser for which target
   (the only choosers are ChooseSkills/ChooseLore/ChooseFromCatalog, and
   feats.rs opens catalog choosers only for whole-record catalogs).
   Splitting into four records would pollute the catalog. One record,
   text describes the choice, no mechanical effect. **Known sheet gap:
   picking Canny Acumen changes no save/Perception number; orchestrator
   to decide (options: a target-chooser slot kind, or four records).**
4. **Assurance ships as ONE record, annotation-only** (RAW: one feat,
   choose a trained skill; selectable multiple times). Same
   choice-in-feat gap as Canny Acumen. Background grants that name a
   skill ("Assurance (Survival)") ship as `skill_feat_display` /
   `skill_feat_display_by_choice` display strings over the single
   `feat.skill.assurance` ID, so the sheet stays RAW-exact for
   backgrounds. Prerequisite "trained in at least one skill" is a
   `special` annotation (every build qualifies in practice).
5. **Skill Training ships annotation-only.** It RAW-grants a chosen
   trained skill; the ChooseSkills chooser only opens from heritage or
   ancestry-feat records (skills.rs `choose_skills_grant`), so a
   ChooseSkills effect on a general feat would be dead data. Prereq
   Int +1 is evaluable and shipped. **Known sheet gap** (same family as
   Canny Acumen/Assurance).
6. **Additional Lore carries `choose_lore`** — the SLOT_FEAT_LORE slot
   reads ChooseLore from folded effects regardless of source, so this
   one works end-to-end (named Lore lands trained; dies with the feat).
7. **Multilingual carries `bonus_languages {count: 2}`** (RAW verified:
   "You learn two new languages"). Divergence note: the engine's
   language chooser restricts picks to the ancestry's
   additional-languages list, while RAW allows any common language —
   pre-existing chooser behavior, same as the Nomadic Halfling pattern.
8. **Or-list prerequisites** (Quick Identification, Recognize Spell,
   Trick Magic Item: "trained in Arcana, Nature, Occultism, or
   Religion"; Seasoned: Alcohol/Cooking Lore or Crafting; Dubious
   Knowledge: "a skill with the Recall Knowledge action"; Experienced
   Professional: "a Lore skill") ship as `{"kind":"special","text":…}` —
   shown, never evaluated, per the T2 convention. Single-skill prereqs
   ship evaluable (`trained_skill`); Fast Recovery Con +2 and Feather
   Step Dex +2 ship evaluable (`attribute`) — both prerequisite lines
   confirmed on AoN remaster records (5148, 5149).

## General feats (14 non-skill; IDs feat.general.*)

| Feat | AoN ID | pg. | Prereq | Effects |
|---|---|---|---|---|
| Adopted Ancestry | 5115 | 252 | — | annotation-only (ancestry choice not modeled) |
| Armor Proficiency | 5120 | 252 | — | annotation-only |
| Breath Control | 5129 | 253 | — | annotation-only |
| Canny Acumen | 5130 | 253 | — | annotation-only (call #3) |
| Diehard* | 5140 | 254 | — | annotation-only |
| Fast Recovery | 5148 | 255 | attribute con 2 | annotation-only |
| Feather Step | 5149 | 256 | attribute dex 2 | annotation-only |
| Fleet* | 5150 | 256 | — | speed_bonus 5 |
| Incredible Initiative* | 5160 | 256 | — | annotation-only |
| Pet | 5186 | 259 | — | annotation-only (condensed text; pet abilities elided) |
| Ride* | 5206 | 261 | — | annotation-only |
| Shield Block | 5212 | 262 | — | annotation-only (fighter also gets it free as a class feature) |
| Toughness* | 5227 | 263 | — | hp_per_level 1 |
| Weapon Proficiency | 5239 | 265 | — | annotation-only (remaster text: martial → one advanced) |

\* previously shipped, unchanged.

## Skill feats (53; IDs feat.skill.*, all General+Skill L1 PC1)

All 53 records: AoN IDs 5114 (Additional Lore), 5117, 5119, 5121
(Assurance), 5123, 5125 (Battle Medicine), 5131, 5132, 5134, 5138, 5142,
5144, 5145, 5146, 5147, 5152, 5154, 5155, 5156, 5157, 5159, 5162, 5176,
5177, 5181 (Multilingual), 5182, 5184, 5185, 5187, 5193, 5195, 5196,
5198, 5199, 5204, 5205, 5209, 5210, 5213, 5214 (Skill Training), 5216,
5217, 5218, 5219, 5220, 5221, 5223, 5224, 5226, 5228, 5229, 5230, 5235
— pages 252–264, names/prereqs/mechanics per the AoN dump. Effects only
where interpreted: Multilingual (bonus_languages 2), Additional Lore
(choose_lore); everything else annotation-only. Every background
skill-feat reference resolves to one of these (integrity-enforced in
data.rs `check_integrity`).

## Scrubs

- No new reserved nouns entered: example-Lore clauses with Golarion
  proper nouns were dropped (Street Urchin precedent — AoN's "such as
  Absalom Lore or Magnimar Lore", Raised by Belief's "Abadar Lore" is
  excluded with its record). Generic AoN examples (Plains/Swamp/Desert
  Lore) were also dropped in favor of paraphrase.
- Virtuosic Performer's specialty table (contains setting dance names
  "huara", "macru") was paraphrased with generic examples.
- Denylist scan of backgrounds.json + general-feats.json: clean.
- Added a denylist **exception** for `gear.wheelchair-chair-storage`
  (T5's equipment record): the substring "torag" inside "storage" is a
  false positive, not a deity reference. Without it the shared
  rules-data lint fails on the case-insensitive substring scan.

## Cross-ticket notes

- `crates/reference-check/src/compare.rs` (T6's crate, untouched)
  lowercases `our["skill_feat"]` and membership-tests it against AoN's
  granted-feat names; now that `skill_feat` holds feat IDs, that
  comparison needs updating (compare the resolved feat name, or the
  `skill_feat_display`). Flagged for T6/orchestrator.
- `checks --test replay` `golden_elyse_human_archer` fails transiently:
  T3's ancestries.json now gives humans `additional_languages`, so
  Elyse's Int boost opens the language chooser her golden log never
  answers. Verified pre-existing by stashing all T4 files and re-running
  (identical failure). T4's files do not touch that slot.
