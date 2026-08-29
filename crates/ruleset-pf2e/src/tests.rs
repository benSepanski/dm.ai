//! Unit tests for the slice-2 machinery (spec req 2+3): versatile
//! heritages, background sub-choices, choice-dependent grants, evaluable
//! prerequisites, the new effect variants, and language selection. All run
//! against a synthetic dataset — the shipped data for these mechanics
//! arrives in later tickets — expressed as JSON so the serde shapes the
//! data tickets must follow are locked here too.

use std::sync::Arc;

use engine_core::{AppendOutcome, EngineError};
use serde_json::json;
use types::{
    Decision, DecisionId, DecisionInput, DecisionSource, OptionId, ProjectionView, Selection,
    SlotId, SlotView,
};

use crate::data::{RulesData, RulesDataFiles};
use crate::mechanics::{
    lore_name_from_text, SLOT_ANCESTRY, SLOT_ANCESTRY_FEAT, SLOT_ANCESTRY_LANGUAGES,
    SLOT_BACKGROUND, SLOT_BACKGROUND_BOOST_CHOICE, SLOT_BACKGROUND_BOOST_FREE,
    SLOT_BACKGROUND_LORE, SLOT_BACKGROUND_SKILL, SLOT_CLASS, SLOT_CLASS_SKILL, SLOT_FEAT_LORE,
    SLOT_FEAT_SKILLS, SLOT_FREE_BOOSTS, SLOT_HERITAGE, SLOT_HERITAGE_GENERAL_FEAT,
    SLOT_REPLACEMENT_1, SLOT_TRAINED_SKILLS,
};

// ---- Synthetic dataset -------------------------------------------------

fn src() -> serde_json::Value {
    json!({ "book": "Pathfinder Player Core", "page": 1, "url": "",
            "license": "ORC", "attribution": "test" })
}

