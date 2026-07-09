# PHB 2024 (D&D 5.5e) Parity Specification

This document is the canonical feature matrix for `game-engine`'s D&D 5.5e
implementation. Target: **full mechanical parity with the 2024 Player's
Handbook**. Every PHB rule system must have a typed, tested engine module.

## Licensing boundary

PHB expressive text is copyrighted. All content data (descriptions, spell
text, feature text) is paraphrased and mechanically sourced from the
**SRD 5.2** (CC-BY-4.0), which carries the 2024 rules. Mechanics (tables,
formulas, numbers) are implemented in full. Where the PHB has content the
SRD omits (e.g. 3 of 4 subclasses per class), the engine ships the typed
*framework* plus the SRD member, and the data registry is extensible.

## Status legend

- ✅ implemented & tested
- 🟡 partial (framework done, data coverage tracked below)
- ⬜ not started

## Feature matrix

### Chapter 1 — Playing the Game

| Feature | Module | Status |
|---|---|---|
| d20 tests, advantage/disadvantage | `core.dice` | ✅ |
| Ability checks, skills, passive checks | `rules.dnd_5_5e._checks` | ✅ |
| Saving throws (proficiency, condition auto-fail, exhaustion) | `rules.dnd_5_5e._saves` | ✅ |
| Proficiency bonus by level | `rules.dnd_5_5e._checks` | ✅ |
| Typical DCs table | `rules.dnd_5_5e.exploration` | ✅ |
| Attack rolls, crits (nat 1/20), unseen attacker | `rules.dnd_5_5e._attacks` | ✅ |
| Cover (half / three-quarters / total) | `rules.dnd_5_5e._attacks` | ✅ |
| Damage, resistance/vulnerability/immunity | `rules.dnd_5_5e._damage` | ✅ |
| Temporary hit points | `rules.dnd_5_5e._damage` | ✅ |
| Healing | `rules.dnd_5_5e._damage` | ✅ |
| Dropping to 0 HP, instant death, death saves (incl. exhaustion on 10+ threshold; nat 1/20 unmodified) | `rules.dnd_5_5e._death` | ✅ |
| Conditions (all 15) + mechanical effects | `core.conditions` | ✅ |
| Exhaustion (2024: −2×level on d20 tests, −5 ft speed) | `core.conditions`, `_saves`, `_attacks`, `_death` | ✅ |
| Short/long rests, hit dice spending | `rules.dnd_5_5e.resting` | ✅ |

### Chapter 2 — Creating a Character

| Feature | Module | Status |
|---|---|---|
| Standard array / point buy / rolled scores | `rules.dnd_5_5e.character_builder` | ✅ |
| Background ability score increases (+2/+1 or +1/+1/+1) | `character_builder` | ✅ |
| Starting HP, AC, saves, proficiencies | `character_builder` | ✅ |
| Level advancement (XP table, milestones) | `rules.dnd_5_5e.progression` | ✅ |
| Hit points per level (fixed or rolled) | `progression` | ✅ |
| ASI / feat at class levels | `progression` | ✅ |
| Multiclassing (prereqs, proficiencies, spell slots) | `progression` | ✅ |
| Epic boons (level 19+) | `data.feats` | ✅ |

### Chapter 3 — Classes

| Feature | Module | Status |
|---|---|---|
| All 12 PHB classes + Artificer: hit die, saves, proficiencies | `rules.dnd_5_5e.classes` | ✅ |
| Per-level class feature tables (1–20) | `data.class_features` | ✅ all 13 classes |
| Class resources (rage, focus points, sorcery points, …) | `data.class_features` | ✅ |
| Sneak attack / martial arts / rage damage scaling tables | `data.class_features` | ✅ |
| Subclasses | `types.enums.Subclass` + `data.class_features` | 🟡 all 52 enumerated; SRD subclass features per class |
| Spell slot progression (full/half/third/pact) | `rules.dnd_5_5e.spellcasting` | ✅ |
| Prepared-spell & cantrip counts per class level | `data.class_features` | ✅ |

### Chapter 4 — Origins

| Feature | Module | Status |
|---|---|---|
| All 16 PHB backgrounds (abilities, skills, origin feat, equipment) | `data.backgrounds` | ✅ |
| Species: 9 SRD species with traits | `data.species` | ✅ |
| Languages (standard + rare) | `types.enums.Language` | ✅ |

### Chapter 5 — Feats

| Feature | Module | Status |
|---|---|---|
| Origin feats (10) | `data.feats` | ✅ |
| General feats (incl. ASI) | `data.feats` | ✅ |
| Fighting style feats (10) | `data.feats` | ✅ |
| Epic boon feats | `data.feats` | ✅ |
| Feat prerequisites & repeatability | `data.feats` | ✅ |

### Chapter 6 — Equipment

| Feature | Module | Status |
|---|---|---|
| Full 2024 weapon table (all simple/martial, melee/ranged) | `data.items` | ✅ |
| Weapon masteries (Cleave, Graze, Nick, Push, Sap, Slow, Topple, Vex) | `data.items` + `_attacks` | ✅ |
| Weapon properties (incl. range, ammunition) | `data.items` | ✅ |
| Full armor table + AC computation (dex caps, str minimums) | `data.items` + `character_builder` | ✅ |
| Adventuring gear, tools, packs | `data.gear` | ✅ |
| Coinage (cp/sp/ep/gp/pp) | `types.Currency` | ✅ |
| Carrying capacity / drag-lift-push | `rules.dnd_5_5e.exploration` | ✅ |

