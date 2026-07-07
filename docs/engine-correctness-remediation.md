# dm.ai D&D 5.5e Engine — Correctness Remediation Plan

**Date:** 2026-07-02
**Findings catalog:** [engine-correctness-audit.md](engine-correctness-audit.md) (71 verified findings: 7 critical, 37 major, 27 minor; IDs `ACT-*`, `SPL-*`, `EQP-*`, `EFF-*` referenced throughout).

## Executive Summary

The audit confirmed 71 correctness defects across the game-engine's combat, spellcasting, equipment, and condition subsystems, every one of which survived adversarial verification with an executed repro. The findings cluster around a small number of systemic root causes rather than scattered typos: (1) a **turn-state lifecycle bug** — `TurnState.reset_turn` wipes cross-turn effect flags at the start of every combatant's turn, silently nullifying Help, Sap, Vex, and Hide in normal play; (2) a **missing action-economy model** — Extra Attack, reactions/opportunity attacks, spell casting-time slots, and the 2024 "one spell-slot-spell per turn" rule are all unrepresentable, so level-5+ martials lose half their attacks and reaction/bonus-action spells have no correct cast path; (3) a **data/logic disconnect in equipment** — the entire 38-weapon registry, weapon properties, armor Str-minimums, stealth penalties, armor/weapon proficiency, starting equipment, currency, and encumbrance are populated as data but read by zero rule code, so masteries and weapon stats are dead at combat time; (4) a **concentration/condition subsystem that is half-wired** — spell damage never triggers concentration saves, incapacitating conditions never break concentration, ending concentration never removes effects, condition immunities are bypassed by every in-combat inflicting path, and several 2024 condition definitions are stale 2014 rules; (5) a **spell-resolution vocabulary gap** — the `SpellData` schema cannot express multi-beam attacks, staged conditions, save-to-end, choice-of-condition, HP-max buffs, revival, non-damage effects (Shield/Counterspell/Bless), or flat-modifier upcasting, causing a long tail of individual spells to misfire; plus (6) discrete **damage/death and dice-doubling bugs**. The parity spec (`docs/phb-parity-spec.md`) marks nearly all of these rows as ✅, so a companion workstream must correct the spec to match reality. Below, findings are grouped by root cause into 12 workstreams, ordered by player impact.

---


## Phase-by-Phase Execution Plan

The 12 workstreams below (A–M) group the findings by root cause. This section sequences them into six phases plus a cross-cutting track, respecting the dependency chain **A → B → E**, **C → E**, and **F.1 → F/G**. Each phase is independently mergeable and leaves the engine strictly more correct than the previous one.

### Phase 1 — Shared foundations (unblocks everything)

| Work | Findings | Size |
|------|----------|------|
| **A** — TurnState lifecycle: split per-turn economy state from cross-turn effect state with per-effect expiry | ACT-03 ✅ done, ACT-19 (check half — still open, needs Workstream H) | M |
| **C** ✅ bridge done — Weapon-registry ↔ attack-resolution bridge (`WeaponData` → `AttackDetails`, incl. dm-api) | EQP-01 ✅, EQP-08 🟡 (Heavy/Versatile/Finesse done, Loading/Ammunition open), ACT-18 ✅ | L |
| **F.1** — Make `_apply_damage_impl` return post-mitigation damage; route all damage paths through one concentration check | groundwork for SPL-02, EFF-07 | M |

**Exit criteria:** Help/Sap/Vex/Hide effects survive `begin_turn` and are consumed on the correct later turn; an attack built through dm-api carries mastery/properties/proficiency from the registry; every damage path reports effective (post-immunity/resistance) damage.

### Phase 2 — Action economy (criticals for martials)

Depends on Phase 1 (A). Split of Workstream **B**:

| Work | Findings | Size |
|------|----------|------|
| **B1** ✅ done — Extra Attack (attacks-per-action by class level), validation-before-consumption, Nick economy | ACT-01, ACT-05, ACT-08 | M |
| **B2** — Reaction slot, opportunity attacks, Ready semantics | ACT-02, ACT-06 | M |
| **B3** — Spell casting-time → economy slot; 2024 one-slot-spell-per-turn; TWF Light validation | SPL-03, SPL-06, ACT-04 | M |

**Exit criteria:** a level-5 fighter makes exactly 2 attacks; opportunity attacks consume the reaction and respect one-per-round; Healing Word leaves the action free; a second leveled spell in a turn is rejected.

### Phase 3 — Concentration & condition criticals

| Work | Findings | Size |
|------|----------|------|
| **F.2–F.4** — Concentration: save on spell damage, break on incapacitation, end effects on loss, DC cap 30 | SPL-02, EFF-01, SPL-07, EFF-07, SPL-16 | M–L |
| **I2** — Centralize condition application so immunities apply on every inflicting path | EFF-10 | M |
| **J (carve-out)** — Revival effect type: Revivify/Raise Dead/True Resurrection actually revive | SPL-01 | S |

**Exit criteria:** Fireball forces a concentration save; stunning a caster drops their spell; losing Hold Person un-paralyzes the target; condition-immune creatures cannot receive the condition from any path; Revivify returns a dead target to 1 HP.

### Phase 4 — Combat-affecting majors

| Work | Findings | Size |
|------|----------|------|
| **G** — Death & damage ordering: instant death at 0 HP, death-save reset on 3 successes, temp HP at 0 HP, crit doubles dice only | EFF-08, EFF-09, EFF-13, ACT-09 | M |
| **D1+D2** — Worn-armor identity, equip/unequip AC recompute, shield-as-armor guard, Str-min speed, stealth disadvantage, armor-training penalties | EQP-04, EQP-02, EQP-03, EQP-06, EQP-07 | L |
| **E** — Mastery mechanics: Slow/Push/Cleave wired, Graze floor removed, grapple/shove size gate | ACT-07, ACT-17, ACT-16 | M |
| **I1** — Stale 2024 condition definitions: Stunned speed, Petrified immunity, Unconscious→Prone, single source of truth | EFF-06, EFF-05, EFF-14, EFF-11 | S–M |
| **H** — Check/initiative correctness ✅ done (independent quick win; can land in any phase) | ACT-10, ACT-20, ACT-12 | S |

**Exit criteria:** massive damage at 0 HP kills; crits double dice only; heavy armor slows weak wearers and noisy armor hinders Hide; Slow/Push/Cleave have table effects; save proficiency no longer leaks into ability checks.

### Phase 5 — Spell system depth