fn data_files() -> Vec<(&'static str, String)> {
    let manifest = json!({
        "version": "pf2e-test.0.0.1",
        "system": "pf2e",
        "description": "synthetic records for machinery tests",
        "license_notice": {
            "orc_notice": "ORC License",
            "attribution": "Pathfinder Player Core",
            "reserved": "Reserved Material"
        }
    });
    let skills = json!([
        { "id": "skill.acrobatics", "name": "Acrobatics", "attribute": "dex", "source": src() },
        { "id": "skill.athletics", "name": "Athletics", "attribute": "str", "source": src() },
        { "id": "skill.arcana", "name": "Arcana", "attribute": "int", "source": src() },
        { "id": "skill.nature", "name": "Nature", "attribute": "wis", "source": src() },
        { "id": "skill.religion", "name": "Religion", "attribute": "wis", "source": src() },
        { "id": "skill.medicine", "name": "Medicine", "attribute": "wis", "source": src() },
    ]);
    let ancestries = json!([
        {
            "id": "ancestry.elf", "name": "Elf", "hp": 6, "size": "medium", "speed": 30,
            "boosts": ["dex"], "free_boosts": 1, "flaws": [],
            "languages": ["Common", "Elven"],
            "additional_languages": ["Sylvan", "Draconic", "Ancient Elvish"],
            "traits": ["elf", "humanoid"], "senses": ["low-light vision"],
            "specials": [], "source": src()
        },
        {
            // No additional_languages key: the serde default must hold.
            "id": "ancestry.human", "name": "Human", "hp": 8, "size": "medium", "speed": 25,
            "boosts": [], "free_boosts": 2, "flaws": [],
            "languages": ["Common"], "traits": ["human", "humanoid"], "senses": [],
            "specials": [], "source": src()
        },
    ]);
    let heritages = json!([
        {
            "id": "heritage.elf.woodland", "ancestry": "ancestry.elf",
            "name": "Woodland Elf", "text": "Forest-born.", "effects": [], "source": src()
        },
        {
            // Versatile: ancestry null, feat catalog union, sense upgrade.
            "id": "heritage.versatile.aiuvarin", "ancestry": null,
            "name": "Aiuvarin", "text": "Elf-touched.",
            "feat_ancestries": ["aiuvarin", "ancestry.elf"],
            "effects": [
                { "type": "sense_upgrade", "sense": "darkvision", "otherwise": "low-light vision" }
            ],
            "source": src()
        },
        {
            "id": "heritage.human.versatile", "ancestry": "ancestry.human",
            "name": "Versatile Human", "text": "A general feat.",
            "effects": [{ "type": "choose_from_catalog", "catalog": "general_feats", "count": 1 }],
            "source": src()
        },
    ]);
    let ancestry_feats = json!([
        {
            "id": "feat.ancestry.elf.otherworldly", "ancestry": "ancestry.elf", "level": 1,
            "name": "Otherworldly Acuity", "prerequisites": [], "text": "Elf feat.",
            "effects": [], "source": src()
        },
        {
            "id": "feat.ancestry.elf.polyglot", "ancestry": "ancestry.elf", "level": 1,
            "name": "Wandering Tongues", "prerequisites": [], "text": "Two more languages.",
            "effects": [{ "type": "bonus_languages", "count": 2 }], "source": src()
        },
        {
            // Versatile-heritage feat: catalog key is the heritage's short key.
            "id": "feat.ancestry.aiuvarin.earned-glory", "ancestry": "aiuvarin", "level": 1,
            "name": "Earned Glory", "prerequisites": [], "text": "Aiuvarin feat.",
            "effects": [], "source": src()
        },
        {
            "id": "feat.ancestry.human.basic", "ancestry": "ancestry.human", "level": 1,
            "name": "Adapted Ways", "prerequisites": [], "text": "Human feat.",
            "effects": [], "source": src()
        },
        {
            "id": "feat.ancestry.human.hold-mark", "ancestry": "ancestry.human", "level": 1,
            "name": "Hold Mark", "prerequisites": [], "text": "Choose one of three skills.",
            "effects": [{
                "type": "choose_skills", "count": 1, "source_label": "Hold Mark",
                "from": ["skill.athletics", "skill.nature", "skill.religion"]
            }],
            "source": src()
        },
        {
            "id": "feat.ancestry.human.obsession", "ancestry": "ancestry.human", "level": 1,
            "name": "Consuming Obsession", "prerequisites": [], "text": "Name a Lore.",
            "effects": [{ "type": "choose_lore", "source_label": "Consuming Obsession" }],
            "source": src()
        },
        {
            "id": "feat.ancestry.human.attr-gate", "ancestry": "ancestry.human", "level": 1,
            "name": "Stoneskin Discipline",
            "prerequisites": [{ "kind": "attribute", "attribute": "con", "value": 2 }],
            "text": "Needs Con +2.", "effects": [], "source": src()
        },
        {
            "id": "feat.ancestry.human.skill-gate", "ancestry": "ancestry.human", "level": 1,
            "name": "Tumbling Tradition",
            "prerequisites": [{ "kind": "trained_skill", "skill": "skill.acrobatics" }],
            "text": "Needs Acrobatics.", "effects": [], "source": src()
        },
        {
            "id": "feat.ancestry.human.seedpod", "ancestry": "ancestry.human", "level": 1,
            "name": "Seedpod", "prerequisites": [], "text": "Ranged unarmed attack.",
            "effects": [{
                "type": "unarmed_attack", "name": "Seedpod", "damage": "1d4 B",
                "traits": ["unarmed"], "range": "30 feet"
            }],
            "source": src()
        },
        {
            "id": "feat.ancestry.human.iron-fists", "ancestry": "ancestry.human", "level": 1,
            "name": "Iron Fists", "prerequisites": [], "text": "Harder fists.",
            "effects": [{
                "type": "unarmed_attack", "name": "Iron Fists", "damage": "1d6 B",
                "traits": ["agile", "unarmed"], "replaces_fist": true
            }],
            "source": src()
        },
        {
            "id": "feat.ancestry.human.canny-will", "ancestry": "ancestry.human", "level": 1,
            "name": "Canny Discipline", "prerequisites": [], "text": "Expert Will and Perception.",
            "effects": [
                { "type": "proficiency_override", "target": "will", "rank": "expert" },
                { "type": "proficiency_override", "target": "perception", "rank": "expert" }
            ],
            "source": src()
        },
    ]);
    let backgrounds = json!([
        {
            // The slice-1 shape, untouched fields: serde defaults must hold.
            "id": "background.field-medic", "name": "Field Medic", "text": "Mended wounds.",
            "boost_choice": ["con", "wis"], "skill": "skill.medicine",
            "lore": "Warfare Lore", "skill_feat": "Battle Medicine", "source": src()
        },
        {
            // Skill sub-choice + choice-dependent skill feat (Scholar).
            "id": "background.scholar", "name": "Scholar", "text": "Studied deeply.",
            "boost_choice": ["int", "wis"], "skill": "",
            "skill_choice": ["skill.arcana", "skill.nature", "skill.religion"],
            "lore": "Academia Lore", "skill_feat": "",
            "skill_feat_by_choice": {
                "skill.arcana": "Assurance (Arcana)",
                "skill.nature": "Assurance (Nature)",
                "skill.religion": "Assurance (Religion)"
            },
            "source": src()
        },
        {
            // Player-named Lore (Nomad).
            "id": "background.nomad", "name": "Nomad", "text": "Wandered far.",
            "boost_choice": ["con", "wis"], "skill": "skill.nature",
            "lore": "", "lore_player_named": true,
            "skill_feat": "Assurance (Survival)", "source": src()
        },
    ]);
    let classes = json!([
        {
            "id": "class.fighter", "name": "Fighter", "text": "Weapon master.",
            "key_attribute_choice": ["str", "dex"], "hp_per_level": 10,
            "proficiencies": {
                "perception": "expert", "fortitude": "expert", "reflex": "expert",
                "will": "trained", "simple_weapons": "expert", "martial_weapons": "expert",
                "advanced_weapons": "trained", "unarmed_attacks": "expert",
                "armor": "trained", "unarmored_defense": "trained", "class_dc": "trained"
            },
            "class_skill_choice": ["skill.acrobatics", "skill.athletics"],
            "additional_skills_base": 3, "features": [], "source": src()
        }
    ]);
    let class_feats = json!([
        {
            "id": "feat.class.fighter.strike", "class": "class.fighter", "level": 1,
            "name": "Certain Strike", "actions": "one-action", "prerequisites": [],
            "requirements": null, "text": "Hit things.", "source": src()
        }
    ]);
    let general_feats = json!([
        {
            "id": "feat.general.toughness", "name": "Toughness", "level": 1,
            "prerequisites": [], "text": "More HP.",
            "effects": [{ "type": "hp_per_level", "value": 1 }], "source": src()
        },
        {
            "id": "feat.general.assurance-gate", "name": "Assured Balance", "level": 1,
            "prerequisites": [{ "kind": "trained_skill", "skill": "skill.acrobatics" }],
            "text": "Needs Acrobatics.", "effects": [], "source": src()
        },
    ]);
    let equipment = json!({ "weapons": [], "armor": [], "shields": [], "gear": [], "kits": [] });

    vec![
        ("manifest", manifest.to_string()),
        ("ancestries", ancestries.to_string()),
        ("heritages", heritages.to_string()),
        ("ancestry_feats", ancestry_feats.to_string()),
        ("backgrounds", backgrounds.to_string()),
        ("classes", classes.to_string()),
        ("class_feats", class_feats.to_string()),
        ("general_feats", general_feats.to_string()),
        ("skills", skills.to_string()),
        ("equipment", equipment.to_string()),
    ]
}

