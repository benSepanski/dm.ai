//! The 5.5e rows of the chargen-dnd architecture: hand-verified goldens
//! (Brannock at 1 and 3, a point-buy gold-alternative build), the level-2
//! empty level and the level-3 subclass catalog, the ability-score
//! machinery property, the fold budget, and — through the real server in
//! a declared 5.5e campaign — the seed sweep to the cap, clone fidelity,
//! and SIGKILL during a confirm and a finalize-pending.

use std::sync::Arc;

use checks::TestServer;
use engine_core::Sampler;
use serde_json::{json, Value};
use types::{
    ChecklistSeverity, Decision, DecisionId, DecisionInput, DecisionSource, OptionId, Selection,
    SlotId, SlotViewKind,
};

#[path = "leveling_helpers.rs"]
mod lv;

const SYSTEM: &str = "dnd5e";

fn engine() -> ruleset_dnd5e::Dnd5eEngine {
    ruleset_dnd5e::engine(Arc::new(
        ruleset_dnd5e::embedded_data().expect("embedded 5.5e data parses"),
    ))
}

fn data() -> ruleset_dnd5e::RulesData {
    ruleset_dnd5e::embedded_data().expect("embedded 5.5e data parses")
}

fn one(id: &str) -> Selection {
    Selection::Option(OptionId::new(id))
}
fn many(ids: &[&str]) -> Selection {
    Selection::Options(ids.iter().map(|i| OptionId::new(*i)).collect())
}
fn score(ability: &str, value: u32) -> String {
    format!("score.{ability}.{value}")
}

fn confirm(
    engine: &ruleset_dnd5e::Dnd5eEngine,
    log: &mut Vec<Decision>,
    slot: &str,
    sel: Selection,
) {
    // Deterministic ids that differ per selection, so re-confirming a slot
    // with a new selection amends rather than replays.
    let key = match &sel {
        Selection::Option(id) => id.as_str().to_string(),
        Selection::Options(ids) => ids.iter().map(|i| i.as_str()).collect::<Vec<_>>().join("+"),
        Selection::Text(t) => t.clone(),
    };
    let input = DecisionInput {
        id: DecisionId::new(format!("{slot}={key}")),
        slot: SlotId::new(slot),
        selection: sel,
        source: DecisionSource::Player,
    };
    match engine.amend(log, input) {
        Ok(engine_core::AppendOutcome::Appended(new_log)) => *log = new_log,
        other => panic!("confirm on '{slot}' rejected: {other:?}"),
    }
}

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

/// Brannock: Human Soldier Fighter, Standard Array, Str +2 / Con +1,
/// Alert and Perception from the Human, Acrobatics + Insight, Defense,
/// greatsword / flail / javelin masteries, package A.
fn brannock_log(engine: &ruleset_dnd5e::Dnd5eEngine) -> Vec<Decision> {
    let mut log = Vec::new();
    confirm(engine, &mut log, "dnd5e.class", one("class.fighter"));
    confirm(
        engine,
        &mut log,
        "dnd5e.background",
        one("background.soldier"),
    );
    confirm(
        engine,
        &mut log,
        "dnd5e.background.increase",
        one("increase.str2-con1"),
    );
    confirm(engine, &mut log, "dnd5e.species", one("species.human"));
    confirm(
        engine,
        &mut log,
        "dnd5e.species.skill",
        one("skill.perception"),
    );
    confirm(
        engine,
        &mut log,
        "dnd5e.species.feat",
        one("feat.origin.alert"),
    );
    confirm(
        engine,
        &mut log,
        "dnd5e.scores.method",
        one("method.standard-array"),
    );
    confirm(engine, &mut log, "dnd5e.scores.assign", brannock_array());
    confirm(
        engine,
        &mut log,
        "dnd5e.class.skills",
        many(&["skill.acrobatics", "skill.insight"]),
    );
    confirm(
        engine,
        &mut log,
        "dnd5e.class.style",
        one("feat.style.defense"),
    );
    confirm(
        engine,
        &mut log,
        "dnd5e.class.masteries",
        many(&["weapon.greatsword", "weapon.flail", "weapon.javelin"]),
    );
    confirm(
        engine,
        &mut log,
        "dnd5e.equipment.package",
        one("package.fighter.a"),
    );
    confirm(
        engine,
        &mut log,
        "dnd5e.background.equipment",
        one("background-equipment.package"),
    );
    confirm(
        engine,
        &mut log,
        "dnd5e.details.name",
        Selection::Text("Brannock".into()),
    );
    log
}

