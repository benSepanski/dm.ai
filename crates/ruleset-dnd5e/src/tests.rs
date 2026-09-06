//! Tests over the embedded SRD 5.2.1 data: the creation walk (Brannock),
//! leveling to 3 through the advance slots and the subclass slot, the
//! ability-score machinery (array and point buy, with their violations),
//! the gold alternative, a Goliath's trait choice, the Magic Initiate
//! note, and the method-change cascade.

use engine_core::{AppendOutcome, EngineError};
use types::{
    ChecklistSeverity, Decision, DecisionId, DecisionInput, DecisionSource, MeterState, OptionId,
    ProjectionView, Selection, SheetView, SlotId, SlotView, SlotViewKind,
};

use crate::mechanics::{
    slot_level_advance, slot_level_subclass, step_level, Ability, Increase,
    BACKGROUND_EQUIPMENT_GOLD, BACKGROUND_EQUIPMENT_PACKAGE, SLOT_BACKGROUND,
    SLOT_BACKGROUND_EQUIPMENT, SLOT_BACKGROUND_INCREASE, SLOT_CLASS, SLOT_CLASS_MASTERIES,
    SLOT_CLASS_SKILLS, SLOT_CLASS_STYLE, SLOT_EQUIPMENT_PACKAGE, SLOT_FEAT_SKILLED, SLOT_NAME,
    SLOT_SCORES_ASSIGN, SLOT_SCORES_METHOD, SLOT_SPECIES, SLOT_SPECIES_ANCESTRY, SLOT_SPECIES_FEAT,
    SLOT_SPECIES_SKILL,
};
use crate::Dnd5eEngine;

fn engine() -> Dnd5eEngine {
    crate::embedded().concrete_clone()
}

impl crate::Dnd5eRuleset {
    /// A fresh engine over the embedded data (the shared one is not
    /// `Clone`; assembling another is cheap).
    fn concrete_clone(&self) -> Dnd5eEngine {
        crate::engine(self.data().clone())
    }
}

fn one(id: &str) -> Selection {
    Selection::Option(OptionId::new(id))
}

fn many(ids: &[&str]) -> Selection {
    Selection::Options(ids.iter().map(|i| OptionId::new(*i)).collect())
}

fn text(t: &str) -> Selection {
    Selection::Text(t.into())
}

fn score(ability: &str, value: u32) -> String {
    format!("score.{ability}.{value}")
}

fn confirm(engine: &Dnd5eEngine, log: &mut Vec<Decision>, slot: &str, selection: Selection) {
    let input = DecisionInput {
        id: DecisionId::new(format!("d{}", log.len())),
        slot: SlotId::new(slot),
        selection,
        source: DecisionSource::Player,
    };
    match engine.append(log, input) {
        Ok(AppendOutcome::Appended(new_log)) => *log = new_log,
        other => panic!("confirm on '{slot}' rejected: {other:?}"),
    }
}

fn try_confirm(
    engine: &Dnd5eEngine,
    log: &[Decision],
    slot: &str,
    selection: Selection,
) -> Result<AppendOutcome, EngineError> {
    engine.append(
        log,
        DecisionInput {
            id: DecisionId::new(format!("t{}", log.len())),
            slot: SlotId::new(slot),
            selection,
            source: DecisionSource::Player,
        },
    )
}

fn slot_view<'a>(p: &'a ProjectionView, slot: &str) -> Option<&'a SlotView> {
    p.steps
        .iter()
        .flat_map(|s| s.slots.iter())
        .find(|s| s.id.as_str() == slot)
}

fn value(sheet: &SheetView, section: &str, label: &str) -> String {
    sheet
        .entry(section, label)
        .unwrap_or_else(|| panic!("sheet has no {section} / {label}"))
        .value
        .clone()
}

fn detail(sheet: &SheetView, section: &str, label: &str) -> String {
    sheet
        .entry(section, label)
        .unwrap_or_else(|| panic!("sheet has no {section} / {label}"))
        .detail
        .clone()
        .unwrap_or_default()
}

/// Brannock's standard-array assignment: Str 15, Con 14, Dex 13, Wis 12,
/// Cha 10, Int 8.
fn brannock_array() -> Selection {
    many(&[
        &score("str", 15),
        &score("con", 14),
        &score("dex", 13),
        &score("wis", 12),
        &score("cha", 10),
        &score("int", 8),
    ])
}