fn data() -> RulesData {
    let files = data_files();
    let get = |name: &str| files.iter().find(|(n, _)| *n == name).unwrap().1.as_str();
    RulesData::parse(&RulesDataFiles {
        manifest: get("manifest"),
        ancestries: get("ancestries"),
        heritages: get("heritages"),
        ancestry_feats: get("ancestry_feats"),
        backgrounds: get("backgrounds"),
        classes: get("classes"),
        class_feats: get("class_feats"),
        general_feats: get("general_feats"),
        skills: get("skills"),
        equipment: get("equipment"),
    })
    .expect("synthetic dataset parses and passes integrity")
}

fn engine() -> crate::Pf2eEngine {
    crate::engine(Arc::new(data()))
}

// ---- Driving helpers ---------------------------------------------------

fn one(id: &str) -> Selection {
    Selection::Option(OptionId::new(id))
}
fn many(ids: &[&str]) -> Selection {
    Selection::Options(ids.iter().map(|i| OptionId::new(*i)).collect())
}
fn text(t: &str) -> Selection {
    Selection::Text(t.to_string())
}

fn try_confirm(
    engine: &crate::Pf2eEngine,
    log: &mut Vec<Decision>,
    slot: &str,
    selection: Selection,
) -> Result<(), EngineError> {
    let input = DecisionInput {
        id: DecisionId::new(format!("t-{}-{}", slot, log.len())),
        slot: SlotId::new(slot),
        selection,
        source: DecisionSource::Player,
    };
    match engine.append(log, input)? {
        AppendOutcome::Appended(new_log) => {
            *log = new_log;
            Ok(())
        }
        AppendOutcome::AlreadyPresent => Ok(()),
    }
}

fn confirm(engine: &crate::Pf2eEngine, log: &mut Vec<Decision>, slot: &str, selection: Selection) {
    try_confirm(engine, log, slot, selection)
        .unwrap_or_else(|e| panic!("confirm on '{slot}' rejected: {e}"));
}

fn slot_view<'a>(projection: &'a ProjectionView, slot: &str) -> Option<&'a SlotView> {
    projection
        .steps
        .iter()
        .flat_map(|s| &s.slots)
        .find(|s| s.id.as_str() == slot)
}

fn option_labels(view: &SlotView) -> Vec<&str> {
    view.options.iter().map(|o| o.label.as_str()).collect()
}

fn find_option<'a>(view: &'a SlotView, id: &str) -> &'a types::OptionView {
    view.options
        .iter()
        .find(|o| o.id.as_str() == id)
        .unwrap_or_else(|| panic!("option '{id}' missing"))
}

// ---- Schema conventions (what T3/T4 data entry must follow) ------------

#[test]
fn synthetic_dataset_parses_and_passes_integrity() {
    let d = data();
    let aiuvarin = d.heritage("heritage.versatile.aiuvarin").unwrap();
    assert!(aiuvarin.is_versatile());
    assert_eq!(aiuvarin.short_key(), "aiuvarin");
    let woodland = d.heritage("heritage.elf.woodland").unwrap();
    assert!(!woodland.is_versatile());
    // Old-shape records get the serde defaults.
    let medic = d.background("background.field-medic").unwrap();
    assert!(medic.skill_choice.is_empty());
    assert!(!medic.lore_player_named);
    assert!(medic.skill_feat_by_choice.is_empty());
    let human = d.ancestry("ancestry.human").unwrap();
    assert!(human.additional_languages.is_empty());
}

#[test]
fn integrity_rejects_bad_new_shapes() {
    let base = data();

    let mut d = base.clone();
    d.heritages[1].feat_ancestries.push("nephilim".into());
    let err = d.check_integrity().unwrap_err().to_string();
    assert!(err.contains("feat_ancestries"), "{err}");

    let mut d = base.clone();
    d.ancestry_feats[2].ancestry = "changeling".into();
    let err = d.check_integrity().unwrap_err().to_string();
    assert!(err.contains("catalog key"), "{err}");

    let mut d = base.clone();
    d.backgrounds[1].skill_choice.clear(); // scholar: no skill, no choice
    d.backgrounds[1].skill_feat_by_choice.clear();
    let err = d.check_integrity().unwrap_err().to_string();
    assert!(err.contains("neither a fixed skill"), "{err}");

    let mut d = base.clone();
    d.backgrounds[1]
        .skill_feat_by_choice
        .insert("skill.medicine".into(), "Assurance (Medicine)".into());
    let err = d.check_integrity().unwrap_err().to_string();
    assert!(err.contains("skill_feat_by_choice"), "{err}");

    let mut d = base.clone();
    d.backgrounds[2].lore = "Fixed Lore".into(); // nomad is lore_player_named
    let err = d.check_integrity().unwrap_err().to_string();
    assert!(err.contains("lore_player_named"), "{err}");

    let mut d = base.clone();
    d.ancestries[0].additional_languages.push("Elven".into());
    let err = d.check_integrity().unwrap_err().to_string();
    assert!(err.contains("additional language"), "{err}");

    let mut d = base.clone();
    if let crate::data::Effect::ChooseSkills { from, .. } = &mut d.ancestry_feats[4].effects[0] {
        from.push("skill.nonexistent".into());
    } else {
        panic!("hold-mark effect shape changed");
    }
    let err = d.check_integrity().unwrap_err().to_string();
    assert!(err.contains("unknown skill"), "{err}");
}