fn advance(engine: &ruleset_dnd5e::Dnd5eEngine, log: &mut Vec<Decision>, level: u32) {
    confirm(
        engine,
        log,
        &ruleset_dnd5e::slot_level_advance(level),
        one(&format!("advance.{level}")),
    );
}

/// Brannock at 3: advance twice, the Champion at 3.
fn brannock_3_log(engine: &ruleset_dnd5e::Dnd5eEngine) -> Vec<Decision> {
    let mut log = brannock_log(engine);
    advance(engine, &mut log, 2);
    advance(engine, &mut log, 3);
    confirm(
        engine,
        &mut log,
        &ruleset_dnd5e::slot_level_subclass(3),
        one("subclass.fighter.champion"),
    );
    log
}

/// A point-buy build spending exactly the budget, taking the gold
/// alternative: unarmored, nothing carried.
fn gold_log(engine: &ruleset_dnd5e::Dnd5eEngine) -> Vec<Decision> {
    let mut log = Vec::new();
    confirm(engine, &mut log, "dnd5e.class", one("class.fighter"));
    confirm(
        engine,
        &mut log,
        "dnd5e.background",
        one("background.criminal"),
    );
    confirm(
        engine,
        &mut log,
        "dnd5e.background.increase",
        one("increase.dex2-con1"),
    );
    confirm(engine, &mut log, "dnd5e.species", one("species.halfling"));
    confirm(
        engine,
        &mut log,
        "dnd5e.scores.method",
        one("method.point-buy"),
    );
    confirm(
        engine,
        &mut log,
        "dnd5e.scores.assign",
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
        engine,
        &mut log,
        "dnd5e.class.skills",
        many(&["skill.athletics", "skill.perception"]),
    );
    confirm(
        engine,
        &mut log,
        "dnd5e.class.style",
        one("feat.style.archery"),
    );
    confirm(
        engine,
        &mut log,
        "dnd5e.class.masteries",
        many(&["weapon.dagger", "weapon.shortbow", "weapon.rapier"]),
    );
    confirm(
        engine,
        &mut log,
        "dnd5e.equipment.package",
        one("package.fighter.gold"),
    );
    confirm(
        engine,
        &mut log,
        "dnd5e.background.equipment",
        one("background-equipment.gold"),
    );
    confirm(
        engine,
        &mut log,
        "dnd5e.details.name",
        Selection::Text("Nell".into()),
    );
    log
}

fn value(sheet: &types::SheetView, section: &str, label: &str) -> String {
    sheet
        .entry(section, label)
        .map(|e| e.value.clone())
        .unwrap_or_else(|| panic!("sheet has no {section} / {label}"))
}

fn golden_names() -> [(
    &'static str,
    fn(&ruleset_dnd5e::Dnd5eEngine) -> Vec<Decision>,
); 3] {
    [
        ("brannock", brannock_log),
        ("brannock-3", brannock_3_log),
        ("nell-gold", gold_log),
    ]
}

