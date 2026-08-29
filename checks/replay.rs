//! Replay determinism: fold(log) equals the stored sheet for all fixture
//! characters, and the golden sheets are hand-verified against Player Core
//! (page references inline). Plus property tests: random wizard sessions
//! never break projection invariants.

use engine_core::AppendOutcome;
use types::{Decision, DecisionId, DecisionInput, DecisionSource, OptionId, Selection, SlotId};

fn engine() -> ruleset_pf2e::Pf2eEngine {
    ruleset_pf2e::engine(std::sync::Arc::new(checks::load_rules_data()))
}

fn confirm(
    engine: &ruleset_pf2e::Pf2eEngine,
    log: &mut Vec<Decision>,
    n: &mut u32,
    slot: &str,
    selection: Selection,
) {
    *n += 1;
    let input = DecisionInput {
        id: DecisionId::new(format!("golden-{n}")),
        slot: SlotId::new(slot),
        selection,
        source: DecisionSource::Player,
    };
    match engine.append(log, input) {
        Ok(AppendOutcome::Appended(new_log)) => *log = new_log,
        other => panic!("golden confirm on '{slot}' rejected: {other:?}"),
    }
}

fn one(id: &str) -> Selection {
    Selection::Option(OptionId::new(id))
}
fn many(ids: &[&str]) -> Selection {
    Selection::Options(ids.iter().map(|i| OptionId::new(*i)).collect())
}