// ---- Versatile heritages -----------------------------------------------

#[test]
fn versatile_heritage_offered_under_any_ancestry() {
    let engine = engine();
    let mut log = Vec::new();
    confirm(&engine, &mut log, SLOT_ANCESTRY, one("ancestry.human"));
    let p = engine.project(&log).unwrap();
    let heritage = slot_view(&p, SLOT_HERITAGE).unwrap();
    let labels = option_labels(heritage);
    assert!(labels.contains(&"Aiuvarin"), "{labels:?}");
    assert!(!labels.contains(&"Woodland Elf"), "{labels:?}");

    let mut log = Vec::new();
    confirm(&engine, &mut log, SLOT_ANCESTRY, one("ancestry.elf"));
    let p = engine.project(&log).unwrap();
    let labels = option_labels(slot_view(&p, SLOT_HERITAGE).unwrap());
    assert!(labels.contains(&"Aiuvarin") && labels.contains(&"Woodland Elf"));
}

#[test]
fn versatile_heritage_applies_anywhere_bound_heritage_does_not() {
    let engine = engine();
    let mut log = Vec::new();
    confirm(&engine, &mut log, SLOT_ANCESTRY, one("ancestry.human"));
    confirm(
        &engine,
        &mut log,
        SLOT_HERITAGE,
        one("heritage.versatile.aiuvarin"),
    );

    let mut log = Vec::new();
    confirm(&engine, &mut log, SLOT_ANCESTRY, one("ancestry.human"));
    let err = try_confirm(
        &engine,
        &mut log,
        SLOT_HERITAGE,
        one("heritage.elf.woodland"),
    )
    .unwrap_err()
    .to_string();
    assert!(err.contains("does not belong"), "{err}");
}

#[test]
fn ancestry_feat_catalog_becomes_the_union() {
    let engine = engine();
    let mut log = Vec::new();
    confirm(&engine, &mut log, SLOT_ANCESTRY, one("ancestry.human"));

    // Without the heritage: base-ancestry feats only, and a versatile-key
    // feat is rejected on apply.
    let p = engine.project(&log).unwrap();
    let labels = option_labels(slot_view(&p, SLOT_ANCESTRY_FEAT).unwrap());
    assert!(labels.contains(&"Adapted Ways"));
    assert!(!labels.contains(&"Earned Glory") && !labels.contains(&"Otherworldly Acuity"));
    let err = try_confirm(
        &engine,
        &mut log,
        SLOT_ANCESTRY_FEAT,
        one("feat.ancestry.aiuvarin.earned-glory"),
    )
    .unwrap_err()
    .to_string();
    assert!(err.contains("not in the feat catalog"), "{err}");

    // With Aiuvarin: human ∪ aiuvarin ∪ elf (its feat_ancestries).
    confirm(
        &engine,
        &mut log,
        SLOT_HERITAGE,
        one("heritage.versatile.aiuvarin"),
    );
    let p = engine.project(&log).unwrap();
    let labels = option_labels(slot_view(&p, SLOT_ANCESTRY_FEAT).unwrap());
    assert!(
        labels.contains(&"Adapted Ways")
            && labels.contains(&"Earned Glory")
            && labels.contains(&"Otherworldly Acuity"),
        "{labels:?}"
    );
    confirm(
        &engine,
        &mut log,
        SLOT_ANCESTRY_FEAT,
        one("feat.ancestry.aiuvarin.earned-glory"),
    );
}

#[test]
fn heritage_change_cascades_the_ancestry_feat() {
    let engine = engine();
    let mut log = Vec::new();
    confirm(&engine, &mut log, SLOT_ANCESTRY, one("ancestry.human"));
    confirm(
        &engine,
        &mut log,
        SLOT_HERITAGE,
        one("heritage.versatile.aiuvarin"),
    );
    confirm(
        &engine,
        &mut log,
        SLOT_ANCESTRY_FEAT,
        one("feat.ancestry.aiuvarin.earned-glory"),
    );
    let cleared = engine.clear(&log, &SlotId::new(SLOT_HERITAGE)).unwrap();
    assert!(
        !cleared
            .iter()
            .any(|d| d.slot.as_str() == SLOT_ANCESTRY_FEAT),
        "the union-derived feat must clear with the heritage"
    );
}