/// Hand-verified goldens: the committed fixtures equal the walks, replay
/// to the committed sheets, and a few numbers hold by hand.
#[test]
fn goldens_brannock_1_and_3_and_the_gold_alternative() {
    let engine = engine();
    for (name, build) in golden_names() {
        let log = build(&engine);
        let projection = engine.project(&log).unwrap();
        assert!(
            projection.can_finalize,
            "{name}: {:#?}",
            projection.checklist
        );
        let dir = checks::workspace_root().join("checks/fixtures");
        let on_disk = std::fs::read_to_string(dir.join(format!("{name}.log.json")))
            .unwrap_or_else(|_| panic!("missing fixture {name} — run regen_dnd5e_fixtures"));
        let parsed: Vec<Decision> = serde_json::from_str(&on_disk).unwrap();
        assert_eq!(
            parsed, log,
            "fixture {name} is stale — rerun regen_dnd5e_fixtures"
        );
        let sheet_on_disk: types::SheetView = serde_json::from_str(
            &std::fs::read_to_string(dir.join(format!("{name}.sheet.json"))).unwrap(),
        )
        .unwrap();
        assert_eq!(
            engine.sheet(&log).unwrap(),
            sheet_on_disk,
            "{name}: sheet drifted"
        );
    }
    // Hand checks (2024 rules): Fighter 10 + Con (+2 after Soldier's +1 on
    // 14 → 15) = 12 HP; chain mail 16 + Defense 1 = 17; Str 17 → +3 + prof
    // 2 = +5; proficiency bonus +2 through level 4; 3 masteries.
    let brannock = engine.sheet(&brannock_log(&engine)).unwrap();
    assert_eq!(value(&brannock, "Combat", "Hit Points"), "12");
    assert_eq!(value(&brannock, "Combat", "Armor Class"), "17");
    assert_eq!(value(&brannock, "Combat", "Proficiency Bonus"), "+2");
    assert_eq!(value(&brannock, "Saving Throws", "Strength"), "+5");
    assert_eq!(value(&brannock, "Skills", "Athletics"), "+5");
    assert!(
        brannock.summary[0].contains("Human Fighter 1"),
        "{:?}",
        brannock.summary
    );
    // Level 3: +8 per level (6 + Con 2), Champion named, features present.
    let three = engine.sheet(&brannock_3_log(&engine)).unwrap();
    assert_eq!(value(&three, "Combat", "Hit Points"), "28");
    assert!(
        three.summary[0].contains("Fighter 3"),
        "{:?}",
        three.summary
    );
    let features: Vec<&str> = three
        .sections
        .iter()
        .find(|s| s.title == "Features")
        .unwrap()
        .entries
        .iter()
        .map(|e| e.label.as_str())
        .collect();
    for f in [
        "Action Surge",
        "Tactical Mind",
        "Improved Critical",
        "Remarkable Athlete",
    ] {
        assert!(features.contains(&f), "level 3 features: {features:?}");
    }
    // Gold alternative: unarmored AC 10 + Dex (17 → +3) = 13, no attacks.
    let nell = engine.sheet(&gold_log(&engine)).unwrap();
    assert_eq!(value(&nell, "Combat", "Armor Class"), "13");
    let attacks = nell
        .sections
        .iter()
        .find(|s| s.title == "Attacks")
        .expect("Attacks section");
    assert!(
        attacks.entries.is_empty(),
        "nothing carried, nothing to attack with"
    );
    assert!(nell.entry("Equipment", "Coin").is_some(), "coin is shown");
}

/// Regenerates the committed 5.5e fixtures after a deliberate golden
/// change: cargo test -p checks --test dnd5e regen_dnd5e_fixtures -- --ignored
#[test]
#[ignore]
fn regen_dnd5e_fixtures() {
    let engine = engine();
    let dir = checks::workspace_root().join("checks/fixtures");
    for (name, build) in golden_names() {
        let log = build(&engine);
        std::fs::write(
            dir.join(format!("{name}.log.json")),
            serde_json::to_string_pretty(&log).unwrap(),
        )
        .unwrap();
        std::fs::write(
            dir.join(format!("{name}.sheet.json")),
            serde_json::to_string_pretty(&engine.sheet(&log).unwrap()).unwrap(),
        )
        .unwrap();
    }
}

