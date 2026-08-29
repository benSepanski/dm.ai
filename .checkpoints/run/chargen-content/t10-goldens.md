# T10 golden-build record — hand-verified sheets per ancestry

Seven new goldens in `checks/replay.rs` (the slice-1 three — Torvald,
Elyse, Krivvy — are untouched): one level-1 build per remaining ancestry
(Elf, Gnome, Halfling, Leshy, Orc), one versatile-heritage build
(Dwarf + Aiuvarin), and the quick-build character (the shipped fighter
`suggested_build` expanded through `Engine::expand_suggestions` on an
empty log). Every number below was derived by hand from the record values
in `rules-data/*.json` and the PF2e level-1 rules before the test ran; the
tests assert these literals, and `regen_fixtures` snapshots the full
sheets into `checks/fixtures/{name}.{log,sheet}.json` (all ten fixtures
now also run through `fixture_logs_match_golden_builders` and
`fixture_sheets_match_replay`).

Shared level-1 arithmetic (Player Core): HP = ancestry HP (after any
heritage override) + class 10 + Con. AC = 10 + Dex (capped by armor) +
armor item bonus + armor proficiency (trained = level+2 = 3). Saves/
Perception = proficiency (fighter: Fort/Ref/Perception expert = 5, Will
trained = 3) + attribute. Class DC = 10 + trained 3 + key attribute.
Attacks = proficiency (martial/simple expert = 5) + Str (Dex if ranged,
or finesse with Dex > Str); Str to damage on melee and thrown, full Str
(even negative) on propulsive when Str ≤ 0, half when positive. Skills =
trained 3 (or untrained 0) + attribute − armor check penalty on Str/Dex
skills when Str < the armor's requirement. Meeting the armor Str
requirement also reduces the speed penalty by 5. Starting wealth 15 gp.

## Caelith — Elf (Whisper Elf), Scholar, Fighter

Exercises: background **skill sub-choice** (Scholar → Occultism, and the
skill feat follows the choice: Assurance (Occultism)); Nimble Elf's
`speed_bonus` +5; Int-driven trained-skill count (3+2 = 5) and the
**language chooser at Int +2**; greatsword kit option.

- Choices: Whisper Elf; Nimble Elf; ancestry free boost Str; Scholar
  (sub-choice Occultism, boost choice Int, free Str); key attr Str;
  Vicious Swing; class skill Athletics; trained Survival, Arcana,
  Crafting, Medicine, Religion; free boosts Str/Dex/Con/Wis; languages
  Draconic, Fey; kit.fighter.greatsword.
- Attributes: Str +4 (anc-free, bg-free, key, free), Dex +2 (fixed,
  free), Con 0 (flaw + free), Int +2 (fixed, bg-choice), Wis +1, Cha 0.
- HP 16 = 6 + 10 + 0. AC 18 = 10 + 2 (Dex capped 2) + 3 scale mail + 3.
  Fort +5 = 5+0; Ref +7 = 5+2; Will +4 = 3+1; Perception +6; Class DC 17.
- Greatsword +9 = 5+4, 1d12 S+4. Speed 35 = 30 + 5 Nimble (scale-mail
  −5 waived at Str +4). Occultism +5 = 3+2 (from Background: Scholar).
- Coins 7 gp 2 sp = 15 gp − 5 gp 8 sp kit − 2 gp option. Bulk 5 Bulk 2 L
  = scale 2 + greatsword 2 + pack 1 + dagger L + hook L.
- Languages: Common, Elven, Draconic, Fey. Lore: Academia.

## Fizzwick — Gnome (Sensate), Barkeep, Fighter