#[test]
fn sense_upgrade_follows_the_base_ancestry() {
    let engine = engine();
    // Elf already has low-light vision: the upgrade grants darkvision.
    let mut log = Vec::new();
    confirm(&engine, &mut log, SLOT_ANCESTRY, one("ancestry.elf"));
    confirm(
        &engine,
        &mut log,
        SLOT_HERITAGE,
        one("heritage.versatile.aiuvarin"),
    );
    let sheet = engine.sheet(&log).unwrap();
    assert!(
        sheet.summary[1].contains("darkvision"),
        "{:?}",
        sheet.summary
    );

    // Human has neither: the upgrade grants the lower sense.
    let mut log = Vec::new();
    confirm(&engine, &mut log, SLOT_ANCESTRY, one("ancestry.human"));
    confirm(
        &engine,
        &mut log,
        SLOT_HERITAGE,
        one("heritage.versatile.aiuvarin"),
    );
    let sheet = engine.sheet(&log).unwrap();
    assert!(
        sheet.summary[1].contains("low-light vision") && !sheet.summary[1].contains("darkvision"),
        "{:?}",
        sheet.summary
    );
}

// ---- Background sub-choices --------------------------------------------

#[test]
fn background_skill_subchoice_opens_only_when_offered() {
    let engine = engine();
    let mut log = Vec::new();
    confirm(
        &engine,
        &mut log,
        SLOT_BACKGROUND,
        one("background.field-medic"),
    );
    let p = engine.project(&log).unwrap();
    assert!(slot_view(&p, SLOT_BACKGROUND_SKILL).is_none());
    assert!(slot_view(&p, SLOT_BACKGROUND_LORE).is_none());

    let mut log = Vec::new();
    confirm(
        &engine,
        &mut log,
        SLOT_BACKGROUND,
        one("background.scholar"),
    );
    let p = engine.project(&log).unwrap();
    let sub = slot_view(&p, SLOT_BACKGROUND_SKILL).expect("sub-choice slot open");
    assert_eq!(option_labels(sub), vec!["Arcana", "Nature", "Religion"]);
    assert!(p
        .checklist
        .iter()
        .any(|e| e.slot.as_str() == SLOT_BACKGROUND_SKILL));
}

#[test]
fn background_skill_subchoice_trains_and_steers_the_skill_feat() {
    let engine = engine();
    let mut log = Vec::new();
    confirm(
        &engine,
        &mut log,
        SLOT_BACKGROUND,
        one("background.scholar"),
    );
    // Only the offered skills are accepted.
    let err = try_confirm(
        &engine,
        &mut log,
        SLOT_BACKGROUND_SKILL,
        one("skill.medicine"),
    )
    .unwrap_err()
    .to_string();
    assert!(
        err.contains("not one of the background's skill options"),
        "{err}"
    );
    confirm(
        &engine,
        &mut log,
        SLOT_BACKGROUND_SKILL,
        one("skill.nature"),
    );
    // Class present so the sheet has a Skills section.
    confirm(&engine, &mut log, SLOT_CLASS, one("class.fighter"));
    let sheet = engine.sheet(&log).unwrap();
    let nature = sheet.entry("Skills", "Nature").unwrap();
    assert!(
        nature
            .detail
            .as_deref()
            .unwrap()
            .contains("from Background: Scholar"),
        "{:?}",
        nature.detail
    );
    // The choice-dependent skill feat follows the chosen skill.
    assert!(
        sheet.entry("Features", "Assurance (Nature)").is_some(),
        "choice-dependent skill feat missing"
    );
    assert!(sheet.entry("Features", "Assurance (Arcana)").is_none());
}

#[test]
fn background_subchoice_clears_with_the_background() {
    let engine = engine();
    let mut log = Vec::new();
    confirm(
        &engine,
        &mut log,
        SLOT_BACKGROUND,
        one("background.scholar"),
    );
    confirm(
        &engine,
        &mut log,
        SLOT_BACKGROUND_SKILL,
        one("skill.arcana"),
    );
    let cleared = engine.clear(&log, &SlotId::new(SLOT_BACKGROUND)).unwrap();
    assert!(cleared.is_empty(), "cascade must take the sub-choice too");
    let state = engine.fold(&cleared).unwrap();
    assert!(state.background_skill_choice.is_none());
    assert!(state.skill_grants.is_empty());
}

#[test]
fn background_subchoice_feeds_the_replacement_machinery() {
    let engine = engine();
    let mut log = Vec::new();
    confirm(&engine, &mut log, SLOT_CLASS, one("class.fighter"));
    confirm(&engine, &mut log, SLOT_CLASS_SKILL, one("skill.acrobatics"));
    confirm(
        &engine,
        &mut log,
        SLOT_TRAINED_SKILLS,
        many(&["skill.religion", "skill.medicine", "skill.athletics"]),
    );
    confirm(
        &engine,
        &mut log,
        SLOT_BACKGROUND,
        one("background.scholar"),
    );
    confirm(
        &engine,
        &mut log,
        SLOT_BACKGROUND_SKILL,
        one("skill.religion"),
    );
    let p = engine.project(&log).unwrap();
    let replacement = slot_view(&p, SLOT_REPLACEMENT_1).expect("collision opens a replacement");
    assert!(replacement.locked_reason.is_none());
    assert!(p.checklist.iter().any(|e| {
        e.slot.as_str() == SLOT_REPLACEMENT_1 && e.message.contains("already trained")
    }));
}