| Work | Findings | Size |
|------|----------|------|
| **J (remainder)** — SpellData vocabulary: non-damage effects, multi-beam, on-hit riders, staged/choice conditions, divided healing, HP-max buffs, thresholds; spell-attack adv/disadv + crits | SPL-08, SPL-09, SPL-10, SPL-11, SPL-12, SPL-13, SPL-14, SPL-18, SPL-20, SPL-21 | L |
| **K** — Slot & upcast math: pact-slot separation, flat-modifier upcast, secondary-pool upcast, Ice Storm dice, typed durations, hashable ClassLevelEntry | SPL-15, SPL-05, SPL-17, SPL-19, SPL-23, SPL-22 | M |
| **I4** — Repeat-save/save-to-end hook + exhaustion stacking (pairs with J staged conditions) | SPL-04, EFF-03 | M |
| **I3** — Condition source-identity: Grappled and Charmed relational effects | EFF-04, EFF-02 | M |

**Exit criteria:** Shield/Counterspell/Bless do something; Scorching Ray rolls per-ray; Hold Person allows end-of-turn re-saves; warlock short rests restore only pact slots; Magic Missile upcasts to 4d4+4.

### Phase 6 — Long tail & cleanup

| Work | Findings | Size |
|------|----------|------|
| **D3** — Starting equipment/gold into inventory, encumbrance consumer, tool-check abilities, currency spend | EQP-05, EQP-10, EQP-09, EQP-11 | M |
| **L** — Dodge speed-0 gate; dead spell metadata (implement or de-claim in spec) | ACT-15, SPL-24 | S |
| Remaining minors folded into their workstreams | ACT-11, ACT-13, ACT-14, EFF-12, EFF-15, EFF-16 | S |

### Cross-cutting (every phase) — Workstream M: parity-spec truth