/// The full Brannock walk: Human Soldier Fighter, Standard Array, Str +2
/// / Con +1, Alert from the Human, Perception from the Human, Acrobatics
/// and Insight from the class, Defense, three masteries, package A.
fn brannock_log(engine: &Dnd5eEngine) -> Vec<Decision> {
    let mut log = Vec::new();
    confirm(engine, &mut log, SLOT_CLASS, one("class.fighter"));
    confirm(engine, &mut log, SLOT_BACKGROUND, one("background.soldier"));
    confirm(
        engine,
        &mut log,
        SLOT_BACKGROUND_INCREASE,
        Selection::Option(Increase::TwoOne(Ability::Str, Ability::Con).option_id()),
    );
    confirm(engine, &mut log, SLOT_SPECIES, one("species.human"));
    confirm(
        engine,
        &mut log,
        SLOT_SPECIES_SKILL,
        one("skill.perception"),
    );
    confirm(
        engine,
        &mut log,
        SLOT_SPECIES_FEAT,
        one("feat.origin.alert"),
    );
    confirm(
        engine,
        &mut log,
        SLOT_SCORES_METHOD,
        one("method.standard-array"),
    );
    confirm(engine, &mut log, SLOT_SCORES_ASSIGN, brannock_array());
    confirm(
        engine,
        &mut log,
        SLOT_CLASS_SKILLS,
        many(&["skill.acrobatics", "skill.insight"]),
    );
    confirm(
        engine,
        &mut log,
        SLOT_CLASS_STYLE,
        one("feat.style.defense"),
    );
    confirm(
        engine,
        &mut log,
        SLOT_CLASS_MASTERIES,
        many(&["weapon.greatsword", "weapon.flail", "weapon.javelin"]),
    );
    confirm(
        engine,
        &mut log,
        SLOT_EQUIPMENT_PACKAGE,
        one("package.fighter.a"),
    );
    confirm(
        engine,
        &mut log,
        SLOT_BACKGROUND_EQUIPMENT,
        one(BACKGROUND_EQUIPMENT_PACKAGE),
    );
    confirm(engine, &mut log, SLOT_NAME, text("Brannock"));
    log
}

#[test]
fn embedded_data_parses_and_the_engine_constructs() {
    let data = crate::embedded_data().expect("embedded data parses");
    assert_eq!(data.manifest.system, "dnd5e");
    assert_eq!(data.manifest.version, "dnd5e-srd.0.1.0");
    assert_eq!(data.max_advancement_level(), 3);
    assert_eq!(data.subclass_levels(), vec![3]);
    let rs = crate::embedded();
    let lines = engine_core::Ruleset::license_lines(&*rs);
    assert!(lines[0]
        .starts_with("This work includes material from the System Reference Document 5.2.1"));
    // Every mastery property is exercised by at least one shipped weapon.
    for mastery in [
        "Cleave", "Graze", "Nick", "Push", "Sap", "Slow", "Topple", "Vex",
    ] {
        assert!(
            data.equipment.weapons.iter().any(|w| w.mastery == mastery),
            "no weapon carries {mastery}"
        );
    }
    let _ = engine();
}