#[test]
fn player_named_background_lore_lands_trained() {
    let engine = engine();
    let mut log = Vec::new();
    confirm(&engine, &mut log, SLOT_BACKGROUND, one("background.nomad"));
    let p = engine.project(&log).unwrap();
    let lore_slot = slot_view(&p, SLOT_BACKGROUND_LORE).expect("lore slot open");
    assert!(matches!(
        lore_slot.kind,
        types::SlotViewKind::Text { multiline: false }
    ));
    // Whitespace-only text is rejected outright.
    let err = try_confirm(&engine, &mut log, SLOT_BACKGROUND_LORE, text("   "))
        .unwrap_err()
        .to_string();
    assert!(err.contains("subject"), "{err}");
    // A trailing "Lore" word is stripped, so "Steppe Lore" doesn't double.
    confirm(
        &engine,
        &mut log,
        SLOT_BACKGROUND_LORE,
        text("  Steppe Lore "),
    );
    let sheet = engine.sheet(&log).unwrap();
    let entry = sheet.entry("Languages & Lore", "Steppe Lore");
    // Sheet's lore section needs an ancestry; check the folded state instead.
    assert!(entry.is_none());
    let state = engine.fold(&log).unwrap();
    assert_eq!(
        state.lores,
        vec![("Steppe Lore".to_string(), "Background: Nomad".to_string())]
    );
}

// ---- Choice-dependent grants on feats ----------------------------------

#[test]
fn choose_skills_from_subset_restricts_catalog_and_apply() {
    let engine = engine();
    let mut log = Vec::new();
    confirm(&engine, &mut log, SLOT_ANCESTRY, one("ancestry.human"));
    confirm(
        &engine,
        &mut log,
        SLOT_ANCESTRY_FEAT,
        one("feat.ancestry.human.hold-mark"),
    );
    let p = engine.project(&log).unwrap();
    let chooser = slot_view(&p, SLOT_FEAT_SKILLS).expect("chooser open");
    assert_eq!(
        option_labels(chooser),
        vec!["Athletics", "Nature", "Religion"]
    );
    let err = try_confirm(&engine, &mut log, SLOT_FEAT_SKILLS, one("skill.acrobatics"))
        .unwrap_err()
        .to_string();
    assert!(err.contains("not one of the skills"), "{err}");
    confirm(&engine, &mut log, SLOT_FEAT_SKILLS, one("skill.athletics"));
    let state = engine.fold(&log).unwrap();
    assert!(state
        .skill_resolution()
        .trained
        .iter()
        .any(|(id, source)| id == "skill.athletics" && source == "Hold Mark"));
}

#[test]
fn choose_lore_feat_opens_the_named_lore_slot() {
    let engine = engine();
    let mut log = Vec::new();
    confirm(&engine, &mut log, SLOT_ANCESTRY, one("ancestry.human"));
    let p = engine.project(&log).unwrap();
    assert!(slot_view(&p, SLOT_FEAT_LORE).is_none());
    confirm(
        &engine,
        &mut log,
        SLOT_ANCESTRY_FEAT,
        one("feat.ancestry.human.obsession"),
    );
    let p = engine.project(&log).unwrap();
    assert!(slot_view(&p, SLOT_FEAT_LORE).is_some());
    assert!(p.checklist.iter().any(|e| {
        e.slot.as_str() == SLOT_FEAT_LORE && e.message.contains("Consuming Obsession")
    }));
    confirm(&engine, &mut log, SLOT_FEAT_LORE, text("Baking"));
    let state = engine.fold(&log).unwrap();
    assert_eq!(
        state.lores,
        vec![("Baking Lore".to_string(), "Consuming Obsession".to_string())]
    );
    // The named Lore dies with the feat.
    let cleared = engine
        .clear(&log, &SlotId::new(SLOT_ANCESTRY_FEAT))
        .unwrap();
    assert!(!cleared.iter().any(|d| d.slot.as_str() == SLOT_FEAT_LORE));
}

#[test]
fn lore_names_normalize() {
    assert_eq!(lore_name_from_text("Steppe").unwrap(), "Steppe Lore");
    assert_eq!(lore_name_from_text("  Steppe  ").unwrap(), "Steppe Lore");
    assert_eq!(lore_name_from_text("Steppe Lore").unwrap(), "Steppe Lore");
    assert_eq!(lore_name_from_text("steppe LORE").unwrap(), "steppe Lore");
    assert!(lore_name_from_text("").is_err());
    assert!(lore_name_from_text("   ").is_err());
    assert!(lore_name_from_text("Lore").is_err());
    assert!(lore_name_from_text(" lore ").is_err());
}

// ---- Evaluable prerequisites -------------------------------------------

#[test]
fn attribute_prerequisite_greys_and_gates_apply() {
    let engine = engine();
    let mut log = Vec::new();
    confirm(&engine, &mut log, SLOT_ANCESTRY, one("ancestry.human"));
    let p = engine.project(&log).unwrap();
    let feat_slot = slot_view(&p, SLOT_ANCESTRY_FEAT).unwrap();
    let gated = find_option(feat_slot, "feat.ancestry.human.attr-gate");
    assert!(!gated.available);
    assert_eq!(
        gated.unavailable_reason.as_deref(),
        Some("requires Constitution +2")
    );
    let err = try_confirm(
        &engine,
        &mut log,
        SLOT_ANCESTRY_FEAT,
        one("feat.ancestry.human.attr-gate"),
    )
    .unwrap_err()
    .to_string();
    assert!(err.contains("requires Constitution +2"), "{err}");

    // Raise Con to +2 (background boost + free boost) and it opens.
    confirm(
        &engine,
        &mut log,
        SLOT_BACKGROUND,
        one("background.field-medic"),
    );
    confirm(
        &engine,
        &mut log,
        SLOT_BACKGROUND_BOOST_CHOICE,
        one("attr.con"),
    );
    confirm(
        &engine,
        &mut log,
        SLOT_BACKGROUND_BOOST_FREE,
        one("attr.wis"),
    );
    confirm(
        &engine,
        &mut log,
        SLOT_FREE_BOOSTS,
        many(&["attr.con", "attr.str", "attr.dex", "attr.wis"]),
    );
    let p = engine.project(&log).unwrap();
    let gated = find_option(
        slot_view(&p, SLOT_ANCESTRY_FEAT).unwrap(),
        "feat.ancestry.human.attr-gate",
    );
    assert!(gated.available, "{:?}", gated.unavailable_reason);
    confirm(
        &engine,
        &mut log,
        SLOT_ANCESTRY_FEAT,
        one("feat.ancestry.human.attr-gate"),
    );
}