/// Level 2 has no choice slot: the pending level folds with an empty
/// checklist (finalize is available at once). Level 3's checklist holds
/// exactly one Single slot whose option ids are the Fighter's subclass
/// records.
#[test]
fn level_2_is_empty_and_level_3_offers_the_subclass_records() {
    let engine = engine();
    let mut log = brannock_log(&engine);
    advance(&engine, &mut log, 2);
    let p2 = engine.project(&log).unwrap();
    assert!(
        p2.checklist.is_empty() && p2.can_finalize,
        "{:#?}",
        p2.checklist
    );
    let live: Vec<_> = p2.steps.iter().map(|s| s.id.as_str().to_string()).collect();
    assert_eq!(
        live,
        vec!["level-2".to_string()],
        "only the pending level's step is live"
    );
    assert!(p2.steps[0].slots.is_empty(), "level 2 renders no card");

    advance(&engine, &mut log, 3);
    let p3 = engine.project(&log).unwrap();
    let slots: Vec<&types::SlotView> = p3.steps.iter().flat_map(|s| s.slots.iter()).collect();
    assert_eq!(
        slots.len(),
        1,
        "one slot at 3: {:?}",
        slots.iter().map(|s| &s.id).collect::<Vec<_>>()
    );
    assert_eq!(slots[0].kind, SlotViewKind::Single);
    assert_eq!(slots[0].id.as_str(), ruleset_dnd5e::slot_level_subclass(3));
    let mut offered: Vec<String> = slots[0]
        .options
        .iter()
        .map(|o| o.id.as_str().to_string())
        .collect();
    offered.sort();
    let mut records: Vec<String> = data()
        .subclasses
        .iter()
        .filter(|s| s.class == "class.fighter")
        .map(|s| s.id.clone())
        .collect();
    records.sort();
    assert_eq!(
        offered, records,
        "the subclass catalog IS the subclass records"
    );
    assert!(!p3.can_finalize, "the subclass is required");
}

/// Ability-score machinery, swept: for random array and point-buy
/// selections, one pick per ability group and each array value once are
/// legal, a duplicate value or a missing group is flagged, the point-buy
/// cost equals the published table and a spend over the budget is Illegal;
/// changing the method clears the assignment through the dependents graph.
#[test]
fn ability_score_machinery_holds_across_a_seed_sweep() {
    let engine = engine();
    let data = data();
    let abilities = ["str", "dex", "con", "int", "wis", "cha"];
    let point_buy = data
        .scores
        .methods
        .iter()
        .find(|m| m.is_point_buy())
        .expect("a point-buy method");
    let array = data
        .scores
        .methods
        .iter()
        .find(|m| !m.is_point_buy())
        .expect("an array method");
    let base = |engine: &ruleset_dnd5e::Dnd5eEngine, method: &str| {
        let mut log = Vec::new();
        confirm(engine, &mut log, "dnd5e.class", one("class.fighter"));
        confirm(
            engine,
            &mut log,
            "dnd5e.background",
            one("background.soldier"),
        );
        confirm(
            engine,
            &mut log,
            "dnd5e.background.increase",
            one("increase.str2-con1"),
        );
        confirm(engine, &mut log, "dnd5e.species", one("species.dwarf"));
        confirm(engine, &mut log, "dnd5e.scores.method", one(method));
        log
    };
    let illegal_on_assign = |p: &types::ProjectionView| {
        p.checklist.iter().any(|e| {
            e.severity == ChecklistSeverity::Illegal && e.slot.as_str() == "dnd5e.scores.assign"
        })
    };
    for seed in 0..40u64 {
        let mut sampler = Sampler::new(seed);
        // Array: a random permutation is always legal; a duplicate value
        // (two abilities sharing one array value) is always Illegal.
        let values = sampler.shuffled(&array.array);
        let picks: Vec<String> = abilities
            .iter()
            .zip(values.iter())
            .map(|(a, v)| score(a, *v))
            .collect();
        let mut log = base(&engine, &array.id);
        confirm(
            &engine,
            &mut log,
            "dnd5e.scores.assign",
            many(&picks.iter().map(String::as_str).collect::<Vec<_>>()),
        );
        let p = engine.project(&log).unwrap();
        assert!(
            !illegal_on_assign(&p),
            "seed {seed}: a permutation is legal: {:#?}",
            p.checklist
        );
        let mut dup = picks.clone();
        dup[1] = score(abilities[1], values[0]);
        confirm(
            &engine,
            &mut log,
            "dnd5e.scores.assign",
            many(&dup.iter().map(String::as_str).collect::<Vec<_>>()),
        );
        let p = engine.project(&log).unwrap();
        assert!(
            illegal_on_assign(&p),
            "seed {seed}: a reused array value is Illegal"
        );
        // A missing group (five picks) is flagged, never clamped.
        confirm(
            &engine,
            &mut log,
            "dnd5e.scores.assign",
            many(&picks[..5].iter().map(String::as_str).collect::<Vec<_>>()),
        );
        let p = engine.project(&log).unwrap();
        assert!(
            p.checklist
                .iter()
                .any(|e| e.slot.as_str() == "dnd5e.scores.assign"),
            "seed {seed}: five picks leave the slot on the checklist"
        );

        // Point buy: random scores in the offered range; the engine's
        // verdict must agree with the published cost table.
        let offered = point_buy.offered_scores();
        let picks: Vec<(String, u32)> = abilities
            .iter()
            .map(|a| {
                let v = *sampler.pick(&offered).unwrap();
                (score(a, v), v)
            })
            .collect();
        let cost: u32 = picks
            .iter()
            .map(|(_, v)| point_buy.cost_of(*v).unwrap())
            .sum();
        let mut log = base(&engine, &point_buy.id);
        confirm(
            &engine,
            &mut log,
            "dnd5e.scores.assign",
            many(&picks.iter().map(|(id, _)| id.as_str()).collect::<Vec<_>>()),
        );
        let p = engine.project(&log).unwrap();
        assert_eq!(
            illegal_on_assign(&p),
            cost > point_buy.budget,
            "seed {seed}: cost {cost} vs budget {} — the engine and the table must agree",
            point_buy.budget
        );
        // Changing the method clears the assignment (and only it).
        let preview = engine
            .clear_preview(&log, &SlotId::new("dnd5e.scores.method"))
            .unwrap();
        let cleared: Vec<&str> = preview.cleared.iter().map(|c| c.slot.as_str()).collect();
        assert!(cleared.contains(&"dnd5e.scores.assign"), "{cleared:?}");
        assert!(!cleared.contains(&"dnd5e.class"), "{cleared:?}");
    }
}