#[test]
fn brannock_walks_to_a_complete_level_1_sheet() {
    let engine = engine();
    let log = brannock_log(&engine);
    let p = engine.project(&log).unwrap();
    assert!(p.checklist.is_empty(), "{:#?}", p.checklist);
    assert!(p.can_finalize);
    let sheet = &p.sheet;
    assert_eq!(sheet.name, "Brannock");
    assert_eq!(sheet.summary[0], "Human Fighter 1");

    // Scores: array plus Soldier's +2 Str / +1 Con.
    assert_eq!(value(sheet, "Ability Scores", "Strength"), "17 (+3)");
    assert_eq!(
        detail(sheet, "Ability Scores", "Strength"),
        "15 (Standard Array) +2 (Soldier)"
    );
    assert_eq!(value(sheet, "Ability Scores", "Dexterity"), "13 (+1)");
    assert_eq!(value(sheet, "Ability Scores", "Constitution"), "15 (+2)");
    assert_eq!(value(sheet, "Ability Scores", "Intelligence"), "8 (-1)");
    assert_eq!(value(sheet, "Ability Scores", "Wisdom"), "12 (+1)");
    assert_eq!(value(sheet, "Ability Scores", "Charisma"), "10 (+0)");

    // Combat: HP 10 + 2; AC 16 chain mail + 1 Defense; Initiative Dex +1
    // plus the Alert proficiency; Speed 30 (Str 17 meets chain mail's 13).
    assert_eq!(value(sheet, "Combat", "Hit Points"), "12");
    assert_eq!(value(sheet, "Combat", "Armor Class"), "17");
    assert!(detail(sheet, "Combat", "Armor Class").contains("Chain Mail"));
    assert!(detail(sheet, "Combat", "Armor Class").contains("Defense"));
    assert_eq!(value(sheet, "Combat", "Initiative"), "+3");
    assert_eq!(value(sheet, "Combat", "Speed"), "30 ft.");
    assert_eq!(value(sheet, "Combat", "Proficiency Bonus"), "+2");
    assert_eq!(value(sheet, "Combat", "Hit Dice"), "1d10");
    assert_eq!(value(sheet, "Combat", "Passive Perception"), "13");

    // Saves: proficient Str and Con.
    assert_eq!(value(sheet, "Saving Throws", "Strength"), "+5");
    assert_eq!(value(sheet, "Saving Throws", "Constitution"), "+4");
    assert_eq!(value(sheet, "Saving Throws", "Dexterity"), "+1");
    assert_eq!(value(sheet, "Saving Throws", "Intelligence"), "-1");

    // Skills: Soldier's Athletics and Intimidation, the Human's Perception,
    // the class's Acrobatics and Insight; Stealth plain Dex.
    assert_eq!(value(sheet, "Skills", "Athletics"), "+5");
    assert!(detail(sheet, "Skills", "Athletics").ends_with("(from Soldier)"));
    assert_eq!(value(sheet, "Skills", "Intimidation"), "+2");
    assert_eq!(value(sheet, "Skills", "Perception"), "+3");
    assert!(detail(sheet, "Skills", "Perception").ends_with("(from Human)"));
    assert_eq!(value(sheet, "Skills", "Acrobatics"), "+3");
    assert!(detail(sheet, "Skills", "Acrobatics").ends_with("(from Fighter)"));
    assert_eq!(value(sheet, "Skills", "Insight"), "+3");
    assert_eq!(value(sheet, "Skills", "Stealth"), "+1");
    assert_eq!(detail(sheet, "Skills", "Stealth"), "1 Dex");
    assert_eq!(
        sheet
            .sections
            .iter()
            .find(|s| s.title == "Skills")
            .unwrap()
            .entries
            .len(),
        18
    );

    // Attacks: package A's weapons and the Soldier's spear and shortbow.
    assert_eq!(value(sheet, "Attacks", "Greatsword"), "+5 · 2d6+3 Slashing");
    assert!(detail(sheet, "Attacks", "Greatsword").contains("mastery: Graze (chosen)"));
    assert_eq!(value(sheet, "Attacks", "Flail"), "+5 · 1d8+3 Bludgeoning");
    assert_eq!(value(sheet, "Attacks", "Javelin"), "+5 · 1d6+3 Piercing");
    assert!(detail(sheet, "Attacks", "Javelin").contains("×8"));
    assert_eq!(
        value(sheet, "Attacks", "Spear"),
        "+5 · 1d6+3 Piercing (1d8+3 two-handed)"
    );
    assert!(detail(sheet, "Attacks", "Spear").contains("mastery: Sap"));
    assert!(!detail(sheet, "Attacks", "Spear").contains("(chosen)"));
    assert_eq!(value(sheet, "Attacks", "Shortbow"), "+3 · 1d6+1 Piercing");

    // Features: fixed level-1 features with the picks rendered into them,
    // the origin feats, the Human's traits.
    assert_eq!(value(sheet, "Features", "Fighting Style"), "Defense");
    assert!(value(sheet, "Features", "Weapon Mastery").contains("Greatsword (Graze)"));
    assert!(sheet.entry("Features", "Second Wind").is_some());
    assert!(sheet.entry("Features", "Savage Attacker").is_some());
    assert!(value(sheet, "Features", "Alert").contains("from Human"));
    assert!(sheet.entry("Features", "Resourceful").is_some());
    assert_eq!(value(sheet, "Features", "Tool Proficiency"), "Gaming Set");
    assert!(sheet.entry("Features", "Action Surge").is_none());

    // Equipment: 134 lb from package A plus 14 lb from the Soldier;
    // capacity Str 17 × 15; coin 4 + 14.
    assert_eq!(value(sheet, "Equipment", "Chain Mail"), "55 lb.");
    assert_eq!(value(sheet, "Equipment", "Javelin ×8"), "16 lb.");
    assert_eq!(value(sheet, "Equipment", "Total Weight"), "148 lb.");
    assert!(detail(sheet, "Equipment", "Total Weight").contains("255 lb."));
    assert_eq!(value(sheet, "Equipment", "Coin"), "18 GP");
}