#[test]
fn trained_skill_prerequisite_greys_and_gates_apply() {
    let engine = engine();
    let mut log = Vec::new();
    confirm(&engine, &mut log, SLOT_ANCESTRY, one("ancestry.human"));
    let p = engine.project(&log).unwrap();
    let gated = find_option(
        slot_view(&p, SLOT_ANCESTRY_FEAT).unwrap(),
        "feat.ancestry.human.skill-gate",
    );
    assert!(!gated.available);
    assert_eq!(
        gated.unavailable_reason.as_deref(),
        Some("requires trained in Acrobatics")
    );

    confirm(&engine, &mut log, SLOT_CLASS, one("class.fighter"));
    confirm(&engine, &mut log, SLOT_CLASS_SKILL, one("skill.acrobatics"));
    let p = engine.project(&log).unwrap();
    let gated = find_option(
        slot_view(&p, SLOT_ANCESTRY_FEAT).unwrap(),
        "feat.ancestry.human.skill-gate",
    );
    assert!(gated.available);
    confirm(
        &engine,
        &mut log,
        SLOT_ANCESTRY_FEAT,
        one("feat.ancestry.human.skill-gate"),
    );
}

#[test]
fn general_feat_prerequisites_grey_and_gate_apply() {
    let engine = engine();
    let mut log = Vec::new();
    confirm(&engine, &mut log, SLOT_ANCESTRY, one("ancestry.human"));
    confirm(
        &engine,
        &mut log,
        SLOT_HERITAGE,
        one("heritage.human.versatile"),
    );
    let p = engine.project(&log).unwrap();
    let general = slot_view(&p, SLOT_HERITAGE_GENERAL_FEAT).expect("general feat slot open");
    let gated = find_option(general, "feat.general.assurance-gate");
    assert!(!gated.available);
    assert_eq!(
        gated.unavailable_reason.as_deref(),
        Some("requires trained in Acrobatics")
    );
    let err = try_confirm(
        &engine,
        &mut log,
        SLOT_HERITAGE_GENERAL_FEAT,
        one("feat.general.assurance-gate"),
    )
    .unwrap_err()
    .to_string();
    assert!(err.contains("requires trained in Acrobatics"), "{err}");
    confirm(
        &engine,
        &mut log,
        SLOT_HERITAGE_GENERAL_FEAT,
        one("feat.general.toughness"),
    );
}

// ---- New effect variants on the sheet ----------------------------------

#[test]
fn proficiency_override_takes_the_max() {
    let engine = engine();
    let mut log = Vec::new();
    confirm(&engine, &mut log, SLOT_ANCESTRY, one("ancestry.human"));
    confirm(&engine, &mut log, SLOT_CLASS, one("class.fighter"));
    let base = engine.sheet(&log).unwrap();
    // Fighter: Will trained (+3 at level 1, Wis 0), Perception expert (+5).
    assert_eq!(base.entry("Defense", "Will").unwrap().value, "+3");
    assert_eq!(base.entry("Defense", "Perception").unwrap().value, "+5");

    confirm(
        &engine,
        &mut log,
        SLOT_ANCESTRY_FEAT,
        one("feat.ancestry.human.canny-will"),
    );
    let sheet = engine.sheet(&log).unwrap();
    let will = sheet.entry("Defense", "Will").unwrap();
    assert_eq!(will.value, "+5", "expert override must lift trained Will");
    assert!(will.detail.as_deref().unwrap().contains("expert"));
    // An override equal to the class rank changes nothing (max semantics).
    assert_eq!(sheet.entry("Defense", "Perception").unwrap().value, "+5");
}

#[test]
fn ranged_unarmed_attack_uses_dex_and_no_damage_mod() {
    let engine = engine();
    let mut log = Vec::new();
    confirm(&engine, &mut log, SLOT_ANCESTRY, one("ancestry.human"));
    confirm(&engine, &mut log, SLOT_CLASS, one("class.fighter"));
    confirm(
        &engine,
        &mut log,
        SLOT_FREE_BOOSTS,
        many(&["attr.str", "attr.dex", "attr.con", "attr.wis"]),
    );
    confirm(
        &engine,
        &mut log,
        SLOT_ANCESTRY_FEAT,
        one("feat.ancestry.human.seedpod"),
    );
    let sheet = engine.sheet(&log).unwrap();
    // Str +1, Dex +1, unarmed expert (+5): Fist +6 · 1d4+1 B (melee, Str
    // to damage); Seedpod +6 · 1d4 B (Dex to attack, nothing to damage).
    let fist = sheet.entry("Attacks", "Fist").unwrap();
    assert_eq!(fist.value, "+6 · 1d4+1 B");
    let seedpod = sheet.entry("Attacks", "Seedpod").unwrap();
    assert_eq!(seedpod.value, "+6 · 1d4 B");
    let detail = seedpod.detail.as_deref().unwrap();
    assert!(
        detail.contains("Dex") && detail.contains("30 feet"),
        "{detail}"
    );
}

