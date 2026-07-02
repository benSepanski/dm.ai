# Game Engine Correctness Audit — Findings

**Date:** 2026-07-02
**Scope:** `game-engine/` — action mechanics, spells, equipment, effect resolution, audited against the D&D 2024 rules (SRD 5.2) and `docs/phb-parity-spec.md`.
**Method:** Multi-agent audit — 12 independent reviewers (4 dimensions x 3 lenses: rules accuracy, code/logic bugs, completeness holes), semantic dedup (143 raw -> 72 unique), then adversarial verification of every finding against three criteria (2024-rule accuracy, traced code behavior, materiality/out-of-scope). 71 findings survived; 1 was refuted (see appendix).

**Totals:** 71 confirmed findings — 7 critical, 37 major, 27 minor.

The remediation plan for these findings, organized into phases and workstreams, is in [engine-correctness-remediation.md](engine-correctness-remediation.md).

## Severity definitions

- **critical** — produces wrong results in ordinary play, or a core claimed feature silently does nothing.
- **major** — wrong in common situations, a rule implemented meaningfully wrong, or a rule-interaction gap yielding wrong outcomes.
- **minor** — edge case, or unused/dead data with no gameplay impact yet.

## Index

### Action Mechanics

| ID | Sev | Finding | Location |
|----|-----|---------|----------|
| ACT-01 | CRITICAL | Extra Attack is impossible: action economy allows exactly one attack per Attack action | `src/game_engine/rules/dnd_5_5e/_actions.py:134` |
| ACT-02 | CRITICAL | Reaction economy and opportunity attacks are unimplemented despite spec claiming both | `src/game_engine/rules/dnd_5_5e/_actions.py:196` |
| ACT-03 | CRITICAL | begin_turn/reset_turn wipes cross-turn effects: Help, Sap, Vex, and Hide are no-ops in normal play | `src/game_engine/types/sheets.py:276` |
| ACT-04 | Major | Two-weapon fighting never validates the Light property or a prior Attack action — any weapon works off-hand | `src/game_engine/rules/dnd_5_5e/_actions.py:122` |
| ACT-05 | Major | Action/bonus-action is consumed before attack validation, so rejected attacks burn the slot | `src/game_engine/rules/dnd_5_5e/_actions.py:138` |
| ACT-06 | Major | Ready action has no trigger, stored action, or reaction semantics | `src/game_engine/rules/dnd_5_5e/_actions.py:189` |
| ACT-07 | Major | Slow, Push, and Cleave weapon masteries are log-only with no mechanical effect | `src/game_engine/rules/dnd_5_5e/_attacks.py:149` |
| ACT-08 | Major | Nick mastery has no mechanical effect — off-hand attack always consumes the bonus action | `src/game_engine/rules/dnd_5_5e/_attacks.py:155` |
| ACT-09 | Major | Critical hits double the flat modifier embedded in the damage dice notation | `src/game_engine/rules/dnd_5_5e/_attacks.py:317` |
| ACT-10 | Major | Saving-throw proficiency is wrongly added to raw ability checks (and contests) | `src/game_engine/rules/dnd_5_5e/_checks.py:132` |
| ACT-11 | Major | Default unarmed strike deals 1d4 + STR instead of the 2024 fixed 1 + STR | `src/game_engine/types/sheets.py:287` |
| ACT-12 | minor | Removing the current combatant makes current_turn() report the previous combatant | `src/game_engine/core/initiative.py:161` |
| ACT-13 | minor | get_available_actions ignores the current turn state and bonus-action/reaction economy | `src/game_engine/rules/dnd_5_5e/_actions.py:43` |
| ACT-14 | minor | Dash flag and movement tracking are dead: dashing and movement_used_ft are never consumed | `src/game_engine/rules/dnd_5_5e/_actions.py:155` |
| ACT-15 | minor | Dodge benefit not cancelled when the dodger's speed is 0 | `src/game_engine/rules/dnd_5_5e/_attacks.py:94` |
| ACT-16 | minor | Unarmed grapple/shove ignores the size restriction | `src/game_engine/rules/dnd_5_5e/_attacks.py:186` |
| ACT-17 | minor | Graze mastery invents a minimum-1 damage floor | `src/game_engine/rules/dnd_5_5e/_attacks.py:290` |
| ACT-18 | minor | Off-hand attack drops a negative ability modifier from damage | `src/game_engine/rules/dnd_5_5e/_attacks.py:313` |
| ACT-19 | minor | Help action never grants advantage on ability checks — only attack rolls consume the helped flag | `src/game_engine/rules/dnd_5_5e/_checks.py:141` |
| ACT-20 | minor | Initiative ignores the exhaustion d20 penalty (char.d20_modifier) | `src/game_engine/rules/dnd_5_5e/engine.py:103` |

### Spells & Spellcasting

| ID | Sev | Finding | Location |
|----|-----|---------|----------|
| SPL-01 | CRITICAL | Revivify / Raise Dead / True Resurrection can never revive a dead target | `src/game_engine/rules/dnd_5_5e/_damage.py:126` |
| SPL-02 | CRITICAL | Spell damage never triggers a concentration save on the target | `src/game_engine/rules/dnd_5_5e/_spell_resolution.py:163` |
| SPL-03 | Major | Spell casting_time is ignored by the action economy — bonus-action and reaction spells always consume the Action | `src/game_engine/rules/dnd_5_5e/_actions.py:133` |
| SPL-04 | Major | No repeat-save/save-to-end mechanism: Hold Person paralyzes for a full minute with no escape | `src/game_engine/rules/dnd_5_5e/_conditions.py:71` |
| SPL-05 | Major | Upcast math drops the flat modifier: Magic Missile upcasts to 4d4+3 instead of 4d4+4 | `src/game_engine/rules/dnd_5_5e/_spell_resolution.py:56` |
| SPL-06 | Major | 2024 'only one spell-slot spell per turn' rule is not enforced or even representable | `src/game_engine/rules/dnd_5_5e/_spell_resolution.py:104` |
| SPL-07 | Major | Breaking or replacing concentration never ends the spell's effects on targets | `src/game_engine/rules/dnd_5_5e/_spell_resolution.py:114` |
| SPL-08 | Major | Spell attack rolls ignore all condition-based advantage/disadvantage and never deal critical damage | `src/game_engine/rules/dnd_5_5e/_spell_resolution.py:129` |
| SPL-09 | Major | Registry spells with no mechanical fields silently no-op when cast (Shield, Counterspell, Power Word Kill, Mage Armor, Bless, Banishment, ...) | `src/game_engine/rules/dnd_5_5e/data/spells/level1.py:106` |
| SPL-10 | Major | Sleep applies Unconscious immediately on the first failed save | `src/game_engine/rules/dnd_5_5e/data/spells/level1.py:142` |
| SPL-11 | Major | Hex and Hunter's Mark deal immediate direct damage when cast | `src/game_engine/rules/dnd_5_5e/data/spells/level1.py:311` |
| SPL-12 | Major | Multi-beam/ray attack spells (Scorching Ray, Eldritch Blast) collapse into one all-or-nothing attack roll with wrong upcast math | `src/game_engine/rules/dnd_5_5e/data/spells/level2.py:85` |
| SPL-13 | Major | Spiritual Weapon damage omits the spellcasting ability modifier | `src/game_engine/rules/dnd_5_5e/data/spells/level2.py:206` |
| SPL-14 | Major | Blindness/Deafness applies both Blinded and Deafened instead of one of the caster's choice | `src/game_engine/rules/dnd_5_5e/data/spells/level2.py:321` |
| SPL-15 | Major | Pact slots merged into the shared multiclass pool let a short rest restore standard spell slots | `src/game_engine/rules/dnd_5_5e/spellcasting.py:146` |
| SPL-16 | minor | Concentration save DC missing the 2024 maximum of 30 | `src/game_engine/rules/dnd_5_5e/_damage.py:147` |
| SPL-17 | minor | Dual-damage spells never upcast their secondary damage pool | `src/game_engine/rules/dnd_5_5e/_spell_resolution.py:150` |
| SPL-18 | minor | Aid cannot raise hit point maximum, so it does nothing at full HP | `src/game_engine/rules/dnd_5_5e/data/spells/level2.py:161` |
| SPL-19 | minor | Ice Storm uses 2014 dice (2d8 bludgeoning, +1d8 upcast) instead of 2024 (2d10, +1d10) | `src/game_engine/rules/dnd_5_5e/data/spells/level4.py:40` |
| SPL-20 | minor | Power Word Stun stuns targets above the 150-HP threshold | `src/game_engine/rules/dnd_5_5e/data/spells/level8.py:72` |
| SPL-21 | minor | Mass Heal restores 700 HP to each target instead of 700 divided among targets | `src/game_engine/rules/dnd_5_5e/data/spells/level9.py:116` |
| SPL-22 | minor | compute_spell_slots caster_types override is unusable — ClassLevelEntry is unhashable | `src/game_engine/rules/dnd_5_5e/spellcasting.py:130` |
| SPL-23 | minor | duration_rounds silently returns None for long durations, making rider conditions permanent | `src/game_engine/rules/dnd_5_5e/spellcasting.py:180` |
| SPL-24 | minor | SpellComponent, SpellRangeType, AreaShape, SpellSchool and range/area/material fields are never consumed by any rule logic | `src/game_engine/types/enums/_core.py:202` |

### Equipment

| ID | Sev | Finding | Location |
|----|-----|---------|----------|
| EQP-01 | CRITICAL | Weapon registry (WeaponData/get_weapon) is never consumed by attack resolution — masteries, proficiency, and weapon stats can never fire in real play | `src/game_engine/rules/dnd_5_5e/data/weapons.py:529` |
| EQP-02 | Major | Armor stealth_disadvantage flag is never consumed — the Hide action ignores noisy armor | `src/game_engine/rules/dnd_5_5e/_actions.py:179` |
| EQP-03 | Major | Armor training and weapon proficiency have no in-play mechanical effect — stored on the sheet but never consulted | `src/game_engine/rules/dnd_5_5e/character_builder.py:228` |
| EQP-04 | Major | Heavy armor Strength minimum never reduces speed — min_strength is dead data and worn-armor identity is never stored | `src/game_engine/rules/dnd_5_5e/character_builder.py:269` |
| EQP-05 | Major | Starting equipment and gold are never applied to the built character's inventory or currency | `src/game_engine/rules/dnd_5_5e/character_builder.py:284` |
| EQP-06 | Major | Passing 'Shield' as body armor yields AC 2 — compute_armor_class treats the shield registry entry as base armor | `src/game_engine/rules/dnd_5_5e/data/armor.py:194` |
| EQP-07 | Major | InventoryItem.equipped is never read — no equip/unequip path recomputes AC or selects weapons | `src/game_engine/types/character_state.py:163` |
| EQP-08 | Major | WeaponProperty enum and AttackDetails.properties have zero rule-logic consumers: Heavy, Loading, Ammunition, Versatile, Finesse, Reach, Thrown all unimplemented | `src/game_engine/types/sheets.py:291` |
| EQP-09 | minor | ToolData.ability is dead data — tool checks never use the governing ability or tool proficiency | `src/game_engine/rules/dnd_5_5e/data/gear.py:28` |
| EQP-10 | minor | is_encumbered has no rule consumers — exceeding carrying capacity has no effect | `src/game_engine/rules/dnd_5_5e/exploration.py:44` |
| EQP-11 | minor | Currency.total_gp is never consumed and no purchase/spend logic exists anywhere | `src/game_engine/types/character_state.py:141` |

### Effect Resolution (Damage, Death, Conditions, Rests)

| ID | Sev | Finding | Location |
|----|-----|---------|----------|
| EFF-01 | CRITICAL | Gaining Incapacitated (or Stunned/Paralyzed/Petrified/Unconscious) never breaks concentration | `src/game_engine/rules/dnd_5_5e/_conditions.py:38` |
| EFF-02 | Major | Charmed has zero mechanical effect anywhere in the engine | `src/game_engine/core/conditions.py:66` |
| EFF-03 | Major | Exhaustion can never be gained through the engine; Condition.EXHAUSTION is a mechanical no-op | `src/game_engine/core/conditions.py:81` |
| EFF-04 | Major | Grappled (2024) missing attack disadvantage vs non-grappler, escape check, and end-on-grappler-incapacitated | `src/game_engine/core/conditions.py:97` |
| EFF-05 | Major | Petrified grants poison and psychic damage immunity instead of Poisoned-condition immunity | `src/game_engine/core/conditions.py:147` |
| EFF-06 | Major | Stunned sets speed to 0 (2014 rule); 2024 Stunned no longer prevents movement | `src/game_engine/core/conditions.py:189` |
| EFF-07 | Major | Concentration save uses pre-mitigation damage; immune targets take 0 damage but can still lose concentration | `src/game_engine/rules/dnd_5_5e/_attacks.py:323` |
| EFF-08 | Major | Damage at 0 HP that equals or exceeds HP maximum does not kill instantly | `src/game_engine/rules/dnd_5_5e/_damage.py:70` |
| EFF-09 | Major | Death save counters not reset when character becomes stable via 3 successes | `src/game_engine/rules/dnd_5_5e/_death.py:63` |
| EFF-10 | Major | Combat resolution paths bypass condition immunities entirely (spell riders, Topple, unarmed grapple/shove) | `src/game_engine/rules/dnd_5_5e/_spell_resolution.py:181` |
| EFF-11 | minor | ConditionEffect.can_act and speed_zero fields are never consumed (duplicate frozensets are the live source) | `src/game_engine/core/conditions.py:41` |
| EFF-12 | minor | Deafened has zero mechanical effect; Blinded/Deafened auto-fail of sight/hearing checks unmodeled | `src/game_engine/core/conditions.py:74` |
| EFF-13 | minor | Temporary hit points are ignored for a creature already at 0 HP | `src/game_engine/rules/dnd_5_5e/_damage.py:81` |
| EFF-14 | minor | Unconscious applied directly (apply_condition or spell rider) does not include the Prone condition | `src/game_engine/rules/dnd_5_5e/_spell_resolution.py:180` |
| EFF-15 | minor | Invisible condition's advantage on initiative (2024 'Surprise' clause) not implemented | `src/game_engine/rules/dnd_5_5e/engine.py:93` |
| EFF-16 | minor | Long rest grants full benefits to a character at 0 HP | `src/game_engine/rules/dnd_5_5e/resting.py:106` |

---

## Action Mechanics

### ACT-01 — Extra Attack is impossible: action economy allows exactly one attack per Attack action