#[test]
fn brannock_levels_to_3_through_the_advance_and_subclass_slots() {
    let engine = engine();
    let rs = crate::embedded();
    let mut log = brannock_log(&engine);
    assert_eq!(engine_core::Ruleset::level_of(&*rs, &log).unwrap(), 1);
    assert_eq!(
        engine_core::Ruleset::next_level(&*rs, &log).unwrap(),
        Some(2)
    );

    // The subclass slot does not exist at level 1, and level 3 cannot be
    // reached before level 2.
    let p = engine.project(&log).unwrap();
    assert!(slot_view(&p, &slot_level_subclass(3)).is_none());
    assert!(try_confirm(&engine, &log, &slot_level_advance(3), one("advance.3")).is_err());

    // Level 2: fixed features only — the rendered step is live and empty,
    // the checklist stays empty, HP grows by 6 + Con.
    confirm(&engine, &mut log, &slot_level_advance(2), one("advance.2"));
    let p = engine.project(&log).unwrap();
    assert!(p.checklist.is_empty(), "{:#?}", p.checklist);
    assert!(p.can_finalize);
    let live: Vec<String> = p.steps.iter().map(|s| s.id.as_str().to_string()).collect();
    assert_eq!(live, vec![step_level(2)]);
    assert!(p.steps[0].slots.is_empty(), "level 2 grants no choice slot");
    assert_eq!(value(&p.sheet, "Combat", "Hit Points"), "20");
    assert_eq!(value(&p.sheet, "Features", "Action Surge"), "Fighter 2");
    assert!(p.sheet.entry("Features", "Tactical Mind").is_some());
    assert_eq!(p.sheet.summary[0], "Human Fighter 2");
    assert_eq!(
        engine_core::Ruleset::next_level(&*rs, &log).unwrap(),
        Some(3)
    );

    // Level 3: exactly one Single slot whose options are the subclass
    // records for the Fighter.
    confirm(&engine, &mut log, &slot_level_advance(3), one("advance.3"));
    let p = engine.project(&log).unwrap();
    assert!(!p.can_finalize);
    let step = &p.steps[0];
    assert_eq!(step.id.as_str(), step_level(3));
    assert_eq!(step.slots.len(), 1);
    let slot = &step.slots[0];
    assert_eq!(slot.id.as_str(), slot_level_subclass(3));
    assert_eq!(slot.kind, SlotViewKind::Single);
    let ids: Vec<&str> = slot.options.iter().map(|o| o.id.as_str()).collect();
    assert_eq!(ids, vec!["subclass.fighter.champion"]);
    assert_eq!(p.checklist.len(), 1);
    assert_eq!(p.checklist[0].rule, "Fighter Subclass");

    confirm(
        &engine,
        &mut log,
        &slot_level_subclass(3),
        one("subclass.fighter.champion"),
    );
    let p = engine.project(&log).unwrap();
    assert!(p.checklist.is_empty(), "{:#?}", p.checklist);
    assert_eq!(p.sheet.summary[0], "Human Fighter 3 (Champion)");
    assert_eq!(value(&p.sheet, "Combat", "Hit Points"), "28");
    assert_eq!(value(&p.sheet, "Combat", "Hit Dice"), "3d10");
    assert_eq!(value(&p.sheet, "Combat", "Proficiency Bonus"), "+2");
    assert_eq!(
        value(&p.sheet, "Features", "Improved Critical"),
        "Champion 3"
    );
    assert!(p.sheet.entry("Features", "Remarkable Athlete").is_some());
    assert_eq!(engine_core::Ruleset::level_of(&*rs, &log).unwrap(), 3);
    assert_eq!(engine_core::Ruleset::next_level(&*rs, &log).unwrap(), None);
    assert!(engine_core::Ruleset::is_advance_slot(
        &*rs,
        &SlotId::new(slot_level_advance(2))
    ));
    assert!(!engine_core::Ruleset::is_advance_slot(
        &*rs,
        &SlotId::new(slot_level_subclass(3))
    ));
}