#[test]
fn replaces_fist_swaps_the_builtin_entry() {
    let engine = engine();
    let mut log = Vec::new();
    confirm(&engine, &mut log, SLOT_ANCESTRY, one("ancestry.human"));
    confirm(&engine, &mut log, SLOT_CLASS, one("class.fighter"));
    confirm(
        &engine,
        &mut log,
        SLOT_ANCESTRY_FEAT,
        one("feat.ancestry.human.iron-fists"),
    );
    let sheet = engine.sheet(&log).unwrap();
    assert!(
        sheet.entry("Attacks", "Fist").is_none(),
        "Fist must be replaced"
    );
    assert!(sheet.entry("Attacks", "Iron Fists").is_some());
}

// ---- Language selection ------------------------------------------------

#[test]
fn language_slot_absent_without_list_or_count() {
    let engine = engine();
    // Human: no additional_languages list — never a slot.
    let mut log = Vec::new();
    confirm(&engine, &mut log, SLOT_ANCESTRY, one("ancestry.human"));
    let p = engine.project(&log).unwrap();
    assert!(slot_view(&p, SLOT_ANCESTRY_LANGUAGES).is_none());
    // Elf with Int +0: a list exists but the count is zero — absent, and
    // nothing blocks finalize on its account.
    let mut log = Vec::new();
    confirm(&engine, &mut log, SLOT_ANCESTRY, one("ancestry.elf"));
    let p = engine.project(&log).unwrap();
    assert!(slot_view(&p, SLOT_ANCESTRY_LANGUAGES).is_none());
    assert!(!p
        .checklist
        .iter()
        .any(|e| e.slot.as_str() == SLOT_ANCESTRY_LANGUAGES));
}

#[test]
fn language_count_tracks_int_and_bonuses() {
    let engine = engine();
    let mut log = Vec::new();
    confirm(&engine, &mut log, SLOT_ANCESTRY, one("ancestry.elf"));
    confirm(
        &engine,
        &mut log,
        SLOT_FREE_BOOSTS,
        many(&["attr.int", "attr.str", "attr.con", "attr.wis"]),
    );
    let p = engine.project(&log).unwrap();
    let langs = slot_view(&p, SLOT_ANCESTRY_LANGUAGES).expect("Int +1 opens the chooser");
    assert!(matches!(
        langs.kind,
        types::SlotViewKind::Multi { count: 1 }
    ));
    assert!(p.checklist.iter().any(|e| {
        e.slot.as_str() == SLOT_ANCESTRY_LANGUAGES && e.message.contains("1 additional language")
    }));

    // A bonus_languages effect raises the same count.
    confirm(
        &engine,
        &mut log,
        SLOT_ANCESTRY_FEAT,
        one("feat.ancestry.elf.polyglot"),
    );
    let p = engine.project(&log).unwrap();
    let langs = slot_view(&p, SLOT_ANCESTRY_LANGUAGES).unwrap();
    assert!(matches!(
        langs.kind,
        types::SlotViewKind::Multi { count: 3 }
    ));

    // Picks must come from the ancestry's list.
    let err = try_confirm(
        &engine,
        &mut log,
        SLOT_ANCESTRY_LANGUAGES,
        many(&["lang.gnomish"]),
    )
    .unwrap_err()
    .to_string();
    assert!(err.contains("additional languages"), "{err}");
    confirm(
        &engine,
        &mut log,
        SLOT_ANCESTRY_LANGUAGES,
        many(&["lang.sylvan", "lang.draconic", "lang.ancient-elvish"]),
    );
    let p = engine.project(&log).unwrap();
    assert!(!p
        .checklist
        .iter()
        .any(|e| e.slot.as_str() == SLOT_ANCESTRY_LANGUAGES));
    let sheet = engine.sheet(&log).unwrap();
    assert_eq!(
        sheet.entry("Languages & Lore", "Languages").unwrap().value,
        "Common, Elven, Sylvan, Draconic, Ancient Elvish"
    );
}

#[test]
fn language_overpick_is_flagged_not_silently_kept() {
    let engine = engine();
    let mut log = Vec::new();
    confirm(&engine, &mut log, SLOT_ANCESTRY, one("ancestry.elf"));
    confirm(
        &engine,
        &mut log,
        SLOT_FREE_BOOSTS,
        many(&["attr.int", "attr.str", "attr.con", "attr.wis"]),
    );
    // Two picks against a count of one: applies (tolerable-but-wrong),
    // flagged Illegal by the validator.
    confirm(
        &engine,
        &mut log,
        SLOT_ANCESTRY_LANGUAGES,
        many(&["lang.sylvan", "lang.draconic"]),
    );
    let p = engine.project(&log).unwrap();
    assert!(p.checklist.iter().any(|e| {
        e.slot.as_str() == SLOT_ANCESTRY_LANGUAGES
            && e.message.contains("only 1 allowed")
            && e.severity == types::ChecklistSeverity::Illegal
    }));
}

#[test]
fn languages_render_with_defaults_only_as_before() {
    let engine = engine();
    let mut log = Vec::new();
    confirm(&engine, &mut log, SLOT_ANCESTRY, one("ancestry.elf"));
    let sheet = engine.sheet(&log).unwrap();
    assert_eq!(
        sheet.entry("Languages & Lore", "Languages").unwrap().value,
        "Common, Elven"
    );
}