/// Fold of a complete 5.5e level-3 log stays under the 5 ms budget.
#[test]
fn fold_of_a_level_3_log_is_under_5ms() {
    let engine = engine();
    let log = brannock_3_log(&engine);
    for _ in 0..10 {
        let _ = engine.sheet(&log).unwrap();
    }
    let runs = 100;
    let start = std::time::Instant::now();
    for _ in 0..runs {
        std::hint::black_box(engine.sheet(std::hint::black_box(&log)).unwrap());
    }
    let per_run = start.elapsed() / runs;
    assert!(
        per_run < std::time::Duration::from_millis(5),
        "5.5e level-3 fold took {per_run:?} per run — budget is 5 ms"
    );
}

// ---- Through the real server, in a declared 5.5e campaign ----

fn client() -> reqwest::blocking::Client {
    reqwest::blocking::Client::builder()
        .timeout(std::time::Duration::from_secs(10))
        .build()
        .unwrap()
}

fn campaign_dir() -> tempfile::TempDir {
    let dir = tempfile::tempdir().unwrap();
    checks::declare_campaign(dir.path(), SYSTEM);
    dir
}

/// Mint a random 5.5e character and finalize it; returns its id.
fn minted_finalized(client: &reqwest::blocking::Client, url: &str, seed: &str) -> String {
    let (status, result) = lv::post_json(
        client,
        url,
        "/api/characters/random-mint",
        json!({ "request_id": seed, "class_id": null, "name": null }),
    );
    assert_eq!(status, 200, "{result}");
    let draft = &result["draft"];
    assert!(
        result["unresolved"].as_array().unwrap().is_empty(),
        "{seed}: every slot filled: {}",
        result["unresolved"]
    );
    assert!(
        draft["projection"]["checklist"]
            .as_array()
            .unwrap()
            .is_empty(),
        "{seed}: empty checklist: {}",
        draft["projection"]["checklist"]
    );
    assert!(draft["projection"]["can_finalize"].as_bool().unwrap());
    let id = draft["id"].as_str().unwrap().to_string();
    let (status, outcome) = lv::post_json(
        client,
        url,
        &format!("/api/characters/{id}/finalize"),
        json!({ "version": draft["version"] }),
    );
    assert_eq!(status, 200, "{outcome}");
    assert_eq!(outcome["outcome"], "finalized");
    id
}

