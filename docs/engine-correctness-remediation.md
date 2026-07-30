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
| **A** ✅ done — TurnState lifecycle: split per-turn economy state from cross-turn effect state with per-effect expiry | ACT-03 ✅ done, ACT-19 ✅ done | M |
| **C** ✅ done — Weapon-registry ↔ attack-resolution bridge (`WeaponData` → `AttackDetails`, incl. dm-api) | EQP-01 ✅ done, EQP-08 🟡 partial (Heavy wired; Ammunition/Loading deferred to D), ACT-18 ✅ done | L |
| **D1** ✅ done — Worn-armor identity + equip/unequip AC recompute + shield-as-body guard + `CharacterSheet.size` | EQP-04 ✅ done (worn-armor stored; Str-min speed penalty in D2), EQP-06 ✅, EQP-07 🟡 (AC recompute done via `worn_armor`/`worn_shield`; `InventoryItem.equipped`-driven weapon selection deferred to D3) | L |
| **F.1** — Make `_apply_damage_impl` return post-mitigation damage; route all damage paths through one concentration check | groundwork for SPL-02, EFF-07 | M |

**Exit criteria:** Help/Sap/Vex/Hide effects survive `begin_turn` and are consumed on the correct later turn; an attack built through dm-api carries mastery/properties/proficiency from the registry; every damage path reports effective (post-immunity/resistance) damage.

### Phase 2 — Action economy (criticals for martials)

Depends on Phase 1 (A). Split of Workstream **B**:

| Work | Findings | Size |
|------|----------|------|
| **B1** ✅ done — Extra Attack (attacks-per-action by class level), validation-before-consumption, Nick economy | ACT-01, ACT-05, ACT-08 | M |
| **B2** ✅ done — Reaction slot, opportunity attacks, Ready semantics | ACT-02, ACT-06 | M |
| **B3** ✅ done — Spell casting-time → economy slot; 2024 one-slot-spell-per-turn; TWF Light validation | SPL-03, SPL-06, ACT-04 | M |

**Exit criteria:** a level-5 fighter makes exactly 2 attacks ✅; opportunity attacks consume the reaction and respect one-per-round ✅; Healing Word leaves the action free ✅; a second leveled spell in a turn is rejected ✅.

### Phase 3 — Concentration & condition criticals

| Work | Findings | Size |
|------|----------|------|
| **F.2–F.4** ✅ save-on-damage/break-on-incapacitation/DC-cap done, end-effects-on-loss (SPL-07) still open — Concentration: save on spell damage, break on incapacitation, end effects on loss, DC cap 30 | SPL-02 ✅, EFF-01 ✅, SPL-07 (open), EFF-07 ✅, SPL-16 ✅ | M–L |
| **I2** ✅ done — Centralize condition application so immunities apply on every inflicting path | EFF-10 ✅ done | M |
| **J (carve-out)** — Revival effect type: Revivify/Raise Dead/Resurrection/True Resurrection actually revive ✅ done | SPL-01 | S |

**Exit criteria:** Fireball forces a concentration save; stunning a caster drops their spell; losing Hold Person un-paralyzes the target (still open, blocked on SPL-07); condition-immune creatures cannot receive the condition from any path ✅; Revivify returns a dead target to 1 HP.

### Phase 4 — Combat-affecting majors

| Work | Findings | Size |
|------|----------|------|
| **G** ✅ done — Death & damage ordering: instant death at 0 HP, death-save reset on 3 successes, temp HP at 0 HP, crit doubles dice only | EFF-08 ✅, EFF-09 ✅, EFF-13 ✅, ACT-09 ✅ | M |
| **D1** ✅ done / **D2** ✅ done — Worn-armor identity ✅, equip/unequip AC recompute ✅, shield-as-armor guard ✅; Str-min speed ✅, stealth disadvantage ✅, armor-training penalties ✅ | EQP-06 ✅, EQP-07 🟡 (AC recompute done; `InventoryItem.equipped` weapon selection in D3), EQP-04 ✅, EQP-02 ✅, EQP-03 ✅ | L |
| **E** ✅ done — Mastery mechanics (Slow/Cleave/Graze/unarmed-strike + Push & grapple/shove size gates, now that `CharacterSheet.size` exists) | ACT-07 ✅, ACT-17 ✅, ACT-16 ✅, ACT-11 ✅ | M |
| **I1** ✅ done — Stale 2024 condition definitions: Stunned speed, Petrified immunity, Unconscious→Prone, single source of truth | EFF-06 ✅, EFF-05 ✅, EFF-14 ✅, EFF-11 ✅ | S–M |
| **H** — Check/initiative correctness ✅ done (independent quick win; can land in any phase) | ACT-10, ACT-20, ACT-12 | S |

**Exit criteria:** massive damage at 0 HP kills; crits double dice only; heavy armor slows weak wearers and noisy armor hinders Hide; Slow/Push/Cleave have table effects; save proficiency no longer leaks into ability checks.

### Phase 5 — Spell system depth

| Work | Findings | Size |
|------|----------|------|
| **J (remainder)** — SpellData vocabulary: non-damage effects, multi-beam, on-hit riders, staged/choice conditions, divided healing, HP-max buffs, thresholds; spell-attack adv/disadv + crits | SPL-08, SPL-09, SPL-10, SPL-11, SPL-12, SPL-13, SPL-14, SPL-18, SPL-20, SPL-21 | L |
| **K** ✅ done — Slot & upcast math: pact-slot separation, flat-modifier upcast, secondary-pool upcast, Ice Storm dice, typed durations, hashable ClassLevelEntry | SPL-15 ✅, SPL-05 ✅, SPL-17 ✅, SPL-19 ✅, SPL-23 ✅, SPL-22 ✅ | M |
| **I4** — Repeat-save/save-to-end hook + exhaustion stacking (pairs with J staged conditions) | SPL-04, EFF-03 | M |
| **I3** — Condition source-identity: Grappled and Charmed relational effects | EFF-04, EFF-02 | M |

**Exit criteria:** Shield/Counterspell/Bless do something; Scorching Ray rolls per-ray; Hold Person allows end-of-turn re-saves; warlock short rests restore only pact slots; Magic Missile upcasts to 4d4+4.

### Phase 6 — Long tail & cleanup

| Work | Findings | Size |
|------|----------|------|
| **D3** ✅ done — Starting equipment/gold into inventory ✅, tool checks ✅, encumbrance consumer ✅, currency spend ✅ | EQP-05 ✅, EQP-09 ✅, EQP-10 ✅, EQP-11 ✅ | M |
| **L** ✅ done — Dodge speed-0 gate; dead spell metadata de-claimed in spec | ACT-15 ✅ done, SPL-24 ✅ de-claimed | S |
| Remaining minors folded into their workstreams | ACT-14, EFF-12, EFF-15, EFF-16 | S |

### Cross-cutting (every phase) — Workstream M: parity-spec truth