#[test]
fn point_buy_overspend_is_illegal_and_the_meter_shows_the_overshoot() {
    let engine = engine();
    let mut log = Vec::new();
    confirm(&engine, &mut log, SLOT_CLASS, one("class.fighter"));
    confirm(
        &engine,
        &mut log,
        SLOT_SCORES_METHOD,
        one("method.point-buy"),
    );
    // 15, 15, 15, 8, 8, 8 costs exactly 27.
    confirm(
        &engine,
        &mut log,
        SLOT_SCORES_ASSIGN,
        many(&[
            &score("str", 15),
            &score("dex", 15),
            &score("con", 15),
            &score("int", 8),
            &score("wis", 8),
            &score("cha", 8),
        ]),
    );
    let p = engine.project(&log).unwrap();
    assert!(!p
        .checklist
        .iter()
        .any(|e| e.slot.as_str() == SLOT_SCORES_ASSIGN));
    let meter = &slot_view(&p, SLOT_SCORES_ASSIGN).unwrap().meters;
    let points = meter.iter().find(|m| m.label == "Points").unwrap();
    assert_eq!(
        (points.current.as_str(), points.state),
        ("0", MeterState::Ok)
    );
    assert_eq!(value(&p.sheet, "Ability Scores", "Strength"), "15 (+2)");

    // Raising Int to 9 spends 28: Illegal, naming the rule, meter Exceeded.
    let over = DecisionInput {
        id: DecisionId::new("over"),
        slot: SlotId::new(SLOT_SCORES_ASSIGN),
        selection: many(&[
            &score("str", 15),
            &score("dex", 15),
            &score("con", 15),
            &score("int", 9),
            &score("wis", 8),
            &score("cha", 8),
        ]),
        source: DecisionSource::Player,
    };
    let p = engine.preview(&log, &over).unwrap();
    let entry = p
        .checklist
        .iter()
        .find(|e| e.severity == ChecklistSeverity::Illegal)
        .expect("overspend is illegal");
    assert_eq!(entry.rule, "Point Cost");
    assert!(entry.message.contains("28"), "{}", entry.message);
    let points = slot_view(&p, SLOT_SCORES_ASSIGN)
        .unwrap()
        .meters
        .iter()
        .find(|m| m.label == "Points")
        .unwrap()
        .clone();
    assert_eq!(
        (points.current.as_str(), points.state),
        ("-1", MeterState::Exceeded)
    );

    // A score outside the cost table is refused structurally.
    assert!(try_confirm(
        &engine,
        &log[..2],
        SLOT_SCORES_ASSIGN,
        many(&[&score("str", 16)])
    )
    .is_err());
}

#[test]
fn array_violations_are_flagged_not_clamped() {
    let engine = engine();
    let mut log = Vec::new();
    confirm(&engine, &mut log, SLOT_CLASS, one("class.fighter"));
    confirm(
        &engine,
        &mut log,
        SLOT_SCORES_METHOD,
        one("method.standard-array"),
    );

    // Each value once: 15 assigned twice.
    let dup = DecisionInput {
        id: DecisionId::new("dup"),
        slot: SlotId::new(SLOT_SCORES_ASSIGN),
        selection: many(&[
            &score("str", 15),
            &score("dex", 15),
            &score("con", 13),
            &score("int", 12),
            &score("wis", 10),
            &score("cha", 8),
        ]),
        source: DecisionSource::Player,
    };
    let p = engine.preview(&log, &dup).unwrap();
    let entry = p
        .checklist
        .iter()
        .find(|e| e.severity == ChecklistSeverity::Illegal)
        .expect("a reused array value is illegal");
    assert_eq!(entry.rule, "Standard Array");
    assert!(entry.message.contains("15"), "{}", entry.message);

    // One per group: Strength twice, Charisma never.
    let twice = DecisionInput {
        id: DecisionId::new("twice"),
        slot: SlotId::new(SLOT_SCORES_ASSIGN),
        selection: many(&[
            &score("str", 15),
            &score("str", 14),
            &score("con", 13),
            &score("int", 12),
            &score("wis", 10),
            &score("dex", 8),
        ]),
        source: DecisionSource::Player,
    };
    let p = engine.preview(&log, &twice).unwrap();
    assert!(p.checklist.iter().any(|e| {
        e.severity == ChecklistSeverity::Illegal
            && e.rule == "Assign Ability Scores"
            && e.message.contains("Strength")
    }));
    assert!(p.checklist.iter().any(|e| {
        e.severity == ChecklistSeverity::Incomplete && e.message.contains("Charisma")
    }));

    // The catalog is grouped by ability and shows a taken value as taken.
    confirm(&engine, &mut log, SLOT_SCORES_ASSIGN, brannock_array());
    let p = engine.project(&log).unwrap();
    let slot = slot_view(&p, SLOT_SCORES_ASSIGN).unwrap();
    assert_eq!(slot.presentation_hint.as_deref(), Some("one-per-group"));
    assert_eq!(slot.options.len(), 36);
    let dex_15 = slot
        .options
        .iter()
        .find(|o| o.id.as_str() == score("dex", 15))
        .unwrap();
    assert_eq!(dex_15.group.as_deref(), Some("Dexterity"));
    assert!(!dex_15.available);
    assert_eq!(
        dex_15.unavailable_reason.as_deref(),
        Some("assigned to Strength")
    );
}