/// Seed sweep: minted 5.5e characters finalize with an empty checklist,
/// verify clean, and level to the cap (an empty level 2, the subclass at
/// 3); the roster offers no quick build.
#[test]
fn minted_5e_characters_finalize_and_level_to_the_cap_across_seeds() {
    let client = client();
    let dir = campaign_dir();
    let server = TestServer::spawn(dir.path());
    let url = &server.url;
    let roster = lv::get_json(&client, url, "/api/roster");
    assert!(
        roster.get("quick_build").is_none_or(Value::is_null),
        "{roster}"
    );
    let mut seen_species = std::collections::BTreeSet::new();
    for seed in 0..8 {
        let id = minted_finalized(&client, url, &format!("sweep-{seed}"));
        let doc = lv::read_doc(dir.path(), &id);
        assert_eq!(doc["system"], SYSTEM);
        assert_eq!(
            doc["log"]
                .as_array()
                .unwrap()
                .iter()
                .find(|d| d["slot"] == "dnd5e.scores.method")
                .unwrap()["selection"]["value"],
            "method.standard-array",
            "a mint assigns the standard array"
        );
        seen_species.insert(
            doc["log"]
                .as_array()
                .unwrap()
                .iter()
                .find(|d| d["slot"] == "dnd5e.species")
                .unwrap()["selection"]["value"]
                .to_string(),
        );
        // Level 2: no slots, finalize at once. Level 3: the subclass.
        let draft = lv::start_level(&client, url, &id);
        let cards: usize = draft["projection"]["steps"]
            .as_array()
            .unwrap()
            .iter()
            .map(|s| s["slots"].as_array().unwrap().len())
            .sum();
        assert_eq!(cards, 0, "level 2 has no choice slot");
        assert!(draft["projection"]["can_finalize"].as_bool().unwrap());
        assert!(
            draft["level_up"]["gains"]
                .as_array()
                .unwrap()
                .iter()
                .any(|g| g["label"] == "Action Surge"),
            "{}",
            draft["level_up"]
        );
        let (status, outcome) = lv::post_json(
            &client,
            url,
            &format!("/api/characters/{id}/finalize"),
            json!({ "version": draft["version"] }),
        );
        assert_eq!(status, 200, "{outcome}");
        let view = lv::complete_level(&client, url, &id);
        assert_eq!(view["state"], "finalized");
        assert!(view["next_level"].is_null(), "at the cap");
        assert!(view["sheet"]["summary"][0]
            .as_str()
            .unwrap()
            .contains("Fighter 3"));
    }
    assert!(seen_species.len() > 1, "mints vary: {seen_species:?}");
    drop(server);
    let (code, out) = TestServer::run_verify(dir.path(), &[]);
    assert_eq!(code, 0, "{out}");
}

/// Clone in a 5.5e campaign: the clone differs from its source only in id
/// and the name decision; a leveling source clones its pending level and
/// the two diverge independently.
#[test]
fn clone_in_a_5e_campaign_keeps_fidelity_and_pending_levels() {
    let client = client();
    let dir = campaign_dir();
    let server = TestServer::spawn(dir.path());
    let url = &server.url;
    let source = minted_finalized(&client, url, "clone-src");
    let (status, result) = lv::post_json(
        &client,
        url,
        "/api/characters/clone",
        json!({ "request_id": "cl-1", "source_id": source, "name": "Twin" }),
    );
    assert_eq!(status, 200, "{result}");
    let clone = result["id"].as_str().unwrap().to_string();
    let a = lv::read_doc(dir.path(), &source);
    let b = lv::read_doc(dir.path(), &clone);
    assert_eq!(b["system"], SYSTEM);
    let strip = |doc: &Value| {
        let mut d = doc.clone();
        d["id"] = Value::Null;
        let log = d["log"].as_array_mut().unwrap();
        for decision in log.iter_mut() {
            if decision["slot"] == "dnd5e.details.name" {
                *decision = Value::Null;
            }
        }
        d["sheet"]["name"] = Value::Null;
        d
    };
    assert_eq!(strip(&a), strip(&b), "only id and the name decision differ");

    // A leveling source: start level 3 on the source (2 is empty), clone.
    let draft = lv::start_level(&client, url, &source);
    let (status, _) = lv::post_json(
        &client,
        url,
        &format!("/api/characters/{source}/finalize"),
        json!({ "version": draft["version"] }),
    );
    assert_eq!(status, 200);
    let draft = lv::start_level(&client, url, &source);
    assert_eq!(draft["level_up"]["level"], 3);
    let (status, result) = lv::post_json(
        &client,
        url,
        "/api/characters/clone",
        json!({ "request_id": "cl-2", "source_id": source, "name": "Twin 3" }),
    );
    assert_eq!(status, 200, "{result}");
    let clone3 = result["id"].as_str().unwrap().to_string();
    let view = lv::character(&client, url, &clone3);
    assert_eq!(view["state"], "leveling", "the pending level came along");
    let (status, outcome) = lv::post_json(
        &client,
        url,
        &format!("/api/characters/{clone3}/level-up/abandon"),
        json!({ "version": view["draft"]["version"] }),
    );
    assert_eq!(status, 200, "{outcome}");
    assert_eq!(lv::character(&client, url, &clone3)["state"], "finalized");
    assert_eq!(
        lv::character(&client, url, &source)["state"],
        "leveling",
        "the source never moved"
    );
}