As each workstream lands, flip the corresponding `docs/phb-parity-spec.md` rows to their true status (✅ only when tested, 🟡 partial, ⬜ not done). At the end of Phase 6, add structural anti-regression tests asserting each claimed-implemented mechanic has at least one rule-code consumer, so ✅-with-no-consumer can never silently recur (harness-engineering principles #1 and #8).

---

## Workstream A — TurnState cross-turn effect lifecycle (root cause: `reset_turn` wipes persistent flags) ✅ done

**Status: ACT-03 and ACT-19 done.** `EffectExpiry` (`game-engine/src/game_engine/types/combat_state.py`) now tracks, per cross-turn flag, which combatant's turn boundary clears it and at which round; `CombatStateData.reset_turn` only clears action-economy fields and calls `_expire_cross_turn_effects`, and `grant_help`/`grant_sap`/`grant_vex` compute the correct expiry round. `dm-api/src/dm_api/api/combat.py`'s `next_turn` now runs the same `reset_turn` instead of overwriting the entry with a bare `TurnState()`. `_roll_check_impl` (`_checks.py`) now takes an optional `turn_state: TurnState | None` and consumes a pending `helped` flag for advantage, mirroring the attack-roll path in `_attacks.py::_advantage_state`; `DnD55eEngine.roll_check`/`RuleEngine.roll_check` grew the matching optional parameter, and the Hide action (`_actions.py::_resolve_non_attack`) now passes the actor's own `TurnState` so a helped character's Stealth check also benefits, matching Help's "advantage on their next roll" text. See `tests/test_engine_checks.py::TestHelpGrantsAdvantageOnChecks` and `tests/test_attacks_2024.py::TestHelpAndHideSurviveBeginTurn::test_help_grants_advantage_on_allys_hide_check`.

The single highest-leverage bug. `TurnState.reset_turn` (`game-engine/src/game_engine/types/sheets.py:276-279`) installs a fresh `TurnState()` at the start of each combatant's turn, and dm-api mirrors this (`dm-api/src/dm_api/api/combat.py:310-311`). But `helped`, `sapped`, `vexed_target_id`, and `hidden` encode effects that by rule persist across turn boundaries and are consumed on a *later* turn — so they are erased before they can ever fire.

**Findings**
- Help/Sap/Vex/Hide are no-ops in normal play (`sheets.py:276` [ACT-03], **critical**) ✅ done
- Help never grants advantage on ability checks — only attack rolls read `helped` (`_checks.py:141` [ACT-19], **minor**) ✅ done — `_roll_check_impl` takes an optional `turn_state` and consumes a pending `helped` flag for advantage; the Hide action passes its own `TurnState` through

**Fix approach**: Split action-economy state (reset every turn) from cross-turn effect state (expires by its own rule). Introduce a source/expiry model on `TurnState`: each carry-over flag records the round/turn it expires and *which* combatant's turn boundary consumes it. `begin_turn` should reset only the actor's own action-economy fields (`action_used`, `bonus_action_used`, `movement_used_ft`, `attacks_made`, `dodging`, `disengaging`, `dashing`) and refresh `reaction_used`, while leaving `helped`/`sapped`/`vexed_target_id`/`hidden` to expire on their correct triggers (Vex: end of attacker's next turn; Sap: before start of sapper's next turn; Help: start of helper's next turn; Hide: on attack/cast-with-verbal/being-found, never on turn start). Mirror the same split in `dm-api/src/dm_api/api/combat.py:310`.

**Tests**: extend `tests/test_attacks_2024.py::test_vex_grants_advantage_on_next_attack` to assert the flag *survives* `begin_turn` and is actually consumed by the follow-up attack; add tests that Help advantage survives to the ally's attack, Sap disadvantage survives to the target's attack, and a Hide grant survives until the hider attacks. Update `test_begin_turn_resets_economy` to assert economy fields reset but effect flags do not.

**Size**: M (touches `sheets.py`, `_actions.py`, `_attacks.py`, dm-api combat, tests). Prerequisite for Workstreams B and I to be observable.

---

## Workstream B — Action economy model (root cause: no attacks-per-action / reaction / casting-time concept)

**Status: B1, B2, and ACT-13 done.** `_get_available_actions_impl`
(`_actions.py`) now reads `combat_state.turn_state_for(char.id)` instead of
returning the same static action list regardless of what economy the actor
has already spent: once `ts.action_used` is set, every action-consuming
option drops out of the list except `ATTACK`, which is only omitted once
the action, bonus action, *and* Nick slot (`ts.bonus_action_used` and
`ts.nick_used`) are all spent — since Attack can still resolve as a
bonus-action off-hand or Nick swing after the main action is gone. A
pending Cleave follow-up (`ts.cleave_available` and not `ts.cleave_used`)
is now surfaced as `ActionType.CLEAVE_ATTACK`, since — unlike
`OPPORTUNITY_ATTACK`/`READIED_ACTION`, which trigger off another creature's
action rather than being chosen from this list — it's a genuine free
action available to the actor this turn. As before, this list is a
same-turn economy filter/hint; `resolve_action` still performs the full
per-submission legality check (e.g. a specific off-hand weapon's Light
property) when the caller actually submits an action. See
`game-engine/tests/test_attacks_2024_economy.py::TestAvailableActionsReflectTurnEconomy`.

**Status: B1 and B2 done.** `_attacks_per_action` (`game-engine/src/game_engine/rules/dnd_5_5e/_actions.py`) now reads the `attacks_granted` field of each class's "Extra Attack" `ClassFeatureData` (`data/class_features/*.py`) through the actor's level — Fighter 5/11/20 → 2/3/4, Barbarian/Monk/Paladin/Ranger/Artificer(Battle Smith) 5 → 2; multiclass characters take the best tier, not the sum. `_resolve_action_impl`/`_resolve_attack_action` validate the attack (`_attacks._validate_attack`) *before* touching any economy slot, so a rejected attack (unknown actor/target, total cover) costs nothing and an unknown actor creates no ghost `TurnState` — the action slot is only marked spent once `attacks_made` reaches the Extra Attack pool. Nick-mastery off-hand attacks now consume a once-per-turn `TurnState.nick_used` flag instead of the bonus action.

`provokes_opportunity_attack` and a new `resolve_opportunity_attack` now live in a new `_reactions.py` module (split out of `_attacks.py`, per the spec's original claim, to stay under the 400-line file-length guideline), dispatched through two new reaction-only `ActionType` members — `OPPORTUNITY_ATTACK` and `READIED_ACTION` — routed through the same `Action`/`resolve_action` entry point on-turn actions use (`_resolve_action_impl` dispatches them before the `action_used` gate, since they spend `TurnState.reaction_used` instead). `resolve_opportunity_attack` validates the attack, checks the mover hasn't disengaged, and rejects if the reactor's reaction is already spent this round (refreshed every `reset_turn`, i.e. at the start of the reactor's own next turn — matching the existing per-turn refresh). Ready (`ActionType.READY`) now stores a `ReadiedAction` (trigger text + target + `AttackDetails`) on `TurnState`, cleared unused at the reader's own next `reset_turn`; `ActionType.READIED_ACTION` triggers it, validating before spending the reaction, exactly as an Attack action would. Only readying an attack is supported — readying a spell or other action is out of scope (documented as such, not silently claimed).

**Status: B3 done.** Spell casting-time economy (SPL-03) was already wired at the
dm-api boundary (`dm_api.api.combat_spells._consume_casting_economy`, which
maps `CastingTime.ACTION`/`BONUS_ACTION`/`REACTION` to the matching
`TurnState` slot and 409s on a casting time too long for combat or an
already-spent slot). The 2024 one-leveled-spell-per-turn rule (SPL-06) is now
enforced in the engine's `cast_spell` (`_spell_resolution.py`): a new
`TurnState.leveled_spell_cast` flag (reset every turn alongside the other
action-economy fields) is checked before a non-cantrip, non-ritual cast
consumes a slot, and set once it does; cantrips and rituals are exempt.
Two-Weapon Fighting Light validation (ACT-04) is now enforced in
`_actions._resolve_attack_action`: a new `TurnState.light_attack_used` flag
is set when a main-hand (non-offhand, non-Nick) attack resolves with a
Light-property weapon, and a bonus-action off-hand attack is rejected unless
both the off-hand weapon has the Light property *and* `light_attack_used` is
set — i.e. a prior same-turn Attack-action attack with a Light main-hand
weapon. Nick-mastery off-hand attacks (B1, folded into the Attack action
itself) are exempt from this check since Nick only unlocks on Light weapons.

`_resolve_action_impl` (`game-engine/src/game_engine/rules/dnd_5_5e/_actions.py:121-142`) charges exactly one attack per Attack action, has no reaction slot logic, and picks the economy slot purely from `is_offhand`. The engine has no representation of how many attacks a character gets, no reaction-consuming path, and never consults spell casting time.

**Findings**
- Extra Attack impossible — one attack per Attack action (`_actions.py:134` [ACT-01], **critical**) ✅ done
- Reaction economy & opportunity attacks unimplemented (`_actions.py:196` [ACT-02], **critical**) ✅ done
- Spell `casting_time` ignored — bonus/reaction spells consume the Action (`_actions.py:133` [SPL-03], **major**) ✅ done (`dm_api.api.combat_spells._consume_casting_economy`)
- 2024 "one spell-slot spell per turn" not enforceable (`_spell_resolution.py:104` [SPL-06], **major**) ✅ done
- Ready action has no trigger/stored-action/reaction semantics (`_actions.py:189` [ACT-06], **major**) ✅ done (readied attacks only; readied spells/other actions remain out of scope)
- Action/bonus slot consumed *before* attack validation, so rejected attacks burn the slot; unknown actor creates a ghost TurnState (`_actions.py:138` [ACT-05], **major**) ✅ done
- Nick mastery: off-hand attack always consumes the bonus action (`_attacks.py:155` [ACT-08], **major**) ✅ done
- Two-weapon fighting never validates the Light property or a prior Attack action — any weapon works off-hand (`_actions.py:122` [ACT-04], **major**) ✅ done
- `get_available_actions` ignores turn state & bonus/reaction economy (`_actions.py:43` [ACT-13], **minor**) ✅ done
- Dash flag / `movement_used_ft` are dead (`_actions.py:155` [ACT-14], **minor**)

**Fix approach**:
1. ✅ Add an **attacks-per-Attack-action** computation (Fighter 5/11/20 → 2/3/4; Barbarian/Monk/Paladin/Ranger 5 → 2) driven off class levels; allow up to that many attack resolutions before setting `action_used`, tracking with the now-live `attacks_made`.
2. ✅ Reaction economy: two new reaction-only `ActionType` members (`OPPORTUNITY_ATTACK`, `READIED_ACTION`) dispatched through the existing `Action`/`resolve_action` entry point, consuming `reaction_used` instead of the on-turn action; `provokes_opportunity_attack` moved to `_attacks.py` per the spec's original claim, and a new `resolve_opportunity_attack` consumes the mover-provoker's reaction and enforces one reaction per round (refreshed by the existing per-turn `reset_turn`).
3. ✅ Thread spell `casting_time` (`CastingTime.BONUS_ACTION`/`REACTION`) into slot selection so MAGIC actions charge the correct slot (`dm_api.api.combat_spells._consume_casting_economy`); a `TurnState.leveled_spell_cast` flag rejects a second leveled-spell cast per turn (cantrips/rituals exempt), enforced in `cast_spell` (`_spell_resolution.py`).
4. ✅ **Reorder validation before consumption** in `_resolve_action_impl`: run the `actor_not_found`/`target_not_found`/`total_cover` guards first, only setting `action_used`/`bonus_action_used` after the attack is legal; do not create a TurnState for an unknown actor.
5. ✅ Nick: when the off-hand weapon has the Nick mastery unlocked, resolve the extra Light attack as part of the Attack action (do not set `bonus_action_used`), once per turn — independent of hit.
5b. ✅ Validate two-weapon fighting: a plain (non-Nick) `is_offhand` attack requires the off-hand weapon to have the Light property and a prior same-turn Attack-action attack with a Light main-hand weapon (`TurnState.light_attack_used`), reject otherwise. Now that Workstream C bridges `WeaponData.properties` into `AttackDetails` in the real dm-api pipeline, this has real-play effect; engine-level callers can still pass `properties` explicitly.
6. ✅ Ready: `TurnState.readied: ReadiedAction | None` stores the trigger text, target, and `AttackDetails`; `ActionType.READIED_ACTION` resolves it later via the same reaction path as opportunity attacks, and an unused readied action is cleared by `reset_turn` (lost at the start of the readier's own next turn, per the 2024 rule). Only readying an attack is supported — readying a spell (which would need concentration wiring into a reaction cast) is left as a documented gap, not silently claimed.
7. ✅ Make `get_available_actions` consult `turn_state_for` and surface remaining action/bonus/reaction options.

**Tests**: ✅ level-5 fighter makes 2 attacks then is rejected on the 3rd; ✅ an attack behind total cover leaves `action_used=False` and a follow-up legal attack succeeds; ✅ Nick off-hand attack leaves `bonus_action_used=False`; ✅ opportunity attack consumes reaction and a second in the same round is rejected (engine tests in `test_attacks_2024.py::TestOpportunityAttacks`, API tests in `dm-api/tests/test_combat_actions.py`); ✅ a disengaged mover provokes no opportunity attack and spends no reaction; ✅ Ready stores a trigger+attack, `READIED_ACTION` fires it once via the reaction, and an unused readied action is lost at the start of the readier's own next turn (`test_attacks_2024.py::TestReadiedActions`); ✅ Healing Word (bonus) leaves the action free (`dm-api/tests/test_combat_spells.py::test_bonus_action_spell_uses_bonus_action`); ✅ a second leveled spell same turn is rejected while a cantrip/ritual is allowed (`test_spellcasting.py::TestOneLeveledSpellPerTurn`); ✅ an off-hand attack with a non-Light weapon, or with no prior Light main-hand attack this turn, is rejected (`test_attacks_2024.py::TestTwoWeaponFighting`); ✅ spending the action drops Dash/Dodge/Hide/etc. from `get_available_actions` but keeps `ATTACK` available for a bonus-action/Nick swing, `ATTACK` itself drops once the bonus action and Nick slot are both spent, and a pending Cleave follow-up surfaces as `CLEAVE_ATTACK` until used (`test_attacks_2024_economy.py::TestAvailableActionsReflectTurnEconomy`).

**Size**: L. Depends on Workstream A (shared `TurnState` refactor). This is the largest single workstream; split into B1 ✅ (Extra Attack + validation ordering + Nick — done), B2 ✅ (reactions/opportunity/Ready — done), B3 ✅ (spell casting-time + one-slot-per-turn + TWF Light validation — done).

---

## Workstream C — Weapon registry ↔ attack-resolution bridge (root cause: `WeaponData`/`get_weapon` never consumed) ✅ done

The audit's most consequential equipment finding: nothing constructed an `AttackDetails` from a `WeaponData`. `dm-api`'s `build_attack_details` (`dm-api/src/dm_api/api/combat_utils.py`) copied only 5 request fields and never called `get_weapon`, so in the real pipeline `mastery` was always `None`, `properties` always empty, and `proficient` always `True`. The mastery/property/proficiency layer was dead code outside hand-crafted unit tests.

**Findings**
- Weapon registry never consumed by attack resolution — masteries/proficiency/stats can't fire in real play (`data/weapons.py:529` [EQP-01], **critical**) ✅ done
- `WeaponProperty` enum & `AttackDetails.properties` have zero consumers: Heavy/Loading/Ammunition/Versatile/Finesse/Reach/Thrown unimplemented (`sheets.py:291` [EQP-08], **major**) 🟡 partial — Heavy, Versatile, Finesse now have consumers; Ammunition/Loading (needs an inventory-backed ammo count) deferred to pair with Workstream D's inventory work; Reach/Thrown are positional/targeting concerns out of this engine's theater-of-mind scope
- Off-hand attack drops a *negative* ability modifier (`_attacks.py:313` [ACT-18], **minor**) ✅ done

**Fix approach**: `game_engine.rules.dnd_5_5e._weapon_bridge.to_attack_details(weapon: WeaponData, actor, *, is_offhand, two_handed, is_ranged) -> AttackDetails` populates `mastery` (checked against actor's unlocked masteries at resolution time, same as before), `properties`, `damage_dice` (swaps to `versatile_dice` when two-handed)/`damage_type`, `attack_ability` (Finesse → best of STR/DEX), and `proficient` (derived from `actor.weapon_category_training` vs the weapon's `WeaponCategory`). `dm-api`'s `build_attack_details` now takes the acting `CharacterSheet` and calls the bridge via `get_weapon(req.weapon_name)`, falling back to the raw (now-widened, with `is_offhand`/`two_handed`) request fields only for weapons outside the registry. `_advantage_state` (`_attacks.py`) now consumes **Heavy**: disadvantage when the ability score used for the attack roll is below 13. `_attacks.py`'s off-hand damage step now zeroes the ability modifier only when it is **> 0**, preserving negative modifiers.

**Tests**: `game-engine/tests/test_weapon_bridge.py` — mastery/properties/proficiency/Finesse/Versatile derivation from the registry; `dm-api/tests/test_combat_utils.py::TestBuildAttackDetails` — registry lookup through `build_attack_details`, non-registry fallback; `game-engine/tests/test_attacks_2024.py` — Heavy disadvantage, negative off-hand modifier preserved.

**Size**: L. Foundational for Workstreams D and the mastery half of E to have any real-play effect; do C before E.

---

## Workstream D — Armor, proficiency & inventory effects (root cause: armor/inventory data stored but never applied; no worn-armor identity)

**D1 status: ✅ done.** `CharacterSheet` now stores worn-armor identity
(`worn_armor: str | None`, `worn_shield: bool`) and a `size: CreatureSize`
field; `rules.dnd_5_5e` exposes `equip_armor`/`unequip_armor`/`equip_shield`/
`unequip_shield` (+ the shared `compute_sheet_ac` helper, which layers
barbarian/monk Unarmored Defense on the armor table) so AC recomputes on
every equip change. `compute_armor_class` now raises on a shield passed as
body armor, and `build_character` warns and treats `armor_name='Shield'` as
unarmored+shield rather than yielding AC 2.

**D2 status: ✅ done.** `_equipment.py` gained three consumers of the
worn-armor identity D1 introduced: `armor_speed_penalty`/`effective_speed`
(−10 ft while STR < the worn armor's `min_strength`, layered onto
`CharacterSheet.effective_speed` — a pure types-layer property with no
armor-registry visibility — from the rules layer instead, and consumed by
`_actions._effective_speed` so Dash's movement reflects it too),
`has_stealth_disadvantage` (consumed by the Hide action in `_actions.py`,
passed as `disadvantage` to `_roll_check_impl`), and `is_armor_untrained`
(refactored out of D1's existing `equip_armor` warning — armor-category not
in `CharacterSheet.armor_training`). `is_armor_untrained` is now also
consumed by `_checks._roll_check_impl` and `_saves._roll_saving_throw_impl`
(disadvantage on STR/DEX checks and saves only) and by
`_spell_resolution.cast_spell` (rejects the cast outright, cantrips and
rituals included, with a new `"armor_untrained"` error code) — the 2024 PHB
armor-training penalty.

**D3 status: ✅ done.** A new `_starting_equipment.py` module
(`resolve_starting_equipment`) expands a background's free-text
`equipment` list — gold entries (`"14 gp"`), pack names (`"Explorer's
Pack"` → its registered `PackData.contents`), and quantity-bearing items
(`"Dagger (2)"`) — into `list[InventoryItem]` + `Currency`, called from
`build_character` right after `equip_armor` (EQP-05). A trailing
parenthetical is only read as a quantity when it's purely digits;
anything else (`"Book (prayers)"`, `"Artisan's Tools (choice)"`) stays
part of the item name rather than being guessed at. `CharacterSheet.to_dict()`
already round-trips `inventory`/`currency` and dm-api already persists
`stats=sheet.to_dict()` verbatim, so no dm-api change was needed — a built
character's inventory/gold show up in the DB automatically. Tool-check
ability wiring (EQP-09) is done (see below). **Encumbrance (EQP-10) is now
wired into `_equipment.effective_speed`**, which caps speed at 5 ft
whenever `exploration.is_encumbered` is true — the same layering point
already used for the under-Strength armor penalty, so both combat's
`_actions._effective_speed` and any other caller of `_equipment.effective_speed`
get the cap for free. **Currency debit/credit (EQP-11)** is a new
`_currency.py` module: `to_copper`/`from_copper` normalize the five
denominations through a single copper-piece total (electrum is never
reintroduced when making change — it collapses into gp/sp/cp, matching how
most tables actually handle the coin in practice), `can_afford`/`spend_gold`/
`credit_gold` operate on a `Currency` in place, and `purchase_item` ties a
looked-up `WeaponData`/`ArmorData`/`GearData`/`ToolData`/`PackData.cost_gp`
to both a debit and an inventory add (pack purchases expand into their
contents exactly like `resolve_starting_equipment`, priced at the pack's own
`cost_gp` rather than the sum of its contents). An unaffordable or unknown
item leaves both currency and inventory untouched — no partial spend.

Originally, `build_character` applied AC once at creation and discarded the armor — `CharacterSheet` had no worn-armor field — so Str-minimum speed penalties, stealth disadvantage, and armor-training penalties were structurally unreachable, and AC never recomputed.

**Findings**
- Heavy-armor Str minimum never reduces speed; worn-armor identity never stored (`character_builder.py:269` [EQP-04], **major**) ✅ done — worn-armor identity (D1) and the Str-min speed penalty (D2, `_equipment.effective_speed`) are both wired
- Armor `stealth_disadvantage` never consumed — Hide ignores noisy armor (`_actions.py:179` [EQP-02], **major**) ✅ done — Hide passes `has_stealth_disadvantage(actor)` as `disadvantage`
- Armor training & weapon proficiency have no in-play effect (`character_builder.py:228` [EQP-03], **major**) ✅ done — weapon proficiency already fed the attack-roll proficiency bonus (Workstream C's `AttackDetails.proficient`); armor training now disadvantages STR/DEX checks/saves and blocks casting (D2, `is_armor_untrained`)
- `InventoryItem.equipped` never read — no equip/unequip recomputes AC or selects weapons (`character_state.py:163` [EQP-07], **major**) 🟡 equip/unequip now recompute AC (D1 ✅, via `worn_armor`/`worn_shield` + `_equipment.equip_armor`); the `InventoryItem.equipped` flag itself is still inert and weapon selection is deferred to D3
- Passing `'Shield'` as body armor yields AC 2 (`data/armor.py:194` [EQP-06], **major**) ✅ done
- Starting equipment & gold never applied to inventory/currency (`character_builder.py:284` [EQP-05], **major**) ✅ done — `_starting_equipment.resolve_starting_equipment`, wired into `build_character`
- `is_encumbered` has no rule consumers (`exploration.py:44` [EQP-10], **minor**) ✅ done — `_equipment.effective_speed` caps speed at 5 ft while `is_encumbered(sheet, sheet.size)` is true
- `Currency.total_gp` never consumed; no purchase/spend logic (`character_state.py:141` [EQP-11], **minor**) ✅ done — new `_currency.py`: `spend_gold`/`credit_gold` debit/credit a `Currency` in place, `purchase_item` links registry `cost_gp` to a debit + inventory add
- `ToolData.ability` dead — tool checks ignore governing ability & proficiency (`data/gear.py:28` [EQP-09], **minor**) ✅ done — `_roll_check_impl` (`_checks.py`) now falls back to `data.gear.get_tool` when a check's `skill` string isn't a `Skill`/`Ability` name, using the tool's governing ability and `char.tool_proficiencies` (case-insensitive) instead of skill proficiency

**Fix approach**:
1. ✅ Add a **worn-armor / equipped-weapon** concept to `CharacterSheet` (store the equipped armor and shield identity, not just the derived AC) plus an equip/unequip API that recomputes AC via `compute_sheet_ac`. *(equipped-weapon selection itself is deferred to D3.)*
2. ✅ Guard `compute_armor_class` against `ArmorCategory.SHIELD` passed as body armor (raises `ValueError`, no longer returns base_ac 2); `build_character` warns and treats `armor_name='Shield'` as unarmored+shield.
3. ✅ Feed worn armor into `effective_speed` (−10 ft while STR < `min_strength`, `_equipment.effective_speed`) and into the Hide check (`disadvantage=True` when the worn armor has `stealth_disadvantage`, `_equipment.has_stealth_disadvantage`).
4. ✅ Apply the 2024 **armor-training** penalty: disadvantage on STR/DEX D20 tests (`_checks.py`, `_saves.py`) and can't-cast (`_spell_resolution.cast_spell`) while wearing untrained armor, via `_equipment.is_armor_untrained`.
5. ✅ Expand `BackgroundData.equipment` (including gold and PACK contents) into `inventory`/`currency` at build time (`_starting_equipment.resolve_starting_equipment`); persisted automatically via dm-api's existing `stats=sheet.to_dict()`, not just as a string column.
6. ✅ Add tool-check resolution mapping tool name → `ToolData.ability` + proficiency (`_checks.py`, EQP-09). ✅ Consume `is_encumbered` in `effective_speed` (`_equipment.py`, EQP-10). ✅ Add currency debit/credit and a registry-priced purchase path (`_currency.py`, EQP-11).

**Tests**: ✅ STR-10 fighter in Chain Mail has speed 20 (`test_equipment_2024.py::TestArmorTrainingAndStrengthPenalties`); ✅ Hide with noisy armor worn rolls with disadvantage (`test_attacks_2024_economy.py::TestHideConsumesArmorStealthPenalty`); ✅ untrained armor gives disadvantage on STR/DEX checks (`test_engine_checks.py::TestArmorTrainingDisadvantage`) and saves (`test_saves_death.py::test_untrained_armor_disadvantages_strength_and_dex_saves`) but not mental ones, and blocks casting including cantrips (`test_spellcasting.py::TestCasting::test_untrained_armor_blocks_leveled_cast`/`test_untrained_armor_blocks_cantrip_too`); ✅ `armor_name='Shield'` no longer yields AC 2; ✅ a built character has non-empty inventory and starting gp, and pack names expand into their contents (`test_starting_equipment.py`); ✅ over-capacity inventory caps speed at 5 ft, stacking correctly with the under-Strength armor penalty and never raising an already-zero speed (`test_equipment_2024.py::TestEncumbrance`); ✅ coin conversion round-trips, `spend_gold`/`credit_gold` debit/credit correctly and reject overspend, and `purchase_item` debits + adds inventory (including pack expansion) or leaves both untouched on failure (`test_currency.py`); equipping/unequipping armor recomputes AC.

**Size**: L. The worn-armor field (step 1) is shared infrastructure; the Str-min/stealth/training consumers depend on it. D1 ✅ (worn-armor field + AC recompute + shield guard), D2 ✅ (speed/stealth/training consumers), D3 ✅ done (EQP-05 starting equipment/currency, EQP-09 tool checks, EQP-10 encumbrance, EQP-11 currency spend).

---

## Workstream E — Weapon mastery mechanics (root cause: masteries write log keys nothing reads; missing TurnState fields & size checks)

**Status: ✅ done.** Slow, Cleave, Graze, and the unarmed-strike default
landed earlier; Push's size gate and the grapple/shove size gate (ACT-16) are
now closed, unblocked by the `CharacterSheet.size: CreatureSize` field added
in Workstream D1. `CreatureSize.rank` gives an ordinal for the two size
comparisons: Push moves a target only if it is Large or smaller
(`_masteries.py`), and unarmed Grapple/Shove rejects a target more than one
size larger than the attacker (`_attacks._resolve_unarmed_special`). PC
combatants get their size from their species' primary `size_options` entry at
build time; any sheet defaults to `CreatureSize.MEDIUM`.

`CombatStateData.grant_slow` (mirroring `grant_sap`) now sets
`TurnState.slowed`/`slowed_expiry` on the *target* on a Slow-mastery hit,
expiring at the start of the *attacker's* next turn exactly like Sap. Since
`CharacterSheet.effective_speed` is a pure sheet property with no combat-state
visibility, a new `_actions._effective_speed(actor, ts)` helper layers the
Slow penalty on top of it; Dash's flavor text now calls this instead of the
bare property (the only other consumer of speed in the engine — see the
"Verified Correct" section: this engine doesn't validate movement against
position, so Slow's effect is real but, like Dash, decorative beyond the
`TurnState`/log layer). Cleave now grants a genuine once-per-turn free
follow-up: a Cleave-mastery hit sets `TurnState.cleave_available` and records
the original target (`cleave_original_target_id`) in `_masteries.py`; a new
`ActionType.CLEAVE_ATTACK`, dispatched in `_actions.py` and resolved by
`_reactions.resolve_cleave_attack`, validates the follow-up targets a
*different* creature, forces `AttackDetails.is_cleave_followup=True` (so the
ability modifier can't be included even if the caller tries), and — because
`_resolve_attack` unconditionally increments `TurnState.attacks_made` for
every call regardless of caller — undoes that increment afterward so a Cleave
fired between two Extra Attack swings doesn't prematurely exhaust the pool
(see `tests/test_weapon_masteries_2024.py::test_cleave_followup_between_extra_attack_swings_does_not_exhaust_pool`,
which reproduces exactly that interaction). `_masteries.py` is a new module
(on-hit mastery effects split out of `_attacks.py`, which was already at the
400-line file-length guideline before this workstream — the same rationale
`_reactions.py` used).

**Findings**
- Slow, Push, Cleave are log-only with no mechanical effect (`_attacks.py:149` [ACT-07], **major**) ✅ Slow, Cleave, and Push all done — Push now gates on target size (Large or smaller) via `CharacterSheet.size`/`CreatureSize.rank`
- Default unarmed strike deals 1d4 + STR instead of the 2024 fixed 1 + STR (`combat_state.py:243` [ACT-11], **major**) ✅ done — `AttackDetails.damage_dice` default changed to `DiceNotation("1d1")` (always rolls 1), reusing the existing dice-notation plumbing rather than adding a flat-damage field; a scaling override (e.g. Monk martial arts) still just passes its own `damage_dice`
- Graze invents a minimum-1 damage floor (`_attacks.py:290` [ACT-17], **minor**) ✅ done
- Unarmed grapple/shove ignores the size restriction (`_attacks.py:186` [ACT-16], **minor**) ✅ done — `_resolve_unarmed_special` rejects a target more than one size larger than the attacker (`CharacterSheet.size`/`CreatureSize.rank`)

**Fix approach**:
- ✅ **Slow**: reduce target speed by 10 ft until the start of the attacker's next turn (`CombatStateData.grant_slow` + `TurnState.slowed`/`slowed_expiry`, consumed by `_actions._effective_speed`).
- ✅ **Cleave**: allow the follow-up attack roll against a second creature (damage without ability modifier), once per turn, without touching the Extra Attack pool (`ActionType.CLEAVE_ATTACK` / `_reactions.resolve_cleave_attack`). This engine has no positional/reach model, so "within reach" isn't validated — only "a different creature than the original target" is.
- ✅ **Push**: gate on target `CreatureSize` (Large or smaller), via `CharacterSheet.size` / `CreatureSize.rank`; Huge/Gargantuan targets log `pushed_ft: 0`, `push_too_large: True`.
- ✅ **Graze**: deal damage exactly equal to the ability modifier (`max(0, ...)`); the invented `max(1, ...)` floor is gone, so `if graze_damage:` and its concentration check correctly no-op at 0.
- ✅ **Grapple/Shove**: reject when the target is more than one size larger than the attacker (`_resolve_unarmed_special` returns a `target_too_large` failure).
- ✅ **Unarmed strike damage**: default `AttackDetails.damage_dice` is now `DiceNotation("1d1")` (1 + ability modifier, no d4).

**Tests**: ✅ Slow reduces and later restores speed (`test_weapon_masteries_2024.py::test_slow_reduces_speed_until_attackers_next_turn`); ✅ Cleave's second attack resolves without consuming the action or the Extra Attack pool, rejects the same target, and rejects a second use (`test_weapon_masteries_2024.py`, `TestWeaponMasteries` Cleave tests); ✅ Graze with STR 10/6 deals 0 (`test_graze_deals_zero_with_negative_ability_mod`, replacing the deleted `test_graze_minimum_damage_is_1_with_negative_ability_mod`, which codified a nonexistent rule); ✅ the `AttackDetails()` default is `"1d1"` (`test_combat_state.py::TestAttackDetails::test_defaults`). ✅ Push moves a Large target but not a Huge one, and Grapple/Shove is rejected against a target 2+ sizes larger but allowed one size larger (`test_weapon_masteries_2024.py::test_push_*`, `test_attacks_2024.py::test_grapple_rejected_when_target_more_than_one_size_larger` / `test_shove_allowed_when_target_exactly_one_size_larger`).

**Size**: M — ✅ fully done. Workstream C (masteries reach the resolver)
enabled the earlier effects; the size-gated remainder (Push, grapple/shove)
landed once Workstream D1 added `CharacterSheet.size`. PC size is wired from
species `size_options` at build time; monster→sheet size wiring lives in
dm-api (any sheet defaults to `CreatureSize.MEDIUM`).

---

## Workstream F — Concentration lifecycle (root cause: save-on-damage, break-on-incapacitation, and end-on-loss are unwired for spells)

**Status: F.1/F.2/F.4 done (steps 1, 2, 4 below); F.3 (step 3, end-on-loss) remains open.**
`_apply_damage_impl` (`_damage.py`) is now a thin wrapper around a new
`_apply_damage_effective`, which mutates the target exactly as before but
*returns* the effective (post-immunity/resistance/vulnerability) damage
int. `_concentration_check` (moved from `_attacks.py` into `_damage.py` so
both the weapon and spell paths can share it) takes that effective amount,
so an immune target now takes 0 and rolls no save (EFF-07) and a resisted
hit is DC'd off the halved figure. `_attacks.py`'s weapon-hit and Graze
paths, and `_spell_resolution.py`'s `cast_spell` (one combined save across
a spell's primary + secondary damage pools, since they're one hit), all
route through it. `concentration_save_dc` is now `min(30, max(10, damage
// 2))` (SPL-16). A new `_break_concentration_on_incapacitation` helper in
`_conditions.py` — driven by the same `Condition.prevents_action` set
`CharacterSheet.can_act` already uses, so there's one source of truth for
"Incapacitated, Stunned, Paralyzed, Petrified, Unconscious" — is called
from both `_apply_condition_impl` and the spell-rider condition-apply loop
in `_spell_resolution.py`, so a Stunned/Paralyzed/etc. rider breaks the
*target's own* concentration (EFF-01) regardless of which of those two
paths applied it. `SpellTargetOutcome` gained
`concentration_save_dc`/`concentration_save_total`/`concentration_broken`
fields, threaded through to the dm-api `cast-spell` combat-log entry so the
fix is observable at the API boundary, not just in engine unit tests. See
`game-engine/tests/test_spellcasting.py::TestConcentration`,
`test_engine_damage_conditions.py::TestApplyDamageEffectiveAmount` /
`TestApplyCondition::test_incapacitating_condition_breaks_concentration`,
`test_saves_death.py::test_concentration_dc_caps_at_30`.

Concentration is tracked as a bare string with three independent gaps: damage from spells never forces the save, incapacitating conditions never break it, and losing it never removes its effects.

**Findings**
- Spell damage never triggers a concentration save on the target (`_spell_resolution.py:163` [SPL-02], **critical**) ✅ done
- Gaining Incapacitated/Stunned/Paralyzed/Petrified/Unconscious never breaks concentration (`_conditions.py:38` [EFF-01], **critical**) ✅ done
- Breaking/replacing concentration never ends the spell's effects on targets (`_spell_resolution.py:114` [SPL-07], **major**) — still open
- Concentration save uses pre-mitigation damage; immune targets still roll & can lose it (`_attacks.py:323` [EFF-07], **major**) ✅ done
- Concentration save DC missing the 2024 max of 30 (`_damage.py:147` [SPL-16], **minor**) ✅ done

**Fix approach**:
1. ✅ Make **`_apply_damage_impl` return the effective (post-immunity/resistance) damage**, and route *every* damage path — `_spell_resolution.py`, `engine.apply_damage`, and the weapon path — through a single `_concentration_check` call using that effective amount (fixes both the spell-damage gap and the pre-mitigation DC bug; a 0-damage immune hit forces no save).
2. ✅ In `_apply_condition_impl` and the spell-rider apply path, **break concentration when the applied condition includes Incapacitated** (Incapacitated, Stunned, Paralyzed, Petrified, Unconscious).
3. **Still open.** Track **concentration → applied effects**: record, per concentration spell, which target conditions/durations it created (a caster→effects back-reference), and remove them when `concentrating_on` is cleared or replaced. This needs an effect-provenance model the engine doesn't have yet (which spell/cast instance created which condition/duration entry) — deferred rather than half-built, and still pairs naturally with Workstream I's save-to-end tracking.
4. ✅ Clamp `concentration_save_dc` to `min(30, max(10, damage // 2))`.

**Tests**: ✅ Fireball on a Haste-concentrating target forces a CON save and can drop Haste; ✅ stunning a Bless-concentrating caster ends Bless (via a spell rider); ✅ a fire-immune target takes 0 and rolls no save; ✅ a 62-damage hit yields DC 30, not 31. Still unwritten (blocked on step 3): losing concentration on Hold Person immediately removes the target's Paralyzed.

**Size**: M–L. Step 1 (effective-damage return) is a shared refactor also relied on by Workstream G — G can now reuse `_apply_damage_effective` instead of duplicating the immunity/resistance walk. Step 3 (effect back-reference) is the largest piece and remains the reason this workstream isn't fully closed.

---

## Workstream G — Damage, death saves & instant-death ordering (root cause: 0-HP branch ordering and missing HP-max checks) ✅ done (EFF-08, EFF-09, EFF-13, ACT-09); EFF-16 deliberately not implemented

Discrete correctness bugs in `_damage.py`/`_death.py` around the 0-HP state.

**Status.** `_apply_damage_effective` (`_damage.py`) now absorbs temp HP
*before* branching on whether the target is already at 0 HP, and the
already-at-0-HP branch itself now checks the post-temp-HP leftover damage
against `hp_max` for instant (massive-damage) death before falling back to
the ordinary 1-failure/2-on-crit accumulation — matching the "drop to 0
with leftover ≥ hp_max" branch that already existed for the positive-HP
case. `_roll_death_save_impl` (`_death.py`) now resets both counters to 0
on the third success, matching `_stabilize_impl`, so a later hit while
stable starts a fresh set of failures instead of resuming from whatever
count was on the board pre-stabilization. `_resolve_attack` (`_attacks.py`)
now reads `AttackDetails.damage_dice`'s cached `num_dice`/`sides`/`modifier`
directly and rolls the crit-extra dice with no modifier, so a crit on
`1d6+2` deals `(1d6 + 1d6) + 2`, not `(1d6+2) + (1d6+2)`. See
`tests/test_saves_death.py::test_massive_damage_while_already_dying_is_instant_death`
/ `test_temp_hp_absorbs_damage_while_already_dying` /
`test_three_successes_resets_counters`,
`tests/test_attacks_2024.py::TestCoverAndCrits::test_critical_hit_doubles_dice_not_flat_modifier`.

**EFF-16 ("long rest grants full benefits to a character at 0 HP") was
investigated and deliberately left as-is, not fixed.** Strict 2024 RAW
requires at least 1 HP at the start of a rest to gain its benefits, but
gating `long_rest` on `hp_current >= 1` would strand a stabilized 0-HP
character forever, since this engine has no natural-recovery rule (regain
1 HP after 1d4 hours) to fall back on. The existing regression tests
`test_long_rest_clears_death_saves_and_unconscious_for_stable_character`
and `test_long_rest_clears_prone_from_unconscious_fall`
(`game-engine/tests/test_resting_exploration.py`) were added specifically
to guard the current "a long rest wakes a stable character" behavior — this
is a maintainer-facing design decision (playability over strict RAW), not
a silent oversight, so it's called out here rather than "fixed" against
the grain of an existing anti-regression test. See the docstring on
`resting.long_rest` for the same note in code.

**Findings**
- Damage at 0 HP ≥ HP max does not kill instantly (`_damage.py:70` [EFF-08], **major**) ✅ done
- Death save counters not reset when a character becomes stable via 3 successes (`_death.py:63` [EFF-09], **major**) ✅ done
- Temp HP ignored for a creature already at 0 HP (`_damage.py:81` [EFF-13], **minor**) ✅ done
- Critical hits double the flat modifier baked into damage-dice notation (`_attacks.py:317` [ACT-09], **major**) ✅ done — reachable via monster data (`data/monsters.py:78,86,122,130`) carrying `1d4+2`/`2d8+4` and dm-api's free-string `damage_dice`
- Long rest grants full benefits to a character at 0 HP (`resting.py:106` [EFF-16], **minor**) — investigated, deliberately not changed (see above); conflicts with an existing intentional/tested behavior

**Fix approach**:
- ✅ Reorder `_apply_damage_impl`: apply **temp-HP absorption first** (at any HP total), then in the 0-HP branch compare *effective* damage against `hp_max` for instant death (two failures on a crit that reaches 3+ still applies), then convert to death-save failures only for leftover damage.
- ✅ On the third death-save success in `_roll_death_save_impl`, **reset successes and failures** (match `_stabilize_impl`).
- ✅ Fix critical hits to double **only the dice**, not the notation's flat modifier: on a crit roll the dice count twice but add the flat modifier once (and add the ability modifier once). `AttackDetails.damage_dice` is a `DiceNotation` with cached `num_dice`/`sides`/`modifier`, so no schema change was needed — `_resolve_attack` just reads those instead of re-rolling the full notation string twice.
- ~~Gate `long_rest` on `hp_current >= 1`~~ — not done; see status note above.

**Tests**: ✅ dying PC (hp_max 20) hit for 25 dies instantly; ✅ dying PC with temp HP 10 hit for 5 loses temp HP and takes no death-save failure; ✅ 2-successes-2-failures-then-1-more-success leaves a stable character at 0/0 counters who survives 1 subsequent damage without dying from the stale failure count; ✅ a `1d6+2` crit deals dice-doubled-plus-single-modifier damage. Long rest at 0 HP intentionally still confers full benefits — no test added for the audit's proposed (and rejected) behavior.

**Size**: M. Shared the effective-damage-return refactor with Workstream F.

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

**Status: I1 and I2 done.** Stunned no longer sets speed to 0 (`Condition.STUNNED` removed
from `_SPEED_ZERO_CONDITIONS`, `types/enums/_core.py`); Petrified's
`ConditionEffect` no longer carries `immunity_types=[POISON, PSYCHIC]` (a
petrified creature now only *resists* poison/psychic damage like every other
type, via the pre-existing `damage_resistances_all=True`) and instead grants
immunity to the Poisoned *condition* through a new
`ConditionEffect.grants_condition_immunities` field, consulted by
`is_immune_to_condition` (`core/conditions.py`) alongside the character's own
declared `condition_immunities`; Unconscious applied directly — via
`engine.apply_condition` (`_conditions.py::_apply_condition_impl`) or a spell
rider (`_spell_resolution.py`) — now also applies Prone, mirroring the
existing `_fall_unconscious` 0-HP path (removing Unconscious does **not**
strip Prone, matching `_apply_healing_impl`'s existing and rules-correct
behavior: waking up doesn't stand you up for free); and the dead
`ConditionEffect.can_act`/`speed_zero` fields (EFF-11's duplicate, unread
source of truth) have been deleted outright — `Condition.prevents_action`/
`sets_speed_to_zero` (`types/enums/_core.py`) are the sole source, which
`core/conditions.py` cannot import without an upward Types→Core layering
violation, so deleting the dead copy (rather than merging into it) was the
layering-safe fix. See `tests/test_conditions.py::TestSetsSpeedToZero`,
`TestIsImmuneToCondition::test_petrified_grants_poisoned_immunity`, and
`tests/test_engine_damage_conditions.py::TestApplyCondition::test_unconscious_applies_prone_too`/`test_stunned_does_not_zero_speed`.

**I2**: the three combat paths that inflicted conditions by appending directly
to `target.conditions` — spell riders (`_spell_resolution.py`'s
`conditions_applied` loop, including the Unconscious→Prone carry-over), the
Topple weapon mastery, and unarmed Grapple/Shove (both in `_attacks.py`) —
now route through `_apply_condition_impl` (`_conditions.py`) instead of
mutating the list themselves, so `is_immune_to_condition` is honored on
every path, not just the explicit `engine.apply_condition` API. Each site
now records "was the condition already present" before the call and compares
after, to know whether to report it as newly applied (`outcome.conditions_applied`
/ mastery `applied` list) without needing `_apply_condition_impl` to change
its return type. This also tightens EFF-14's Unconscious→Prone coupling: it
now checks Prone immunity too, which the old duplicated per-path logic did
not. `_damage.py`'s 0-HP `_fall_unconscious` knockout path was investigated
but left as a direct append — it isn't cited by the audit's EFF-10 evidence
and centralizing it would additionally need to special-case the death-save
mutations `_apply_condition_impl` doesn't perform; flagged here rather than
folded in silently. See `tests/test_attacks_2024.py::test_topple_does_not_affect_prone_immune_target`
/ `test_grapple_does_not_affect_grappled_immune_target` / `test_shove_does_not_affect_prone_immune_target`,
`tests/test_spellcasting.py::test_condition_immune_target_is_unaffected_by_rider`
/ `test_unconscious_rider_still_respects_prone_immunity`.

**Findings**
- Combat paths bypass condition immunities (spell riders, Topple, unarmed grapple/shove) (`_spell_resolution.py:181` [EFF-10], **major**) ✅ done
- No repeat-save/save-to-end: Hold Person paralyzes for a full minute (`_conditions.py:71` [SPL-04], **major**)
- Stunned sets speed 0 (2014); 2024 Stunned doesn't prevent movement (`core/conditions.py:189` [EFF-06], **major**) ✅ done
- Petrified grants poison/psychic *damage* immunity instead of *Poisoned-condition* immunity (`core/conditions.py:147` [EFF-05], **major**) ✅ done
- Grappled (2024) missing attack-disadvantage-vs-non-grappler, escape check, end-on-grappler-incapacitated (`core/conditions.py:97` [EFF-04], **major**)
- Exhaustion can never be gained via the engine; `Condition.EXHAUSTION` is a no-op (`core/conditions.py:81` [EFF-03], **major**)
- Charmed has zero mechanical effect (`core/conditions.py:66` [EFF-02], **major**)
- Deafened has zero effect; Blinded/Deafened auto-fail of sight/hearing checks unmodeled (`core/conditions.py:74` [EFF-12], **minor**)
- Unconscious applied directly doesn't add Prone (`_spell_resolution.py:180` [EFF-14], **minor**) ✅ done
- Invisible initiative-advantage clause not implemented (`engine.py:93` [EFF-15], **minor**)
- `ConditionEffect.can_act`/`speed_zero` never read — duplicate frozensets are the live source (`core/conditions.py:41` [EFF-11], **minor**) ✅ done (fields deleted; frozensets in `types/enums/_core.py` are now the only definition)

**Fix approach**:
1. ✅ **Centralize condition application**: route spell riders, Topple, and unarmed grapple/shove through `_apply_condition_impl` (or a shared helper) so `is_immune_to_condition` is honored everywhere and future centralized handling (concentration break from Workstream F, Prone coupling, exhaustion stacking) runs uniformly.
2. ✅ **Fix stale/incorrect definitions**: remove `speed_zero=True` from Stunned (and drop it from `_SPEED_ZERO_CONDITIONS`); change Petrified from poison/psychic damage immunity to Poisoned-*condition* immunity (keep resistance-to-all); couple Unconscious → Prone. (Removal-side Prone cleanup was deliberately *not* added — `_apply_healing_impl` already leaves Prone in place when Unconscious ends via healing, which is the rules-correct behavior since standing up costs movement; coupling removal would have made waking up stand you up for free.)
3. **Add source-identity** to conditions so Grappled (disadvantage vs non-grappler, end on grappler incapacitated, escape check as an action) and Charmed (can't attack/target charmer; charmer advantage on social checks) can be honored.
4. **Add exhaustion stacking**: `apply_condition(EXHAUSTION)` increments `exhaustion_level` (cumulative, death at 6); a `gain_exhaustion` API; keep `Condition.EXHAUSTION` and `exhaustion_level` consistent (long rest should also clear the stale enum entry).
5. **Add a repeat-save / save-to-end hook**: a `SpellData.repeat_save` field and an end-of-turn re-save step in the condition-tick path for Hold Person/Monster/Confusion/Dominate/Blindness/Sleep's second save.
6. **Add sight/hearing-requirement plumbing** to `_roll_check_impl` for Blinded/Deafened auto-fail; add Invisible advantage to initiative.
7. ✅ **Eliminate the duplicate source of truth**: `ConditionEffect.can_act`/`speed_zero` deleted (dead fields, zero consumers); `CharacterSheet.can_act`/`effective_speed` already read the canonical `Condition.prevents_action`/`sets_speed_to_zero` frozensets in `types/enums/_core.py`, unchanged.

**Tests**: ✅ a PARALYZED-immune target is not paralyzed by Hold Person; ✅ a GRAPPLED-immune target isn't grappled, and a PRONE-immune target isn't Toppled or Shoved; ✅ a stunned creature can still move; ✅ a petrified creature takes halved (not zero) poison damage and can't be Poisoned; a grappled creature attacks non-grapplers at disadvantage and can escape; `apply_condition(EXHAUSTION)` twice yields level 2 with −4/−10 ft; a charmed creature can't target its charmer; ✅ a slept creature is Prone (and a Prone-immune target sleeps without falling Prone); an invisible creature rolls initiative with advantage.

**Size**: L. The centralization (step 1) and source-identity (step 3) are shared with Workstreams A and F. Split into I1 ✅ done (definition fixes: Stunned/Petrified/Unconscious/duplicate-source), I2 ✅ done (immunity centralization for spell riders/Topple/grapple-shove — concentration coupling itself was already wired directly in Workstream F, independent of this centralization), I3 (source-identity: Grappled/Charmed), I4 (exhaustion stacking + repeat-save + auto-fail hooks).

---

## Workstream J — Spell schema vocabulary gaps (root cause: `SpellData` can't express multi-target division, multi-beam, staged/choice conditions, HP-max, revival, non-damage effects, thresholds)

A long tail of individual spells misfire because the schema lacks the fields to express their rules. These are grouped because they all require extending `SpellData` + the resolver rather than per-spell data tweaks.

**Findings**
- Revivify/Raise Dead/Resurrection/True Resurrection can never revive a dead target (`_damage.py:126` [SPL-01], **critical**) ✅ done — `SpellData.revives`/`revive_full_heal` added; `cast_spell` clears `death_saves` before the healing step when `revives` is set and a target's `death_saves.is_dead` is true, then either applies the spell's normal healing (Revivify/Raise Dead → 1 HP) or sets `hp_current = hp_max` (Resurrection/True Resurrection, per their "full hit points" text — the original audit line omitted 7th-level Resurrection, which has the identical bug). `SpellTargetOutcome.revived` and flavor text surface the revival to callers. See `tests/test_spellcasting.py::TestRevival`.
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

## Workstream K — Spell slot & upcast math (root cause: pact/standard pool merge; flat-modifier upcast dropped; secondary-damage not upcast) ✅ done

Slot bookkeeping and upcast-scaling arithmetic bugs in `spellcasting.py`/`_spell_resolution.py`.

**Status: ✅ all six findings done.** `SpellSlotState` gained an `is_pact: bool
= False` field; `pact_slots_for_level` sets it, and `compute_spell_slots`
(`spellcasting.py`) now `extend`s pact slots onto the standard-slot list
instead of merging into an existing same-level entry — a Warlock/Wizard
multiclass sharing a slot level ends up with two separate `SpellSlotState`
rows at that level, one `is_pact=True`. `resting.short_rest` now restores
by iterating `char.spell_slots` for `is_pact` directly instead of
recomputing `pact_slots_for_level` and matching by slot level (the latter
could accidentally hit a same-level standard slot post-merge — the actual
SPL-15 bug). `_scale_dice` (`spellcasting.py`) gained an `extra_flat`
parameter, and `_roll_damage` (`_spell_resolution.py`) now computes it as
`upcast_per_slot.modifier * upcast_levels`, so Magic Missile's upcast
notation `"1d4+1"` scales its own `+1` alongside its die — a level-2 slot
now deals `4d4+4`, not `4d4+3`. `SpellData` gained a
`secondary_upcast_damage_per_slot: DiceNotation | None` field, independent
of the primary pool's `upcast_damage_per_slot`; the secondary-damage roll
in `cast_spell` now passes the real `upcast_levels` and this new field
instead of always `(None, 0)`. Ice Storm's dice were stale 2014 values
(`2d8`/`+1d8`) — corrected to the 2024 PHB's `2d10`/`+1d10`, with its cold
pool's `secondary_upcast_damage_per_slot` left `None` (2024 Ice Storm only
upcasts bludgeoning); Flame Strike sets
`secondary_upcast_damage_per_slot=DiceNotation("1d6")` since 2024 Flame
Strike upcasts *both* damage types. `duration_rounds` (`spellcasting.py`)
replaced its four literal-substring checks with a single regex matching any
`N round(s)`/`N minute(s)`/`N hour(s)` substring, so durations like "8
hours" (present in the spell data but previously falling through to
`None`) now parse correctly; still returns `None` for genuinely
unparseable/unbounded text ("Instantaneous", "Until dispelled"). Finally,
`ClassLevelEntry` (`types/character_state.py`) is now `@dataclass(eq=False)`
— identity-based equality/hash, since `progression.level_up` mutates
`.level`/`.subclass` in place and no code relies on value equality — which
makes it hashable and unblocks `compute_spell_slots`'s `caster_types`
override (previously `TypeError: unhashable type` on first use). See
`game-engine/tests/test_spellcasting.py::TestSlotTables::test_multiclass_pact_and_standard_slots_kept_separate`
/ `test_caster_types_override_is_hashable`,
`TestCasting::test_upcast_scales_flat_modifier` /
`test_secondary_pool_upcasts_when_configured` /
`test_secondary_pool_fixed_when_not_configured`, `TestDurationRounds`,
`game-engine/tests/test_resting_exploration.py::test_multiclass_short_rest_restores_only_pact_slots`,
`game-engine/tests/test_data_spells.py::TestSpotChecks::test_magic_missile`
/ `test_ice_storm` / `test_flame_strike`.

**Findings**
- Pact slots merged into the shared multiclass pool let a short rest restore standard slots (`spellcasting.py:146` [SPL-15], **major**) ✅ done
- Upcast drops the flat modifier: Magic Missile → 4d4+3 instead of 4d4+4 (`_spell_resolution.py:56` [SPL-05], **major**) ✅ done
- Dual-damage spells never upcast their secondary pool (Flame Strike) (`_spell_resolution.py:150` [SPL-17], **minor**) ✅ done
- Ice Storm uses stale 2014 dice (2d8/+1d8 vs 2024 2d10/+1d10) (`level4.py:40` [SPL-19], **minor**) ✅ done
- `duration_rounds` returns None for long durations, making rider conditions permanent (`spellcasting.py:180` [SPL-23], **minor**) ✅ done — general regex parsing; still `None` for genuinely unbounded/unparseable text
- `compute_spell_slots` `caster_types` override unusable — `ClassLevelEntry` is unhashable (`spellcasting.py:130` [SPL-22], **minor**) ✅ done

**Fix approach**:
- ✅ Add an `is_pact` distinction to `SpellSlotState` (kept as a separate pool, not merged) so short rest restores only pact slots and `compute_spell_slots` stops merging pact into standard.
- ✅ Add an `extra_flat` scale to `_scale_dice`/`_roll_damage` sourced from the upcast notation's own modifier (Magic Missile +1 per dart).
- ✅ Pass real `upcast_per_slot`/`upcast_levels` when rolling `secondary_damage_dice`, via a new `secondary_upcast_damage_per_slot` field (Flame Strike radiant scales too; Ice Storm's cold pool deliberately does not).
- ✅ Update Ice Storm to 2024 dice (2d10 bludgeoning + 4d6 cold, +1d10/level).
- ✅ Make `duration_rounds` parse any `N round/minute/hour` substring instead of four literal phrases (a full typed-duration schema was judged out of scope for this workstream's size; still returns `None` for unbounded/unparseable text rather than a distinct sentinel).
- ✅ Make `ClassLevelEntry` hashable (`eq=False`, identity-based) so the `caster_types` override works.

**Tests**: ✅ Warlock2/Wizard3 keeps a separate pact slot at level 1 instead of merging into the standard level-1 pool; ✅ a short rest on that multiclass restores only the pact slot; ✅ Magic Missile at a level-3 slot deals 4d4+4 (not 4d4+3); ✅ Flame Strike upcast adds 1d6 to both the fire and radiant pools; ✅ Ice Storm upcast adds 1d10 to bludgeoning only, cold stays fixed at 4d6; ✅ `duration_rounds("8 hours") == 4800`, `duration_rounds("24 hours") == 14400`, `duration_rounds("Until dispelled") is None`; ✅ the `caster_types` override no longer raises `TypeError`.

**Size**: M. Mostly independent; can proceed in parallel with J.

---

## Workstream L — Dead spell metadata & Dodge speed-zero (root cause: declared-scope data with no consumer; a small Dodge gating gap) ✅ done

Lowest-impact cleanup, partly excused by the engine's theater-of-mind scope. Grouped so the spec can be corrected honestly.

**Status.** ACT-15 fixed: all three Dodge-benefit sites — `_attacks.py`'s
attacker-disadvantage check, `_attacks.py`'s unarmed-strike (grapple/shove)
DEX-save-advantage check, and `_spell_resolution.py`'s combined
attack-disadvantage/DEX-save-advantage check — now additionally require
`target.effective_speed > 0`, so a Grappled or Restrained dodger (or one at
exhaustion level 5+ with a low enough base speed) gets neither benefit. SPL-24
was **not implemented** — per the fix approach's stated alternative, spell
component/range/area-of-effect fields remain theater-of-mind data with no
rule-code consumer, and `docs/phb-parity-spec.md`'s "Components (V/S/M),
casting time, range, areas of effect" row is corrected from a blanket ✅ to
🟡 (casting time is genuinely consumed; components/range/area are not). See
`game-engine/tests/test_attacks_2024.py::test_grappled_dodging_target_imposes_no_disadvantage`
/ `test_grappled_dodging_target_gets_no_dex_save_advantage_vs_shove`,
`game-engine/tests/test_spellcasting_effects.py::test_grappled_dodging_target_gives_no_spell_attack_disadvantage`
/ `test_grappled_dodging_target_gets_no_dex_save_advantage`.

**Findings**
- `SpellComponent`/`SpellRangeType`/`AreaShape`/`SpellSchool` and range/area/material fields never consumed (`types/enums/_core.py:202` [SPL-24], **minor**) — investigated, deliberately not implemented; parity spec corrected instead (see Status above)
- Dodge benefit not cancelled when the dodger's speed is 0 (`_attacks.py:94` [ACT-15], **minor**) ✅ done

**Fix approach**: For Dodge, gate the attacker-disadvantage (`_attacks.py:94`), DEX-save advantage (`_attacks.py:192-197`), and the spell-save-advantage path (`_spell_resolution.py:127`) on `target.effective_speed > 0` in addition to `can_act`. For spell metadata, either implement component-gating/school-keyed rules where they matter, or (given theater-of-mind scope) leave range/area unconsumed but **correct the parity spec** to stop claiming these rows are ✅.

**Tests**: ✅ a grappled dodging target no longer imposes disadvantage, nor gets DEX-save advantage, across all three Dodge-benefit sites (melee attack, unarmed grapple/shove save, spell attack/save).

**Size**: S.

---

## Workstream M — Parity-spec truth reconciliation (cross-cutting)

`docs/phb-parity-spec.md` marks nearly every audited row ✅ (masteries `:91`, weapon properties/armor Str-min `:92-93`, coinage/carrying `:94-95`, concentration `:104`, components/casting-time `:106`, action/reaction economy `:115-117`, TWF/Nick `:118`, Dodge/Disengage/Dash `:119`) while the code does not implement them. As each workstream lands, update the corresponding spec row to reflect true status (✅ only when tested, 🟡 partial, ⬜ not done). Per this repo's harness-engineering principle #1 (the repository is the single source of truth) and #8 (golden principles are mechanical), also add **structural tests** that assert each claimed-implemented mechanic actually has a consumer (e.g., grep-style tests that fail if `WeaponProperty.HEAVY`, `stealth_disadvantage`, `min_strength`, `is_immune_to_condition` in rider paths, etc. have zero rule-code readers) so these regressions can't silently recur.

**Size**: S per workstream (fold into each), plus one M to add the structural "no dead spec claim" tests.

---

## Priority Order & Dependencies

**Critical (fix first — these break ordinary play at its core):**
1. **Workstream A** ✅ done (TurnState lifecycle — `EffectExpiry` per-effect expiry, `reset_turn` splits action-economy reset from cross-turn effect expiry, dm-api's `next_turn` mirrors it) — unblocked Help/Sap/Vex/Hide *and* was a prerequisite for B, E, I.
2. **Workstream B** ✅ done — action economy: Extra Attack, reactions, casting-time, one-slot-per-turn, TWF Light validation, validation ordering — depends on A. B1 (Extra Attack + validation ordering), B2 (reactions/opportunity attacks/Ready), and B3 (spell casting-time, one-slot-per-turn, TWF Light) are all done.
3. **Workstream C** ✅ done (weapon registry ↔ resolver bridge) — masteries/proficiency/Heavy now reach the real dm-api pipeline; Ammunition/Loading tracking remains deferred to Workstream D.
4. **Workstream F** ✅ save-on-damage/break-on-incapacitation/DC-cap done (SPL-02, EFF-01, EFF-07, SPL-16) — **F.3 (end-effects-on-concentration-loss, SPL-07) remains open**, needing an effect-provenance model; effective-damage return (step 1) is shared with G.
5. **Workstream J revival carve-out** (Revivify can't revive) ✅ done — small, self-contained critical.
6. **Workstream I2** ✅ done (condition-immunity centralization — spell riders/Topple/unarmed grapple-shove now route through `_apply_condition_impl`, honoring `is_immune_to_condition` on every path, EFF-10) — the concentration-on-incapacitation break itself was already done as part of Workstream F, wired into both `_apply_condition_impl` and the spell-rider path directly (not blocked on I2's broader centralization).

**Majors that affect ordinary play (fix next):**
7. **Workstream G** ✅ done (instant death, death-save reset, crit modifier doubling — EFF-08/EFF-09/EFF-13/ACT-09) — F's effective-damage refactor (`_apply_damage_effective`) was reused here. EFF-16 (long-rest-at-0-HP) investigated and deliberately not changed; see the workstream section.
8. **Workstream D** (armor/proficiency/inventory) — **D1 ✅ done** (worn-armor identity + equip/unequip AC recompute + shield guard + `CharacterSheet.size`), **D2 ✅ done** (Str-min speed penalty, Hide stealth disadvantage, armor-training disadvantage on STR/DEX checks/saves and the can't-cast gate), and **D3 ✅ done** (EQP-05 starting equipment/gold → inventory/currency, EQP-09 tool-check ability wiring, EQP-10 encumbrance consumer, EQP-11 currency spend/purchase).
9. **Workstream E** ✅ done — Slow/Cleave/Graze/unarmed-strike plus the Push and grapple/shove size gates, the latter unblocked by D1's `CharacterSheet.size` field.
10. **Workstream I1** ✅ done (stale condition definitions: Stunned speed, Petrified immunity, Unconscious→Prone, duplicate source of truth) and **I2** ✅ done (condition-immunity centralization) / **I3/I4** remain (source-identity, exhaustion/repeat-save) — I3/I4 share source-identity with I2 and repeat-save with J.
11. **Workstream H** ✅ done (check proficiency leak, initiative) — small, independent; a fast major/minor win that can land any time.
12. **Workstream J** (remaining spell-schema gaps) — still open. **Workstream K** ✅ done (pact/standard slot separation, upcast flat-modifier scaling, secondary-pool upcast, Ice Storm 2024 dice, `duration_rounds` parsing, `ClassLevelEntry` hashability).

**Minors (fix last):**
13. Remaining minor items folded into their workstreams (D3 currency/encumbrance/tools, L Dodge-speed-zero & dead spell metadata, H initiative/remove-combatant). K's minors (duration parsing, `ClassLevelEntry` hashability) are done.

**Cross-cutting throughout:** **Workstream M** (spec reconciliation + structural anti-regression tests) — update the relevant spec row and add a consumer-existence test as each workstream merges.

**Key dependency chain:** A → B (shared TurnState) → E (masteries need economy); C → E (masteries need the registry); F.step1 (effective-damage return) ✅ done → available to G; I2 ✅ done (centralized apply) — Topple/grapple immunity now honored, available to E once its mastery-effects land; F's own concentration break (EFF-01) never needed I2, since it was wired directly into both condition-application paths. Do A and C early — they are the shared foundations the majority of other workstreams build on.

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