#[test]
fn the_gold_alternative_yields_unarmored_ac_and_an_empty_attacks_section() {
    let engine = engine();
    let mut log = Vec::new();
    confirm(&engine, &mut log, SLOT_CLASS, one("class.fighter"));
    confirm(
        &engine,
        &mut log,
        SLOT_BACKGROUND,
        one("background.criminal"),
    );
    confirm(
        &engine,
        &mut log,
        SLOT_BACKGROUND_INCREASE,
        Selection::Option(Increase::AllOne.option_id()),
    );
    confirm(&engine, &mut log, SLOT_SPECIES, one("species.halfling"));
    confirm(
        &engine,
        &mut log,
        SLOT_SCORES_METHOD,
        one("method.point-buy"),
    );
    confirm(
        &engine,
        &mut log,
        SLOT_SCORES_ASSIGN,
        many(&[
            &score("str", 13),
            &score("dex", 15),
            &score("con", 14),
            &score("int", 8),
            &score("wis", 12),
            &score("cha", 10),
        ]),
    );
    confirm(
        &engine,
        &mut log,
        SLOT_CLASS_SKILLS,
        many(&["skill.athletics", "skill.perception"]),
    );
    confirm(
        &engine,
        &mut log,
        SLOT_CLASS_STYLE,
        one("feat.style.archery"),
    );
    confirm(
        &engine,
        &mut log,
        SLOT_CLASS_MASTERIES,
        many(&["weapon.longbow", "weapon.rapier", "weapon.dagger"]),
    );
    confirm(
        &engine,
        &mut log,
        SLOT_EQUIPMENT_PACKAGE,
        one("package.fighter.gold"),
    );
    confirm(
        &engine,
        &mut log,
        SLOT_BACKGROUND_EQUIPMENT,
        one(BACKGROUND_EQUIPMENT_GOLD),
    );
    confirm(&engine, &mut log, SLOT_NAME, text("Pell"));
    let p = engine.project(&log).unwrap();
    assert!(p.checklist.is_empty(), "{:#?}", p.checklist);
    let sheet = &p.sheet;
    // Criminal's +1 to each: Dex 16 (+3), Con 15, Int 9.
    assert_eq!(value(sheet, "Ability Scores", "Dexterity"), "16 (+3)");
    assert_eq!(value(sheet, "Ability Scores", "Intelligence"), "9 (-1)");
    assert_eq!(value(sheet, "Combat", "Armor Class"), "13");
    assert!(detail(sheet, "Combat", "Armor Class").contains("unarmored"));
    let attacks = sheet
        .sections
        .iter()
        .find(|s| s.title == "Attacks")
        .unwrap();
    assert!(attacks.entries.is_empty());
    assert_eq!(value(sheet, "Equipment", "Coin"), "205 GP");
    assert_eq!(value(sheet, "Equipment", "Total Weight"), "0 lb.");
    assert_eq!(value(sheet, "Combat", "Hit Points"), "12");
    assert!(sheet.summary[1].starts_with("Small"));
}

#[test]
fn a_goliath_chooses_its_giant_ancestry() {
    let engine = engine();
    let mut log = Vec::new();
    confirm(&engine, &mut log, SLOT_CLASS, one("class.fighter"));
    confirm(&engine, &mut log, SLOT_SPECIES, one("species.goliath"));
    let p = engine.project(&log).unwrap();
    let slot = slot_view(&p, SLOT_SPECIES_ANCESTRY).expect("Giant Ancestry is a slot");
    assert_eq!(slot.options.len(), 6);
    assert!(
        slot_view(&p, SLOT_SPECIES_SKILL).is_none(),
        "no skill choice for a Goliath"
    );
    assert!(slot_view(&p, SLOT_SPECIES_FEAT).is_none());
    assert!(p
        .checklist
        .iter()
        .any(|e| e.slot.as_str() == SLOT_SPECIES_ANCESTRY && e.rule == "Giant Ancestry"));
    assert!(try_confirm(&engine, &log, SLOT_SPECIES_ANCESTRY, one("ancestry.nope")).is_err());
    confirm(
        &engine,
        &mut log,
        SLOT_SPECIES_ANCESTRY,
        one("ancestry.stone"),
    );
    let p = engine.project(&log).unwrap();
    assert!(!p
        .checklist
        .iter()
        .any(|e| e.slot.as_str() == SLOT_SPECIES_ANCESTRY));
    assert_eq!(
        value(&p.sheet, "Features", "Giant Ancestry"),
        "Stone's Endurance (Stone Giant)"
    );
    assert_eq!(value(&p.sheet, "Combat", "Speed"), "35 ft.");
    // Powerful Build: one size larger for carrying capacity.
    assert!(detail(&p.sheet, "Equipment", "Total Weight").contains("× 30"));
    // Changing species takes the ancestry pick with it.
    let preview = engine
        .clear_preview(&log, &SlotId::new(SLOT_SPECIES))
        .unwrap();
    assert!(preview
        .cleared
        .iter()
        .any(|c| c.slot.as_str() == SLOT_SPECIES_ANCESTRY));
}