/// SIGKILL during a 5.5e confirm and a finalize-pending leaves the prior
/// or the next state: every file loads, verify is clean.
#[test]
fn confirm_and_finalize_pending_under_sigkill_are_prior_or_next_state() {
    let client = reqwest::blocking::Client::builder()
        .timeout(std::time::Duration::from_secs(2))
        .build()
        .unwrap();
    let dir = campaign_dir();
    let id;
    {
        let server = TestServer::spawn(dir.path());
        id = minted_finalized(&client, &server.url, "crash-src");
    }
    for (cycle, delay_ms) in [0u64, 2, 5, 12].into_iter().enumerate() {
        let mut server = TestServer::spawn(dir.path());
        let url = server.url.clone();
        // A pending level 3 to confirm into (level 2 finalizes empty).
        let view = lv::character(&client, &url, &id);
        if view["state"] == "finalized" && view["next_level"] == 2 {
            let draft = lv::start_level(&client, &url, &id);
            let (status, _) = lv::post_json(
                &client,
                &url,
                &format!("/api/characters/{id}/finalize"),
                json!({ "version": draft["version"] }),
            );
            assert_eq!(status, 200);
        }
        let view = lv::character(&client, &url, &id);
        if view["state"] == "finalized" && view["next_level"].is_null() {
            break; // reached the cap in an earlier cycle
        }
        let draft = if view["state"] == "leveling" {
            view["draft"].clone()
        } else {
            lv::start_level(&client, &url, &id)
        };
        let version = draft["version"].as_u64().unwrap();
        let has_pick = draft["projection"]["steps"]
            .as_array()
            .unwrap()
            .iter()
            .flat_map(|s| s["slots"].as_array().unwrap())
            .any(|sl| !sl["decision"].is_null());
        let fire = std::thread::spawn({
            let client = client.clone();
            let id = id.clone();
            move || {
                if has_pick {
                    let _ = client
                        .post(format!("{url}/api/characters/{id}/finalize"))
                        .json(&json!({ "version": version }))
                        .send();
                } else {
                    let _ = client
                        .post(format!("{url}/api/characters/{id}/confirm"))
                        .json(&json!({ "version": version, "decision": {
                            "id": format!("crash-{cycle}-subclass"),
                            "slot": ruleset_dnd5e::slot_level_subclass(3),
                            "selection": {"kind": "option", "value": "subclass.fighter.champion"},
                            "source": "player" } }))
                        .send();
                }
            }
        });
        std::thread::sleep(std::time::Duration::from_millis(delay_ms));
        server.kill();
        fire.join().unwrap();
        let (code, out) = TestServer::run_verify(dir.path(), &[]);
        assert_eq!(code, 0, "cycle {cycle}: {out}");
        let doc = lv::read_doc(dir.path(), &id);
        assert!(doc["state"] == "finalized", "never torn: {}", doc["state"]);
    }
}