/// Torvald, the spec's first-run Dwarf Fighter. Values hand-verified against
/// Pathfinder Player Core: proficiency pg. 11, boosts pg. 17-19, Dwarf
/// pg. 42-44, Warrior pg. 88, Fighter pg. 136-141, armor pg. 273,
/// weapons pg. 277-280, kit pg. 268, Bulk pg. 269-271.
fn torvald_log(engine: &ruleset_pf2e::Pf2eEngine) -> Vec<Decision> {
    let mut log = Vec::new();
    let n = &mut 0;
    confirm(engine, &mut log, n, "pf2e.ancestry", one("ancestry.dwarf"));
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.ancestry.heritage",
        one("heritage.dwarf.rock"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.ancestry.feat",
        one("feat.ancestry.dwarf.rock-runner"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.ancestry-free",
        many(&["attr.str"]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.background",
        one("background.warrior"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.background-choice",
        one("attr.str"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.background-free",
        one("attr.con"),
    );
    confirm(engine, &mut log, n, "pf2e.class", one("class.fighter"));
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.class.key-attribute",
        one("attr.str"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.class.feat",
        one("feat.class.fighter.sudden-charge"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.skills.class-choice",
        one("skill.athletics"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.skills.trained",
        many(&["skill.survival", "skill.religion", "skill.crafting"]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.free",
        many(&["attr.str", "attr.dex", "attr.con", "attr.wis"]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.equipment.kit",
        one("kit.fighter.sword-and-board"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.details.name",
        Selection::Text("Torvald".into()),
    );
    log
}

/// Elyse, a Human archer exercising Skilled Human's chooser and the
/// armor check/speed penalty for an unmet Strength requirement.
fn elyse_log(engine: &ruleset_pf2e::Pf2eEngine) -> Vec<Decision> {
    let mut log = Vec::new();
    let n = &mut 0;
    confirm(engine, &mut log, n, "pf2e.ancestry", one("ancestry.human"));
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.ancestry.heritage",
        one("heritage.human.skilled"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.skills.heritage-choice",
        one("skill.medicine"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.ancestry.feat",
        one("feat.ancestry.human.cooperative-nature"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.ancestry-free",
        many(&["attr.dex", "attr.wis"]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.background",
        one("background.hunter"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.background-choice",
        one("attr.dex"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.background-free",
        one("attr.str"),
    );
    confirm(engine, &mut log, n, "pf2e.class", one("class.fighter"));
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.class.key-attribute",
        one("attr.dex"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.class.feat",
        one("feat.class.fighter.point-blank-stance"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.skills.class-choice",
        one("skill.acrobatics"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.skills.trained",
        many(&[
            "skill.stealth",
            "skill.athletics",
            "skill.society",
            "skill.thievery",
        ]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.free",
        many(&["attr.dex", "attr.con", "attr.wis", "attr.int"]),
    );
    // Int +1 grants one bonus language from the human list (chargen-content:
    // the language chooser opened once ancestries carried additional
    // languages; hand-verified addition to the golden).
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.ancestry.languages",
        many(&["lang.elven"]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.equipment.kit",
        one("kit.fighter.longbow"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.details.name",
        Selection::Text("Elyse".into()),
    );
    log
}

/// Krivvy, an Unbreakable Goblin street urchin, built out of order so the
/// background's Thievery grant collides with an existing skill pick and
/// forces the replacement rule.
fn krivvy_log(engine: &ruleset_pf2e::Pf2eEngine) -> Vec<Decision> {
    let mut log = Vec::new();
    let n = &mut 0;
    confirm(engine, &mut log, n, "pf2e.class", one("class.fighter"));
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.class.key-attribute",
        one("attr.dex"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.skills.class-choice",
        one("skill.acrobatics"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.skills.trained",
        many(&["skill.thievery", "skill.stealth", "skill.deception"]),
    );
    confirm(engine, &mut log, n, "pf2e.ancestry", one("ancestry.goblin"));
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.ancestry.heritage",
        one("heritage.goblin.unbreakable"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.ancestry.feat",
        one("feat.ancestry.goblin.goblin-song"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.ancestry-free",
        many(&["attr.con"]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.background",
        one("background.street-urchin"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.background-choice",
        one("attr.con"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.background-free",
        one("attr.str"),
    );
    // The background granted Thievery, already trained above: replacement.
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.skills.replacement-1",
        one("skill.society"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.class.feat",
        one("feat.class.fighter.exacting-strike"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.free",
        many(&["attr.dex", "attr.con", "attr.str", "attr.cha"]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.equipment.kit",
        one("equipment.no-kit"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.equipment.extra",
        many(&[
            "armor.leather",
            "weapon.shortsword",
            "weapon.sling",
            "weapon.sling-bullets",
            "gear.adventurers-pack",
        ]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.details.name",
        Selection::Text("Krivvy".into()),
    );
    log
}

fn assert_entry(sheet: &types::SheetView, section: &str, label: &str, value: &str) {
    let entry = sheet
        .entry(section, label)
        .unwrap_or_else(|| panic!("sheet is missing {section} / {label}"));
    assert_eq!(
        entry.value, value,
        "{section} / {label}: got '{}' (detail: {:?}), hand calculation says '{value}'",
        entry.value, entry.detail
    );
}

#[test]
fn golden_torvald_dwarf_fighter() {
    let engine = engine();
    let log = torvald_log(&engine);
    let projection = engine.project(&log).unwrap();
    assert!(
        projection.can_finalize,
        "Torvald should be complete and legal: {:#?}",
        projection.checklist
    );
    let sheet = &projection.sheet;
    assert_eq!(sheet.name, "Torvald");
    assert_eq!(sheet.summary[0], "Dwarf (Rock Dwarf) Fighter 1");

    // Modifiers: Str +4 (ancestry free, background, class key, free boost),
    // Dex +1, Con +3, Int +0, Wis +2, Cha -1 (dwarf flaw).
    assert_entry(sheet, "Attributes", "Strength", "+4");
    assert_entry(sheet, "Attributes", "Dexterity", "+1");
    assert_entry(sheet, "Attributes", "Constitution", "+3");
    assert_entry(sheet, "Attributes", "Intelligence", "+0");
    assert_entry(sheet, "Attributes", "Wisdom", "+2");
    assert_entry(sheet, "Attributes", "Charisma", "-1");

    // HP 23 = 10 ancestry + 10 class + 3 Con (Player Core pg. 42, 136).
    assert_entry(sheet, "Defense", "Hit Points", "23");
    // AC 17 = 10 + 1 Dex (scale mail cap +2) + 3 item + 3 trained.
    assert_entry(sheet, "Defense", "Armor Class", "17");
    // Saves: Fort +8 (expert 5 + Con 3), Ref +6, Will +5; Perception +7.
    assert_entry(sheet, "Defense", "Fortitude", "+8");
    assert_entry(sheet, "Defense", "Reflex", "+6");
    assert_entry(sheet, "Defense", "Will", "+5");
    assert_entry(sheet, "Defense", "Perception", "+7");
    assert_entry(sheet, "Defense", "Class DC", "17");

    // Longsword +9 (martial expert 5 + Str 4), 1d8+4 S.
    assert_entry(sheet, "Attacks", "Longsword", "+9 · 1d8 S+4");
    assert_entry(sheet, "Attacks", "Dagger", "+9 · 1d4 P+4");

    // Skills: Athletics +7 trained (Str 4, no armor penalty — Str meets the
    // scale mail requirement), Intimidation +2 (Warrior), Acrobatics +1
    // untrained.
    assert_entry(sheet, "Skills", "Athletics", "+7");
    assert_entry(sheet, "Skills", "Intimidation", "+2");
    assert_entry(sheet, "Skills", "Acrobatics", "+1");
    assert_entry(sheet, "Skills", "Survival", "+5");
    assert_entry(sheet, "Skills", "Religion", "+5");
    assert_entry(sheet, "Skills", "Crafting", "+3");

    // Coins: 15 gp - 5 gp 8 sp kit - 3 gp option = 6 gp 2 sp.
    assert_entry(sheet, "Equipment", "Coins", "6 gp, 2 sp");
    // Bulk: scale mail 2 (worn) + longsword 1 + shield 1 + pack 1 +
    // dagger L + grappling hook L = 5 Bulk, 2 L.
    assert_entry(sheet, "Equipment", "Bulk", "5 Bulk, 2 L");

    // Speed 20 (dwarf); scale mail penalty waived (Str +4 >= +2 req).
    assert!(
        sheet.summary[1].contains("Speed 20 feet"),
        "summary: {:?}",
        sheet.summary
    );
}

#[test]
fn golden_elyse_human_archer() {
    let engine = engine();
    let log = elyse_log(&engine);
    let projection = engine.project(&log).unwrap();
    assert!(
        projection.can_finalize,
        "Elyse should be complete and legal: {:#?}",
        projection.checklist
    );
    let sheet = &projection.sheet;
    assert_eq!(sheet.summary[0], "Human (Skilled Human) Fighter 1");
    assert_entry(sheet, "Attributes", "Strength", "+1");
    assert_entry(sheet, "Attributes", "Dexterity", "+4");
    assert_entry(sheet, "Attributes", "Constitution", "+1");
    assert_entry(sheet, "Attributes", "Intelligence", "+1");
    assert_entry(sheet, "Attributes", "Wisdom", "+2");
    assert_entry(sheet, "Attributes", "Charisma", "+0");
    // HP 19 = 8 + 10 + 1.
    assert_entry(sheet, "Defense", "Hit Points", "19");
    // AC 18 = 10 + 2 (Dex capped by scale mail) + 3 + 3.
    assert_entry(sheet, "Defense", "Armor Class", "18");
    // Longbow +9 (martial expert 5 + Dex 4), 1d8 P, no Str to damage.
    assert_entry(sheet, "Attacks", "Longbow", "+9 · 1d8 P");
    // Armor check penalty applies (Str +1 < scale mail's +2 requirement):
    // Acrobatics trained 3 + Dex 4 - 2 armor = +5; Athletics 3 + 1 - 2 = +2.
    assert_entry(sheet, "Skills", "Acrobatics", "+5");
    assert_entry(sheet, "Skills", "Athletics", "+2");
    assert_entry(sheet, "Skills", "Medicine", "+5");
    // Speed 25 - 5 (unmet Str requirement keeps the scale mail penalty).
    assert!(
        sheet.summary[1].contains("Speed 20 feet"),
        "summary: {:?}",
        sheet.summary
    );
    // Coins: 15 gp - 5 gp 8 sp - 6 gp 2 sp = 3 gp.
    assert_entry(sheet, "Equipment", "Coins", "3 gp");
}

#[test]
fn golden_krivvy_goblin_replacement() {
    let engine = engine();
    let log = krivvy_log(&engine);
    let projection = engine.project(&log).unwrap();
    assert!(
        projection.can_finalize,
        "Krivvy should be complete and legal: {:#?}",
        projection.checklist
    );
    let sheet = &projection.sheet;
    assert_eq!(sheet.summary[0], "Goblin (Unbreakable Goblin) Fighter 1");
    // Unbreakable Goblin: ancestry HP 10 instead of 6 -> 10 + 10 + 3 Con.
    assert_entry(sheet, "Defense", "Hit Points", "23");
    // Small size, darkvision.
    assert!(sheet.summary[1].starts_with("Small"), "{:?}", sheet.summary);
    assert!(sheet.summary[1].contains("darkvision"));
    // AC 17 = 10 + 3 Dex (leather cap +4) + 1 leather + 3 trained.
    assert_entry(sheet, "Defense", "Armor Class", "17");
    // Replacement rule: Thievery stayed trained from the class picks, and
    // the background's collision was replaced with Society.
    assert_entry(sheet, "Skills", "Thievery", "+6");
    assert_entry(sheet, "Skills", "Society", "+3");
    // Shortsword: finesse, Dex +3 > Str +2 -> +8 to hit, Str to damage.
    assert_entry(sheet, "Attacks", "Shortsword", "+8 · 1d6 P+2");
    // Sling: propulsive, half Str (+1) to damage.
    assert_entry(sheet, "Attacks", "Sling", "+8 · 1d6 B+1");
    // Coins: 15 gp - 4 gp 4 sp 1 cp itemized = 10 gp 5 sp 9 cp.
    assert_entry(sheet, "Equipment", "Coins", "10 gp, 5 sp, 9 cp");
    // Bulk: leather 1 + pack 1 + shortsword L + sling L + bullets L.
    assert_entry(sheet, "Equipment", "Bulk", "2 Bulk, 3 L");
}

/// The committed fixture logs must stay in sync with the golden builders —
/// they are the shared input for the WASM/native parity smoke.
#[test]
fn fixture_logs_match_golden_builders() {
    let engine = engine();
    for (name, log) in [
        ("torvald", torvald_log(&engine)),
        ("elyse", elyse_log(&engine)),
        ("krivvy", krivvy_log(&engine)),
    ] {
        let path = checks::workspace_root().join(format!("checks/fixtures/{name}.log.json"));
        let on_disk = std::fs::read_to_string(&path)
            .unwrap_or_else(|_| panic!("missing fixture {path:?} — run the regen test"));
        let parsed: Vec<Decision> = serde_json::from_str(&on_disk).expect("fixture parses");
        assert_eq!(
            parsed, log,
            "fixture {name} is stale — rerun: cargo test -p checks --test replay regen_fixtures -- --ignored"
        );
        // And replay of the fixture reproduces the same sheet twice.
        assert_eq!(engine.sheet(&parsed).unwrap(), engine.sheet(&log).unwrap());
    }
}

/// Regenerates the committed fixtures. Run manually after a deliberate
/// golden-build change: cargo test -p checks --test replay regen_fixtures -- --ignored
#[test]
#[ignore]
fn regen_fixtures() {
    let engine = engine();
    let dir = checks::workspace_root().join("checks/fixtures");
    std::fs::create_dir_all(&dir).unwrap();
    for (name, log) in [
        ("torvald", torvald_log(&engine)),
        ("elyse", elyse_log(&engine)),
        ("krivvy", krivvy_log(&engine)),
    ] {
        let path = dir.join(format!("{name}.log.json"));
        std::fs::write(&path, serde_json::to_string_pretty(&log).unwrap()).unwrap();
        // Alongside each log, the expected sheet — the parity smoke and the
        // persistence fixtures reuse these.
        let sheet = engine.sheet(&log).unwrap();
        let sheet_path = dir.join(format!("{name}.sheet.json"));
        std::fs::write(&sheet_path, serde_json::to_string_pretty(&sheet).unwrap()).unwrap();
    }
}

#[test]
fn fixture_sheets_match_replay() {
    let engine = engine();
    for name in ["torvald", "elyse", "krivvy"] {
        let dir = checks::workspace_root().join("checks/fixtures");
        let log: Vec<Decision> = serde_json::from_str(
            &std::fs::read_to_string(dir.join(format!("{name}.log.json"))).unwrap(),
        )
        .unwrap();
        let stored: types::SheetView = serde_json::from_str(
            &std::fs::read_to_string(dir.join(format!("{name}.sheet.json"))).unwrap(),
        )
        .unwrap();
        assert_eq!(
            engine.sheet(&log).unwrap(),
            stored,
            "replay of fixture '{name}' diverges from its stored sheet"
        );
    }
}

mod properties {
    use super::*;
    use proptest::prelude::*;

    #[derive(Debug, Clone)]
    enum Op {
        Confirm { slot: usize, pick: usize },
        Clear { slot: usize },
    }

    fn ops() -> impl Strategy<Value = Vec<Op>> {
        proptest::collection::vec(
            prop_oneof![
                (0usize..64, 0usize..8).prop_map(|(slot, pick)| Op::Confirm { slot, pick }),
                (0usize..64).prop_map(|slot| Op::Clear { slot }),
            ],
            0..30,
        )
    }

    proptest! {
        #![proptest_config(ProptestConfig::with_cases(48))]
        /// Random walks over the real PF2e slot graph, driven through the
        /// projection (as a client would be): whatever happens, projection
        /// stays deterministic, orders stay dense, at most one decision per
        /// slot, and can_finalize tracks the checklist.
        #[test]
        fn pf2e_random_walk(ops in ops()) {
            let engine = engine();
            let mut log: Vec<Decision> = vec![];
            let mut n = 0u32;
            for op in ops {
                let projection = engine.project(&log).unwrap();
                let open_slots: Vec<_> = projection
                    .steps
                    .iter()
                    .flat_map(|s| &s.slots)
                    .filter(|s| s.locked_reason.is_none())
                    .collect();
                if open_slots.is_empty() {
                    break;
                }
                match op {
                    Op::Confirm { slot, pick } => {
                        let slot_view = open_slots[slot % open_slots.len()];
                        if slot_view.decision.is_some() {
                            continue;
                        }
                        let available: Vec<_> =
                            slot_view.options.iter().filter(|o| o.available).collect();
                        let selection = match &slot_view.kind {
                            types::SlotViewKind::Single => {
                                if available.is_empty() { continue; }
                                Selection::Option(available[pick % available.len()].id.clone())
                            }
                            types::SlotViewKind::Multi { count } => {
                                if available.is_empty() { continue; }
                                // Sometimes under- or over-pick on purpose.
                                let take = (pick % (*count as usize + 2)).min(available.len());
                                Selection::Options(
                                    available.iter().cycle().skip(pick % available.len()).take(take).map(|o| o.id.clone()).collect(),
                                )
                            }
                            types::SlotViewKind::List => {
                                let take = pick % 3;
                                Selection::Options(
                                    available.iter().take(take).map(|o| o.id.clone()).collect(),
                                )
                            }
                            types::SlotViewKind::Text { .. } => {
                                Selection::Text(format!("text-{pick}"))
                            }
                        };
                        n += 1;
                        let input = DecisionInput {
                            id: DecisionId::new(format!("walk-{n}")),
                            slot: slot_view.id.clone(),
                            selection,
                            source: DecisionSource::Player,
                        };
                        if let Ok(AppendOutcome::Appended(new_log)) = engine.append(&log, input) {
                            log = new_log;
                        }
                    }
                    Op::Clear { slot } => {
                        let slot_view = open_slots[slot % open_slots.len()];
                        if slot_view.decision.is_none() {
                            continue;
                        }
                        if let Ok(new_log) = engine.clear(&log, &slot_view.id) {
                            log = new_log;
                        }
                    }
                }

                let orders: Vec<u32> = log.iter().map(|d| d.order).collect();
                prop_assert_eq!(&orders, &(0..log.len() as u32).collect::<Vec<_>>());
                let mut seen = std::collections::BTreeSet::new();
                for d in &log {
                    prop_assert!(seen.insert(d.slot.clone()));
                }
                let p1 = engine.project(&log).unwrap();
                let p2 = engine.project(&log).unwrap();
                prop_assert_eq!(&p1, &p2);
                prop_assert_eq!(p1.can_finalize, p1.checklist.is_empty());
                // Coherence: statuses, entries, and explanations agree.
                for slot in p1.steps.iter().flat_map(|s| &s.slots) {
                    match slot.status {
                        types::SlotStatus::Locked => {
                            prop_assert!(slot.locked_reason.is_some());
                        }
                        types::SlotStatus::Partial | types::SlotStatus::Illegal => {
                            prop_assert!(
                                p1.checklist.iter().any(|e| e.slot == slot.id),
                                "{} is {:?} with no checklist entry",
                                slot.id, slot.status
                            );
                        }
                        _ => {}
                    }
                }
                for entry in &p1.checklist {
                    let target = p1
                        .steps
                        .iter()
                        .flat_map(|s| &s.slots)
                        .find(|s| s.id == entry.slot);
                    prop_assert!(target.is_some(), "entry for absent slot {}", entry.slot);
                    prop_assert!(
                        target.unwrap().status != types::SlotStatus::Complete,
                        "entry against Complete slot {}", entry.slot
                    );
                }
            }
        }
    }
}