Exercises: **Gnome Obsession's player-named Lore** (the
`pf2e.skills.feat-lore` text slot → "Clockwork Lore"); Sensate's scent
sense in the summary; **unmet armor Str requirement** (Str −1 < studded
leather's +1 → −1 check penalty); negative Str on finesse damage; no-kit
itemized shopping.

- Choices: Sensate; Gnome Obsession (Lore "Clockwork"); ancestry free
  Dex; Barkeep (choice Con, free Dex); key attr Dex; Combat Assessment;
  class skill Acrobatics; trained Stealth, Thievery, Deception; free
  Dex/Con/Wis/Cha; no kit; studded leather, rapier, dagger, pack, mug.
- Attributes: Str −1 (flaw), Dex +4, Con +3, Int 0, Wis +1, Cha +2.
- HP 21 = 8 + 10 + 3. AC 18 = 10 + 3 (Dex capped 3) + 2 studded + 3.
  Fort +8; Ref +9; Will +4; Perception +6; Class DC 17.
- Rapier +9 = 5 + 4 Dex (finesse), 1d6 P−1 (Str −1 to damage).
  Acrobatics +6 = 3 + 4 − 1 ACP; untrained Athletics −2 = 0 − 1 − 1.
- Coins 8 gp 2 sp 9 cp = 15 gp − (3 gp + 2 gp + 2 sp + 1 gp 5 sp +
  1 cp) = 15 gp − 6 gp 7 sp 1 cp. Bulk 3 Bulk 1 L = studded 1 + rapier 1
  + pack 1 + dagger L + mug —.
- Languages: Common, Fey, Gnomish. Lores: Clockwork (Gnome Obsession),
  Alcohol (Barkeep).

## Wenna — Halfling (Nomadic), Nomad, Fighter

Exercises: **Nomadic Halfling's two bonus languages at Int +0** (the
chooser opens on the `bonus_languages` effect alone); the **player-named
background Lore** (`pf2e.background.lore` text → "Steppe Lore");
propulsive with negative Str (full −1 to sling damage); leather's Str +0
requirement missed at Str −1 (−1 ACP).

- Choices: Nomadic; Titan Slinger; ancestry free Con; Nomad (Lore
  "Steppe", choice Wis, free Dex); key attr Dex; Snagging Strike; class
  skill Acrobatics; trained Stealth, Nature, Medicine; free
  Dex/Con/Wis/Cha; languages Dwarven, Goblin; no kit; leather, sling,
  bullets, dagger, pack, bedroll.
- Attributes: Str −1 (flaw), Dex +4, Con +2, Int 0, Wis +3, Cha +1.
- HP 18 = 6 + 10 + 2. AC 18 = 10 + 4 (Dex, cap 4) + 1 leather + 3.
  Fort +7; Ref +9; Will +6; Perception +8.
- Sling +9 = 5 + 4 Dex, 1d6 B−1 (propulsive, full negative Str).
  Survival +6 = 3 + 3 (from Background: Nomad). Athletics −2.
- Coins 11 gp 2 sp 7 cp = 15 gp − (2 gp + 0 + 1 cp + 2 sp + 1 gp 5 sp +
  2 cp) = 15 gp − 3 gp 7 sp 3 cp. Bulk 2 Bulk 4 L = leather 1 + pack 1 +
  sling L + bullets L + dagger L + bedroll L.
- Languages: Common, Halfling, Dwarven, Goblin. Lore: Steppe.

## Bramble — Leshy (Root Leshy), Field Medic, Fighter

Exercises: **Root Leshy's `ancestry_hp_override`** (10 instead of 8);
**Seedpod's ranged unarmed attack** (Dex to hit, no attribute to
damage); Int −1 shrinking the fighter's additional skills to 2 (3 + Int,
floor 0); the plain class kit (no option) plus purchased extras.

- Choices: Root; Seedpod; ancestry free Str; Field Medic (choice Con,
  free Str); key attr Str; Double Slice; class skill Athletics; trained
  Nature, Stealth (count 2); free Str/Dex/Con/Wis; kit.fighter base;
  hatchet + light hammer.
- Attributes: Str +4, Dex +1, Con +3, Int −1 (flaw), Wis +2, Cha 0.
- HP 23 = **10 override** + 10 + 3. AC 17 = 10 + 1 (Dex, cap 2) + 3
  scale + 3. Fort +8; Ref +6; Will +5; Perception +7.
- Seedpod +6 = 5 + 1 Dex, 1d4 B flat (ranged unarmed). Hatchet and
  light hammer +9 = 5 + 4, 1d6+4. Trained-skill count 2 = 3 + (−1).
- Coins 8 gp 5 sp = 15 gp − 5 gp 8 sp kit − 4 sp − 3 sp. Bulk 3 Bulk
  4 L = scale 2 + pack 1 + dagger L + hook L + hatchet L + hammer L.
- Languages: Common, Fey (Int −1: chooser hidden). Lore: Warfare.

## Grashk — Orc (Hold-Scarred), Miner, Fighter

Exercises: **Hold-Scarred's `ancestry_hp_override` 12**; **Iron Fists'
`replaces_fist` unarmed attack** (the default fist entry is gone, the
effect entry renders on Str despite finesse); orc's two free ancestry
boosts (no fixed); hide armor with the Str requirement met (−2 ACP and
−5 speed both waived); shield in the basket.