### Chapter 7 — Spells

| Feature | Module | Status |
|---|---|---|
| Spell slot consumption, upcasting | `rules.dnd_5_5e.spellcasting` | ✅ |
| Cantrip damage scaling (char levels 5/11/17) | `spellcasting` | ✅ |
| Concentration (single effect, CON save on damage) | `spellcasting` + `_damage` | ✅ |
| Ritual casting | `spellcasting` | ✅ |
| Spell attack rolls & save DCs | `spellcasting` | ✅ |
| Components (V/S/M), casting time, range, areas of effect | `data.spells` | ✅ |
| Spell data registry | `data.spells` | 🟡 ~100 SRD spells, levels 0–9 (registry extensible to full SRD list) |

### Chapters 1 & 8 — Combat & Adventuring (action economy, movement, environment)

| Feature | Module | Status |
|---|---|---|
| 2024 action list (Attack, Dash, Disengage, Dodge, Help, Hide, Influence, Magic, Ready, Search, Study, Utilize) + reaction events (Opportunity Attack, Readied Action) | `types.enums.ActionType` + `_actions` | ✅ |
| Action / bonus action / reaction economy per turn | `types.TurnState` + `_actions` + `spellcasting.check_casting_economy`/`commit_casting_economy` | 🟡 Extra Attack, validation-before-consumption, Nick's once-per-turn slot, the reaction slot (opportunity attacks + Ready), spell casting-time economy, and the one-slot-spell-per-turn rule are all wired (`engine-correctness-remediation.md` Workstreams B1/B2/B3 — SPL-03, SPL-06 done); TWF Light-property validation is not (ACT-04, blocked on Workstream C) |
| Initiative & turn order | `core.initiative` | ✅ |
| Opportunity attacks | `_reactions.resolve_opportunity_attack` | ✅ validates the attack, checks the mover didn't disengage, and consumes the reactor's reaction (one per round, refreshed at the start of the reactor's own next turn) — Workstream B2, ACT-02 |
| Ready action | `_reactions.resolve_readied_action` + `types.ReadiedAction` | 🟡 readying an attack (target + weapon + free-text trigger) is wired end-to-end, resolved later via `ActionType.READIED_ACTION` through the reaction slot; readying a spell or other action is out of scope (Workstream B2, ACT-06) |
| Spell casting-time economy (action/bonus action/reaction) + one-spell-slot-per-turn | `spellcasting.check_casting_economy`/`commit_casting_economy`, called from `_spell_resolution.cast_spell` | ✅ enforced inside `cast_spell` itself (not just the caller), so it applies uniformly wherever the engine is invoked; casting times outside the turn economy (10 minutes, 1 hour, ...) are exempt from both checks — they're downtime rituals no single turn can represent — and the dm-api `/combat/cast-spell` endpoint separately 409s those as inappropriate for an active-combat request (Workstream B3, SPL-03, SPL-06) |
| Two-weapon fighting (Light property, Nick) | `_attacks` | 🟡 Nick's once-per-turn free attack is wired (B1); off-hand attacks don't yet validate the Light property or require a prior Attack action this turn — genuinely blocked on the weapon-registry bridge (ACT-04, Workstream C), since `AttackDetails.properties` is never populated by the real dm-api pipeline yet |
| Unarmed strike (damage / grapple / shove) | `_attacks` | ✅ |
| Dodge / Disengage / Dash effects | `_actions` + `_attacks` + `_spell_resolution` | ✅ attack-disadvantage (melee + spell); DEX save advantage (grapple/shove + spell saves) |
| Mounted/underwater combat | — | ⬜ (needs positional model; out of theater-of-mind scope) |
| Jumping, falling, suffocation | `rules.dnd_5_5e.exploration` | ✅ |
| Travel pace, light & vision | `exploration` | ✅ |

## Engine architecture

```
game_engine/
  types/            # Layer 1: enums (package), value types, dataclasses
  core/             # Layer 2: rule-agnostic dice, initiative, conditions
  interface.py      # Layer 3: RuleEngine ABC + result dataclasses
  rules/dnd_5_5e/   # Layer 4: the 5.5e implementation
    engine.py         # facade implementing RuleEngine
    _checks.py        # ability/skill checks
    _saves.py         # saving throws
    _attacks.py       # attack resolution (adv/dis, cover, crits, masteries)
    _actions.py       # action economy + non-attack actions
    _damage.py        # damage/temp HP/healing
    _death.py         # death saves, dying
    _conditions.py    # condition application
    _validation.py    # sheet validation
    spellcasting.py   # slots, casting, concentration
    progression.py    # XP, level-up, multiclassing
    character_builder.py
    resting.py
    exploration.py    # encumbrance, environment, DCs
    classes.py        # static class data
    data/             # SRD 5.2 content registries
      items.py  gear.py  species.py  backgrounds.py  feats.py
      spells/  class_features/  monsters.py
```

All data modules expose `<NAME>S` registries keyed by enums and a
`get_<name>()` lookup. No `dict[str, Any]` crosses any boundary.

## Out of scope (PHB content that is DM-facing or positional)

- Grid/positioning rules (the engine is theater-of-mind; range and reach are
  modelled as flags on `AttackDetails`).
- Mounted & underwater combat modifiers (requires positional model).
- Crafting downtime economics (Chapter 6 sidebar) — gear data includes tool
  mappings; downtime resolution stays at the orchestration layer.