#[test]
fn magic_initiate_renders_its_text_and_the_unsupported_note() {
    let engine = engine();
    let mut log = Vec::new();
    confirm(
        &engine,
        &mut log,
        SLOT_BACKGROUND,
        one("background.acolyte"),
    );
    let sheet = engine.sheet(&log).unwrap();
    let entry = sheet
        .entry("Features", "Magic Initiate (Cleric)")
        .expect("the origin feat renders");
    assert!(entry.value.contains("spell choices not yet supported"));
    assert!(entry.value.contains("from Acolyte"));
    assert!(entry.detail.as_deref().unwrap().contains("Two Cantrips"));
}

#[test]
fn changing_the_method_cascades_the_assignment() {
    let engine = engine();
    let mut log = Vec::new();
    confirm(
        &engine,
        &mut log,
        SLOT_SCORES_METHOD,
        one("method.standard-array"),
    );
    confirm(&engine, &mut log, SLOT_SCORES_ASSIGN, brannock_array());
    let preview = engine
        .clear_preview(&log, &SlotId::new(SLOT_SCORES_METHOD))
        .unwrap();
    let cleared: Vec<&str> = preview.cleared.iter().map(|c| c.slot.as_str()).collect();
    assert!(cleared.contains(&SLOT_SCORES_ASSIGN));
    let assign = preview
        .cleared
        .iter()
        .find(|c| c.slot.as_str() == SLOT_SCORES_ASSIGN)
        .unwrap();
    assert!(assign.selection_label.contains("Strength 15"));
    let cleared_log = engine
        .clear(&log, &SlotId::new(SLOT_SCORES_METHOD))
        .unwrap();
    assert!(cleared_log.is_empty());
    // Assignment is locked until a method exists.
    let p = engine.project(&cleared_log).unwrap();
    assert!(slot_view(&p, SLOT_SCORES_ASSIGN)
        .unwrap()
        .locked_reason
        .is_some());
}

#[test]
fn the_human_cannot_double_up_on_the_backgrounds_feat_or_skills() {
    let engine = engine();
    let mut log = Vec::new();
    confirm(&engine, &mut log, SLOT_CLASS, one("class.fighter"));
    confirm(
        &engine,
        &mut log,
        SLOT_BACKGROUND,
        one("background.soldier"),
    );
    confirm(&engine, &mut log, SLOT_SPECIES, one("species.human"));
    let p = engine.project(&log).unwrap();
    let feat = slot_view(&p, SLOT_SPECIES_FEAT).unwrap();
    let savage = feat
        .options
        .iter()
        .find(|o| o.id.as_str() == "feat.origin.savage-attacker")
        .unwrap();
    assert!(!savage.available);
    assert_eq!(
        savage.unavailable_reason.as_deref(),
        Some("already granted by Soldier")
    );
    // The feat still applies (the log is honest) and the checklist flags it.
    confirm(
        &engine,
        &mut log,
        SLOT_SPECIES_FEAT,
        one("feat.origin.savage-attacker"),
    );
    confirm(
        &engine,
        &mut log,
        SLOT_SPECIES_SKILL,
        one("skill.athletics"),
    );
    let p = engine.project(&log).unwrap();
    assert!(p.checklist.iter().any(|e| {
        e.severity == ChecklistSeverity::Illegal && e.slot.as_str() == SLOT_SPECIES_FEAT
    }));
    assert!(p.checklist.iter().any(|e| {
        e.severity == ChecklistSeverity::Illegal && e.slot.as_str() == SLOT_SPECIES_SKILL
    }));
    // Class skills mark background and species grants unavailable.
    let skills = slot_view(&p, SLOT_CLASS_SKILLS).unwrap();
    let athletics = skills
        .options
        .iter()
        .find(|o| o.id.as_str() == "skill.athletics")
        .unwrap();
    assert!(!athletics.available);
}