**Severity:** critical · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/_actions.py:134`

_resolve_action_impl sets ts.action_used = True on the first Attack action and rejects any subsequent Attack with 'Action already used this turn'. _resolve_attack resolves exactly one attack roll. TurnState.attacks_made is incremented in _attacks.py:272 but never read by any code, and there is no attacks-per-action concept anywhere: no module computes how many attacks a character gets (Fighter 5/11/20, Barbarian/Paladin/Ranger/Monk 5). Class feature registries contain 'Extra Attack' / 'Two Extra Attacks' / 'Three Extra Attacks' as descriptive text only. Every level-5+ martial character loses half (or more) of their attacks every combat turn — the second resolve_action returns error 'action_used', which dm-api turns into a 409. This also makes the Nick and Vex masteries' same-turn interactions unreachable.

**2024 rule (SRD 5.2):** SRD 5.2 Extra Attack (Fighter et al., level 5): 'You can attack twice instead of once whenever you take the Attack action on your turn' (Fighter scaling to 3 and 4 attacks).

**Evidence:**

```
_actions.py:133-138: `if ts.action_used: return _simple_result(action, False, "Action already used this turn.", {"error": "action_used"}); ts.action_used = True`. grep -rn 'attacks_made' src/ → written at _attacks.py:272 and serialized in sheets.py; zero reads. grep -rn 'Extra Attack' src/ → only prose strings in data/class_features/*.py (fighter.py:56,89,121 and 5 other classes). Executed repro: level-5 fighter, first Attack succeeds, second Attack same turn -> success=False, log_entry['error']='action_used'. tests/test_attacks_2024.py::test_action_used_once_per_turn asserts the second attack always fails with no Extra Attack carve-out.
```

**Verification:** Confirmed: _actions.py:134-138 unconditionally rejects a second Attack action per turn with no Extra Attack carve-out, and grep confirms 'Extra Attack'/'attacks_made' exist only as descriptive class-feature text and a dead-write counter, never read anywhere in game-engine or dm-api. The parity spec claims the full action economy is implemented with no caveat for multiclass/level-based attack counts.

### ACT-02 — Reaction economy and opportunity attacks are unimplemented despite spec claiming both

**Severity:** critical · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/_actions.py:196`

The parity spec claims 'Action / bonus action / reaction economy per turn' and 'Opportunity attacks' are implemented and tested. In reality: (1) TurnState.reaction_used (types/sheets.py:210) is never set or read by any rule logic — it only appears in to_dict/from_dict serialization; (2) there is no code path anywhere to resolve an attack as a reaction — Action/AttackDetails has no is_reaction field and _resolve_action_impl always consumes the actor's action or bonus action slot, so an opportunity attack resolved through the engine either wrongly burns the reactor's on-turn action or fails outright with 'action_used' if they already acted; (3) the only opportunity-attack logic is provokes_opportunity_attack() in _actions.py (not _attacks as the spec states), which only checks the mover's disengaging flag, never checks or consumes the attacker's reaction, and is never called by any module nor exported. A creature can therefore make unlimited opportunity attacks per round and nothing enforces one-reaction-per-round; reaction refresh at turn start is moot because nothing ever consumes a reaction.

**2024 rule (SRD 5.2):** SRD 5.2 Reactions: a creature can take only one Reaction per round, regaining it at the start of its next turn; an Opportunity Attack uses the Reaction to make one melee attack against a creature leaving reach.

**Evidence:**

```
grep -rn 'reaction_used' src/ → only types/sheets.py:210,227,246 (field + serde); zero reads in rules/. _actions.py:196-201: `def provokes_opportunity_attack(mover_id, combat_state): return not combat_state.turn_state_for(mover_id).disengaging` — no reference to the attacker at all. grep -rn 'provokes_opportunity_attack' src/ ../dm-api/src → only its own definition; no callers, not in __init__.py __all__. Executed repro: after 'a' used their action, resolving an attack for 'a' (the opportunity-attack scenario) returns success=False error='action_used' with reaction_used still False. Spec docs/phb-parity-spec.md:115-117 marks both rows as implemented.
```

**Verification:** Core claim holds: provokes_opportunity_attack (_actions.py:196-201) only checks the mover's disengaging flag, has no caller anywhere in game-engine or dm-api besides its own test, and never consumes a reaction, so opportunity attacks are unenforced and unlimited. One inaccuracy in the evidence: reaction_used IS actually read/set for reaction-cast spells in dm-api/src/dm_api/api/combat_spells.py:112-114, so the reaction economy is not a complete no-op system-wide — but that doesn't cover opportunity attacks, which remain fully unimplemented as claimed, and the spec marks both rows implemented.

### ACT-03 — begin_turn/reset_turn wipes cross-turn effects: Help, Sap, Vex, and Hide are no-ops in normal play

**Severity:** critical · **Location:** `game-engine/src/game_engine/types/sheets.py:276`

TurnState.reset_turn (called by DnD55eEngine.begin_turn at the start of each combatant's turn, and mirrored by dm-api next_turn which stores TurnState().to_dict()) replaces the combatant's TurnState with a brand-new one, erasing helped, sapped, vexed_target_id, and hidden. But these flags represent effects that by rule persist across turn boundaries: Help grants an ally advantage on its NEXT attack roll (which happens on the ally's later turn — wiped by the ally's own begin_turn before it can be consumed); Sap gives the TARGET disadvantage on its next attack roll before the start of the sapper's next turn (wiped by the target's own begin_turn before the target ever attacks); Vex lasts until the end of the attacker's NEXT turn (wiped at the start of that turn); a successful Hide (Invisible condition) lasts until the hider attacks or is found, not until the start of their next turn. Under the engine's documented turn flow, the Help action and the Sap mastery therefore never have any mechanical effect, and hiding one turn to attack with advantage the next never works.

**2024 rule (SRD 5.2):** SRD 5.2: Help action — 'the ally has Advantage on the next ability check/attack roll it makes' (persists until start of your next turn); Sap mastery — 'that creature has Disadvantage on its next attack roll before the start of your next turn'; Vex mastery — 'Advantage on your next attack roll against that creature before the end of your next turn'; Hide action — the Invisible condition lasts until you make an attack roll, cast a spell with a verbal component, or an enemy finds you.

**Evidence:**

```
sheets.py:276-279 `def reset_turn(self, char_id): self.turn_states[char_id] = TurnState()` (fresh TurnState, all flags False) called from _actions.py:73-75 `_begin_turn_impl`. Flags set on the OTHER party's turn (_actions.py:172-177 Help; _attacks.py:143-147 Sap/Vex; _actions.py:178-187 Hide) and only consumed in _attacks.py:_advantage_state (96-107) during a later attack. Executed repro: engine.resolve_action(HELP a->b) sets turn_state_for('b').helped=True; engine.begin_turn(b) -> helped=False before b ever attacks; same for vexed_target_id/hidden/sapped. dm-api combat.py:310-311 does turn_states[sheet.id] = TurnState().to_dict() identically. tests/test_attacks_2024.py::test_vex_grants_advantage_on_next_attack only asserts the flag is set, never that it survives to the next attack; test_begin_turn_resets_economy confirms the full wipe.
```

**Verification:** Confirmed by tracing sheets.py:276-279 (reset_turn replaces TurnState entirely) called only for the single combatant whose turn is beginning (_actions.py:73-75, combat.py:307-311). Help sets target's helped flag on the helper's turn, but the target's own begin_turn fires before the target's next attack and wipes it; Vex/Sap/Hide follow the identical pattern since all four flags are consumed only in _advantage_state during a later attack (_attacks.py:96-107). The spec marks the full 2024 action list and reaction/action economy as implemented (docs/phb-parity-spec.md:114-115), so this is not declared out of scope.

### ACT-04 — Two-weapon fighting never validates the Light property or a prior Attack action — any weapon works off-hand

**Severity:** major · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/_actions.py:122`

The spec claims 'Two-weapon fighting (Light property, Nick)' is implemented, but any attack flagged is_offhand is accepted as a bonus-action attack regardless of whether the actor took the Attack action this turn with a Light weapon (ts.action_used / ts.attacks_made are not consulted), whether the off-hand weapon is Light, or whether the weapons are different. AttackDetails.properties (which carries WeaponProperty.LIGHT) is never consulted anywhere in _actions.py or _attacks.py — WeaponProperty.LIGHT has zero references in rule code. A character can thus open their turn with a bonus-action greatsword 'off-hand' attack and still take a full action, which the 2024 Light property forbids. Only the damage-modifier half of TWF (Feat.TWO_WEAPON_FIGHTING at _attacks.py:313) is implemented.

**2024 rule (SRD 5.2):** SRD 5.2 Light weapon property: 'When you take the Attack action on your turn and attack with a Light weapon, you can make one extra attack as a Bonus Action later on the same turn. That extra attack must be made with a different Light weapon.'

**Evidence:**

```
_actions.py:122-132: `uses_bonus_action = (action.action_type is ActionType.ATTACK and action.details is not None and action.details.is_offhand)` — only checks ts.bonus_action_used, never ts.action_used, ts.attacks_made, nor `WeaponProperty.LIGHT in details.properties`. grep -rn 'WeaponProperty\.' src/game_engine/rules src/game_engine/core (excluding data/) → zero hits; details.properties never read in _attacks.py/_actions.py. docs/phb-parity-spec.md:118 claims Light-property TWF implemented.
```

**Verification:** Confirmed: _actions.py:122-132 computes uses_bonus_action from is_offhand alone with no check of ts.action_used, ts.attacks_made, or WeaponProperty.LIGHT; grep confirms zero references to WeaponProperty in _actions.py/_attacks.py outside data files. Spec claims Light-property TWF implemented (docs/phb-parity-spec.md:118).

### ACT-05 — Action/bonus-action is consumed before attack validation, so rejected attacks burn the slot

**Severity:** major · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/_actions.py:138`

_resolve_action_impl sets ts.action_used (or bonus_action_used) BEFORE delegating to _resolve_attack, but _resolve_attack has failure guards that reject the action without anything happening: actor_not_found, target_not_found (_attacks.py:239-241) and total_cover (_attacks.py:242-245). A player who targets a creature behind total cover (a legal thing to attempt) or a mistyped/departed target id loses their entire action: the immediate result is a failure AND every subsequent attack that turn fails with 'action_used'. The consumption should happen only after validation passes. (dm-api happens to mask this by raising a 409 before committing state, but the engine's own contract — exercised by TestMissingTarget — is wrong for any in-process consumer.) Also, for an unknown actor_id a ghost TurnState is created and marked used.

**2024 rule (SRD 5.2):** n/a — logic bug

**Evidence:**

```
Executed repro: attack vs target with CoverType.TOTAL -> error='total_cover' and turn_state_for('a').action_used == True; follow-up legal attack in same turn -> success=False, error='action_used'.
```

**Verification:** Confirmed by direct repro: attacking a target with CoverType.TOTAL sets action_used=True before _resolve_attack's total_cover guard rejects it, and the following legal attack in the same turn then fails with error='action_used'. The existing TestMissingTarget test only asserts success is False, never checking action_used, so this regression is untested. This is a clear logic bug with concrete failure scenario, correctly scoped as major.

### ACT-06 — Ready action has no trigger, stored action, or reaction semantics

**Severity:** major · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/_actions.py:189`

ActionType.READY falls through to the generic 'success' branch: it consumes the actor's action and returns '{name} uses Ready.' with no way to specify a trigger or the readied action, no storage of the readied action on TurnState, and no reaction linkage (the readied action is supposed to be taken later using the Reaction, and a readied spell requires concentration). Unlike Influence and Magic, the code comment does not defer Ready to the orchestration layer — and Ready cannot be implemented at the orchestration layer anyway because the engine offers no way to resolve any action as a reaction (resolve_action always spends the on-turn action slot). The parity spec marks the full 2024 action list as implemented; as written, Ready is a pure no-op that wastes the action.

**2024 rule (SRD 5.2):** SRD 5.2 Ready action: you choose a perceivable trigger and an action (or movement) in response; taking the readied response uses your Reaction before the start of your next turn; readying a spell requires casting it on your turn and holding it with Concentration.

**Evidence:**

```
_actions.py:189-193: comment defers only Influence/Magic then `return _simple_result(action, True, f"{name} uses {action.action_type.value}.")`. grep -rn 'READY|Ready' src/game_engine (excluding data/) → only the enum (_combat.py:23), the availability list (_actions.py:33), and this generic-success branch. No 'readied', 'trigger', or reaction-consuming code exists anywhere; TurnState (sheets.py:205-220) has no readied-action field and reaction_used is never used.
```

**Verification:** Confirmed: _actions.py:189-193 falls through to a generic success message for Ready with no trigger, stored readied action, or reaction linkage, and (per finding 2) the engine has no mechanism to resolve any action as a reaction later, so Ready cannot even be completed at the orchestration layer as the code comment implies for Influence/Magic. No TurnState field for a readied action exists.

### ACT-07 — Slow, Push, and Cleave weapon masteries are log-only with no mechanical effect

**Severity:** major · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/_attacks.py:149`

The spec marks 'Weapon masteries (Cleave, Graze, Nick, Push, Sap, Slow, Topple, Vex)' as implemented in data.items + _attacks. Topple, Sap, Vex, and Graze have mechanics (though Sap/Vex are undermined by the begin_turn wipe), but three masteries only write log entries that nothing consumes: SLOW writes log['slowed_ft'] = 10 with nothing ever reducing the target's speed even though speed IS modeled (CharacterSheet.speed / effective_speed only reads conditions and exhaustion); PUSH writes log['pushed_ft'] = 10 with no CreatureSize check (the rule applies only to Large or smaller targets, and Push is arguably positional/theater-of-mind, but the row is claimed done without qualification); CLEAVE writes log['cleave_available'] = True and no code path allows the follow-up attack roll against a second creature — even if the orchestrator re-submitted an attack, the action economy would reject it as 'action_used'. Grep confirms none of these log keys is read anywhere in game-engine or dm-api, and TurnState has no slow/cleave state.

**2024 rule (SRD 5.2):** SRD 5.2/PHB 2024 masteries: Slow — reduce the target's Speed by 10 ft until the start of your next turn; Cleave — on a hit with a melee weapon, make one extra attack roll against a second creature within reach (damage without ability modifier), once per turn; Push — push the target up to 10 ft away if it is Large or smaller.

**Evidence:**

```
_attacks.py:149-156: the SLOW/PUSH/CLEAVE branches contain only log[...] assignments. grep -rn 'slowed_ft|pushed_ft|cleave_available' src/ ../dm-api/src → only the write sites in _attacks.py. effective_speed (sheets.py:160-164) has no per-target speed-reduction input and no CreatureSize check exists for Push; TurnState (sheets.py:205-256) has no slow/cleave fields; docs/phb-parity-spec.md:91 claims masteries implemented in `_attacks`.
```

**Verification:** Confirmed: _attacks.py:149-154 SLOW/PUSH/CLEAVE branches only write log dict entries; grep confirms none of slowed_ft/pushed_ft/cleave_available is read anywhere, effective_speed (sheets.py:160-164) has no per-target speed-reduction hook, no CreatureSize check exists for Push, and TurnState has no slow/cleave fields. Spec marks the full mastery list implemented without qualification (docs/phb-parity-spec.md:91).

### ACT-08 — Nick mastery has no mechanical effect — off-hand attack always consumes the bonus action

**Severity:** major · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/_attacks.py:155`

The Nick mastery's entire implementation is a log entry ('nick_extra_attack': True) written only when a Nick-weapon attack HITS, which nothing reads. Per the 2024 rules Nick lets you make the Light-property extra attack as part of the Attack action itself instead of as a bonus action (freeing the bonus action), and this benefit does not depend on hitting. In the engine, _resolve_action_impl chooses the economy slot purely from details.is_offhand before any mastery is examined and unconditionally charges every is_offhand attack to the bonus action (and an is_offhand=False variant would consume the action), so a Scimitar/Dagger wielder can never combine the Nick extra attack with another bonus action, contradicting the parity spec's 'Two-weapon fighting (Light property, Nick)' claim.

**2024 rule (SRD 5.2):** SRD 5.2 Nick mastery: 'When you make the extra attack of the Light property, you can make it as part of the Attack action instead of as a Bonus Action. You can make this extra attack only once per turn.'

**Evidence:**

```
_attacks.py:155-156: `elif mastery is WeaponMastery.NICK: log["nick_extra_attack"] = True` — inside _apply_mastery_effects, only reached on a hit (_attacks.py:328-331), changes no action-economy state, and no code reads the log key. _actions.py:122-132: `uses_bonus_action = (action.action_type is ActionType.ATTACK and action.details is not None and action.details.is_offhand)` → `ts.bonus_action_used = True`, with no Nick exemption. Executed repro: actor with weapon_masteries=['Dagger'], main-hand Dagger attack then is_offhand Nick attack -> Nick attack succeeds but turn_state.bonus_action_used == True. docs/phb-parity-spec.md:118 claims Nick is implemented.
```

**Verification:** Confirmed: _attacks.py:155-156 Nick only writes a log key inside _apply_mastery_effects (reached only on a hit), and _actions.py:122-132 always routes any is_offhand attack to the bonus-action slot with no Nick exemption, so Nick can never free the bonus action as SRD 5.2 requires. Spec claims Nick implemented at docs/phb-parity-spec.md:118.

### ACT-09 — Critical hits double the flat modifier embedded in the damage dice notation

**Severity:** major · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/_attacks.py:317`

On a crit, the code calls dice_roll(details.damage_dice) twice and sums the totals. dice_roll (core.dice.roll) returns count*dice + the notation's flat modifier, so a damage_dice value like '1d6+2' contributes its +2 twice on a critical hit. Crits must double only the dice. This is directly reachable: the shipped monster registry stores attack damage with baked-in modifiers (data/monsters.py e.g. DiceNotation('1d4+2'), '1d6+2', '2d8+4'), and dm-api's AttackDetailsRequest accepts any damage_dice string from the client. (Relatedly, ability_mod is then added on top at line 319, so a caller passing a monster's '1d4+2' notation plus its attack ability double-counts the ability modifier even on normal hits.)

**2024 rule (SRD 5.2):** SRD 5.2 Critical Hits: roll the attack's damage dice twice; modifiers are not doubled.

**Evidence:**

```
Executed repro: AttackDetails(damage_dice=DiceNotation('1d6+2')), forced nat 20 and die face 1, STR mod 0 -> result.damage == 6 (1+2 + 1+2); correct crit damage is 4 (1+1+2). Monster data at src/game_engine/rules/dnd_5_5e/data/monsters.py:78,86,122,130 carries flat modifiers in damage_dice.
```

**Verification:** Confirmed by reading core/dice.py: roll(notation) parses and re-adds the flat modifier every call, and _attacks.py:315-318 calls dice_roll(details.damage_dice) twice on a crit and sums both totals, doubling the embedded modifier. The existing test (test_engine_actions.py test_natural_20_doubles_damage_dice) mocks dice_roll directly and uses a modifier-free '1d6' notation, masking this. dm-api's build_attack_details (combat_utils.py:255-261) passes client-supplied damage_dice strings straight into AttackDetails, and the monster registry (monsters.py) stores baked-in modifiers like '1d4+2', confirming reachability. Severity 'major' is justified given SRD 5.2 explicitly says only dice double, not modifiers.

### ACT-10 — Saving-throw proficiency is wrongly added to raw ability checks (and contests)

**Severity:** major · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/_checks.py:132`

When _roll_check_impl resolves a raw ability check (skill_key is an ability name, so Skill(skill_key) raises and proficiency_key falls back to the Ability), it calls char.is_proficient(ability), which checks CharacterSheet.proficient_abilities. That list holds SAVING-THROW proficiencies (character_builder.py:271 fills it from class_data.saving_throw_proficiencies, and _saves.py:58 uses it for saves). Ability checks have no proficiency in D&D, so every raw ability check — including Hide-adjacent contests, grapple-escape STR/DEX checks routed through roll_check, and Influence CHA checks — is inflated by +2..+6 for any class whose save proficiencies match.

**2024 rule (SRD 5.2):** SRD 5.2: proficiency in a saving throw does not apply to ability checks; plain ability checks add only the ability modifier.

**Evidence:**

```
Executed repro: level-5 fighter (proficient_abilities=[STRENGTH] as per class save proficiencies), STR 10, forced d20=10 -> roll_check(char, Ability.STRENGTH, dc=10).total == 13 (prof +3 wrongly included); correct total is 10.
```

**Verification:** Confirmed by direct repro: a level-5 fighter with proficient_abilities=[STRENGTH] (populated from class SAVE proficiencies per character_builder.py:271) gets +3 wrongly added to a raw STR ability check via _checks.py:132's is_proficient(ability) fallback. total came back 13 instead of the correct 10. roll_check is part of the public DnD55eEngine API so any orchestration-layer raw ability check (grapple escape, Influence, etc.) is exposed to this bug, even though skill checks (the common path) are unaffected since they use proficient_skills.

### ACT-11 — Default unarmed strike deals 1d4 + STR instead of the 2024 fixed 1 + STR

**Severity:** major · **Location:** `game-engine/src/game_engine/types/sheets.py:287`

AttackDetails defaults to weapon_name='Unarmed Strike' with damage_dice=DiceNotation('1d4'), and _attacks.py uses this default (_DEFAULT_ATTACK) whenever an Attack action has no details (the dm-api AttackDetailsRequest default is also '1d4'). The 2024 rules set unarmed strike damage to 1 + Strength modifier bludgeoning (a fixed 1, no die; 1d4 is only granted by Tavern Brawler, which the engine's own feats.py:98 correctly describes). Additionally, UnarmedStrikeOption.DAMAGE is never referenced by any rule code (_attacks.py:250 checks only GRAPPLE and SHOVE; DAMAGE falls through to the generic weapon path). Every default/unarmed attack resolved by the engine deals 1d4+STR (avg +1.5 too high, and doubled dice on a crit that shouldn't exist).

**2024 rule (SRD 5.2):** SRD 5.2 Unarmed Strike (Damage option): 'the target takes damage equal to 1 plus your Strength modifier' (bludgeoning); there is no damage die.

**Evidence:**

```
sheets.py:286-288: `weapon_name: str = "Unarmed Strike"` / `damage_dice: DiceNotation = DiceNotation("1d4")` / `damage_type: DamageType = DamageType.BLUDGEONING`. _attacks.py:36 `_DEFAULT_ATTACK = AttackDetails()` and _attacks.py:236 `details = action.details or _DEFAULT_ATTACK`; damage computed at _attacks.py:315-319 as `dice_roll(details.damage_dice)` + ability mod (plus a second 1d4 on crit). dm-api/src/dm_api/db/models/combat.py:86 defaults damage_dice='1d4'. grep -rn 'UnarmedStrikeOption.DAMAGE' src/ → zero consumers.
```

**Verification:** Confirmed: sheets.py:286-288 defaults AttackDetails to 1d4 unarmed damage, _attacks.py:36/236 uses this default whenever an Attack has no details, and feats.py's Tavern Brawler text ('deal 1d4 damage') independently confirms the base unarmed strike is not supposed to be 1d4. UnarmedStrikeOption.DAMAGE is indeed never referenced — only GRAPPLE/SHOVE are checked at _attacks.py:250.

### ACT-12 — Removing the current combatant makes current_turn() report the previous combatant

**Severity:** minor · **Location:** `game-engine/src/game_engine/core/initiative.py:161`

remove_combatant decrements _current_index when idx <= _current_index so the NEXT next_turn() call is correct, but it leaves current_turn() pointing at the combatant whose turn already finished. Scenario: order [A, B, C], next_turn() twice so it is B's turn (_current_index=1); B dies and remove_combatant('B') is called -> _current_index=0 and current_turn() now returns A, even though it is actually still the gap between B and C. Any UI or logic that reads current_turn() after a mid-turn removal displays the wrong active combatant.

**2024 rule (SRD 5.2):** n/a — logic bug

**Evidence:**

```
initiative.py:156-163: on removal 'if idx <= self._current_index: self._current_index = max(-1, self._current_index - 1)' — for idx == _current_index the index now points at the prior entry, and current_turn() (lines 139-141) returns self._entries[self._current_index] with no awareness that this entry's turn already happened.
```

**Verification:** Confirmed by direct repro: order [A,B,C], advance to B's turn (_current_index=1), remove_combatant('B') decrements _current_index to 0, and current_turn() now incorrectly returns A even though B's turn had already started/finished. next_turn() semantics are preserved but current_turn() misreports the active combatant for that gap, exactly as described.

### ACT-13 — get_available_actions ignores the current turn state and bonus-action/reaction economy

**Severity:** minor · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/_actions.py:43`

_get_available_actions_impl takes combat_state but never uses it: it returns the full action list even when TurnState.action_used is already True, never surfaces bonus-action options (off-hand attack), and never reflects reaction availability. The spec claims this is the implemented 'available actions' surface for the action economy; as written, its answer to 'what can this character legally do' is wrong for the second half of every turn.

**2024 rule (SRD 5.2):** PHB 2024 action economy: one action, at most one bonus action, and one reaction per round; a legal-actions query must reflect what has been spent.

**Evidence:**

```
_actions.py:43-70: combat_state parameter is unused (no turn_state_for call); the only filters are char.can_act and spell availability for MAGIC.
```

**Verification:** Confirmed: _get_available_actions_impl (_actions.py:43-70) takes combat_state as a parameter but never calls turn_state_for or reads action_used/bonus_action_used, so it returns the same full action list regardless of what's already been spent this turn, and never distinguishes bonus-action or reaction availability. This matches the finding precisely; correctly scoped as minor since it's a convenience/query surface rather than something that lets illegal actions actually resolve (resolve_action's own economy checks in _actions.py:121-138 remain authoritative).

### ACT-14 — Dash flag and movement tracking are dead: dashing and movement_used_ft are never consumed

**Severity:** minor · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/_actions.py:155`

The Dash action sets TurnState.dashing = True and logs extra_movement, but no code ever reads the dashing flag, and TurnState.movement_used_ft is never written or read by any rule logic (both appear only in to_dict/from_dict). There is no movement budget enforcement at all, so Dash grants nothing mechanical, and provokes_opportunity_attack (itself unused) is the only movement-adjacent rule. Since the engine is theater-of-mind this may be intentional altitude, but the fields then exist as unconsumed state that serializes across requests for no purpose.

**2024 rule (SRD 5.2):** PHB 2024 Dash: gain extra movement equal to your Speed for the turn; movement is a per-turn budget.

**Evidence:**

```
grep -rn 'dashing|movement_used_ft' src/ ../dm-api/src → writes at _actions.py:155 and serde in sheets.py:211,215,228,232,247,251 only; zero reads in any rule module.
```

**Verification:** Confirmed dashing and movement_used_ft are write-only (_actions.py:155, sheets.py:211/215 + serde) with zero reads anywhere in game-engine or dm-api. However this is materially softer than 'major' bug status: the spec (docs/phb-parity-spec.md) explicitly declares the engine theater-of-mind with 'Grid/positioning rules... out of scope' and no movement-budget concept exists anywhere for Dash to plug into — so this reads as unused scaffolding consistent with the engine's declared scope, not a broken feature. Severity 'minor' as tagged is appropriate; it is dead state rather than an incorrect ruling.

### ACT-15 — Dodge benefit not cancelled when the dodger's speed is 0

**Severity:** minor · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/_attacks.py:94`

The Dodge action's attacker-disadvantage (line 94) and DEX-save advantage (_resolve_unarmed_special lines 192-197, plus _spell_resolution.py:127) are gated only on target.can_act (incapacitated). The 2024 Dodge benefit is also lost while the creature's Speed is 0 (e.g. Grappled or Restrained), which the sheet can already detect via effective_speed == 0. A grappled, dodging target still imposes disadvantage in the engine.

**2024 rule (SRD 5.2):** SRD 5.2 Dodge action: '...attack rolls against you have Disadvantage, and you make Dexterity saving throws with Advantage. You lose these benefits if you have the Incapacitated condition or if your Speed is 0.'

**Evidence:**

```
_attacks.py:94-95: `if target_ts.dodging and target.can_act: disadvantage = True` and _attacks.py:192-197 (DEX-save advantage) — neither checks `target.effective_speed > 0`, even though sheets.py:159-164 provides effective_speed with speed-zero condition handling (GRAPPLED/RESTRAINED set speed_zero=True in core/conditions.py).
```

**Verification:** Confirmed: _attacks.py:94 and _resolve_unarmed_special (192-197) gate Dodge's disadvantage-against-attacker and DEX-save-advantage solely on target.can_act (incapacitated), never on target.effective_speed. sheets.py:159-164 effective_speed already detects speed_zero conditions (GRAPPLED/RESTRAINED both set speed_zero=True per core/conditions.py), so the SRD 5.2 rule 'You lose these benefits if... your Speed is 0' is unenforced even though the data to check it exists on the sheet.

### ACT-16 — Unarmed grapple/shove ignores the size restriction

**Severity:** minor · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/_attacks.py:186`

_resolve_unarmed_special applies Grappled/Prone on a failed save with no check that the target is at most one size larger than the attacker, even though the engine models CreatureSize on the sheet. A Small goblin can grapple or shove a Gargantuan dragon.

**2024 rule (SRD 5.2):** SRD 5.2 Unarmed Strike (Grapple/Shove options): the target must be no more than one size larger than you (and within your reach); Grapple additionally requires a hand free.

**Evidence:**

```
_attacks.py:178-204: `_resolve_unarmed_special` computes dc = 8 + STR + PB and rolls the save immediately; there is no reference to actor.size / target.size (CreatureSize) anywhere in the function or its caller (_attacks.py:250-251).
```

**Verification:** The core defect is real — _resolve_unarmed_special never checks relative size before allowing Grapple/Shove, and SRD 5.2 requires the target be no more than one size larger. However the finding overstates existing infrastructure: CharacterSheet has no `size` field at all (CreatureSize is only used as an external parameter in exploration.py's carrying-capacity helpers, not stored per-combatant), so there's no sheet-level size data being 'ignored' — the gap is a missing field plus a missing check. The rules citation and reachability are still accurate.

### ACT-17 — Graze mastery invents a minimum-1 damage floor

**Severity:** minor · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/_attacks.py:290`

On a miss with a Graze weapon the code deals max(1, ability_mod) damage. The rule deals damage exactly equal to the ability modifier used for the attack roll; with a +0 or negative modifier the correct result is 0 damage, not 1. The engine deals 1 damage on every miss for STR 10-11 (or lower) attackers, the subsequent `if graze_damage:` guard is always true (dead condition) so every Graze miss also triggers a concentration check it should not, and the test suite codifies the invented rule, citing a nonexistent '2024 PHB GRAZE: minimum 1 damage' clause.

**2024 rule (SRD 5.2):** SRD 5.2 Graze mastery: 'If your attack roll with this weapon misses a creature, you can deal damage to that creature equal to the ability modifier you used to make the attack roll... the damage can be increased only by increasing the ability modifier.' No minimum is specified.

**Evidence:**

```
_attacks.py:289-294: `if details.mastery is WeaponMastery.GRAZE and _has_mastery(actor, details): graze_damage = max(1, ability_mod); if graze_damage: _apply_damage_impl(...)` — `max(1, ...)` makes the guard always true and awards 1 damage for mod <= 0. tests/test_attacks_2024.py:150-161 `test_graze_minimum_damage_is_1_with_negative_ability_mod` asserts damage == 1 with STR 6, with a comment misciting the 2024 PHB.
```

**Verification:** Confirmed by direct read of _attacks.py:289-294 (max(1, ability_mod) with an always-true guard) and the test at tests/test_attacks_2024.py:150-161, which asserts damage==1 for STR 6 and cites a nonexistent 'PHB minimum 1 damage' rule in its comment — the actual SRD 5.2 Graze text (also quoted in the finding) has no floor, so mod<=0 should yield 0 damage, not 1.

### ACT-18 — Off-hand attack drops a negative ability modifier from damage

**Severity:** minor · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/_attacks.py:313`

For off-hand attacks without the Two-Weapon Fighting style, the code sets damage_mod = 0 unconditionally. The 2024 Light property says you don't add the modifier UNLESS it is negative — a negative modifier must still be applied. A STR 6 (−2) character's off-hand handaxe should deal 1d6−2, but the engine deals a flat 1d6, overdealing damage.

**2024 rule (SRD 5.2):** SRD 5.2 Light property: 'You don't add your ability modifier to the extra attack's damage unless that modifier is negative.'

**Evidence:**

```
_attacks.py:312-314: `damage_mod = ability_mod; if details.is_offhand and Feat.TWO_WEAPON_FIGHTING not in actor.feats: damage_mod = 0` — zeroes the modifier even when ability_mod < 0; no branch preserves a negative ability_mod.
```

**Verification:** Confirmed: _attacks.py:312-314 unconditionally zeroes damage_mod for non-TWF off-hand attacks with no branch preserving a negative ability_mod, contradicting the SRD 5.2 Light property text quoted ('unless that modifier is negative'). Correctly scoped as minor since it only affects unusual low-Strength/Dexterity off-hand attackers.

### ACT-19 — Help action never grants advantage on ability checks — only attack rolls consume the helped flag

**Severity:** minor · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/_checks.py:141`

The Help action sets turn_state_for(target).helped = True and the flavor text promises 'advantage on their next roll', but the only consumer of the helped flag is _advantage_state in _attacks.py (attack rolls). _roll_check_impl never receives or consults CombatStateData/TurnState, so a Help action aimed at assisting an ally's ability check (the 2024 Help action's primary mode: 'Assist an Ability Check') has no effect on any subsequent roll_check. Combined with the begin_turn wipe, Help currently affects nothing in a normal turn sequence.

**2024 rule (SRD 5.2):** PHB 2024 Help action: choose 'Assist an Ability Check' (ally has Advantage on the next check with the chosen skill/tool before the start of your next turn) or 'Assist an Attack Roll'.

**Evidence:**

```
grep -rn 'helped' src/ → set in _actions.py:174, consumed only in _attacks.py:97-98; _roll_check_impl signature (_checks.py:85-91) takes no combat/turn state and its advantage inputs come solely from the caller and conditions.
```

**Verification:** Confirmed: TurnState.helped is set by the Help action (_actions.py:174) but the only consumer is _advantage_state in _attacks.py:96-98 (attack rolls). _roll_check_impl / DnD55eEngine.roll_check (_checks.py:85-91, 109-116) take an explicit advantage: bool from the caller and never look at CombatStateData/TurnState, so a Help action assisting an ability check (the PHB 2024 'Assist an Ability Check' mode) has no automatic mechanical effect in the engine.

### ACT-20 — Initiative ignores the exhaustion d20 penalty (char.d20_modifier)

**Severity:** minor · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/engine.py:103`

roll_initiative returns raw d20 + DEX modifier only. In 2024, initiative is a Dexterity check — a D20 Test — so the exhaustion penalty (−2 × level, exposed on the sheet as char.d20_modifier and applied to every other check, save, attack, passive score, and death save in this engine) must apply. An exhausted creature rolls initiative unpenalized (a level-3-exhausted, DEX 10 character with forced d20=10 gets 10 instead of 4). Check-disadvantage conditions like Poisoned are likewise not applied to initiative.

**2024 rule (SRD 5.2):** SRD 5.2: 'Initiative... a Dexterity check'; Exhaustion condition: 'D20 Tests Affected: The creature subtracts 2 from D20 Tests for each of its Exhaustion levels' (D20 Tests = ability checks, attack rolls, saving throws; initiative is an ability check).

**Evidence:**

```
engine.py:102-103: `raw = _roll_initiative_impl(char); return raw + char.ability_scores.modifier(Ability.DEXTERITY)` — no `+ char.d20_modifier`, unlike checks (_checks.py:138), saves (_saves.py:60), attacks (_attacks.py:255), passive scores (_checks.py:65), and death saves (_death.py:42). Executed repro: exhaustion_level=3 (d20_modifier == −6), DEX 10, forced d20=10 -> engine.roll_initiative(char) == 10; should be 4.
```

**Verification:** Confirmed by direct repro: engine.py:102-103 computes raw + DEX mod only, omitting char.d20_modifier that every sibling roll (_checks.py:65/138, _saves.py:60, _attacks.py:255, _death.py:42) applies. SRD 5.2 explicitly defines initiative as a Dexterity check (a D20 Test), so exhaustion's -2/level and check-disadvantage conditions (Poisoned/Frightened, per _CHECK_DISADVANTAGE_CONDITIONS in _checks.py) should apply but don't. Repro: exhaustion_level=3, DEX 10, forced d20=10 -> roll_initiative returns 10 instead of 4.

---

## Spells & Spellcasting

### SPL-01 — Revivify / Raise Dead / True Resurrection can never revive a dead target

**Severity:** critical · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/_damage.py:126`

The revival spells are modeled as healing_flat=1, but _apply_healing_impl starts with 'if target.is_dead or amount <= 0: return target', so healing a dead creature is a no-op. cast_spell still consumes the level-3 slot, returns success=True, records outcome.healing=1, and emits 'Restores 1 hit points' flavor while the target stays dead at 0 HP. The revival feature is unreachable, and the result actively misreports what happened.

**2024 rule (SRD 5.2):** SRD 5.2 Revivify: 'You touch a creature that has died within the last minute. That creature revives with 1 Hit Point.'

**Evidence:**

```
Executed repro: corpse.death_saves.is_dead=True; cast_spell(cleric, get_spell('revivify'), ...) -> 'Revivify success: True reported healing: 1 target hp: 0 still dead: True; flavor: c casts Revivify. Restores 1 hit points.'
```

**Verification:** Live repro confirms: casting Revivify on a corpse with death_saves.is_dead=True returns success=True, flavor 'Restores 1 hit points', but target.hp_current stays 0 and still_dead=True, because _apply_healing_impl (_damage.py:126) short-circuits on `target.is_dead`. This makes all revival spells (Revivify, Raise Dead, True Resurrection) completely non-functional while misreporting success — critical severity is well earned since a core spell category silently does nothing while claiming success.

### SPL-02 — Spell damage never triggers a concentration save on the target

**Severity:** critical · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/_spell_resolution.py:163`

cast_spell applies damage via _apply_damage_impl directly (lines 162-167) and never calls _concentration_check; the concentration-save-on-damage subsystem exists (_concentration_check in _attacks.py, concentration_save_dc in _damage.py) but is only invoked from the weapon-attack path (_attacks.py:293, 323), and the public DnD55eEngine.apply_damage also never checks concentration. So a Fireball (or any damaging spell) hitting a creature concentrating on Bless/Hold Person/Haste never forces the CON save and never breaks concentration (unless the target drops to 0 HP). The parity spec (docs/phb-parity-spec.md:104) claims 'Concentration (single effect, CON save on damage)' is fully implemented.

**2024 rule (SRD 5.2):** SRD 5.2 'Concentration': whenever you take damage while concentrating on a spell, you must succeed on a Constitution saving throw (DC 10 or half the damage taken, whichever is higher) or the concentration ends — regardless of the damage source.

**Evidence:**

```
grep -rn '_concentration_check' src/game_engine → only _attacks.py:160 (def), 293, 323; no hits in _spell_resolution.py, _damage.py, or engine.py. _spell_resolution.py:162-167: `if damage > 0 and spell.damage_type is not None: _apply_damage_impl(target, damage, spell.damage_type)` with no follow-up. Executed repro: target with concentrating_on='Haste' hit by Fireball for 33 damage (failed DEX save mocked) -> hp 17, still concentrating on Haste, no concentration_save entry anywhere in the outcome.
```

**Verification:** Confirmed by direct read of _spell_resolution.py: cast_spell calls _apply_damage_impl directly (lines 163, 166) with no call to _concentration_check anywhere in the file or transitively from cast_spell. _concentration_check exists only in _attacks.py and is invoked solely from the weapon-attack path. The parity spec (docs/phb-parity-spec.md:104) explicitly marks 'Concentration (single effect, CON save on damage)' as fully implemented (checkmark), so this is a real, undocumented gap, not an out-of-scope item. Severity of critical is justified since this silently breaks a core defensive spellcasting mechanic for every damaging spell.

### SPL-03 — Spell casting_time is ignored by the action economy — bonus-action and reaction spells always consume the Action

**Severity:** major · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/_actions.py:133`

_resolve_action_impl only uses the bonus action for off-hand attacks; every other action type, including MAGIC, sets ts.action_used regardless of the spell's casting_time. SpellData.casting_time (BONUS_ACTION for Healing Word, Misty Step, Spiritual Weapon, Hex; REACTION for Shield, Counterspell, Feather Fall) is never consulted anywhere in the engine — cast_spell explicitly ignores action economy ('the caller's responsibility') and never touches TurnState, and TurnState.reaction_used is never set by anything spell-related. Casting Healing Word therefore consumes the character's Action (leaving the bonus action free), and reaction spells have no correct cast path at all, while the parity spec claims both 'casting time' and the action/bonus-action/reaction economy are fully implemented. CastingTime.REACTION/BONUS_ACTION are pure data, only ever assigned in data files.

**2024 rule (SRD 5.2):** SRD 5.2 'Casting Time': a spell with a casting time of 1 bonus action is cast using a Bonus Action, and a reaction spell is cast using a Reaction — neither uses the action; only 1-action spells use the Magic action.

**Evidence:**

```
_actions.py:122-138: `uses_bonus_action = (action.action_type is ActionType.ATTACK and ... is_offhand)` ... `else: ... ts.action_used = True` — MAGIC always falls into the action branch. grep -rn 'casting_time|CastingTime\.' over src/game_engine/rules, interface.py and core (excluding data/spells and the enum definition) returns zero hits. Executed repro: MAGIC action for a caster knowing Healing Word -> action_used=True, bonus_action_used=False.
```

**Verification:** Confirmed by reading _actions.py:122-138: uses_bonus_action is gated only on ActionType.ATTACK with is_offhand; every other action type including MAGIC falls into the else branch that unconditionally sets ts.action_used = True. A grep confirms casting_time/CastingTime are referenced nowhere outside data/spells and the enum definition. The parity spec claims full action-economy parity (✅) with no carve-out for bonus-action/reaction spells, so this is a genuine, undocumented defect.

### SPL-04 — No repeat-save/save-to-end mechanism: Hold Person paralyzes for a full minute with no escape

**Severity:** major · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/_conditions.py:71`

Many registry spells state 'repeating the save at the end of each of its turns' (Hold Person, Hold Monster, Blindness/Deafness, Confusion, Dominate Person, Sleep's second save), but condition expiry supports only fixed round counts: _tick_condition_durations_impl decrements condition_durations per turn, SpellData has no repeat_save field, and no engine hook exists for end-of-turn saves. duration_rounds('Concentration, up to 1 minute') = 10, so a target that fails one save against Hold Person is Paralyzed (auto-crit within 5 ft, auto-fail STR/DEX saves) for 10 full rounds with no chance to shake it off — a drastically wrong outcome for spells explicitly designed around repeat saves.

**2024 rule (SRD 5.2):** SRD 5.2 Hold Person (and similar): at the end of each of its turns the target repeats the saving throw, ending the effect on itself on a success.

**Evidence:**

```
_tick_condition_durations_impl (_conditions.py:71-94) only decrements integer durations; grep -rni 'repeat|save_to_end|save_ends' src/game_engine → matches only feat `repeatable` flags and spell description prose (level2.py:107,316, level4.py:231, level5.py:63,222). SpellData (_base.py) has no repeat-save field; _spell_resolution.py:184-185 stores conditions with a fixed rider_duration from duration_rounds().
```

**Verification:** Confirmed: _tick_condition_durations_impl (_conditions.py:71-94) only decrements a fixed integer count with no repeat-save hook; duration_rounds() maps 'Concentration, up to 1 minute' to a flat 10 rounds; SpellData has no repeat-save field. Hold Person's actual description text (level2.py:105-108) explicitly says 'repeating the save at the end of each of its turns,' which the engine has no mechanism to honor, so a single failed save produces a full 10-round paralysis lockout. This is a materially significant divergence from a heavily-used spell mechanic and is undocumented as future work anywhere in the repo.

### SPL-05 — Upcast math drops the flat modifier: Magic Missile upcasts to 4d4+3 instead of 4d4+4

**Severity:** major · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/_spell_resolution.py:56`

_roll_damage computes upcast extra dice as `upcast_per_slot.num_dice * upcast_levels`, discarding the upcast notation's flat modifier, and _scale_dice keeps only the base spell's modifier. Magic Missile (base 3d4+3, upcast 1d4+1 per slot) cast with a level-2 slot deals 4d4+3 instead of 4d4+4; a level-9 cast is short by 6 damage. Any spell whose per-slot upcast includes a flat modifier is affected, and SpellData has upcast_healing_flat_per_slot for healing but no upcast_damage_flat_per_slot, so the correct scaling cannot even be expressed in data.

**2024 rule (SRD 5.2):** SRD 5.2 'Magic Missile': each dart deals 1d4+1 Force damage; a higher-level slot adds one dart (1d4+1) per slot level above 1 — the +1 scales with the darts.

**Evidence:**

```
_spell_resolution.py:55-57: `extra_dice = upcast_per_slot.num_dice * upcast_levels` then `_scale_dice(dice, multiplier, extra_dice)`; spellcasting.py:172-177 `_scale_dice` keeps `mod` from the base dice only. Data: level1.py:38-39 `damage_dice=DiceNotation("3d4+3"), upcast_damage_per_slot=DiceNotation("1d4+1")`. _base.py:52-61 confirms no flat-damage-per-slot field exists. Executed repro: _scale_dice(mm.damage_dice, 1, 1) -> '4d4+3 (expected 4d4+4)'. tests/test_spellcasting.py::test_upcast_adds_dice only asserts the dice count.
```

**Verification:** Executed and reproduced exactly as claimed: _scale_dice(DiceNotation('3d4+3'), 1, 1) returns '4d4+3' instead of the expected '4d4+4' for a level-2 Magic Missile cast, because _roll_damage's extra_dice computation (upcast_per_slot.num_dice * upcast_levels) discards the upcast notation's flat modifier and _scale_dice only preserves the base dice's mod. SpellData confirmed to have no upcast_damage_flat_per_slot field (only upcast_healing_flat_per_slot exists), so this cannot even be expressed in data today.

### SPL-06 — 2024 'only one spell-slot spell per turn' rule is not enforced or even representable

**Severity:** major · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/_spell_resolution.py:104`

cast_spell consumes a slot via _consume_slot with no per-turn tracking, TurnState (types/sheets.py:205-220) has no field recording that a slot-expending spell was cast this turn, and _actions.py resolves MAGIC as a generic success without invoking the spellcasting module. A character can cast Healing Word (bonus action, level-1 slot) and Fireball (action, level-3 slot) on the same turn with no error, violating the 2024 replacement for the 2014 bonus-action-spell rule. cast_spell's docstring explicitly punts economy to the caller, but no engine artifact exists for the caller to enforce the slot-per-turn rule with. The parity spec claims full action-economy parity.

**2024 rule (SRD 5.2):** SRD 5.2 (2024) 'One Spell with a Spell Slot per Turn': on a turn, a creature can expend only one spell slot to cast a spell; a second leveled spell on the same turn is not allowed (cantrips are unrestricted).

**Evidence:**

```
_spell_resolution.py:104: `if not _consume_slot(caster, used_slot):` is the only gate on slot spending; TurnState fields are action_used/bonus_action_used/reaction_used/movement/attack flags only, with no spell-slot-this-turn flag; cast_spell never touches combat_state.turn_state_for(caster.id). grep 'spell_cast|leveled_spell|per_turn' over src/game_engine finds nothing; consecutive leveled casts in one turn both succeed.
```

**Verification:** Confirmed: TurnState (types/sheets.py:205-221) has fields for action_used/bonus_action_used/reaction_used/movement/attacks/dodging etc. but no flag tracking that a slot-consuming spell was cast this turn, and cast_spell in _spell_resolution.py never touches combat_state.turn_state_for(caster.id). This is a real, unenforceable 2024 rule with no engine artifact for a caller to implement it against, and it is not flagged as future work in the parity spec.

### SPL-07 — Breaking or replacing concentration never ends the spell's effects on targets

**Severity:** major · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/_spell_resolution.py:114`

Concentration is tracked as a bare string (CharacterSheet.concentrating_on). Starting a new concentration spell just overwrites the string (line 114), and concentration loss from damage (_attacks.py:175) or falling unconscious/dying (_damage.py:97/110) only sets concentrating_on = None. Conditions applied by the ended concentration spell (e.g. Hold Person's PARALYZED with a 10-round rider duration) remain on targets for the full duration_rounds; nothing links a target's conditions back to the caster's concentration or the spell. A cleric who loses concentration on Hold Person in round 1 leaves the enemy paralyzed for 9 more rounds. The spec claims 'Concentration (single effect...)' is done, but the 'effect ends when concentration ends' half is missing.

**2024 rule (SRD 5.2):** SRD 5.2 Concentration: when you lose concentration (or cast another concentration spell), the spell ends and its ongoing effects end with it.

**Evidence:**

```
grep 'concentrating_on' shows every write site: _spell_resolution.py:114 (overwrite), _attacks.py:174-175 and _damage.py:97/110 (set None). _spell_resolution.py:179-185 stores conditions/durations on the target with no back-reference to the caster or spell; no other code correlates them — conditions persist until _tick_condition_durations_impl expires them by round count.
```

**Verification:** Confirmed via grep across _spell_resolution.py, _attacks.py, and _damage.py: concentrating_on is a bare string, ended by simple overwrite/None-assignment with no back-reference to which targets/conditions the spell created. _spell_resolution.py:179-185 stores conditions with a fixed rider_duration and no link to the caster's concentration state, so losing concentration never removes conditions the spell applied. This is a genuine gap not mentioned as out-of-scope in phb-parity-spec.md (which only lists positional/mounted/crafting items as out of scope).

### SPL-08 — Spell attack rolls ignore all condition-based advantage/disadvantage and never deal critical damage

**Severity:** major · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/_spell_resolution.py:129`

The spell attack path checks only the target's Dodge state (roll_with_disadvantage when dodging). It never calls _advantage_state or consults CONDITION_EFFECTS: an attacker who is Blinded/Poisoned/Restrained/Prone/Invisible gets no disadvantage/advantage on spell attacks, and a target that is Paralyzed/Unconscious/Restrained/Stunned/Prone/Invisible grants no advantage/disadvantage and no auto-crit. A natural 20 merely hits (`outcome.hit = raw == 20 or ...`): damage dice are never doubled (_roll_damage has no critical parameter — a crit with Fire Bolt deals 1d10 instead of 2d10), and _apply_damage_impl is called without critical=True, so a crit on a dying target inflicts only one death-save failure instead of two. Weapon attacks handle all of this correctly (_attacks.py:258-271, 315-322), so conditions and crits only modify weapon attacks, not spell attacks like Fire Bolt and Guiding Bolt.

**2024 rule (SRD 5.2):** SRD 5.2: attack rolls (including spell attacks) are subject to condition-based advantage/disadvantage; a natural 20 is a critical hit that doubles damage dice; hits on a Paralyzed/Unconscious creature within 5 feet are critical hits; damage from a critical hit while at 0 HP causes two death-save failures.

**Evidence:**

```
_spell_resolution.py:129-146: `raw, _ = roll_dice(1, 20)` (or roll_with_disadvantage only if target_dodging) ... `outcome.hit = raw == 20 or (raw != 1 and total >= target.ac)` followed by `damage = _roll_damage(spell, spell.damage_dice, ...)` — raw == 20 never doubles dice, no CONDITION_EFFECTS lookup, and lines 162-167 call _apply_damage_impl with default critical=False. Executed repro: nat-20 Fire Bolt at caster level 5 rolled 2 dice (cantrip x2 scaling only, no crit doubling). Contrast _attacks.py:55-111, 267-271, 315-322.
```

**Verification:** Confirmed: the spell attack path in _spell_resolution.py:129-136 only branches on target_dodging for advantage/disadvantage, never calls _advantage_state or consults CONDITION_EFFECTS as _attacks.py does (lines 258-271). outcome.hit is set from raw==20 with no crit-doubling of damage dice in _roll_damage, and _apply_damage_impl is called without critical=True at line 163/166 (default critical=False per _damage.py signature). This is a real, materially significant divergence between weapon and spell attacks that is not documented as intentional.

### SPL-09 — Registry spells with no mechanical fields silently no-op when cast (Shield, Counterspell, Power Word Kill, Mage Armor, Bless, Banishment, ...)

**Severity:** major · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/data/spells/level1.py:106`

SpellData can only express attack/save + damage/healing + rider conditions. Spells whose effects fall outside that vocabulary are registered with no mechanical fields and cast_spell returns success while doing nothing: Shield (+5 AC reaction — no AC-buff mechanic anywhere), Mage Armor (AC 13+Dex), Bless/Bane/Guidance (d4 riders on d20 tests), Mirror Image, Haste, Power Word Kill (instant death at ≤100 HP), Dispel Magic. Worse, Counterspell (level3.py:72) and Banishment (level4.py:73) have save fields, so casting them rolls a real CON/CHA save against the target and then applies zero effect — a misleading half-resolution. All of these consume slots and report success=True.

**2024 rule (SRD 5.2):** SRD 5.2 spell effects: Shield grants +5 AC as a reaction; Counterspell (2024) forces a CON save or the triggering spell fails; Power Word Kill kills a creature with 100 HP or fewer.

**Evidence:**

```
Shield entry (level1.py:106-122) has no attack_roll/save/damage/healing/conditions fields; cast_spell consumes a level-1 slot, sets no state, returns success. Counterspell (level3.py:87) sets save=Ability.CONSTITUTION but has no effect fields, so the resolver rolls the save at _spell_resolution.py:142 and nothing happens either way. grep shows no AC-modifier, spell-negation, or hp-threshold-kill mechanic anywhere in rules/.
```

**Verification:** Verified directly: Shield (level1.py:106-122) has zero mechanical fields (no attack_roll/save/damage/healing/conditions), Counterspell (level3.py:72-88) and Banishment (level4.py:73-96) set `save` but no effect fields, and grep confirms no AC-buff, spell-negation, or HP-threshold-kill mechanic exists anywhere in rules/. cast_spell (_spell_resolution.py:204-211) unconditionally returns success=True and consumes the slot regardless. Existing tests (test_data_spells.py) only assert data-registry shape for these spells, never mechanical cast outcomes, so nothing masks the no-op behavior. Severity of major is appropriate given Shield/Counterspell/Power Word Kill are iconic, frequently-cast spells whose complete non-function is silent.

### SPL-10 — Sleep applies Unconscious immediately on the first failed save

**Severity:** major · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/data/spells/level1.py:142`

Sleep lists conditions_applied=[INCAPACITATED, UNCONSCIOUS], and cast_spell applies every listed condition on the initial failed save (_spell_resolution.py:179-185). Per the 2024 rules (and this entry's own description) the target is only Incapacitated on the first failed save and falls Unconscious only if it fails the repeated save at the end of its next turn. The engine skips the intermediate stage entirely — the schema has no staged-condition support — making a first-round Sleep grant Unconscious (auto-crit melee, auto-fail STR/DEX saves) a full round early, drastically overpowering a level-1 spell.

**2024 rule (SRD 5.2):** SRD 5.2 'Sleep' (2024): on a failed save the target has the Incapacitated condition until the end of its next turn, when it repeats the save; only on that second failed save does it have the Unconscious condition for the duration.

**Evidence:**

```
level1.py:141-142: `save=Ability.WISDOM, conditions_applied=[Condition.INCAPACITATED, Condition.UNCONSCIOUS]` combined with _spell_resolution.py:179-183 `if not saved and spell.conditions_applied: for condition in spell.conditions_applied: target.conditions.append(condition)`. Executed repro (forced failed save): 'Sleep failed save -> conditions: [incapacitated, unconscious]'.
```

**Verification:** Confirmed: level1.py:141-142 sets conditions_applied=[INCAPACITATED, UNCONSCIOUS] and _spell_resolution.py:179-183 appends every listed condition on any failed save with no staging mechanism. The spell's own description string documents the correct two-stage 2024 rule, directly contradicting the flat conditions_applied list, so this is a genuine, verifiable data/logic bug rather than a debatable rules interpretation.

### SPL-11 — Hex and Hunter's Mark deal immediate direct damage when cast

**Severity:** major · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/data/spells/level1.py:311`

Hex (level1.py:311) and Hunter's Mark (level1.py:330) encode their per-attack rider damage as damage_dice with no attack_roll and no save. cast_spell treats damage_dice with neither attack_roll nor save as auto-hit damage (the Magic Missile path), so merely casting Hex instantly deals 1d6 necrotic to the target, even though the spell itself deals no damage on cast — the 1d6 only applies when the caster later hits with an attack.

**2024 rule (SRD 5.2):** SRD 5.2 Hex: 'the target takes an extra 1d6 Necrotic damage whenever you hit it with an attack roll' — no damage on cast.

**Evidence:**

```
Executed repro: cast_spell(caster, get_spell('hex'), ...) -> 'Hex cast: target hp 45 damage dealt: 5' (target started at 50 HP). Same for Hunter's Mark: 'dmg 4 target hp 46'.
```

**Verification:** Live repro confirms: casting Hex (bonus-action rider spell, no attack_roll, no save, damage_dice=1d6) immediately deals damage to the target on cast (target hp 50->46), because _spell_resolution.py's damage path (lines 129-167) treats any damage_dice without attack_roll/save as auto-hit (the Magic Missile pattern). Per SRD 5.2, Hex/Hunter's Mark only deal their rider damage when the caster later hits with a separate attack roll, not on cast — this is a real and fairly severe mechanical error for two commonly-used spells.

### SPL-12 — Multi-beam/ray attack spells (Scorching Ray, Eldritch Blast) collapse into one all-or-nothing attack roll with wrong upcast math

**Severity:** major · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/data/spells/level2.py:85`

Scorching Ray is stored as a single 2d6 attack with upcast_damage_per_slot=2d6: cast at one target it deals one ray (2d6) instead of three rays (three attack rolls, 2d6 each), and if the caller enumerates one target entry per ray, upcasting adds +2d6 to EVERY ray (level-3 slot: 4 rays x 4d6 = 16d6 expected) instead of one extra 2d6 ray — no calling convention produces SRD-correct results. Eldritch Blast is likewise stored as a single 1d10 attack whose beams at levels 5/11/17 are modeled purely via the cantrip dice multiplier: one attack roll for 2d10/3d10/4d10 against one target. Per the rules (and these entries' own descriptions, 'each requiring its own attack roll'), each beam/ray is a separate attack roll with independently assignable targets. One miss zeroes all beams, one crit doubles all of them, and beams cannot be split across targets — materially different hit distribution, tactics, and Shield/AC interaction.

**2024 rule (SRD 5.2):** SRD 5.2 'Scorching Ray': three rays, a ranged spell attack for each, 2d6 Fire each; one additional ray per slot level above 2. 'Eldritch Blast': two beams at level 5, three at 11, four at 17; a separate attack roll for each beam, targets assignable per beam.

**Evidence:**

```
level2.py:82-85: `attack_roll=True, damage_type=DamageType.FIRE, damage_dice=DiceNotation("2d6"), upcast_damage_per_slot=DiceNotation("2d6")` with _spell_resolution.py:55-57 adding upcast dice to the per-target damage roll for every target. cantrips.py:54-56: Eldritch Blast `attack_roll=True, damage_dice=DiceNotation("1d10")` + _spell_resolution.py:53 `multiplier = cantrip_dice_multiplier(caster_level)`. _spell_resolution.py:129-139 performs exactly one roll_dice(1, 20) per target gating the whole damage roll; no per-beam loop exists anywhere.
```

**Verification:** Confirmed by reading _spell_resolution.py: the per-target loop (lines 118-187) performs exactly one roll_dice(1,20) attack roll per target_id with no per-beam/per-ray loop. Scorching Ray (level2.py:82-85) and Eldritch Blast (cantrips.py:54-56) are both stored as a single attack_roll spell with damage_dice and (for Scorching Ray) upcast_damage_per_slot, with no multi-attack representation. Both spells' own description text says each beam/ray 'requires its own attack roll,' confirming this is a real, material mismatch between documented intent and implementation.

### SPL-13 — Spiritual Weapon damage omits the spellcasting ability modifier

**Severity:** major · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/data/spells/level2.py:206`

Spiritual Weapon is registered with damage_dice=1d8 only. The resolver adds the spellcasting ability modifier to healing (_spell_resolution.py:172-173) but never to damage, and SpellData has no field for modifier-added damage — so the spell deals a flat 1d8 force instead of 1d8 + spellcasting modifier, typically 3-5 points low on every hit of a staple cleric spell (a large fraction of 1d8). (Concentration=True and +1d8 per slot level above 2 are correct per 2024.)

**2024 rule (SRD 5.2):** SRD 5.2 'Spiritual Weapon': on a hit, the target takes Force damage equal to 1d8 plus your spellcasting ability modifier.

**Evidence:**

```
level2.py:204-207: `attack_roll=True, damage_type=DamageType.FORCE, damage_dice=DiceNotation("1d8"), upcast_damage_per_slot=DiceNotation("1d8")` — no mechanism in SpellData or _roll_damage adds the caster's ability modifier to spell damage; _spell_resolution.py:146-148 rolls only spell.damage_dice, ability modifier added only in the healing branch (lines 172-173).
```

**Verification:** Confirmed: level2.py:204-207 Spiritual Weapon has only damage_dice=1d8 with no modifier-add mechanism, and _spell_resolution.py only adds caster.ability_scores.modifier(spellcasting_ability) in the healing branch (lines 172-174), never for damage (lines 162-167). The spell's own description text even states 'plus your spellcasting modifier,' confirming the data/resolver genuinely omit a mechanic the engine's own description claims to implement.

### SPL-14 — Blindness/Deafness applies both Blinded and Deafened instead of one of the caster's choice

**Severity:** major · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/data/spells/level2.py:321`

The registry entry lists conditions_applied=[BLINDED, DEAFENED] and the resolver applies every listed condition on a failed save, so a single failed CON save leaves the target both Blinded and Deafened. The spell imposes one condition of the caster's choice, not both; no choice mechanism exists in SpellData or the resolver.

**2024 rule (SRD 5.2):** SRD 5.2 'Blindness/Deafness': the target has the Blinded or Deafened condition (your choice) for the duration — one condition, not both.

**Evidence:**

```
level2.py:320-321: `save=Ability.CONSTITUTION, conditions_applied=[Condition.BLINDED, Condition.DEAFENED]`; _spell_resolution.py:180-183 appends every condition in the list on a failed save. Executed repro (forced failed save): 'B/D failed save -> conditions: [blinded, deafened]'.
```

**Verification:** Confirmed: level2.py:320-321 lists conditions_applied=[BLINDED, DEAFENED] and the same unconditional apply-all-conditions loop in _spell_resolution.py applies both on one failed save, while the entry's own description explicitly says 'blinded or deafened (your choice)'. No choice mechanism exists in SpellData, matching the finding precisely.

### SPL-15 — Pact slots merged into the shared multiclass pool let a short rest restore standard spell slots

**Severity:** major · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/spellcasting.py:146`

compute_spell_slots merges warlock pact slots into the same SpellSlotState as standard multiclass slots of equal level (existing.maximum += pact_slot.maximum). SpellSlotState carries no pact/standard distinction, so short_rest — which restores pact slots by setting the merged slot's remaining to its full maximum (resting.py:78-84, finding the slot by slot_level alone) — also restores every standard slot of that level. Example: Warlock 5/Wizard 9-10 has 3 standard 3rd-level slots + 2 pact slots merged into one maximum-5 pool; after spending all 5, a short rest restores all 5 instead of only the 2 pact slots.

**2024 rule (SRD 5.2):** SRD 5.2 'Pact Magic' / 'Multiclass Spellcaster': Pact Magic slots are regained on a short rest, but Spellcasting-feature slots return only on a long rest; the two pools are tracked separately.

**Evidence:**

```
spellcasting.py:141-147 merges pact into the standard list (`existing.maximum += pact_slot.maximum`); SpellSlotState has no is_pact flag; resting.py:78-84: `for pact_slot in pact_slots_for_level(warlock_levels): slot = next((s for s in char.spell_slots if s.slot_level == pact_slot.slot_level), None); ... slot.remaining = slot.maximum`. Executed repro: Wizard10/Warlock5 -> merged L3 slots max: 5; set remaining=0; short_rest -> L3 remaining: 5 (pact-only restore should be 2).
```

**Verification:** Verified by direct execution: Wizard10/Warlock5 produces one merged level-3 SpellSlotState with maximum=5 (3 standard + 2 pact); after zeroing remaining and calling short_rest, remaining becomes 5 instead of the 2 pact slots the 2024 rules would restore. SpellSlotState has no pact/standard distinction anywhere in the codebase, confirming the pools are structurally unseparated. Major severity is justified — this breaks long-rest resource scarcity for a common multiclass build.

### SPL-16 — Concentration save DC missing the 2024 maximum of 30

**Severity:** minor · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/_damage.py:147`

concentration_save_dc returns max(10, damage // 2) with no upper bound. The 2024 rules cap the Constitution save DC to maintain concentration at 30, so a single hit of 62+ damage (dragon breath, Meteor Swarm, Disintegrate) produces DCs of 31+ that the 2024 rules disallow, making the save mathematically harder than allowed.

**2024 rule (SRD 5.2):** SRD 5.2 'Concentration': the DC equals 10 or half the damage taken (round down), whichever number is greater, up to a maximum DC of 30 (the cap is a 2024 addition).

**Evidence:**

```
_damage.py:145-147: `def concentration_save_dc(damage: int) -> int: return max(10, damage // 2)` — no min(30, ...) clamp.
```

**Verification:** Confirmed at _damage.py:145-147: `return max(10, damage // 2)` with no upper clamp. The 2024 rules add a DC cap of 30 for the concentration save that did not exist in 2014; this engine targets 2024/SRD 5.2 per CLAUDE.md and the parity spec, so the missing cap is a real, if narrow (needs 62+ damage), defect.

### SPL-17 — Dual-damage spells never upcast their secondary damage pool

**Severity:** minor · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/_spell_resolution.py:150`

cast_spell passes upcast_per_slot=None when rolling secondary_damage_dice, and SpellData has no secondary upcast field. Flame Strike upcast with a level-6 slot adds 1d6 fire but no radiant, while the 2024 rule increases both the Fire and the Radiant damage by 1d6 per slot level above 5.

**2024 rule (SRD 5.2):** SRD 5.2 'Flame Strike' (Using a Higher-Level Spell Slot): the Fire damage and the Radiant damage each increase by 1d6 for each spell slot level above 5.

**Evidence:**

```
_spell_resolution.py:149-150: `secondary = _roll_damage(spell, spell.secondary_damage_dice, None, caster.level, 0)` (upcast arg hard-coded None, upcast_levels hard-coded 0); level5.py:112-116 defines Flame Strike with 5d6 fire + 5d6 radiant and only upcast_damage_per_slot=1d6 on the primary.
```

**Verification:** Confirmed: _spell_resolution.py:150 hard-codes `_roll_damage(spell, spell.secondary_damage_dice, None, caster.level, 0)`, and SpellData has no secondary-upcast field. Flame Strike (level5.py:95-119) has secondary_damage_dice=5d6 radiant but only a single upcast_damage_per_slot=1d6 applied to the primary Fire pool. This is a real, narrower-impact defect (affects only dual-damage-pool spells); minor severity as stated is reasonable given the limited blast radius relative to findings like 0/1/2/3.

### SPL-18 — Aid cannot raise hit point maximum, so it does nothing at full HP

**Severity:** minor · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/data/spells/level2.py:161`

Aid is encoded as healing_flat=5, but the spell increases both current AND maximum HP by 5 for 8 hours. _apply_healing_impl caps at hp_max (target.hp_current = min(target.hp_max, ...)), so casting Aid on an uninjured ally has zero effect, and on an injured ally it is just 5 points of ordinary healing that can later be lost below where the spell should guarantee.

**2024 rule (SRD 5.2):** SRD 5.2 Aid: each target's Hit Point maximum and current Hit Points increase by 5 for the duration.

**Evidence:**

```
level2.py:161-162 healing_flat=5/upcast_healing_flat_per_slot=5; _damage.py:130 'target.hp_current = min(target.hp_max, target.hp_current + amount)' — hp_max is never modified anywhere in the spell path.
```

**Verification:** Verified precisely: Aid (level2.py:139-163) is encoded with healing_flat=5/upcast_healing_flat_per_slot=5 and no hp_max modification, while hp_max is a genuine mutable CharacterSheet field elsewhere (progression.py:167 increments it on level-up). _apply_healing_impl (_damage.py:130) does 'target.hp_current = min(target.hp_max, ...)', confirming Aid on an uninjured target truly has zero effect and on an injured target is indistinguishable from ordinary capped healing, contradicting the SRD 5.2 text that Aid raises both current and maximum HP for 8 hours.

### SPL-19 — Ice Storm uses 2014 dice (2d8 bludgeoning, +1d8 upcast) instead of 2024 (2d10, +1d10)

**Severity:** minor · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/data/spells/level4.py:40`

The registry gives Ice Storm damage_dice=2d8 bludgeoning with upcast_damage_per_slot=1d8. The 2024 version deals 2d10 Bludgeoning plus 4d6 Cold, and higher-level slots increase the Bludgeoning damage by 1d10 per level above 4. The engine targets 2024/SRD 5.2, so this is stale 2014 data.

**2024 rule (SRD 5.2):** SRD 5.2 'Ice Storm': a creature takes 2d10 Bludgeoning damage and 4d6 Cold damage on a failed save; Using a Higher-Level Spell Slot: the Bludgeoning damage increases by 1d10 for each spell slot level above 4.

**Evidence:**

```
level4.py:37-43: `save=Ability.DEXTERITY, half_damage_on_save=True, damage_type=DamageType.BLUDGEONING, damage_dice=DiceNotation("2d8"), secondary_damage_type=DamageType.COLD, secondary_damage_dice=DiceNotation("4d6"), upcast_damage_per_slot=DiceNotation("1d8")`.
```

**Verification:** Code confirmed at level4.py:40-43: damage_dice=2d8, upcast_damage_per_slot=1d8. The 2024 SRD 5.2/PHB Ice Storm deals 2d10 Bludgeoning (a well-documented dice-size increase from the 2014 2d8), with +1d10 per slot level above 4 on upcast. This is stale 2014 data as claimed; minor severity is appropriate since it's a single-spell numeric fix.

### SPL-20 — Power Word Stun stuns targets above the 150-HP threshold

**Severity:** minor · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/data/spells/level8.py:72`

Power Word Stun has no save and conditions_applied=[STUNNED]; cast_spell applies listed conditions whenever the target hasn't succeeded on a save, so the spell unconditionally stuns any target regardless of current hit points. The rule only affects a creature with 150 hit points or fewer, and target.hp_current is available to check.

**2024 rule (SRD 5.2):** SRD 5.2 'Power Word Stun': if the target has 150 hit points or fewer, it has the Stunned condition; otherwise the spell has a lesser/no stun effect.

**Evidence:**

```
level8.py:72: `conditions_applied=[Condition.STUNNED]` with no save and no HP gate; _spell_resolution.py:179-183 applies the condition to every target since `saved` is always False when spell.save is None.
```

**Verification:** Confirmed level8.py:51-73: Power Word Stun has save=None (default) and conditions_applied=[STUNNED] with no HP check anywhere in _spell_resolution.py or spellcasting.py. Since `save is None` means the code never sets save_success, `saved` is always False, so STUNNED applies unconditionally regardless of the SRD's 150-HP threshold.

### SPL-21 — Mass Heal restores 700 HP to each target instead of 700 divided among targets

**Severity:** minor · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/data/spells/level9.py:116`

Mass Heal is stored as healing_flat=700, and cast_spell applies the full healing amount to every entry in target_ids. Casting on six creatures restores up to 4200 HP total instead of 700 divided among them as the caster chooses.

**2024 rule (SRD 5.2):** SRD 5.2 'Mass Heal': you restore up to 700 hit points, divided as you choose among any number of creatures you can see within range.

**Evidence:**

```
level9.py:116: `healing_flat=700` with _spell_resolution.py:169-177 applying `healing += spell.healing_flat ...; _apply_healing_impl(target, max(0, healing))` inside the per-target loop.
```

**Verification:** Confirmed level9.py:116 `healing_flat=700` and _spell_resolution.py:169-177 apply spell.healing_flat to every target in the per-target loop with no division logic anywhere in the module. Matches the SRD 5.2 Mass Heal text requiring the 700 to be divided among targets as the caster chooses.

### SPL-22 — compute_spell_slots caster_types override is unusable — ClassLevelEntry is unhashable

**Severity:** minor · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/spellcasting.py:130`

compute_spell_slots accepts caster_types: dict[ClassLevelEntry, SpellcasterType], but ClassLevelEntry is a plain mutable @dataclass (eq=True, no frozen/eq-hash), so it cannot be a dict key. Any caller trying to build the override dict gets 'TypeError: unhashable type', making the parameter a dead feature; the 'entry in caster_types' lookup at line 130 is unreachable with a real dict.

**2024 rule (SRD 5.2):** n/a — logic bug

**Evidence:**

```
Executed repro: {ClassLevelEntry(CharacterClass.WIZARD, 5): SpellcasterType.FULL} -> "TypeError: cannot use 'game_engine.types.character_state.ClassLevelEntry' as a dict key (unhashable type: 'ClassLevelEntry')". grep shows no caller ever passes caster_types.
```

**Verification:** Confirmed via direct execution: `{ClassLevelEntry(...): SpellcasterType.FULL}` raises TypeError (unhashable type) because ClassLevelEntry is a plain @dataclass with default eq=True/frozen=False, which sets __hash__=None. grep confirms no caller in src/ or tests/ ever passes caster_types, so the parameter and the `entry in caster_types` branch at spellcasting.py:130 are dead/unusable code. Minor severity is appropriate since it doesn't break any exercised path, just a latent unusable API surface.

### SPL-23 — duration_rounds silently returns None for long durations, making rider conditions permanent

**Severity:** minor · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/spellcasting.py:180`

duration_rounds only recognizes '1 round', '1 minute', '10 minutes' and '1 hour'. Spells with '8 hours', '24 hours', or other durations get rider_duration=None, and _spell_resolution.py:184-185 then stores no duration for applied conditions, so they never expire via tick_condition_durations. Any long-duration condition spell silently applies a permanent condition. Also 'Concentration, up to 10 minutes' durations map to 100 rounds only because of substring luck; the helper string-matches a field that could have been a typed enum per the repo's own no-raw-strings standard.

**2024 rule (SRD 5.2):** SRD 5.2: spell effects end when their duration expires.

**Evidence:**

```
spellcasting.py:180-191: returns None for any duration not in the four hardcoded substrings. _spell_resolution.py:184-185 only writes target.condition_durations when rider_duration is not None, so None-duration conditions persist indefinitely (only removable via explicit remove_condition).
```

**Verification:** duration_rounds does return None for '8 hours' and 'Instantaneous' strings, confirming the parsing gap is real and the substring-based design (not a typed enum) is a legitimate style violation of the repo's no-raw-strings standard. However, materiality is weaker than claimed: scanning the actual SPELLS registry shows no spell that both has an '8/24 hour' duration AND sets conditions_applied (Mage Armor and Aid, the only two 8-hour spells, apply no conditions), so the 'silently permanent rider conditions' failure mode described does not currently manifest with real registry data — it's a latent/future-proofing bug rather than an active one today. The 'Concentration, up to 10 minutes' 'substring luck' claim is also slightly inaccurate: 'up to 10 minutes' correctly matches '10 minutes' before '1 minute' would even apply (since '1 minute' is not a substring of '10 minutes'), so there's no actual collision bug there, just fragile string design. Already scoped correctly as minor since it's a real but not currently-triggered defect.

### SPL-24 — SpellComponent, SpellRangeType, AreaShape, SpellSchool and range/area/material fields are never consumed by any rule logic

**Severity:** minor · **Location:** `game-engine/src/game_engine/types/enums/_core.py:202`

Every SpellData entry carries components, material, range_type/range_ft, area/area_size_ft and school, and the parity spec marks 'Components (V/S/M), casting time, range, areas of effect' as done. Grep proves none of these enums or fields are read anywhere outside the data registry and enum definitions: no range validation on cast, no area-based target derivation (target_ids are caller-supplied), no component gating, no school-keyed rule. Range/area non-consumption is partially excused by the declared theater-of-mind scope, but components and school have no consumer at all, making them dead data.

**2024 rule (SRD 5.2):** SRD 5.2: spells require their V/S/M components to cast; range limits legal targets; area determines affected creatures.

**Evidence:**

```
grep -rn 'components|SpellComponent|range_ft|range_type|SpellRangeType|AreaShape|SpellSchool|material' over rules/dnd_5_5e/{_spell_resolution.py,spellcasting.py,_actions.py,engine.py} and interface.py returns zero hits; grep -rn 'SpellRangeType\.|AreaShape\.' outside data/spells and enums also returns nothing. cast_spell (_spell_resolution.py:61) accepts arbitrary target_ids with no range/area/component checks.
```

**Verification:** Reproduced the grep exactly: components/range_ft/range_type/SpellRangeType/AreaShape/SpellSchool/material have zero hits in _spell_resolution.py, spellcasting.py, _actions.py, engine.py, or any interface.py, and SpellRangeType./AreaShape. usage outside data/spells and enums also returns nothing. cast_spell accepts arbitrary target_ids with no range/area/component gating, confirming components and school are genuinely dead data with no consumer at all, distinct from the range/area gap which the finding itself concedes is partially excused by the declared theater-of-mind scope.

---

## Equipment

### EQP-01 — Weapon registry (WeaponData/get_weapon) is never consumed by attack resolution — masteries, proficiency, and weapon stats can never fire in real play

**Severity:** critical · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/data/weapons.py:529`

The parity spec claims 'Weapon masteries ... data.items + _attacks' is done, but the two halves are never connected. No code in game-engine constructs an AttackDetails from a WeaponData: get_weapon/WeaponData are imported only by data/__init__.py (re-export). Attack resolution trusts a caller-populated AttackDetails whose mastery defaults to None. The only real caller, dm-api combat_utils.build_attack_details (combat_utils.py:255-264), copies just the five AttackDetailsRequest fields (weapon_name/damage_dice/damage_type/attack_ability/is_ranged) and never calls get_weapon — so in the actual game pipeline details.mastery is always None (the engine's entire weapon-mastery branch — Topple/Sap/Vex/Graze/etc. — is dead code even though character creation lets players pick masteries and stores them on the sheet), properties is always empty, proficient is always True (a wizard attacking with a greatsword still adds proficiency bonus), and is_offhand/long_range/target_cover/unarmed_option can never be set. The entire 38-weapon table (dice, types, masteries, ranges, finesse/versatile data) is decorative at combat time; masteries only work in unit tests that hand-craft AttackDetails.

**2024 rule (SRD 5.2):** SRD 5.2 / PHB 2024 Weapon Mastery: a character with a weapon's mastery property unlocked applies Cleave/Graze/Nick/Push/Sap/Slow/Topple/Vex on attacks with that weapon; the weapon table defines each weapon's damage, properties, and mastery; proficiency bonus applies only to weapons you have proficiency with.

**Evidence:**

```
grep -rn 'get_weapon|WeaponData' src/ excluding data/weapons.py returns only data/__init__.py re-exports and tests; no attack_details_from/to_attack_details bridge exists in src/ or tests/. dm-api/src/dm_api/api/combat_utils.py:255-264 constructs AttackDetails with only 5 fields (mastery omitted → None); dm-api/src/dm_api/db/models/combat.py:85-89 AttackDetailsRequest has no mastery/properties/proficient fields; dm-api only uses WEAPONS to list mastery options in character_creation.py:135-143. AttackDetails.proficient defaults True (sheets.py:293) and is never derived from sheet.weapon_category_training.
```

**Verification:** Confirmed by direct inspection: dm-api combat_utils.py:255-265 build_attack_details only copies weapon_name/damage_dice/damage_type/attack_ability/is_ranged from the request, leaving mastery=None (default), properties=[] (default), proficient=True (default) always. get_weapon/WeaponData are re-exported from data/__init__.py but never called anywhere else in src/ or dm-api/src/, confirmed via grep. This makes the entire weapon-mastery attack-time branch and weapon-proficiency gating dead in the real pipeline, matching the finding precisely.

### EQP-02 — Armor stealth_disadvantage flag is never consumed — the Hide action ignores noisy armor

**Severity:** major · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/_actions.py:179`

ArmorData.stealth_disadvantage is set correctly for Padded, Scale Mail, Half Plate, and all heavy armor, but no code reads it. The Hide action calls _roll_check_impl(actor, Skill.STEALTH, _HIDE_DC) without passing disadvantage, and there is no path that could derive worn armor anyway (no equipped-armor concept on the sheet). A character in Plate Armor hides with a flat Stealth roll.

**2024 rule (SRD 5.2):** SRD 5.2 armor table: while wearing armor with the Stealth: Disadvantage note, the wearer has Disadvantage on Dexterity (Stealth) checks; the 2024 Hide action is a DC 15 Dexterity (Stealth) check.

**Evidence:**

```
grep -rn 'stealth_disadvantage' src/ returns only data/armor.py; _actions.py:179 rolls _roll_check_impl(actor, Skill.STEALTH, _HIDE_DC) with default advantage=False, disadvantage=False.
```

**Verification:** Confirmed: stealth_disadvantage only appears in data/armor.py; the Hide action (_actions.py:179) calls _roll_check_impl(actor, Skill.STEALTH, _HIDE_DC) with no disadvantage argument and there is no worn-armor concept to derive it from anyway. 2024 Hide is indeed a DC 15 Dex(Stealth) check per SRD 5.2, correctly cited.

### EQP-03 — Armor training and weapon proficiency have no in-play mechanical effect — stored on the sheet but never consulted

**Severity:** major · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/character_builder.py:228`

build_character detects that the class lacks training for the chosen armor category but merely appends a warning string and still grants the armor's full AC. Nothing anywhere in the engine applies the 2024 penalties for lacking armor training: Disadvantage on D20 Tests involving Strength or Dexterity (attacks in _attacks.py:_advantage_state, checks in _checks.py, and saves in _saves.py never consider worn armor) and the inability to cast spells (spellcasting.py has no such gate) — a wizard built with Plate Armor gets AC 18 with zero downside. On the weapon side, CharacterSheet stores armor_training, weapon_category_training, and weapon_training but no rule logic reads them: AttackDetails.proficient defaults to True and is caller-trusted, nothing cross-checks the weapon's WeaponCategory against the actor's training, and dm-api's build_attack_details never sets proficient, so every attacker always adds the proficiency bonus with every weapon.

**2024 rule (SRD 5.2):** SRD 5.2 / PHB 2024 'Armor Training': 'If you wear armor that you lack training with, you have Disadvantage on any D20 Test that involves Strength or Dexterity, and you can't cast spells.' Attack rolls add the proficiency bonus only if you have proficiency with the weapon.

**Evidence:**

```
character_builder.py:228-230 `if armor is not None and armor.armor_type not in class_data.armor_training: warnings.append(...)` followed unconditionally by `ac = compute_armor_class(armor, dex_mod, shield=shield)`. grep -rn 'weapon_category_training|armor_training|weapon_training' src/ excluding sheets.py/_sheet_serde/character_builder.py returns only the ClassData definitions (data, not consumption); _attacks.py:254 `prof_bonus = _calc_prof_bonus(actor.level) if details.proficient else 0` with proficient defaulting True (sheets.py:293); dm-api combat_utils.py:259 omits proficient.
```

**Verification:** Confirmed: character_builder.py:228-230 only appends a warning string for armor-training mismatch and still applies full AC via compute_armor_class; grep confirms armor_training/weapon_category_training/weapon_training are stored on the sheet but never read by _attacks.py, _checks.py, _saves.py, or spellcasting.py. AttackDetails.proficient defaults True (sheets.py:293) and dm-api's build_attack_details (combat_utils.py:259-265) never sets it, so proficiency/training gating is genuinely absent from the actual play pipeline.

### EQP-04 — Heavy armor Strength minimum never reduces speed — min_strength is dead data and worn-armor identity is never stored

**Severity:** major · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/character_builder.py:269`

ArmorData carries min_strength (Chain Mail 13, Splint 15, Plate 15) and the parity spec claims 'Full armor table + AC computation (dex caps, str minimums)' is implemented, but no code ever reads min_strength outside the data file and tests: build_character sets sheet.speed = species_data.speed unconditionally even when the chosen armor's Strength requirement is unmet, compute_armor_class ignores it, and CharacterSheet.effective_speed only accounts for exhaustion and conditions. Worse, build_character applies the armor's AC and then discards the armor — CharacterSheet has no worn-armor field — so the speed penalty (and stealth_disadvantage, see separate finding) are structurally unreachable, not just unimplemented. A STR 8-12 fighter or cleric built with Chain Mail/Plate keeps full 30-ft speed instead of losing 10 ft.

**2024 rule (SRD 5.2):** SRD 5.2 / PHB 2024 Armor table & 'Heavy Armor' — Str column: 'If the Armor table shows a Strength score in the Str column... your speed is reduced by 10 feet' while the wearer's Strength is below that score.

**Evidence:**

```
character_builder.py:269 `speed=species_data.speed,` with no adjustment; armor.py:19 `min_strength: int` referenced nowhere else in src/ (grep matches only data/armor.py and tests/test_items_data.py); compute_armor_class (armor.py:183-195) reads only dex_bonus/dex_cap/base_ac; effective_speed (sheets.py:160-164) has no armor term; sheet has no armor field (sheets.py:86-135); docs/phb-parity-spec.md:93 claims 'str minimums' done.
```

**Verification:** Confirmed: grep shows min_strength appears only in data/armor.py and tests/test_items_data.py (assertions on the raw field), never consumed in character_builder.py or sheets.py's effective_speed. build_character sets speed=species_data.speed unconditionally (character_builder.py:269) with no armor-derived adjustment, and CharacterSheet has no worn-armor field, so the STR-minimum speed penalty is structurally unreachable as described.

### EQP-05 — Starting equipment and gold are never applied to the built character's inventory or currency

**Severity:** major · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/character_builder.py:284`

The spec claims 'All 16 PHB backgrounds (abilities, skills, origin feat, equipment)' is done. BackgroundData.equipment (which includes gold entries like '8 gp') is populated for every background, but build_character never reads it: the constructed CharacterSheet gets tool_proficiencies from the background but inventory stays [] and currency stays Currency() (all zeros); equipment packs (PACKS) referenced by background equipment are never expanded into inventory items. On the dm-api side, build_player_character stores starting equipment (background equipment, armor, shield) only as a plain string list on the Character.equipment DB column while the engine sheet's inventory is persisted empty inside stats=sheet.to_dict(). Since exploration.is_encumbered sums item.weight_lb * quantity over sheet.inventory, encumbrance is always False for any built character regardless of what they carry, the GEAR/ARMOR/WEAPON weight data never reaches the sheet, and starting characters own nothing and have 0 gp.

**2024 rule (SRD 5.2):** PHB 2024 chapter 4 / SRD 5.2 backgrounds: each background grants starting equipment (or 50 gp), including gold pieces, added to the character at creation; SRD 5.2 carrying capacity: Strength score × 15 lb.

**Evidence:**

```
grep -rn '\.equipment' src/ excluding data/backgrounds.py returns nothing; build_character's CharacterSheet(...) call (character_builder.py:260-288) passes tool_proficiencies=[background_data.tool_proficiency] but no inventory= or currency=; backgrounds.py:34-40 shows equipment lists ending in gp entries. dm-api character_creation.py:190-194 builds `equipment = list(BACKGROUNDS[...].equipment)` + armor/shield names and passes it to Character(equipment=equipment) only; grep -rn inventory ../dm-api/src returns no matches; exploration.py:44-47 sums over the always-empty sheet.inventory.
```

**Verification:** Confirmed: BackgroundData.equipment (backgrounds.py) is populated per background but build_character's CharacterSheet(...) constructor call never passes inventory= or currency=, leaving both at their empty defaults; grep confirms no '.equipment' consumption outside data/backgrounds.py. dm-api's character_creation.py:191-211 stores equipment only as a separate string list on the Character DB row, not folded into sheet.inventory, so exploration.is_encumbered (which sums sheet.inventory) is always False regardless of gear carried.

### EQP-06 — Passing 'Shield' as body armor yields AC 2 — compute_armor_class treats the shield registry entry as base armor

**Severity:** major · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/data/armor.py:194`

The shield lives in the same ARMOR registry as body armor with base_ac=2 and dex_bonus=False. compute_armor_class has no guard for armor_type == ArmorCategory.SHIELD, so an ArmorData shield passed as the `armor` argument produces AC = base_ac = 2. build_character forwards any registry-resolvable armor_name, so armor_name='Shield' (a valid registry name, hence no 'unknown armor' warning) silently builds a character with AC 2 (or 4 with shield=True). The API build endpoint accepts armor_name as a free string (only the options listing filters shields out), so this is reachable from any client.

**2024 rule (SRD 5.2):** SRD 5.2: a shield grants +2 AC on top of worn armor or unarmored AC; it is not base armor.

**Evidence:**

```
Executed: build_character(..., armor_name='Shield', shield=True) -> sheet.ac == 4 with no armor-related warning; armor_name='Shield', shield=False -> sheet.ac == 2. compute_armor_class falls into the `else: ac = armor.base_ac` branch (armor.py:193-194) with base_ac=2 from the Shield entry (armor.py:162-172).
```

**Verification:** Reproduced directly: build_character(armor_name='Shield', shield=True) yields sheet.ac == 4 with no armor-related warning, confirming compute_armor_class's else-branch (armor.py:193-194) falls through to ac = armor.base_ac = 2 for the Shield registry entry since there is no ArmorCategory.SHIELD guard. character_creation.py:127 filters shields only from the armor-options listing, not from validation of the armor_name field itself, so this is reachable via the API as described.

### EQP-07 — InventoryItem.equipped is never read — no equip/unequip path recomputes AC or selects weapons

**Severity:** major · **Location:** `game-engine/src/game_engine/types/character_state.py:163`

InventoryItem carries an equipped flag that is serialized but consumed by zero code. There is no notion of currently-worn armor or wielded weapon anywhere in the engine: compute_armor_class's only consumer is the level-1 build_character, so AC is frozen at creation — donning/doffing armor, picking up a shield, or leveling never recomputes it; attacks never look at inventory to find the equipped weapon (the caller free-declares dice/type). Improvised-weapon and unarmed fallback logic based on what is actually held also cannot exist without this link.

**2024 rule (SRD 5.2):** SRD 5.2: AC is determined by the armor and shield you are wearing/wielding (don/doff to change); attacks are made with a weapon you are holding.

**Evidence:**

```
grep -rn '\.equipped|equipped=' src/ excluding character_state.py/_sheet_serde returns nothing; grep for compute_armor_class consumers returns only character_builder.py:230 and the data/__init__ re-export; _attacks.py never touches actor.inventory.
```

**Verification:** Confirmed: InventoryItem.equipped (character_state.py:165) is a stored/serialized field but grep for '.equipped'/'equipped=' outside character_state.py and its serde returns nothing; compute_armor_class's only caller is the level-1 build_character, and _attacks.py never touches actor.inventory, so there is no equip/unequip-driven AC or weapon-selection logic anywhere in the engine.

### EQP-08 — WeaponProperty enum and AttackDetails.properties have zero rule-logic consumers: Heavy, Loading, Ammunition, Versatile, Finesse, Reach, Thrown all unimplemented

**Severity:** major · **Location:** `game-engine/src/game_engine/types/sheets.py:291`

The spec claims 'Weapon properties (incl. range, ammunition)' are done. Every weapon lists properties and AttackDetails carries a properties: list[WeaponProperty] field, but no rule module ever reads either. Consequences: HEAVY never imposes disadvantage when STR/DEX < 13 (a STR 8 character swinging a Greatsword, or a DEX 10 character firing a Longbow, attacks with a straight roll — _advantage_state aggregates conditions, dodge, help, vex/sap, hidden, and long range only); AMMUNITION is never expended (no arrow/bolt decrement); LOADING never limits crossbows/muskets to one shot; VERSATILE's versatile_dice field on WeaponData is read by nothing (no two-handed toggle exists); FINESSE never validates/selects DEX vs STR (attack_ability is caller-trusted); REACH, THROWN, and SPECIAL trigger no logic. WeaponData.range_normal_ft/range_long_ft are likewise never compared to anything (long_range is a bare caller flag). The properties field is a silently ignored parameter on the engine's typed attack boundary.

**2024 rule (SRD 5.2):** SRD 5.2 weapon properties: Heavy (disadvantage if STR/DEX < 13), Ammunition (expend one piece per attack), Loading (one attack per action/bonus action/reaction), Versatile (larger die when two-handed), Finesse (choose STR or DEX), Thrown, Reach, Two-Handed.

**Evidence:**

```
grep -rn 'WeaponProperty\.' src/ excluding data/weapons.py returns nothing; grep -rni 'versatile|ammunition|loading' src/ outside the data modules returns nothing; grep -rn '\.properties' src ../dm-api/src matches only the weapon data module and the creation-options listing — _attacks.py and _actions.py never reference details.properties. _attacks.py:55-111 _advantage_state never inspects WeaponProperty.HEAVY; nothing consumes LOADING or AMMUNITION anywhere in src/.
```

**Verification:** Confirmed: AttackDetails.properties (sheets.py:170) is populated but grep confirms _attacks.py and _actions.py never read WeaponProperty values. _advantage_state (lines 55-111) aggregates conditions/dodge/help/vex/sap/hidden/long_range only, with no HEAVY/LOADING/AMMUNITION/VERSATILE/FINESSE handling anywhere in src/. The parity spec marks 'Weapon properties (incl. range, ammunition)' done at data.items only, not as a consumed rule, so the finding correctly identifies a real gap despite the spec's checkmark being data-only.

### EQP-09 — ToolData.ability is dead data — tool checks never use the governing ability or tool proficiency

**Severity:** minor · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/data/gear.py:28`

Every tool registers a governing ability (e.g. Thieves' Tools → DEX), and CharacterSheet stores tool_proficiencies, but no check path consumes either: _roll_check_impl accepts only Skill/Ability, the Utilize action resolves as a generic success ('detailed resolution happens at the orchestration layer'), and nothing maps a tool name to its ToolData.ability or adds proficiency bonus for a proficient tool user. The field is written and never read.

**2024 rule (SRD 5.2):** SRD 5.2 tools: a tool check is an ability check using the tool's associated ability, adding your proficiency bonus if you have proficiency with the tool.

**Evidence:**

```
grep -rn 'get_tool|ToolData' src/ excluding data/gear.py returns only data/__init__.py re-exports; grep 'tool_proficiencies' outside sheets/serde/builder returns nothing; _actions.py:189-193 resolves UTILIZE as _simple_result(action, True, ...) with no check.
```

**Verification:** Verified against _checks.py: _roll_check_impl only accepts Skill | Ability | str and resolves proficiency via char.is_proficient(Skill|Ability) — there is no path that maps a tool name to ToolData.ability or checks tool_proficiencies for a bonus. _actions.py:189-193 confirms UTILIZE resolves as a generic success with an explicit comment that detailed resolution happens at the orchestration layer. tool_proficiencies (sheets.py:131) is set during character build and serialized but never read by rules code, confirming dead data as claimed. This aligns with the SRD 5.2 rule cited and the spec's explicit deferral of downtime/tool-use resolution to the orchestration layer, so 'minor' severity is appropriate.

### EQP-10 — is_encumbered has no rule consumers — exceeding carrying capacity has no effect

**Severity:** minor · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/exploration.py:44`

carrying_capacity, push_drag_lift, and is_encumbered exist and are unit-tested, satisfying the data half of the spec's 'Carrying capacity / drag-lift-push' row, but no other engine code ever calls is_encumbered: effective_speed, checks, and travel pace never consult it, so a character carrying 10x their capacity moves and acts normally. The subsystem exists but nothing invokes it.

**2024 rule (SRD 5.2):** SRD 5.2: you can carry weight up to Strength x 15; while pushing/dragging weight above carrying capacity your Speed is reduced to 5 feet.

**Evidence:**

```
grep -rn 'is_encumbered|carrying_capacity|push_drag_lift' src/ tests/ excluding exploration.py matches only tests/test_resting_exploration.py (unit tests of the functions themselves); CharacterSheet.effective_speed (sheets.py:160) considers only conditions and exhaustion.
```

**Verification:** Confirmed: is_encumbered/carrying_capacity/push_drag_lift are defined and used only within exploration.py and its own unit tests (test_resting_exploration.py); effective_speed (sheets.py:160-164) only accounts for exhaustion and speed-zero conditions, with no encumbrance term. Correctly scoped as minor since the subsystem's math is implemented and tested, just unwired into any speed/action consumer.

### EQP-11 — Currency.total_gp is never consumed and no purchase/spend logic exists anywhere

**Severity:** minor · **Location:** `game-engine/src/game_engine/types/character_state.py:141`

The Currency dataclass with all five denominations exists (satisfying the spec's 'Coinage' data claim), but total_gp is referenced by no code, and there is no debit/credit/convert helper, no gear-purchase path linking GearData.cost_gp / WeaponData.cost_gp / ArmorData.cost_gp to a character's coin. All cost_gp fields across weapons/armor/gear/tools/packs are therefore dead data.

**2024 rule (SRD 5.2):** SRD 5.2 coinage: 100 cp = 10 sp = 2 ep = 1 gp = 1/10 pp; equipment is bought with coin at listed costs.

**Evidence:**

```
grep -rn 'total_gp|\.currency' src/ returns only _sheet_serde.py:109 (serialization); grep for cost_gp consumers outside the data modules returns nothing.
```

**Verification:** Verified: total_gp has no consumers besides definition, and grep across game-engine/src confirms no code reads Currency for spend/purchase logic — cost_gp fields on WeaponData/ArmorData/GearData/ToolData/PackData are indeed never linked to a character's coin balance. The parity spec (docs/phb-parity-spec.md:95) marks 'Coinage' complete as a data type, and line 161-162 explicitly places 'downtime resolution' (which purchasing falls under) at the orchestration layer rather than the engine — so this is a real but intentionally-scoped gap, matching the reported 'minor' severity.

---

## Effect Resolution (Damage, Death, Conditions, Rests)

### EFF-01 — Gaining Incapacitated (or Stunned/Paralyzed/Petrified/Unconscious) never breaks concentration

**Severity:** critical · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/_conditions.py:38`

Concentration is only cleared when a creature drops to 0 HP (_fall_unconscious in _damage.py:110) or dies instantly (_damage.py:97). Applying an incapacitating condition to a conscious concentrating caster — via engine.apply_condition (_conditions.py:38-42) or via a spell rider (_spell_resolution.py:179-185) — leaves `concentrating_on` intact. The registry ships spells that apply PARALYZED (level2.py:112, level5.py:68), STUNNED (level8.py:72), INCAPACITATED (level1.py:142, level3.py:275) and UNCONSCIOUS (level1.py:142), so a caster concentrating on a hostile spell who is held/stunned/slept keeps the spell running while paralyzed/stunned/unconscious. The 2024 rules state you lose concentration the moment you have the Incapacitated condition, and Paralyzed, Petrified, Stunned, and Unconscious all include Incapacitated.

**2024 rule (SRD 5.2):** SRD 5.2, Rules Glossary, 'Concentration': 'You lose Concentration on an effect ... [if] you have the Incapacitated condition or the Unconscious condition.' Also 'Incapacitated' condition: 'Concentration Broken. Your Concentration is broken.'

**Evidence:**

```
_conditions.py:35-44 — `if is_immune_to_condition(target, condition): return target` / `if condition not in target.conditions: target.conditions.append(condition)` ... returns without touching `target.concentrating_on`. Same in _spell_resolution.py:179-185. grep -n 'concentrating_on' across rules/: set to None only in _damage.py:97,110; set to spell name in _spell_resolution.py:114. Executed repro: char concentrating_on='bless', engine.apply_condition(char, Condition.STUNNED) -> conditions=[STUNNED], concentrating_on still 'bless'.
```

**Verification:** Confirmed by grep and execution: concentrating_on is cleared only in _damage.py:97 (instant death) and _damage.py:110 (_fall_unconscious at 0 HP) — never in _apply_condition_impl or the spell-rider condition path. Executed repro: applying STUNNED to a PC with concentrating_on='bless' leaves concentration intact, contradicting the 2024 rule that Incapacitated (and its supersets Paralyzed/Petrified/Stunned/Unconscious) breaks concentration. Severity of critical is justified given this affects core combat balance (held/stunned casters keep control spells running).

### EFF-02 — Charmed has zero mechanical effect anywhere in the engine

**Severity:** major · **Location:** `game-engine/src/game_engine/core/conditions.py:66`

CONDITION_EFFECTS[CHARMED] sets no mechanical fields (can_act=True, everything else default), and no rule module reads Condition.CHARMED: attack resolution never prevents the charmed creature from attacking or targeting its charmer (no charmer/source tracking exists), and checks never grant the charmer advantage on social ability checks. Registry spells apply it (charm person level1.py:382, dominate person level5.py:226, dominate monster level8.py:96, hypnotic pattern level3.py:275) — it is stored on the sheet and does nothing. The spec claims 'Conditions (all 15) + mechanical effects' are done.

**2024 rule (SRD 5.2):** SRD 5.2 Charmed: the charmed creature can't attack the charmer or target the charmer with damaging abilities or magical effects; the charmer has advantage on ability checks to interact socially with the creature.

**Evidence:**

```
grep -rn 'Condition.CHARMED' src/game_engine --include='*.py' (excluding data/) → only core/conditions.py:66 (the empty effect entry). Not referenced in _attacks.py, _checks.py, _saves.py, _actions.py, or _spell_resolution.py; target selection in _resolve_attack (lines 232-251) performs no charmer check.
```

**Verification:** Confirmed: CONDITION_EFFECTS[CHARMED] (conditions.py:66-73) sets only description/can_act=True with no attack_modifier, attack_against_modifier, or any charmer-tracking field, and grep confirms no rule module reads Condition.CHARMED outside the empty definition. _resolve_attack has no charmer/source tracking to block attacking the charmer, and _checks.py's only disadvantage set is {POISONED, FRIGHTENED} — no social-check advantage for the charmer. docs/phb-parity-spec.md:39 explicitly claims all 15 conditions have mechanical effects, so this is a real parity gap, not declared future work.

### EFF-03 — Exhaustion can never be gained through the engine; Condition.EXHAUSTION is a mechanical no-op

**Severity:** major · **Location:** `game-engine/src/game_engine/core/conditions.py:81`

All exhaustion mechanics read the integer CharacterSheet.exhaustion_level (d20_modifier = -2*level, effective_speed -5 ft/level, death at level 6, long-rest reduction). But nothing in the engine ever increments it: the only mutation is the decrement in resting.py:125-127. There is no gain_exhaustion API, and apply_condition(Condition.EXHAUSTION) just appends the enum to conditions once (duplicates skipped, so levels can never stack to 6) — CONDITION_EFFECTS[EXHAUSTION] is an empty effect and no rule module reads Condition.EXHAUSTION from the list, so a monster ability or effect that inflicts exhaustion through the engine's condition API imposes no d20 penalty and no speed reduction, contradicting the 2024 rule that each instance adds one cumulative level. Conversely long_rest decrements exhaustion_level but never removes the stale Condition.EXHAUSTION entry, and monster condition_immunities=[EXHAUSTION] can never be exercised.

**2024 rule (SRD 5.2):** SRD 5.2, 'Exhaustion' condition: 'This condition is cumulative. Each time you receive it, you gain 1 Exhaustion level... D20 Tests Affected: the roll is reduced by 2 times your Exhaustion level. Speed Reduced: your Speed is reduced by 5 times your Exhaustion level.' The creature dies at level 6; a long rest removes one level.

**Evidence:**

```
_conditions.py:38-39 — `if condition not in target.conditions: target.conditions.append(condition)` (no EXHAUSTION special-case, no exhaustion_level increment); core/conditions.py:81-87 — `Condition.EXHAUSTION: ConditionEffect(description=..., can_act=True)` carries zero mechanical fields; grep -rn 'exhaustion_level' src/game_engine/rules src/game_engine/core → only resting.py:125-126 mutates it (decrement). Executed repro: eng.apply_condition(c, Condition.EXHAUSTION) -> conditions=[EXHAUSTION] but exhaustion_level=0, d20_modifier=0, speed=30. Monster data monsters.py:156,392,598,920 declares exhaustion immunity.
```

**Verification:** Confirmed by code trace and execution: CONDITION_EFFECTS[EXHAUSTION] carries no mechanical fields, and _apply_condition_impl just appends the enum with no exhaustion_level increment; only resting.py:125-126 mutates exhaustion_level (decrement only). Executed repro: engine.apply_condition(c, EXHAUSTION) leaves exhaustion_level=0, d20_modifier=0, effective_speed=30 despite Condition.EXHAUSTION being in conditions — the parity spec (line 40) claims exhaustion is '✅' implemented via core.conditions/_saves/_attacks/_death, but there is no gain path through the condition API at all, so this is a real gap, not documented as future work.

### EFF-04 — Grappled (2024) missing attack disadvantage vs non-grappler, escape check, and end-on-grappler-incapacitated

**Severity:** major · **Location:** `game-engine/src/game_engine/core/conditions.py:97`

CONDITION_EFFECTS[GRAPPLED] sets only speed_zero=True (attack_modifier=None), and _advantage_state in _attacks.py applies no modifier for a grappled attacker, so a grappled creature attacks third parties with no disadvantage. The 2024 Grappled condition imposes Disadvantage on attack rolls against any target other than the grappler — impossible here because the engine stores no grappler/source identity for any condition (_resolve_unarmed_special appends Condition.GRAPPLED without recording the grappler). There is also no escape mechanic (the 2024 rule lets the grappled creature use an action to make a STR (Athletics) or DEX (Acrobatics) check against the grapple escape DC) and no automatic end when the grappler is incapacitated (the effect's own description text documents this rule but nothing implements it). This is a non-positional, purely relational effect, so it is not covered by the parity spec's positional-rules exclusion.

**2024 rule (SRD 5.2):** SRD 5.2, 'Grappled' condition: 'Speed 0. Your Speed is 0 and can't increase. / Attacks Affected. You have Disadvantage on attack rolls against any target other than the grappler.' Ends if the grappler has the Incapacitated condition; escapable via a STR (Athletics) or DEX (Acrobatics) check as an action.

**Evidence:**

```
core/conditions.py:97-106 — `Condition.GRAPPLED: ConditionEffect(..., can_act=True, speed_zero=True)` with no attack_modifier; _attacks.py:69-92 applies only `effect.attack_modifier`/`attack_against_modifier`, so a grappled attacker rolls normally against every target. grep -rn 'escape|grappler' src/game_engine/rules → no escape-check implementation; grapple application (_attacks.py:200-204) records no grappler id; no field on CharacterSheet or TurnState stores the grappler.
```

**Verification:** Confirmed: GRAPPLED's ConditionEffect has no attack_modifier and _advantage_state only reads attack_modifier/attack_against_modifier plus explicit PRONE handling, so a grappled attacker gets no disadvantage vs third parties. Grep confirms zero occurrences of 'grappler' or 'escape' logic anywhere in src/game_engine (only prose descriptions and monster ability text). This is not covered by the parity spec's positional exclusions (only grid/positioning, mounted/underwater combat, and crafting downtime are declared out of scope), so the missing escape mechanic, grappler-identity tracking, and attack-vs-third-party disadvantage are genuine in-scope gaps.

### EFF-05 — Petrified grants poison and psychic damage immunity instead of Poisoned-condition immunity

**Severity:** major · **Location:** `game-engine/src/game_engine/core/conditions.py:147`

The PETRIFIED ConditionEffect sets immunity_types=[DamageType.POISON, DamageType.PSYCHIC], and _apply_damage_impl (_damage.py:53-54) zeroes out any poison or psychic damage against a petrified creature. Neither the 2014 nor 2024 rules grant psychic damage immunity, and the 2024 rule grants immunity to the Poisoned CONDITION, not to poison damage. Per 2024 rules, poison and psychic damage against a petrified creature should be halved (Resistance to all damage, which is correctly implemented via damage_resistances_all), not negated, and applying the POISONED condition should be blocked — which the engine does not do (_apply_condition_impl consults only char.condition_immunities, which PETRIFIED never extends).

**2024 rule (SRD 5.2):** SRD 5.2, 'Petrified' condition: 'Resist Damage. You have Resistance to all damage. / Poison Immunity. You have Immunity to the Poisoned condition.' There is no poison- or psychic-damage immunity.

**Evidence:**

```
core/conditions.py:133-149 — `Condition.PETRIFIED: ConditionEffect(..., immunity_types=[DamageType.POISON, DamageType.PSYCHIC], damage_resistances_all=True)`; _damage.py:53-54 — `if damage_type in effect.immunity_types: return target` returns 0 damage. No code adds Poisoned-condition immunity while petrified: is_immune_to_condition (core/conditions.py:213/223) checks only char.condition_immunities.
```

**Verification:** Confirmed by code trace and execution: PETRIFIED sets immunity_types=[POISON, PSYCHIC] which _damage.py:53-54 turns into full damage negation (0 damage), not resistance. Executed repro shows a petrified target takes 0 net effect from 20 poison and 20 psychic damage (should be resistance/half, and even then damage_resistances_all already grants that resistance — the extra immunity_types entry is purely wrong). No code anywhere adds Poisoned-condition immunity while petrified, confirming the fix is misdirected (damage immunity instead of condition immunity).

### EFF-06 — Stunned sets speed to 0 (2014 rule); 2024 Stunned no longer prevents movement

**Severity:** major · **Location:** `game-engine/src/game_engine/core/conditions.py:189`

The STUNNED ConditionEffect has speed_zero=True and its description says the creature "can't move"; STUNNED is also in _SPEED_ZERO_CONDITIONS (types/enums/_core.py:146), so CharacterSheet.effective_speed returns 0 while stunned. The 2024 Stunned condition was deliberately changed: it grants Incapacitated, auto-failed STR/DEX saves, and advantage on attack rolls against the creature — but it does NOT set Speed to 0 or prevent movement. The engine implements the 2014 version, wrongly rooting stunned creatures in place (common with Stunning Strike and many monster abilities).

**2024 rule (SRD 5.2):** SRD 5.2, 'Stunned' condition: effects are only 'Incapacitated. / Saving Throws Affected: automatically fail Strength and Dexterity saving throws. / Attack Rolls Affected: attack rolls against you have Advantage.' No Speed 0 clause (unlike Paralyzed/Petrified/Unconscious, which retain 'Speed 0').

**Evidence:**

```
core/conditions.py:180-190 — `Condition.STUNNED: ConditionEffect(description=("A stunned creature is incapacitated, can't move, ..."), ..., speed_zero=True)`; types/enums/_core.py:140-149 — `_SPEED_ZERO_CONDITIONS = frozenset({... Condition.STUNNED, ...})` consumed by `CharacterSheet.effective_speed` (types/sheets.py:162-164).
```

**Verification:** Confirmed by code trace and execution: Condition.STUNNED has speed_zero=True in core/conditions.py:180-190 and is in _SPEED_ZERO_CONDITIONS (types/enums/_core.py), consumed by CharacterSheet.effective_speed. Executed repro shows effective_speed=0 while stunned. The 2024 SRD Stunned condition genuinely omits the Speed-0 clause present in Paralyzed/Petrified/Unconscious — this is the 2014 rule bleeding into a 2024-targeting engine, exactly the failure mode the task description warns about, and it was caught correctly here.

### EFF-07 — Concentration save uses pre-mitigation damage; immune targets take 0 damage but can still lose concentration

**Severity:** major · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/_attacks.py:323`

_resolve_attack calls _concentration_check(target, total_damage, log) with the raw rolled damage, not the effective damage after immunity/resistance computed inside _apply_damage_impl (which does not return the effective amount). A target immune to the damage type takes 0 damage yet is still forced to roll a CON save and can lose concentration; a resistant target's DC is computed from the unhalved damage (e.g. DC 11 for 22 raw / 11 taken instead of DC 10). Same defect on the graze path (line 293).

**2024 rule (SRD 5.2):** SRD 5.2 Concentration: a CON save is required only when you take damage, DC = max(10, half the damage taken).

**Evidence:**

```
Executed repro: fire-immune target concentrating on 'bless', apply_damage(22 FIRE) leaves HP unchanged, then _concentration_check as _resolve_attack does -> log {'concentration_save': {'dc': 11, ...}, 'concentration_broken': 'bless'}; resistant target (takes 11) gets DC 11 instead of 10.
```

**Verification:** Confirmed: _attacks.py:322-323 calls _apply_damage_impl (mutates target, returns nothing usable) then _concentration_check(target, total_damage, log) using the pre-mitigation total_damage, not any effective-damage figure. _damage.py never returns/exposes effective damage. _concentration_check (_attacks.py:160-175) only guards damage<=0 on the raw value, so an immune target (0 actual HP loss but positive raw damage) still rolls a CON save, and a resistant target's DC uses unhalved damage. Same bug repeats on the graze path at line 293. Matches SRD 5.2 concentration rule (DC = half damage *taken*).

### EFF-08 — Damage at 0 HP that equals or exceeds HP maximum does not kill instantly

**Severity:** major · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/_damage.py:70`

When a PC is already at 0 HP, _apply_damage_impl always converts damage into 1 death-save failure (2 on a crit), regardless of magnitude — it never compares effective_damage against target.hp_max. The 2024 rules say that if damage taken while at 0 HP equals or exceeds your Hit Point maximum, you die instantly. E.g. a dying PC with hp_max 20 hit by a 25-damage breath weapon should be dead outright; the engine records a single death-save failure instead. The hp_max instant-death check at line 92 is only reached when the target starts above 0 HP.

**2024 rule (SRD 5.2):** SRD 5.2 / PHB 2024, 'Death Saving Throws — Damage at 0 Hit Points': 'If you take damage while you have 0 Hit Points, you suffer a Death Saving Throw failure. If the damage is from a Critical Hit, you suffer two failures instead. If the damage equals or exceeds your Hit Point maximum, you die instantly.'

**Evidence:**

```
_damage.py:70-78 — `if target.hp_current <= 0: ... target.death_saves.failures += 2 if critical else 1; if target.death_saves.failures >= 3: target.death_saves.is_dead = True; return target` — no comparison against `target.hp_max`. Executed repro: char hp_max=10 dropped to 0, then eng.apply_damage(c, 100, FIRE) -> 'dead? False failures: 1' (should be instant death).
```

**Verification:** Confirmed by code trace and execution: the hp_current <= 0 branch in _damage.py:70-78 converts any damage into 1 (or 2 on crit) death-save failures with no comparison to hp_max, unlike the correctly-implemented instant-death check at line 92 for damage dropping a conscious creature to 0. Executed repro: PC at 0 HP with hp_max=10 takes 100 fire damage, ends with is_dead=False, failures=1, contradicting the 2024 instant-death-at-0-HP rule.

### EFF-09 — Death save counters not reset when character becomes stable via 3 successes

**Severity:** major · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/_death.py:63`

_roll_death_save_impl sets saves.is_stable = True on the third success but never clears the accumulated successes/failures, unlike _stabilize_impl (which resets both). A character who accrued 2 failures before rolling 3 successes remains 'stable' with failures=2; the next single point of damage (_apply_damage_impl 0-HP branch adds +1 failure) pushes failures to 3 and kills them outright, when the correct outcome is 1 failure and back to dying.

**2024 rule (SRD 5.2):** SRD 5.2 Death Saving Throws: the number of successes and failures resets to zero when you regain any hit points or become stable.

**Evidence:**

```
Executed repro: dying char rolls nat 1 (2 failures) then three 15s -> 'stable: True failures: 2 successes: 3'; then eng.apply_damage(c, 1, SLASHING) -> 'after 1 damage while stable -> dead? True failures: 3'. Compare _stabilize_impl (lines 91-93) which zeroes both counters.
```

**Verification:** Confirmed by direct read of _death.py:60-63: the is_stable branch sets saves.is_stable = True but never zeroes successes/failures, whereas _stabilize_impl (lines 91-93) explicitly resets both. _apply_damage_impl's 0-HP branch (_damage.py:70-78) adds to the un-reset failures counter and kills at >=3, exactly as described. This is a genuine and dangerous logic bug matching the SRD 5.2 rule that counters reset on becoming stable; major severity is appropriate.

### EFF-10 — Combat resolution paths bypass condition immunities entirely (spell riders, Topple, unarmed grapple/shove)

**Severity:** major · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/_spell_resolution.py:181`

is_immune_to_condition is only consulted inside _apply_condition_impl (the explicit engine.apply_condition API). Every in-combat path that actually inflicts conditions appends directly to target.conditions: spell riders (_spell_resolution.py:179-185 — a creature immune to Paralyzed is still paralyzed by Hold Person, a charm-immune monster is Charmed by Charm Person), the Topple weapon mastery (_attacks.py:140-142 — a PRONE-immune creature can be toppled), and unarmed grapple/shove (_attacks.py:202-204 — a Grappled-immune creature is grappled on a failed save). The direct appends also skip any future centralized handling (exhaustion, concentration breaking) in the condition module, even though monster data ships condition_immunities.

**2024 rule (SRD 5.2):** SRD 5.2: a creature with immunity to a condition is unaffected by effects that would impose that condition.

**Evidence:**

```
grep -rn 'is_immune_to_condition' src/game_engine → defined core/conditions.py:213, consumed only in _conditions.py:35. _spell_resolution.py:181 `target.conditions.append(condition)`, _attacks.py:141 `target.conditions.append(Condition.PRONE)`, _attacks.py:203 `target.conditions.append(condition)` — none check immunity. Executed repros: target with condition_immunities=[PARALYZED], forced failed save vs Hold Person -> conditions=[PARALYZED]; victim with condition_immunities=[GRAPPLED] grappled with forced failed save -> conditions=[GRAPPLED]. Monster data monsters.py:392,597,919 declares charm immunity that can never be honored.
```

**Verification:** Confirmed by code trace and execution: _apply_condition_impl (the only path checking is_immune_to_condition) is bypassed by direct target.conditions.append() calls in _spell_resolution.py:181-182, _attacks.py:141 (Topple), and _attacks.py:203 (grapple/shove). Executed repro confirms apply_condition correctly respects immunity while the direct-append paths never call is_immune_to_condition at all, so spell riders and mastery/unarmed conditions ignore condition_immunities declared on monster data.

### EFF-11 — ConditionEffect.can_act and speed_zero fields are never consumed (duplicate frozensets are the live source)

**Severity:** minor · **Location:** `game-engine/src/game_engine/core/conditions.py:41`

The ConditionEffect dataclass exposes `can_act` and `speed_zero`, and CONDITION_EFFECTS painstakingly sets them per condition — but nothing reads them. The live implementations are the parallel frozensets `_ACTION_BLOCKING_CONDITIONS` and `_SPEED_ZERO_CONDITIONS` in types/enums/_core.py:130-141, consumed by CharacterSheet.can_act / effective_speed (sheets.py:157,162). Two sources of truth for the same rule invite drift (e.g. adding a new speed-zero condition to CONDITION_EFFECTS alone would silently do nothing).

**2024 rule (SRD 5.2):** SRD 5.2 condition effects: Incapacitated family prevents actions; Grappled/Restrained/Paralyzed/Stunned/Unconscious/Petrified set speed to 0.

**Evidence:**

```
grep -rn 'effect.can_act|\.speed_zero' src/game_engine --include='*.py' → zero consumers (only field definitions/assignments in core/conditions.py). sheets.py:157 uses Condition.prevents_action and sheets.py:162 uses Condition.sets_speed_to_zero, both backed by the enums/_core.py frozensets, not CONDITION_EFFECTS.
```

**Verification:** Confirmed by direct read: ConditionEffect.can_act/speed_zero fields are defined and populated throughout CONDITION_EFFECTS but grep for '.can_act'/'.speed_zero' usage shows zero consumers of those specific fields; the actually-live logic is CharacterSheet.can_act/effective_speed (sheets.py:152-163) which call Condition.prevents_action/sets_speed_to_zero, backed by the separate _ACTION_BLOCKING_CONDITIONS/_SPEED_ZERO_CONDITIONS frozensets in enums/_core.py. This is a genuine duplicate-source-of-truth drift risk, correctly scoped as minor since both sets currently agree and no live bug results today.

### EFF-12 — Deafened has zero mechanical effect; Blinded/Deafened auto-fail of sight/hearing checks unmodeled

**Severity:** minor · **Location:** `game-engine/src/game_engine/core/conditions.py:74`

CONDITION_EFFECTS[DEAFENED] sets no mechanical fields and no rule module reads Condition.DEAFENED — the condition is pure storage. Its sole SRD effect (automatically fail ability checks that require hearing) has no hook: _roll_check_impl carries no sight/hearing-requirement parameter, so Blinded's 'automatically fails any ability check that requires sight' is likewise unenforceable (Blinded's attack adv/disadv IS wired). The registry applies DEAFENED via Blindness/Deafness (level2.py:321). Spec claims all 15 conditions' mechanical effects are done.

**2024 rule (SRD 5.2):** SRD 5.2 Deafened: automatically fails any ability check that requires hearing. Blinded: automatically fails any ability check that requires sight.

**Evidence:**

```
grep -rn 'Condition.DEAFENED' src/game_engine (excluding data/) → only core/conditions.py:74. _checks.py's only condition logic is _CHECK_DISADVANTAGE_CONDITIONS = {POISONED, FRIGHTENED} (line 16); no auto-fail path for checks exists (auto_fail exists only for saves in _saves.py:16-22).
```

**Verification:** Confirmed: CONDITION_EFFECTS[DEAFENED] (conditions.py:74-80) has no mechanical fields set, and grep shows Condition.DEAFENED referenced nowhere else in rule logic. _checks.py has no sight/hearing-requirement parameter or auto-fail path for checks (only auto_fail_saves exists in _saves.py, which is a different mechanic for saving throws, not ability checks). Blinded's auto-fail-on-sight-checks is likewise unenforced even though Blinded's attack roll adv/disadv works. This is a real, narrow gap; minor severity is reasonable since it's an edge-case auto-fail rather than a broken core mechanic, and spec claims full parity.

### EFF-13 — Temporary hit points are ignored for a creature already at 0 HP

**Severity:** minor · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/_damage.py:81`

_apply_damage_impl handles the `hp_current <= 0` branch (line 70) before the temp-HP absorption block (line 81). A dying creature that has temporary hit points (grant_temp_hp works fine at 0 HP) therefore suffers a death-save failure even when its temp HP would have absorbed all of the damage, and the temp HP pool is left untouched. Per the rules, temporary hit points are lost first whenever a creature takes damage, at any HP total; damage fully absorbed by temp HP is not damage taken at 0 HP and causes no death-save failure.

**2024 rule (SRD 5.2):** SRD 5.2, 'Temporary Hit Points': 'If you have Temporary Hit Points and take damage, those points are lost first, and any leftover damage carries over to your Hit Points.' Combined with 'Death Saving Throws — Damage at 0 Hit Points' (failure only when you take damage).

**Evidence:**

```
_damage.py:70-78 executes and returns before line 81's `if target.temp_hp > 0: absorbed = min(target.temp_hp, effective_damage) ...`, so temp HP is never consulted once hp_current is 0. Executed repro: char dying at 0 HP, grant_temp_hp(10), apply_damage(5, SLASHING) -> 'temp_hp after: 10 death save failures: 1'.
```

**Verification:** Confirmed by code trace and execution: the hp_current <= 0 early-return at _damage.py:70-78 executes and returns before the temp_hp absorption block at line 81, so temp HP is never consulted for a creature already at 0 HP. Executed repro: dying PC granted 10 temp HP takes 5 damage, ends with temp_hp still 10 (untouched) and a death-save failure recorded despite temp HP that should have fully absorbed the hit and caused no failure. Correctly scoped as minor given it's an edge case (temp HP applied while already dying).

### EFF-14 — Unconscious applied directly (apply_condition or spell rider) does not include the Prone condition

**Severity:** minor · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/_spell_resolution.py:180`

The 2024 Unconscious condition explicitly includes the Incapacitated and Prone conditions ('Inert'), and dropping held items. The engine only pairs UNCONSCIOUS with PRONE in the dropping-to-0-HP path (_damage.py::_fall_unconscious). When UNCONSCIOUS is applied directly — via engine.apply_condition (_conditions.py:38-39) or via a spell rider such as Sleep (level1.py:142 applies [INCAPACITATED, UNCONSCIOUS]) — PRONE is not added, so a slept creature is not prone: melee attacks get advantage from UNCONSCIOUS but the prone melee-advantage/ranged-disadvantage interaction and crawl-speed rules never engage, and the creature isn't prone on waking (no prone bookkeeping exists to clean up when UNCONSCIOUS is removed).

**2024 rule (SRD 5.2):** SRD 5.2, 'Unconscious' condition: 'Inert. You have the Incapacitated and Prone conditions'; 'You drop whatever you're holding and fall Prone.'

**Evidence:**

```
_spell_resolution.py:179-185 appends exactly spell.conditions_applied with no Unconscious→Prone coupling; _conditions.py:38-39 likewise; grep 'Condition.PRONE' in _damage.py → only line 108 inside _fall_unconscious (_damage.py:103-110); no other UNCONSCIOUS→PRONE coupling exists.
```

**Verification:** Confirmed by code trace: only _fall_unconscious (_damage.py:103-110, triggered by dropping to 0 HP) pairs UNCONSCIOUS with PRONE; both _apply_condition_impl and the spell-rider path in _spell_resolution.py:179-185 append UNCONSCIOUS alone with no Prone coupling. The Sleep spell (level1.py:142) applies exactly [INCAPACITATED, UNCONSCIOUS] with no PRONE, confirming a slept creature is missing the Prone rider its 2024 Unconscious condition should carry (melee-advantage/ranged-disadvantage and crawl-speed interactions never engage). Minor severity is appropriate — it affects a secondary interaction rather than core combat resolution.

### EFF-15 — Invisible condition's advantage on initiative (2024 'Surprise' clause) not implemented

**Severity:** minor · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/engine.py:93`

The 2024 Invisible condition grants advantage on initiative rolls made while invisible. The engine's initiative path (engine.roll_initiative → _roll_initiative_impl) rolls a flat d20 with no advantage support and never inspects the character's conditions, so an invisible creature gains no initiative advantage. The attack-roll halves of Invisible are implemented; this clause — new in 2024 — is not.

**2024 rule (SRD 5.2):** SRD 5.2, 'Invisible' condition: 'Surprise. If you're Invisible when you roll Initiative, you have Advantage on the roll.'

**Evidence:**

```
engine.py:93-103 and _checks.py:68-82 — `raw, _ = roll_dice(1, 20); return raw` — no condition inspection and no advantage/disadvantage parameters anywhere in the initiative path; core/conditions.py:111-120 defines Invisible only via attack_modifier/attack_against_modifier.
```

**Verification:** Confirmed by direct read of engine.py:93-103 and _checks.py:68-82: _roll_initiative_impl rolls a flat 1d20 with roll_dice(1,20), no advantage/disadvantage parameter exists anywhere in the initiative call chain, and conditions.py's INVISIBLE effect only sets attack_modifier/attack_against_modifier (no initiative hook). The 2024 SRD 'Surprise' clause on Invisible is a real, distinct addition from 2014. docs/phb-parity-spec.md claims Conditions + mechanical effects are fully done, so this is not declared out-of-scope. Correctly minor since it's a narrow situational miss, not a broken core mechanic.

### EFF-16 — Long rest grants full benefits to a character at 0 HP

**Severity:** minor · **Location:** `game-engine/src/game_engine/rules/dnd_5_5e/resting.py:106`

long_rest only bails out for dead characters; a character at 0 HP (dying or stable) is restored to full HP, has death saves reset, and UNCONSCIOUS/PRONE stripped. The 2024 Long Rest rule requires at least 1 Hit Point to start a Long Rest and gain its benefits; a creature at 0 HP cannot begin one (a Stable creature first regains 1 HP after 1d4 hours, then could rest). Tests (test_resting_exploration.py:125-163) encode this non-rules behavior as intended.

**2024 rule (SRD 5.2):** SRD 5.2 / PHB 2024, 'Long Rest': 'To start a Long Rest, you must have at least 1 Hit Point.'

**Evidence:**

```
resting.py:102-113 — `if char.is_dead: return result` is the only guard; then `char.hp_current = char.hp_max` and `if before <= 0 and char.hp_current > 0: char.death_saves.reset(); ... conditions ... not in {UNCONSCIOUS, PRONE}` explicitly heals a 0-HP character through a long rest.
```

**Verification:** Confirmed by code trace and execution: long_rest's only guard is `if char.is_dead: return result`; a character at 0 HP is unconditionally healed to full, has death saves reset, and UNCONSCIOUS/PRONE stripped. Executed repro: PC at 0 HP with 1 death-save failure ends a long rest at hp_current=10, is_dead=False — contradicting the 2024 rule requiring at least 1 HP to start a Long Rest. Minor severity is reasonable since it's a benign-direction bug (over-generous healing) rather than a combat-correctness break.

---

## Appendix — Refuted finding

One candidate finding was rejected during adversarial verification:

- **Lance has 2014 stats (1d10 instead of 1d12, plus removed 'Special' property)** (`data/weapons.py`) — refuted: the engine's entry (1d10 piercing; Heavy/Reach/Two-Handed/Special; mastery Topple; 6 lb; 10 gp) matches the actual 2024 rules, which retained the Lance's Special property and 1d10 damage die.
