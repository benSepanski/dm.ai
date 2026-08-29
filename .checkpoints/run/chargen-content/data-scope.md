# chargen-content data-entry scope (T3–T5 shared brief)

Ground truth: Archives of Nethys public Elasticsearch at
`https://elasticsearch.aonprd.com/aon/_search` (the chargen-fighter run used
index snapshot `aon-20260802-141253`; see
`.checkpoints/run/chargen-fighter/aon-reference.md` for query patterns and
per-record verification style). Filter every query to source == "Player
Core" (strict PC1; a naive query pulls Player Core 2 records — 17 of the
naive 70 L1 skill feats are PC2-only). Rarity: **common only** ships.

Verified counts (adversarially checked in the research pass; the implement
report records the finalized numbers):

| Catalog | Shipped (0.1.0) | Target | Delta |
|---|---|---|---|
| Ancestries | 4 | 8 (add gnome, halfling, leshy, orc) | +4 |
| Versatile heritages | 0 | 2 (aiuvarin, dromaar — common; NOT changeling/nephilim) | +2 |
| Ancestry-bound heritages | 18 (complete for their 4) | 45 (gnome 5, halfling 6 incl. NO jinxed [uncommon], leshy 9, orc 7) | +27 |
| L1 ancestry feats | 30 (complete for their 4 minus any uncommon) | 63 core (gnome 8, halfling 10, leshy 7, orc 8) + ~5 versatile (aiuvarin 2, dromaar 3 incl. dual-traited Tusks → 2 new records) | +~38 |
| Backgrounds | 5 | 39 (all PC1 common EXCEPT Raised by Belief — excluded by name) | +34 |
| L1 fighter class feats | 8 | 8 — ALREADY COMPLETE, no-op | 0 |
| L1 general feats (non-skill) | 5 | 14 | +9 |
| L1 skill feats | 0 | 53 (all carry General trait) | +53 |
| Weapons | 11 | ~65 common (43 martial + 18 simple + 4 ammunition rows; NO uncommon — 23 excluded) | +~54 |
| Armor | 7 | 13 | +6 |
| Shields | 2 | 4 (add buckler, tower shield) | +2 |
| Adventuring gear + assistive | 3 | ~140 common (130 adventuring-gear docs collapsed sensibly + 11 assistive; NO services) | +~137 |

Known license scrubs (denylist lint will catch violations —
`cargo test -p checks --test rules_data`):
- Gnome: heritages Chameleon, Fey-touched (text "First World") — paraphrase
  ("the fey realm"); feats Fey Fellowship (text), **First World Magic (name
  + text → rename, e.g. "Fey World Magic"**, keep AoN url pointing at the
  original; flag record `"scrubbed": true`).
- Street Urchin precedent: example city Lores genericized (already shipped).
- No deity names anywhere (Raised by Belief excluded entirely).

Greyed-with-reason records (ship the record; its chooser catalog is absent
this version, so the option greys per the Ancient Elf precedent): gnome
heritages Fey-touched + Wellspring (cantrip choice), the renamed First
World Magic successor (cantrip), Otherworldly Magic (already shipped
greyed). Unconventional Weaponry stays greyed (uncommon weapons excluded).

Schema conventions: follow existing rules-data/*.json shapes exactly; new
mechanics fields (versatile heritages, background sub-choices, prereq
kinds, language lists, new effects) follow the T2 conventions doc appended
below when it lands. Every record: stable dotted ID (existing convention),
full source block (book "Pathfinder Player Core", page, AoN url, license
"ORC", attribution "Pathfinder Player Core © 2023 Paizo Inc."). Effects
only where the engine interprets them (see T2 conventions); everything else
is annotation text — precedent: resistances/reactions ship as text.

## T2 schema conventions (landed; follow exactly)

- **Skill feats live in general-feats.json** with IDs `feat.skill.<slug>`
  (non-skill general feats keep `feat.general.<slug>`). The general-feat
  chooser catalog automatically includes them (RAW-correct).
- Versatile heritage: `"ancestry": null` (written explicitly); catalog keys:
  full ancestry IDs or the heritage's short key (last ID segment).
  `{ "id": "heritage.versatile.aiuvarin", "ancestry": null, "feat_ancestries": ["aiuvarin", "ancestry.elf"], "effects": [{ "type": "sense_upgrade", "sense": "darkvision", "otherwise": "low-light vision" }] }`
  Versatile-heritage feats: `"ancestry": "aiuvarin"` (short key), `level: 1`.
- Background sub-choices: `skill: ""` + `skill_choice: ["skill.arcana", ...]`
  (opens pf2e.background.skill); `lore: ""` + `lore_player_named: true`
  (opens pf2e.background.lore); `skill_feat_by_choice: {"skill.arcana": "..."}`
  keys ⊆ skill_choice. A background must have `skill` or `skill_choice`.
- Prerequisites: `{"kind": "attribute", "attribute": "con", "value": 2}`,
  `{"kind": "trained_skill", "skill": "skill.acrobatics"}`; `text` optional
  (reason auto-generated). Unknown kinds = annotation-only (shown, never
  evaluated) — use `{"kind": "special", "text": "..."}`-style for
  non-evaluable prose prereqs.
- Effects: `proficiency_override {target, rank}`, `unarmed_attack` with
  optional `range` and `replaces_fist`, `choose_skills {count, source_label,
  from?}`, `choose_lore {source_label}`, `bonus_languages {count}`,
  plus the slice-1 set (ancestry_hp_override, hp_per_level, speed_bonus,
  ignore_armor_speed_penalty, sense, grant_skills, grant_lore,
  choose_from_catalog). Annotation-only precedent for everything else
  (resistances, reactions, save riders, weapon familiarity).
- Languages: `additional_languages: ["Sylvan", ...]` on ancestries (must not
  repeat `languages`); names are the surface (IDs derived as
  `lang.<slug>`).