#[test]
fn skilled_opens_a_three_pick_chooser_and_clears_with_the_feat() {
    let engine = engine();
    let mut log = Vec::new();
    confirm(&engine, &mut log, SLOT_BACKGROUND, one("background.sage"));
    confirm(&engine, &mut log, SLOT_SPECIES, one("species.human"));
    let p = engine.project(&log).unwrap();
    assert!(slot_view(&p, SLOT_FEAT_SKILLED).is_none());
    confirm(
        &engine,
        &mut log,
        SLOT_SPECIES_FEAT,
        one("feat.origin.skilled"),
    );
    let p = engine.project(&log).unwrap();
    let chooser = slot_view(&p, SLOT_FEAT_SKILLED).expect("Skilled opens its chooser");
    assert_eq!(chooser.kind, SlotViewKind::Multi { count: 3 });
    assert!(chooser
        .options
        .iter()
        .any(|o| o.group.as_deref() == Some("Tools")));
    let arcana = chooser
        .options
        .iter()
        .find(|o| o.id.as_str() == "skill.arcana")
        .unwrap();
    assert!(!arcana.available, "Sage already grants Arcana");
    confirm(
        &engine,
        &mut log,
        SLOT_FEAT_SKILLED,
        many(&["skill.stealth", "skill.nature", "tool.thieves-tools"]),
    );
    let p = engine.project(&log).unwrap();
    assert!(!p
        .checklist
        .iter()
        .any(|e| e.slot.as_str() == SLOT_FEAT_SKILLED));
    assert_eq!(value(&p.sheet, "Skills", "Stealth"), "+2");
    assert!(detail(&p.sheet, "Skills", "Stealth").contains("from Skilled"));
    assert!(value(&p.sheet, "Features", "Additional Tool Proficiencies").contains("Thieves' Tools"));
    let preview = engine
        .clear_preview(&log, &SlotId::new(SLOT_SPECIES_FEAT))
        .unwrap();
    assert!(preview
        .cleared
        .iter()
        .any(|c| c.slot.as_str() == SLOT_FEAT_SKILLED));
}

#[test]
fn a_dwarf_in_package_b_gets_toughness_and_light_armor_dex() {
    let engine = engine();
    let mut log = Vec::new();
    confirm(&engine, &mut log, SLOT_CLASS, one("class.fighter"));
    confirm(
        &engine,
        &mut log,
        SLOT_BACKGROUND,
        one("background.soldier"),
    );
    confirm(
        &engine,
        &mut log,
        SLOT_BACKGROUND_INCREASE,
        Selection::Option(Increase::TwoOne(Ability::Dex, Ability::Con).option_id()),
    );
    confirm(&engine, &mut log, SLOT_SPECIES, one("species.dwarf"));
    confirm(
        &engine,
        &mut log,
        SLOT_SCORES_METHOD,
        one("method.standard-array"),
    );
    confirm(
        &engine,
        &mut log,
        SLOT_SCORES_ASSIGN,
        many(&[
            &score("dex", 15),
            &score("con", 14),
            &score("str", 13),
            &score("wis", 12),
            &score("cha", 10),
            &score("int", 8),
        ]),
    );
    confirm(
        &engine,
        &mut log,
        SLOT_EQUIPMENT_PACKAGE,
        one("package.fighter.b"),
    );
    let sheet = engine.sheet(&log).unwrap();
    // Dex 17 (+3): studded leather 12 + 3.
    assert_eq!(value(&sheet, "Combat", "Armor Class"), "15");
    // HP 10 + 2 Con + 1 Dwarven Toughness.
    assert_eq!(value(&sheet, "Combat", "Hit Points"), "13");
    assert!(detail(&sheet, "Combat", "Hit Points").contains("Dwarf"));
    // Finesse weapons use the better of Str and Dex; the longbow Dex.
    assert_eq!(value(&sheet, "Attacks", "Scimitar"), "+5 · 1d6+3 Slashing");
    assert_eq!(value(&sheet, "Attacks", "Longbow"), "+5 · 1d8+3 Piercing");
    assert!(sheet.summary[1].contains("Darkvision 120 ft."));
    confirm(&engine, &mut log, &slot_level_advance(2), one("advance.2"));
    let sheet = engine.sheet(&log).unwrap();
    assert_eq!(value(&sheet, "Combat", "Hit Points"), "22");
}

#[test]
fn name_pool_key_is_the_species_and_the_subclass_step_is_never_live_early() {
    let rs = crate::embedded();
    let engine = engine();
    let mut log = Vec::new();
    assert_eq!(engine_core::Ruleset::name_pool_key(&*rs, &log), None);
    confirm(&engine, &mut log, SLOT_SPECIES, one("species.halfling"));
    assert_eq!(
        engine_core::Ruleset::name_pool_key(&*rs, &log).as_deref(),
        Some("species.halfling")
    );
    assert!(engine_core::Ruleset::text_fill_candidates(&*rs, &SlotId::new(SLOT_NAME)).is_empty());
    assert!(engine_core::Ruleset::suggested_builds(&*rs).is_empty());
    let steps = engine.live_steps(&log).unwrap();
    let ids: Vec<&str> = steps.iter().map(|(id, _)| id.as_str()).collect();
    assert_eq!(
        ids,
        vec![
            "class",
            "origin",
            "scores",
            "class-choices",
            "equipment",
            "details"
        ]
    );
}