- Choices: Hold-Scarred; Iron Fists; ancestry free Str+Con; Miner
  (choice Str, free Con); key attr Str; Reactive Shield; class skill
  Athletics; trained Intimidation, Nature, Religion; free
  Str/Dex/Con/Wis; no kit; hide, warhammer, steel shield, javelin, pack,
  torch.
- Attributes: Str +4, Dex +1, Con +3, Int 0, Wis +1, Cha 0.
- HP 25 = **12 override** + 10 + 3. AC 17 = 10 + 1 (Dex, cap 2) + 3
  hide + 3. Fort +8; Ref +6; Will +4; Perception +6; Class DC 17.
- Fist +9 = 5 + 4 Str (finesse but Dex +1 < Str), 1d4 B (+4).
  Warhammer +9, 1d8 B+4. Javelin (thrown) +9 on Str, 1d6 P+4. Speed 25
  (hide −5 waived at Str +4); no ACP on Athletics +7.
- Coins 8 gp 3 sp 9 cp = 15 gp − (2 gp + 1 gp + 2 gp + 1 sp + 1 gp 5 sp
  + 1 cp) = 15 gp − 6 gp 6 sp 1 cp. Bulk 5 Bulk 2 L = hide 2 +
  warhammer 1 + shield 1 + pack 1 + javelin L + torch L.
- Languages: Common, Orcish. Lore: Mining.

## Maera — Dwarf + Aiuvarin (versatile heritage), Bounty Hunter, Fighter

Exercises: a **versatile heritage under a bound ancestry** and the
**feat-catalog union** — `feat.ancestry.aiuvarin.earned-glory` is keyed
to "aiuvarin", legal only because the heritage's `feat_ancestries`
carries it; the union feat's skill grant (Performance); heritage sense
stacking (dwarven darkvision + Aiuvarin low-light vision); kit option +
extras together.

- Choices: Aiuvarin; Earned Glory; ancestry free Str; Bounty Hunter
  (choice Str, free Con); key attr Str; Sudden Charge; class skill
  Athletics; trained Medicine, Society, Intimidation; free
  Str/Dex/Con/Wis; kit.fighter.sword-and-board; javelin + rope.
- Attributes: Str +4, Dex +1, Con +3 (fixed + bg-free + free), Int 0,
  Wis +2, Cha −1 (flaw).
- HP 23 = 10 dwarf (no override) + 10 + 3. AC 17 = 10 + 1 + 3 + 3.
  Fort +8; Ref +6; Will +5; Perception +7.
- Longsword +9, 1d8 S+4. Performance +2 = 3 + (−1 Cha), trained by the
  union feat. Speed 20 (dwarf; scale −5 waived).
- Coins 5 gp 6 sp = 15 gp − 5 gp 8 sp − 3 gp − 1 sp − 5 sp. Bulk 5 Bulk
  4 L = scale 2 + longsword 1 + shield 1 + pack 1 + dagger L + hook L +
  javelin L + rope L.
- Languages: Common, Dwarven. Lore: Legal.

## Garrek Ironvale — the quick-build character

`golden_garrek_quick_build` expands the shipped
`classes.json → suggested_build` block through
`Engine::expand_suggestions` on an empty log (same drive as
`checks/quick_build.rs`), asserts zero unresolved slots, all-Suggested
provenance, `can_finalize`, and the sheet literals below — so **any edit
to the dm.ai-authored block shows up as a golden and fixture diff**
(`garrek.log.json` pins the exact 16-decision expansion).

- Planner resolution (first legal candidate per slot): Human, Skilled
  Human (heritage choice → Diplomacy), Cooperative Nature, ancestry free
  Str+Con, Warrior (choice Str, free Wis), Fighter key Str, Sudden
  Charge, class skill Athletics, trained Acrobatics/Medicine/Survival,
  free Str/Dex/Con/Wis, sword-and-board kit, name "Garrek Ironvale".
  The language candidates never fire (Int +0 keeps the chooser hidden);
  `pf2e.equipment.extra` is optional and the planner fills required
  slots only.
- Attributes: Str +4, Dex +1, Con +2, Int 0, Wis +2, Cha 0.
- HP 20 = 8 + 10 + 2. AC 17 = 10 + 1 (Dex, cap 2) + 3 + 3. Fort +7;
  Ref +6; Will +5; Perception +7; Class DC 17.
- Longsword +9, 1d8 S+4. Athletics +7; Diplomacy +3 (Skilled Human);
  Intimidation +3 (Warrior); Medicine/Survival +5.