As each workstream lands, flip the corresponding `docs/phb-parity-spec.md` rows to their true status (✅ only when tested, 🟡 partial, ⬜ not done). At the end of Phase 6, add structural anti-regression tests asserting each claimed-implemented mechanic has at least one rule-code consumer, so ✅-with-no-consumer can never silently recur (harness-engineering principles #1 and #8).

---

## Workstream A — TurnState cross-turn effect lifecycle (root cause: `reset_turn` wipes persistent flags)

**Status: ACT-03 done.** `EffectExpiry` (`game-engine/src/game_engine/types/combat_state.py`) now tracks, per cross-turn flag, which combatant's turn boundary clears it and at which round; `CombatStateData.reset_turn` only clears action-economy fields and calls `_expire_cross_turn_effects`, and `grant_help`/`grant_sap`/`grant_vex` compute the correct expiry round. `dm-api/src/dm_api/api/combat.py`'s `next_turn` now runs the same `reset_turn` instead of overwriting the entry with a bare `TurnState()`. ACT-19 (Help on ability checks) is still open — it needs Workstream H to thread `CombatStateData` into `_roll_check_impl`.

The single highest-leverage bug. `TurnState.reset_turn` (`game-engine/src/game_engine/types/sheets.py:276-279`) installs a fresh `TurnState()` at the start of each combatant's turn, and dm-api mirrors this (`dm-api/src/dm_api/api/combat.py:310-311`). But `helped`, `sapped`, `vexed_target_id`, and `hidden` encode effects that by rule persist across turn boundaries and are consumed on a *later* turn — so they are erased before they can ever fire.

**Findings**
- Help/Sap/Vex/Hide are no-ops in normal play (`sheets.py:276` [ACT-03], **critical**)
- Help never grants advantage on ability checks — only attack rolls read `helped` (`_checks.py:141` [ACT-19], **minor**; the check-path half also depends on Workstream H threading combat state into `_roll_check_impl`)

**Fix approach**: Split action-economy state (reset every turn) from cross-turn effect state (expires by its own rule). Introduce a source/expiry model on `TurnState`: each carry-over flag records the round/turn it expires and *which* combatant's turn boundary consumes it. `begin_turn` should reset only the actor's own action-economy fields (`action_used`, `bonus_action_used`, `movement_used_ft`, `attacks_made`, `dodging`, `disengaging`, `dashing`) and refresh `reaction_used`, while leaving `helped`/`sapped`/`vexed_target_id`/`hidden` to expire on their correct triggers (Vex: end of attacker's next turn; Sap: before start of sapper's next turn; Help: start of helper's next turn; Hide: on attack/cast-with-verbal/being-found, never on turn start). Mirror the same split in `dm-api/src/dm_api/api/combat.py:310`.

**Tests**: extend `tests/test_attacks_2024.py::test_vex_grants_advantage_on_next_attack` to assert the flag *survives* `begin_turn` and is actually consumed by the follow-up attack; add tests that Help advantage survives to the ally's attack, Sap disadvantage survives to the target's attack, and a Hide grant survives until the hider attacks. Update `test_begin_turn_resets_economy` to assert economy fields reset but effect flags do not.

**Size**: M (touches `sheets.py`, `_actions.py`, `_attacks.py`, dm-api combat, tests). Prerequisite for Workstreams B and I to be observable.

---

## Workstream B — Action economy model (root cause: no attacks-per-action / reaction / casting-time concept)

**Status: B1 done.** `_attacks_per_action` (`game-engine/src/game_engine/rules/dnd_5_5e/_actions.py`) now reads the `attacks_granted` field of each class's "Extra Attack" `ClassFeatureData` (`data/class_features/*.py`) through the actor's level — Fighter 5/11/20 → 2/3/4, Barbarian/Monk/Paladin/Ranger/Artificer(Battle Smith) 5 → 2; multiclass characters take the best tier, not the sum. `_resolve_action_impl`/`_resolve_attack_action` validate the attack (`_attacks._validate_attack`) *before* touching any economy slot, so a rejected attack (unknown actor/target, total cover) costs nothing and an unknown actor creates no ghost `TurnState` — the action slot is only marked spent once `attacks_made` reaches the Extra Attack pool. Nick-mastery off-hand attacks now consume a once-per-turn `TurnState.nick_used` flag instead of the bonus action. B2 (reactions/opportunity/Ready) and B3 (spell casting-time, one-slot-per-turn, TWF Light validation — ACT-02, ACT-06, SPL-03, SPL-06, ACT-04) are still open.

`_resolve_action_impl` (`game-engine/src/game_engine/rules/dnd_5_5e/_actions.py:121-142`) charges exactly one attack per Attack action, has no reaction slot logic, and picks the economy slot purely from `is_offhand`. The engine has no representation of how many attacks a character gets, no reaction-consuming path, and never consults spell casting time.

**Findings**
- Extra Attack impossible — one attack per Attack action (`_actions.py:134` [ACT-01], **critical**) ✅ done
- Reaction economy & opportunity attacks unimplemented (`_actions.py:196` [ACT-02], **critical**)
- Spell `casting_time` ignored — bonus/reaction spells consume the Action (`_actions.py:133` [SPL-03], **major**)
- 2024 "one spell-slot spell per turn" not enforceable (`_spell_resolution.py:104` [SPL-06], **major**)
- Ready action has no trigger/stored-action/reaction semantics (`_actions.py:189` [ACT-06], **major**)
- Action/bonus slot consumed *before* attack validation, so rejected attacks burn the slot; unknown actor creates a ghost TurnState (`_actions.py:138` [ACT-05], **major**) ✅ done
- Nick mastery: off-hand attack always consumes the bonus action (`_attacks.py:155` [ACT-08], **major**) ✅ done
- Two-weapon fighting never validates the Light property or a prior Attack action — any weapon works off-hand (`_actions.py:122` [ACT-04], **major**)
- `get_available_actions` ignores turn state & bonus/reaction economy (`_actions.py:43` [ACT-13], **minor**)
- Dash flag / `movement_used_ft` are dead (`_actions.py:155` [ACT-14], **minor**)

**Fix approach**:
1. ✅ Add an **attacks-per-Attack-action** computation (Fighter 5/11/20 → 2/3/4; Barbarian/Monk/Paladin/Ranger 5 → 2) driven off class levels; allow up to that many attack resolutions before setting `action_used`, tracking with the now-live `attacks_made`.
2. Add `is_reaction` to `Action`/`AttackDetails` and a reaction-resolution path that consumes `reaction_used` instead of the on-turn action; wire `provokes_opportunity_attack` (move it to `_attacks.py` per the spec's claim, export it, and have it consume the mover-provoker's reaction) and enforce one reaction per round.
3. Thread spell `casting_time` (`CastingTime.BONUS_ACTION`/`REACTION`) into slot selection so MAGIC actions charge the correct slot; add a `spell_slot_expended_this_turn` flag to `TurnState` and reject a second leveled-spell cast per turn (cantrips exempt).
4. ✅ **Reorder validation before consumption** in `_resolve_action_impl`: run the `actor_not_found`/`target_not_found`/`total_cover` guards first, only setting `action_used`/`bonus_action_used` after the attack is legal; do not create a TurnState for an unknown actor.
5. ✅ Nick: when the off-hand weapon has the Nick mastery unlocked, resolve the extra Light attack as part of the Attack action (do not set `bonus_action_used`), once per turn — independent of hit.
5b. Validate two-weapon fighting: an `is_offhand` attack requires both weapons to have the Light property (from the Workstream C bridge) and a prior Attack action this turn; reject otherwise.
6. Ready: store a readied `(trigger, action)` on `TurnState`; resolve later via the reaction path (depends on step 2). Readied spells require concentration.
7. Make `get_available_actions` consult `turn_state_for` and surface remaining action/bonus/reaction options.

**Tests**: ✅ level-5 fighter makes 2 attacks then is rejected on the 3rd; ✅ an attack behind total cover leaves `action_used=False` and a follow-up legal attack succeeds; ✅ Nick off-hand attack leaves `bonus_action_used=False`. Still open: opportunity attack consumes reaction and a second in the same round is rejected; Healing Word (bonus) leaves the action free; a second leveled spell same turn is rejected while a cantrip is allowed; an off-hand greatsword attack (non-Light) is rejected, as is an off-hand attack with no prior Attack action; Ready stores and later fires via reaction.

**Size**: L. Depends on Workstream A (shared `TurnState` refactor). This is the largest single workstream; split into B1 ✅ (Extra Attack + validation ordering + Nick — done), B2 (reactions/opportunity/Ready), B3 (spell casting-time + one-slot-per-turn + TWF Light validation).

---

## Workstream C — Weapon registry ↔ attack-resolution bridge (root cause: `WeaponData`/`get_weapon` never consumed)

**Status: bridge + Heavy/Versatile/Finesse + ACT-18 done.** `game_engine.rules.dnd_5_5e._weapon_bridge.to_attack_details(weapon, actor, *, is_offhand, two_handed, is_ranged)` builds an `AttackDetails` from a registry `WeaponData` and the acting `CharacterSheet`: `mastery`/`properties` copy straight from the registry, `proficient` compares `weapon.category` against `actor.weapon_category_training`, `attack_ability` is Finesse-aware (best of STR/DEX), and `damage_dice` swaps to `versatile_dice` when `two_handed=True`. `dm-api`'s `build_attack_details` (`combat_utils.py`) now looks the request's `weapon_name` up via `get_weapon` and calls the bridge when found, falling back to the raw request fields only for weapons outside the registry (Unarmed Strike, monster natural weapons, homebrew) — those still carry no mastery/properties/proficiency, which is correct since they aren't in a proficiency-gated registry. `AttackDetailsRequest` gained `is_offhand`/`two_handed` fields so off-hand and Versatile attacks are reachable through the real API, not only engine unit tests. `_advantage_state` (`_attacks.py`) now imposes disadvantage for the Heavy property when the attacker's relevant score (STR melee / DEX ranged) is below 13. ACT-18 (off-hand attacks zeroing a *negative* ability modifier instead of only a positive one) is also fixed. **Still open:** Ammunition/Loading tracking (EQP-08 remainder — no ammo count, no one-shot-per-action cap for Loading weapons) and Reach/Thrown range (see `docs/phb-parity-spec.md`).

The audit's most consequential equipment finding: nothing constructs an `AttackDetails` from a `WeaponData`. `dm-api`'s `build_attack_details` (`dm-api/src/dm_api/api/combat_utils.py:255-264`) copies only 5 request fields and never calls `get_weapon`, so in the real pipeline `mastery` is always `None`, `properties` always empty, and `proficient` always `True`. The entire mastery/property/proficiency layer is dead code outside hand-crafted unit tests.

**Findings**
- Weapon registry never consumed by attack resolution — masteries/proficiency/stats can't fire in real play (`data/weapons.py:529` [EQP-01], **critical**) ✅ done
- `WeaponProperty` enum & `AttackDetails.properties` have zero consumers: Heavy/Loading/Ammunition/Versatile/Finesse/Reach/Thrown unimplemented (`sheets.py:291` [EQP-08], **major**) 🟡 Heavy/Versatile/Finesse done; Loading/Ammunition/Reach/Thrown/Special remain
- Off-hand attack drops a *negative* ability modifier (`_attacks.py:313` [ACT-18], **minor**) ✅ done

**Fix approach**: Add a `to_attack_details(weapon: WeaponData, actor, *, two_handed, is_offhand, ...) -> AttackDetails` bridge in the engine that populates `mastery` (only if the actor has that mastery unlocked), `properties`, `damage_dice`/`damage_type`, `attack_ability` (Finesse → best of STR/DEX), and `proficient` (derived from `actor.weapon_category_training` vs the weapon's `WeaponCategory`). Call it from `dm-api` `build_attack_details` via a widened `AttackDetailsRequest` (add weapon-name → registry lookup; stop trusting `proficient`). Then consume `properties` in `_advantage_state`/`_actions`:
- ✅ **Heavy**: disadvantage when STR (melee) or DEX (ranged) < 13.
- **Ammunition/Loading**: track/expend ammo and limit to one attack per action for Loading weapons. *(still open — needs an inventory-backed ammo count and an economy change in `_actions.py`, not just an `AttackDetails` flag; deferred to pair with Workstream D's inventory work.)*
- ✅ **Versatile**: honor `versatile_dice` when two-handed.
- ✅ Fix `_attacks.py:312-314` to zero the off-hand modifier only when it is **≥ 0**, preserving negative modifiers.

**Tests**: ✅ `game-engine/tests/test_weapon_bridge.py` builds an `AttackDetails` from a Scimitar via the bridge and confirms `mastery=NICK`; a wizard attacking with a greatsword gets no proficiency bonus; Finesse/Versatile/thrown-at-range selection. ✅ `test_attacks_2024.py::TestHeavyProperty` covers a STR-10 vs STR-13 melee Heavy swing and a Heavy ranged weapon checking DEX not STR. ✅ `TestTwoWeaponFighting::test_offhand_attack_preserves_negative_ability_mod` covers the ACT-18 fix. ✅ `dm-api/tests/test_combat_utils.py::TestBuildAttackDetails` is a pipeline test confirming mastery/proficiency survive the dm-api bridge. Still open: a Loading crossbow rejecting a second shot (needs the ammo/economy work above).

**Size**: L. Foundational for Workstreams D and the mastery half of E to have any real-play effect; do C before E. Loading/Ammunition carved out as a follow-up pairing with Workstream D.

---

## Workstream D — Armor, proficiency & inventory effects (root cause: armor/inventory data stored but never applied; no worn-armor identity)

`build_character` applies AC once at creation and discards the armor — `CharacterSheet` has no worn-armor field — so Str-minimum speed penalties, stealth disadvantage, and armor-training penalties are structurally unreachable, and AC never recomputes.

**Findings**
- Heavy-armor Str minimum never reduces speed; worn-armor identity never stored (`character_builder.py:269` [EQP-04], **major**)
- Armor `stealth_disadvantage` never consumed — Hide ignores noisy armor (`_actions.py:179` [EQP-02], **major**)
- Armor training & weapon proficiency have no in-play effect (`character_builder.py:228` [EQP-03], **major**)
- `InventoryItem.equipped` never read — no equip/unequip recomputes AC or selects weapons (`character_state.py:163` [EQP-07], **major**)
- Passing `'Shield'` as body armor yields AC 2 (`data/armor.py:194` [EQP-06], **major**)
- Starting equipment & gold never applied to inventory/currency (`character_builder.py:284` [EQP-05], **major**)
- `is_encumbered` has no rule consumers (`exploration.py:44` [EQP-10], **minor**)
- `Currency.total_gp` never consumed; no purchase/spend logic (`character_state.py:141` [EQP-11], **minor**)
- `ToolData.ability` dead — tool checks ignore governing ability & proficiency (`data/gear.py:28` [EQP-09], **minor**)

**Fix approach**:
1. Add a **worn-armor / equipped-weapon** concept to `CharacterSheet` (store the equipped armor and shield identity, not just the derived AC) plus an equip/unequip API that recomputes AC via `compute_armor_class`.
2. Guard `compute_armor_class` against `ArmorCategory.SHIELD` passed as body armor (raise/warn, don't return base_ac 2); reject or warn on `armor_name='Shield'` in `build_character`.
3. Feed worn armor into `effective_speed` (−10 ft while STR < `min_strength`) and into the Hide check (`disadvantage=True` when the worn armor has `stealth_disadvantage`).
4. Apply the 2024 **armor-training** penalty: disadvantage on STR/DEX D20 tests and can't-cast while wearing untrained armor — wire through `_advantage_state`, `_checks`, `_saves`, and a spellcasting gate.
5. Expand `BackgroundData.equipment` (including gold and PACK contents) into `inventory`/`currency` at build time; persist inventory in dm-api (`stats=sheet.to_dict()`), not just as a string column.
6. Consume `is_encumbered` in `effective_speed`/travel pace; add tool-check resolution mapping tool name → `ToolData.ability` + proficiency; add basic currency debit/credit for purchases.

**Tests**: STR-10 fighter in Chain Mail has speed 20; character in Plate rolls Hide with disadvantage; wizard in Plate gets disadvantage on DEX saves and can't cast; `armor_name='Shield'` no longer yields AC 2; a built character has non-empty inventory and starting gp; over-capacity inventory reduces speed; equipping/unequipping armor recomputes AC.

**Size**: L. The worn-armor field (step 1) is shared infrastructure; the Str-min/stealth/training consumers depend on it. Best done as D1 (worn-armor field + AC recompute + shield guard), D2 (speed/stealth/training consumers), D3 (starting equipment/currency/encumbrance/tools).

---

## Workstream E — Weapon mastery mechanics (root cause: masteries write log keys nothing reads; missing TurnState fields & size checks)

Several masteries only emit unread log entries. Note Sap/Vex are undermined by Workstream A's wipe. Workstream C now bridges the registry into real play, so a mastery an actor has trained now actually reaches `_apply_mastery_effects` via dm-api — but Slow/Push/Cleave still no-op past the log line below.

**Findings**
- Slow, Push, Cleave are log-only with no mechanical effect (`_attacks.py:149` [ACT-07], **major**)
- Default unarmed strike deals 1d4 + STR instead of the 2024 fixed 1 + STR (`sheets.py:287` [ACT-11], **major**)
- Graze invents a minimum-1 damage floor (`_attacks.py:290` [ACT-17], **minor**)
- Unarmed grapple/shove ignores the size restriction (`_attacks.py:186` [ACT-16], **minor**)

**Fix approach**:
- **Slow**: reduce target speed by 10 ft until the start of the attacker's next turn (needs a per-target speed-reduction input into `effective_speed`, and a `TurnState` field/expiry).
- **Cleave**: allow the follow-up attack roll against a second creature within reach (damage without ability modifier), once per turn — reuse the Extra-Attack-style economy carve-out from Workstream B so it isn't rejected as `action_used`.
- **Push**: gate on target `CreatureSize` (Large or smaller) using the sheet's `CreatureSize`.
- **Graze**: deal damage exactly equal to the ability modifier (`max(0, ...)`); remove the invented `max(1, ...)` floor so the `if graze_damage:` guard and its spurious concentration check no longer always fire.
- **Grapple/Shove**: reject when the target is more than one size larger than the attacker.
- **Unarmed strike damage**: change the default unarmed damage to the 2024 fixed `1 + STR` (no d4), keeping a hook for Monk martial-arts dice and the Tavern Brawler-style overrides that legitimately change it.

**Tests**: Slow reduces and later restores speed; Cleave's second attack resolves without burning the action; Push against a Huge creature no-ops; Graze with STR 10/6 deals 0; a Small attacker can't grapple a Gargantuan target; a default unarmed strike with STR 16 deals exactly 4. **Delete/replace** `test_graze_minimum_damage_is_1_with_negative_ability_mod` (it codifies a nonexistent rule).

**Size**: M. Depends on Workstream C (masteries must reach the resolver) and shares the speed-reduction and economy plumbing with A/B.

---

## Workstream F — Concentration lifecycle (root cause: save-on-damage, break-on-incapacitation, and end-on-loss are unwired for spells)

Concentration is tracked as a bare string with three independent gaps: damage from spells never forces the save, incapacitating conditions never break it, and losing it never removes its effects.

**Findings**
- Spell damage never triggers a concentration save on the target (`_spell_resolution.py:163` [SPL-02], **critical**)
- Gaining Incapacitated/Stunned/Paralyzed/Petrified/Unconscious never breaks concentration (`_conditions.py:38` [EFF-01], **critical**)
- Breaking/replacing concentration never ends the spell's effects on targets (`_spell_resolution.py:114` [SPL-07], **major**)
- Concentration save uses pre-mitigation damage; immune targets still roll & can lose it (`_attacks.py:323` [EFF-07], **major**)
- Concentration save DC missing the 2024 max of 30 (`_damage.py:147` [SPL-16], **minor**)

**Fix approach**:
1. Make **`_apply_damage_impl` return the effective (post-immunity/resistance) damage**, and route *every* damage path — `_spell_resolution.py`, `engine.apply_damage`, and the weapon path — through a single `_concentration_check` call using that effective amount (fixes both the spell-damage gap and the pre-mitigation DC bug; a 0-damage immune hit forces no save).
2. In `_apply_condition_impl` and the spell-rider apply path, **break concentration when the applied condition includes Incapacitated** (Incapacitated, Stunned, Paralyzed, Petrified, Unconscious).
3. Track **concentration → applied effects**: record, per concentration spell, which target conditions/durations it created (a caster→effects back-reference), and remove them when `concentrating_on` is cleared or replaced.
4. Clamp `concentration_save_dc` to `min(30, max(10, damage // 2))`.

**Tests**: Fireball on a Haste-concentrating target forces a CON save and can drop Haste; stunning a Bless-concentrating caster ends Bless; losing concentration on Hold Person immediately removes the target's Paralyzed; a fire-immune target takes 0 and rolls no save; a 62-damage hit yields DC 30, not 31.

**Size**: M–L. Step 1 (effective-damage return) is a shared refactor also relied on by Workstream G. Step 3 (effect back-reference) is the largest piece and pairs naturally with Workstream I's save-to-end tracking.

---

## Workstream G — Damage, death saves & instant-death ordering (root cause: 0-HP branch ordering and missing HP-max checks)

Discrete correctness bugs in `_damage.py`/`_death.py` around the 0-HP state.

**Findings**
- Damage at 0 HP ≥ HP max does not kill instantly (`_damage.py:70` [EFF-08], **major**)
- Death save counters not reset when a character becomes stable via 3 successes (`_death.py:63` [EFF-09], **major**)
- Temp HP ignored for a creature already at 0 HP (`_damage.py:81` [EFF-13], **minor**)
- Critical hits double the flat modifier baked into damage-dice notation (`_attacks.py:317` [ACT-09], **major**) — reachable via monster data (`data/monsters.py:78,86,122,130`) carrying `1d4+2`/`2d8+4` and dm-api's free-string `damage_dice`
- Long rest grants full benefits to a character at 0 HP (`resting.py:106` [EFF-16], **minor**) — 2024 requires at least 1 HP to gain a long rest's benefits

**Fix approach**:
- Reorder `_apply_damage_impl`: apply **temp-HP absorption first** (at any HP total), then in the 0-HP branch compare *effective* damage against `hp_max` for instant death (two failures on a crit that reaches 3+ still applies), then convert to death-save failures only for leftover damage.
- On the third death-save success in `_roll_death_save_impl`, **reset successes and failures** (match `_stabilize_impl`).
- Fix critical hits to double **only the dice**, not the notation's flat modifier: on a crit roll the dice count twice but add the flat modifier once (and add the ability modifier once). Consider splitting dice from flat modifier at the `AttackDetails` boundary so monster notations like `1d6+2` don't double the `+2` and don't double-count the ability mod.
- Gate `long_rest` on `hp_current >= 1` (return a no-benefit result for a character at 0 HP, per the 2024 rule).

**Tests**: dying PC (hp_max 20) hit for 25 dies instantly; dying PC with temp HP 10 hit for 5 loses temp HP and takes no death-save failure; 2-failures-then-3-successes leaves a stable character at 0/0 counters who survives 1 subsequent damage; a `1d6+2` crit deals dice-doubled-plus-single-modifier damage; a long rest at 0 HP confers no benefits.

**Size**: M. Shares the effective-damage-return refactor with Workstream F.

---

## Workstream H — Ability-check & roll correctness (root cause: save proficiency leaking into checks; missing d20_modifier/condition plumbing on non-attack rolls)

**Status: done.** `_roll_check_impl` (`game-engine/src/game_engine/rules/dnd_5_5e/_checks.py`)
now only consults `Skill` proficiency/expertise for a check bonus — a raw
`Ability` check never reads `proficient_abilities` (saving-throw
proficiency). `_roll_initiative_impl` rolls with disadvantage when the
character is Poisoned/Frightened, and `DnD55eEngine.roll_initiative`
(`engine.py`) now adds `char.d20_modifier` (exhaustion) to the total.
`InitiativeTracker.remove_combatant` (`game_engine/core/initiative.py`) now
tracks a `_current_vacated` flag: removing the current combatant still
advances `_current_index` so the next `next_turn()` lands on the correct
successor, but `current_turn()` reports `None` (a "between turns" state)
instead of the previous combatant until `next_turn()` runs again. The
Invisible initiative-advantage clause (EFF-15) remains out of scope here —
tracked under Workstream I.

Roll-modifier bugs where check/initiative paths diverge from the (correct) attack/save paths.

**Findings**
- Saving-throw proficiency wrongly added to raw ability checks & contests (`_checks.py:132` [ACT-10], **major**)
- Initiative ignores the exhaustion d20 penalty `char.d20_modifier` (and check-disadvantage conditions) (`engine.py:103` [ACT-20], **minor**)
- Removing the current combatant makes `current_turn()` report the previous combatant (`core/initiative.py:161` [ACT-12], **minor**)

**Fix approach**:
- In `_roll_check_impl`, **do not** add `is_proficient(ability)` on raw ability checks — `proficient_abilities` holds *saving-throw* proficiencies; ability checks add only the ability modifier (skill/tool proficiency handled separately).
- Add `char.d20_modifier` to `roll_initiative` (it's a Dexterity check / D20 Test) and apply check-disadvantage conditions and the 2024 Invisible initiative-advantage clause (see Workstream I).
- Fix `remove_combatant`: when removing the current combatant, leave `current_turn()` in a correct "between turns" state rather than pointing at the prior entry (e.g. mark the index invalid until the next `next_turn`).

**Tests**: a fighter with STR save proficiency rolls a plain STR check with no proficiency bonus; an exhaustion-3 creature rolls initiative at −6; removing the acting combatant leaves `current_turn()` correct.

**Size**: S. Independent of A/B; can land early as a quick win.

---

## Workstream I — Condition definitions & mechanical effects (root cause: stale 2014 rules, missing source-identity/auto-fail/repeat-save hooks, duplicate source of truth)

The 2024 condition set is partly stale and partly unwired. Many require relational (source-identity) or hook (auto-fail, repeat-save) support the engine lacks.

**Findings**
- Combat paths bypass condition immunities (spell riders, Topple, unarmed grapple/shove) (`_spell_resolution.py:181` [EFF-10], **major**)
- No repeat-save/save-to-end: Hold Person paralyzes for a full minute (`_conditions.py:71` [SPL-04], **major**)
- Stunned sets speed 0 (2014); 2024 Stunned doesn't prevent movement (`core/conditions.py:189` [EFF-06], **major**)
- Petrified grants poison/psychic *damage* immunity instead of *Poisoned-condition* immunity (`core/conditions.py:147` [EFF-05], **major**)
- Grappled (2024) missing attack-disadvantage-vs-non-grappler, escape check, end-on-grappler-incapacitated (`core/conditions.py:97` [EFF-04], **major**)
- Exhaustion can never be gained via the engine; `Condition.EXHAUSTION` is a no-op (`core/conditions.py:81` [EFF-03], **major**)
- Charmed has zero mechanical effect (`core/conditions.py:66` [EFF-02], **major**)
- Deafened has zero effect; Blinded/Deafened auto-fail of sight/hearing checks unmodeled (`core/conditions.py:74` [EFF-12], **minor**)
- Unconscious applied directly doesn't add Prone (`_spell_resolution.py:180` [EFF-14], **minor**)
- Invisible initiative-advantage clause not implemented (`engine.py:93` [EFF-15], **minor**)
- `ConditionEffect.can_act`/`speed_zero` never read — duplicate frozensets are the live source (`core/conditions.py:41` [EFF-11], **minor**)

**Fix approach**:
1. **Centralize condition application**: route spell riders, Topple, and unarmed grapple/shove through `_apply_condition_impl` (or a shared helper) so `is_immune_to_condition` is honored everywhere and future centralized handling (concentration break from Workstream F, Prone coupling, exhaustion stacking) runs uniformly.
2. **Fix stale/incorrect definitions**: remove `speed_zero=True` from Stunned (and drop it from `_SPEED_ZERO_CONDITIONS`); change Petrified from poison/psychic damage immunity to Poisoned-*condition* immunity (keep resistance-to-all); couple Unconscious → Prone (and clean up Prone when Unconscious is removed).
3. **Add source-identity** to conditions so Grappled (disadvantage vs non-grappler, end on grappler incapacitated, escape check as an action) and Charmed (can't attack/target charmer; charmer advantage on social checks) can be honored.
4. **Add exhaustion stacking**: `apply_condition(EXHAUSTION)` increments `exhaustion_level` (cumulative, death at 6); a `gain_exhaustion` API; keep `Condition.EXHAUSTION` and `exhaustion_level` consistent (long rest should also clear the stale enum entry).
5. **Add a repeat-save / save-to-end hook**: a `SpellData.repeat_save` field and an end-of-turn re-save step in the condition-tick path for Hold Person/Monster/Confusion/Dominate/Blindness/Sleep's second save.
6. **Add sight/hearing-requirement plumbing** to `_roll_check_impl` for Blinded/Deafened auto-fail; add Invisible advantage to initiative.
7. **Eliminate the duplicate source of truth**: make `CharacterSheet.can_act`/`effective_speed` read `ConditionEffect.can_act`/`speed_zero` (or delete the unread fields), so there is one place to edit.

**Tests**: a PARALYZED-immune target is not paralyzed by Hold Person; a GRAPPLED-immune target isn't grappled; a stunned creature can still move; a petrified creature takes halved (not zero) poison damage and can't be Poisoned; a grappled creature attacks non-grapplers at disadvantage and can escape; `apply_condition(EXHAUSTION)` twice yields level 2 with −4/−10 ft; a charmed creature can't target its charmer; a slept creature is Prone; an invisible creature rolls initiative with advantage.

**Size**: L. The centralization (step 1) and source-identity (step 3) are shared with Workstreams A and F. Split into I1 (definition fixes: Stunned/Petrified/Unconscious/duplicate-source), I2 (immunity centralization + concentration coupling — pair with F), I3 (source-identity: Grappled/Charmed), I4 (exhaustion stacking + repeat-save + auto-fail hooks).

---

## Workstream J — Spell schema vocabulary gaps (root cause: `SpellData` can't express multi-target division, multi-beam, staged/choice conditions, HP-max, revival, non-damage effects, thresholds)

A long tail of individual spells misfire because the schema lacks the fields to express their rules. These are grouped because they all require extending `SpellData` + the resolver rather than per-spell data tweaks.

**Findings**
- Revivify/Raise Dead/True Resurrection can never revive a dead target (`_damage.py:126` [SPL-01], **critical**)
- Registry spells with no mechanical fields silently no-op: Shield, Counterspell, Power Word Kill, Mage Armor, Bless, Banishment, … (`level1.py:106` [SPL-09], **major**)
- Multi-beam/ray spells collapse into one all-or-nothing attack with wrong upcast math: Scorching Ray, Eldritch Blast (`level2.py:85` [SPL-12], **major**)
- Spell attack rolls ignore all condition-based advantage/disadvantage and never deal critical damage (`_spell_resolution.py:129` [SPL-08], **major**)
- Hex & Hunter's Mark deal immediate direct damage on cast (`level1.py:311` [SPL-11], **major**)
- Spiritual Weapon damage omits the spellcasting ability modifier (`level2.py:206` [SPL-13], **major**)
- Sleep applies Unconscious immediately on the first failed save (`level1.py:142` [SPL-10], **major**)
- Blindness/Deafness applies both conditions instead of one of the caster's choice (`level2.py:321` [SPL-14], **major**)
- Mass Heal restores full HP to each target instead of dividing 700 (`level9.py:116` [SPL-21], **minor**)
- Power Word Stun stuns targets above the 150-HP threshold (`level8.py:72` [SPL-20], **minor**)
- Aid can't raise HP maximum, so it does nothing at full HP (`level2.py:161` [SPL-18], **minor**)

**Fix approach** — extend the schema and resolver, then re-encode data:
- **Revival**: add a revival effect type (or `revives=True`); `cast_spell` sets `hp_current=1` and clears death saves for a target dead within the window, instead of routing 1 HP through `_apply_healing_impl` (which no-ops on the dead) and misreporting success.
- **Non-damage effects**: add representations for AC buffs (Shield +5 reaction, Mage Armor 13+DEX), d20 riders (Bless/Bane/Guidance d4), spell negation (Counterspell CON save → target spell fails), and HP-threshold instant effects (Power Word Kill ≤100, Power Word Stun ≤150). Where a full effect is out of scope, at minimum stop rolling a save that applies nothing (Counterspell/Banishment currently half-resolve).
- **Multi-beam/ray**: add a `beams`/`rays`-per-attack model with per-beam attack rolls and independently assignable targets; upcasting adds rays (Scorching Ray), cantrip scaling adds beams (Eldritch Blast) — each its own roll and crit.
- **Spell attack parity with weapon attacks**: route spell attack rolls through the same advantage/disadvantage aggregation as `_advantage_state` (conditions, Dodge, hidden, etc.) and honor nat-20 crits (double the spell's damage dice) and nat-1 misses — the weapon path is the reference implementation.
- **Rider vs on-hit damage**: mark Hex/Hunter's Mark damage as an on-attack rider (no damage on cast).
- **Ability-mod spell damage**: add a `add_spellcasting_mod_to_damage` flag for Spiritual Weapon.
- **Staged conditions**: add staged/second-save support so Sleep applies Incapacitated first, Unconscious only on the second failed save (pairs with Workstream I's repeat-save hook).
- **Choice-of-condition**: let Blindness/Deafness apply one caster-chosen condition.
- **Divided healing**: Mass Heal's 700 is a pool divided among targets, not per-target.
- **HP-max buff**: Aid raises both current and maximum HP.

**Tests**: Revivify on a corpse yields a live target at 1 HP; Scorching Ray at level 3 rolls four independent rays; Fire Bolt against a paralyzed adjacent target rolls with advantage and auto-crits; a nat-20 spell attack doubles the damage dice; Hex deals 0 on cast; Spiritual Weapon deals `1d8 + mod`; Sleep leaves only Incapacitated on the first save; Blindness/Deafness applies exactly one chosen condition; Mass Heal divides 700; Power Word Stun no-ops above 150 HP; Aid raises max HP and helps at full HP; Counterspell no longer applies nothing after rolling a save.

**Size**: L (schema surface plus ~10 spell re-encodings). The revival fix is a quick **critical** carve-out that can land first; multi-beam and non-damage-effect modeling are the heavy parts.

---

## Workstream K — Spell slot & upcast math (root cause: pact/standard pool merge; flat-modifier upcast dropped; secondary-damage not upcast)

Slot bookkeeping and upcast-scaling arithmetic bugs in `spellcasting.py`/`_spell_resolution.py`.

**Findings**
- Pact slots merged into the shared multiclass pool let a short rest restore standard slots (`spellcasting.py:146` [SPL-15], **major**)
- Upcast drops the flat modifier: Magic Missile → 4d4+3 instead of 4d4+4 (`_spell_resolution.py:56` [SPL-05], **major**)
- Dual-damage spells never upcast their secondary pool (Flame Strike) (`_spell_resolution.py:150` [SPL-17], **minor**)
- Ice Storm uses stale 2014 dice (2d8/+1d8 vs 2024 2d10/+1d10) (`level4.py:40` [SPL-19], **minor**)
- `duration_rounds` returns None for long durations, making rider conditions permanent (`spellcasting.py:180` [SPL-23], **minor**)
- `compute_spell_slots` `caster_types` override unusable — `ClassLevelEntry` is unhashable (`spellcasting.py:130` [SPL-22], **minor**)

**Fix approach**:
- Add an `is_pact` distinction to `SpellSlotState` (or track pact slots as a separate pool) so short rest restores only pact slots and `compute_spell_slots` stops merging pact into standard.
- Add `upcast_damage_flat_per_slot` and have `_scale_dice`/`_roll_damage` scale the flat modifier with the dice (Magic Missile +1 per dart).
- Pass real `upcast_per_slot`/`upcast_levels` when rolling `secondary_damage_dice` (Flame Strike radiant scales too).
- Update Ice Storm to 2024 dice (2d10 bludgeoning + 4d6 cold, +1d10/level).
- Make `duration_rounds` total (or return an explicit "until dispelled" sentinel) instead of silently `None`; per the repo's no-raw-strings standard, prefer a typed duration on `SpellData` over substring matching.
- Make `ClassLevelEntry` hashable (frozen or `eq=True`+`__hash__`) so the `caster_types` override works, or drop the dead parameter.

**Tests**: Warlock5/Wizard10 short rest restores only 2 of 5 L3 slots; Magic Missile at L2 deals 4d4+4; Flame Strike at L6 adds 1d6 to both pools; Ice Storm rolls 2d10+4d6; an 8-hour rider condition expires; the `caster_types` override no longer raises `TypeError`.

**Size**: M. Mostly independent; can proceed in parallel with J.

---

## Workstream L — Dead spell metadata & Dodge speed-zero (root cause: declared-scope data with no consumer; a small Dodge gating gap)

Lowest-impact cleanup, partly excused by the engine's theater-of-mind scope. Grouped so the spec can be corrected honestly.

**Findings**
- `SpellComponent`/`SpellRangeType`/`AreaShape`/`SpellSchool` and range/area/material fields never consumed (`types/enums/_core.py:202` [SPL-24], **minor**)
- Dodge benefit not cancelled when the dodger's speed is 0 (`_attacks.py:94` [ACT-15], **minor**)

**Fix approach**: For Dodge, gate the attacker-disadvantage (`_attacks.py:94`), DEX-save advantage (`_attacks.py:192-197`), and the spell-save-advantage path (`_spell_resolution.py:127`) on `target.effective_speed > 0` in addition to `can_act`. For spell metadata, either implement component-gating/school-keyed rules where they matter, or (given theater-of-mind scope) leave range/area unconsumed but **correct the parity spec** to stop claiming these rows are ✅.

**Tests**: a grappled dodging target no longer imposes disadvantage.

**Size**: S.

---

## Workstream M — Parity-spec truth reconciliation (cross-cutting)

`docs/phb-parity-spec.md` marks nearly every audited row ✅ (masteries `:91`, weapon properties/armor Str-min `:92-93`, coinage/carrying `:94-95`, concentration `:104`, components/casting-time `:106`, action/reaction economy `:115-117`, TWF/Nick `:118`, Dodge/Disengage/Dash `:119`) while the code does not implement them. As each workstream lands, update the corresponding spec row to reflect true status (✅ only when tested, 🟡 partial, ⬜ not done). Per this repo's harness-engineering principle #1 (the repository is the single source of truth) and #8 (golden principles are mechanical), also add **structural tests** that assert each claimed-implemented mechanic actually has a consumer (e.g., grep-style tests that fail if `WeaponProperty.HEAVY`, `stealth_disadvantage`, `min_strength`, `is_immune_to_condition` in rider paths, etc. have zero rule-code readers) so these regressions can't silently recur.

**Size**: S per workstream (fold into each), plus one M to add the structural "no dead spec claim" tests.

---

## Priority Order & Dependencies

**Critical (fix first — these break ordinary play at its core):**
1. **Workstream A** (TurnState lifecycle) — unblocks Help/Sap/Vex/Hide *and* is a prerequisite for B, E, I.
2. **Workstream B** (action economy: Extra Attack, reactions, casting-time, one-slot-per-turn, validation ordering) — depends on A. B1 (Extra Attack + validation ordering) first; every level-5+ martial is broken without it.
3. **Workstream C** ✅ bridge done (weapon registry ↔ resolver bridge) — masteries/proficiency now reach the real dm-api pipeline; Loading/Ammunition tracking remains open (pairs with Workstream D).
4. **Workstream F** (concentration lifecycle) — three critical/major concentration gaps; step 1 (effective-damage return) is shared with G.
5. **Workstream J revival carve-out** (Revivify can't revive) — small, self-contained critical.
6. **Workstream I2** (condition-immunity centralization + concentration-on-incapacitation break) — the two condition *critical* items.

**Majors that affect ordinary play (fix next):**
7. **Workstream G** (instant death, death-save reset, crit modifier doubling) — depends on F's effective-damage refactor.
8. **Workstream D** (armor/proficiency/inventory) — D1 worn-armor field first; independent of A/B.
9. **Workstream E** (mastery mechanics) — depends on C (registry bridge) and shares speed-reduction/economy plumbing with A/B.
10. **Workstream I1/I3/I4** (stale condition definitions, source-identity, exhaustion/repeat-save) — I1 is independent; I3/I4 share source-identity with I2 and repeat-save with J.
11. **Workstream H** ✅ done (check proficiency leak, initiative) — small, independent; a fast major/minor win that can land any time.
12. **Workstream J** (remaining spell-schema gaps) & **Workstream K** (slot/upcast math) — parallelizable; K is largely independent.

**Minors (fix last):**
13. Remaining minor items folded into their workstreams (D3 currency/encumbrance/tools, K duration/hashable, L Dodge-speed-zero & dead spell metadata, H initiative/remove-combatant).

**Cross-cutting throughout:** **Workstream M** (spec reconciliation + structural anti-regression tests) — update the relevant spec row and add a consumer-existence test as each workstream merges.

**Key dependency chain:** A → B (shared TurnState) → E (masteries need economy); C → E (masteries need the registry); F.step1 (effective-damage return) → G and F; I2 (centralized apply) ← relied on by F (concentration break) and E (Topple/grapple immunity). Do A, C, and F.step1 early — they are the shared foundations the majority of other workstreams build on.

---

## Verified Correct (audit confirmed sound)

The audit exercised these areas and found them behaving to 2024/SRD 5.2 rules; they are **not** in scope for remediation:

- **Core d20 mechanics on the attack and save paths** — `d20_modifier` (exhaustion) is correctly applied to attacks (`_attacks.py:255`), saves (`_saves.py:60`), skill checks (`_checks.py:138`), passive scores (`_checks.py:65`), and death saves (`_death.py:42`); only *ability checks* (wrong proficiency) and *initiative* (missing modifier) were defective.
- **Weapon-attack advantage/disadvantage aggregation** for conditions, Dodge, Help, Vex/Sap, hidden, and long range in `_advantage_state` (`_attacks.py:55-111`) — the *weapon* path handles crits, conditions, and auto-crit-on-paralyzed correctly (the spell path does not, per Workstream J-adjacent finding, but the weapon path is the reference implementation).
- **Cantrip damage scaling** at character levels 5/11/17 (`spellcasting.cantrip_dice_multiplier`) is correct.
- **Spell save DC and spell attack bonus** computation (`spell_save_dc`, `spell_attack_bonus`) are correct.
- **Slot consumption and basic upcast dice count** (dice are added correctly; only the *flat modifier* and *secondary pool* upcasts are wrong — Workstream K).
- **Damage resistance / immunity / vulnerability** application in `_apply_damage_impl` (`_damage.py:53-54`) works for damage types (the *condition*-immunity bypass is separate — Workstream I).
- **`grant_temp_hp`, `grant_healing`, resistance-to-all (Petrified base)**, exhaustion's integer-driven `d20_modifier`/`effective_speed`/death-at-6 and long-rest decrement all compute correctly — the gap is only that nothing *increments* exhaustion (Workstream I).
- **`_stabilize_impl`** correctly zeroes death-save counters (it's the reference the buggy 3-successes path in `_death.py` should match).
- **The layered architecture and typed boundaries themselves** — no upward-import or `dict[str, Any]`-across-boundary violations were surfaced by this correctness audit; the defects are rule-logic and data-consumption gaps within otherwise well-typed modules.
- **Exploration data functions** (`carrying_capacity`, `push_drag_lift`, `is_encumbered`, jumping/falling/travel/light) compute correctly in isolation; the only defect is that combat/movement never *invokes* `is_encumbered` (Workstream D).