- Coins 6 gp 2 sp = 15 gp − 5 gp 8 sp − 3 gp. Bulk 5 Bulk 2 L.
  Languages: Common. Lore: Warfare.

## AoN double-checks

Verified against the Archives of Nethys public Elasticsearch
(`https://elasticsearch.aonprd.com/aon/_search`) on 2026-08-29,
`match_phrase` on name + source "Player Core", record text read from the
Player Core hit:

| Record | AoN result | Outcome |
|---|---|---|
| heritage.leshy.root | Heritage, PC pg. 67: "You gain 10 Hit Points from your ancestry instead of 8" | matches `ancestry_hp_override: 10` |
| heritage.orc.hold-scarred | Heritage, PC pg. 71: "You gain 12 Hit Points from your ancestry instead of 10. You also gain the Diehard feat." | matches override 12; the Diehard grant is text-only in the record (same modeling as every named-feat grant in heritages this slice — surfaced on the sheet as heritage text, not folded) |
| heritage.halfling.nomadic | Heritage, PC pg. 59: "two additional languages of your choice" | matches `bonus_languages: 2` |
| feat.ancestry.orc.iron-fists | Feat 1, PC pg. 72: fists lose nonlethal, gain shove | matches the record's fist 1d4 B agile/finesse/shove/unarmed, `replaces_fist` |
| feat.ancestry.leshy.seedpod | Feat 1, PC pg. 68: ranged unarmed, range increment 30 feet, 1d4 B | matches |
| feat.ancestry.elf.nimble-elf | Feat 1, PC pg. 48: Speed +5 feet | matches `speed_bonus: 5` |
| feat.ancestry.gnome.gnome-obsession | Feat 1, PC pg. 52: "gain the Additional Lore feat and the Assurance feat for the chosen Lore" | trained named Lore matches Additional Lore at level 1; the Assurance rider is text-only, consistent with the slice's named-feat modeling |
| background.scholar | Background, PC pg. 88: Int/Wis boost; choice of Arcana/Nature/Occultism/Religion; Academia Lore; Assurance in the chosen skill | matches, incl. `skill_feat_display_by_choice` |
| background.nomad | Background, PC pg. 88: Con/Wis; Survival; a terrain Lore you name; Assurance (Survival) | matches, incl. `lore_player_named` |
| background.miner | Background, PC pg. 87: Str/Wis; Survival; Mining Lore; Terrain Expertise | matches |
| background.bounty-hunter | Background, PC pg. 85: Str/Wis; Survival; Legal Lore; Experienced Tracker | matches |
| background.barkeep | Background, PC pg. 84: Con/Cha; Diplomacy; Alcohol Lore; Hobnobber | matches |
| background.field-medic | Background, PC pg. 86: Con/Wis; Medicine; Warfare Lore; Battle Medicine | matches |
| heritage.versatile.aiuvarin | Heritage, PC pg. 82 (AoN shows first-printing text: plain low-light vision) | see finding below |

## Findings (reported, not fixed here — task chips filed)

1. **Aiuvarin/Dromaar sense encoding.** Both versatile-heritage records
   ship `{"type":"sense","value":"low-light vision"}` while their own
   record text carries the errata wording "(or darkvision, if your
   ancestry already has low-light vision)", and the engine + its unit
   tests already model exactly this via `sense_upgrade`. Consequence: an
   Elf/Gnome/Leshy base misses the darkvision upgrade. The Maera golden
   uses a Dwarf base, where both encodings produce the same sheet
   (darkvision from the ancestry, low-light vision granted), so the
   golden's values are correct either way.
2. **Heritage `grant_skills` never folds.** The heritage apply only
   collects effects; nothing converts a heritage's `GrantSkills` into
   `skill_grants` (ancestry feats and backgrounds do). Verified
   empirically: Battle-Ready Orc leaves Intimidation untrained ("0
   untrained + 0 Cha"). Battle-Ready and Winter Orc are therefore
   deliberately absent from the goldens (Grashk uses Hold-Scarred).

## Gates

- `cargo test -p checks --test replay` — green (13 passed, regen
  ignored), including the property tests.
- `cargo test -p checks --test perf` — green (fold budget holds).
- `cargo fmt -p checks --check` — clean.
- `cargo clippy -p checks --all-targets` — no code warnings (the only
  output is the pre-existing clippy.toml `tokio::*` disallowed-path
  notes, unrelated to checks code).
- Fixtures regenerated via `regen_fixtures`; all ten logs and sheets
  replay byte-identical (`fixture_logs_match_golden_builders`,
  `fixture_sheets_match_replay`). Nothing committed.
