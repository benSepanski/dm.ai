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
        Selection::Rolled(sets) => format!(
            "rolled{}:{:?}",
            sets.len(),
            sets.iter().map(|s| &s.groups).collect::<Vec<_>>()
        ),
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

type GoldenBuild = fn(&ruleset_dnd5e::Dnd5eEngine) -> Vec<Decision>;

fn golden_names() -> [(&'static str, GoldenBuild); 4] {
    [
        ("brannock", brannock_log),
        ("brannock-3", brannock_3_log),
        ("nell-gold", gold_log),
        ("ysolde", ysolde_log),
    ]
}

fn rolled_set(groups: &[[u8; 4]], origin: types::RollOrigin) -> types::RolledSet {
    types::RolledSet {
        groups: groups.iter().map(|g| g.to_vec()).collect(),
        origin,
    }
}

/// Ysolde (dnd-dice): Brannock's picks with the rolling method — an app
/// roll first, then an entered set that supersedes it with duplicate
/// twelves and an 18, so Strength reaches the cap with the Soldier's +2.
/// The history keeps both sets; the assignment uses the entered one:
/// Str 18, Dex 12, Con 12, Wis 10, Int 9, Cha 8.
fn ysolde_log(engine: &ruleset_dnd5e::Dnd5eEngine) -> Vec<Decision> {
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
    confirm(engine, &mut log, "dnd5e.scores.method", one("method.roll"));
    // The app's first roll: 9, 8, 8, 7, 11, 6.
    confirm(
        engine,
        &mut log,
        "dnd5e.scores.roll",
        Selection::Rolled(vec![rolled_set(
            &[
                [3, 3, 3, 1],
                [4, 2, 2, 1],
                [3, 3, 2, 2],
                [5, 1, 1, 1],
                [6, 4, 1, 1],
                [2, 2, 2, 1],
            ],
            types::RollOrigin::App,
        )]),
    );
    // Entered by hand, superseding it: 18, 12, 12, 10, 9, 8 (the confirm
    // helper amends, and the engine appends the set onto the history).
    confirm(
        engine,
        &mut log,
        "dnd5e.scores.roll",
        Selection::Rolled(vec![rolled_set(
            &[
                [6, 6, 6, 1],
                [4, 4, 4, 1],
                [5, 4, 3, 3],
                [4, 3, 3, 2],
                [3, 3, 3, 1],
                [6, 1, 1, 1],
            ],
            types::RollOrigin::Entered,
        )]),
    );
    confirm(
        engine,
        &mut log,
        "dnd5e.scores.assign",
        many(&[
            &score("str", 18),
            &score("dex", 12),
            &score("con", 12),
            &score("wis", 10),
            &score("int", 9),
            &score("cha", 8),
        ]),
    );
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
        Selection::Text("Ysolde".into()),
    );
    log
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
    // Level 2 renders no choice card: its one card is the unrequired hit
    // die (dnd-dice), which never blocks finalize.
    let required: Vec<&types::SlotView> = p2.steps[0].slots.iter().filter(|s| s.required).collect();
    assert!(required.is_empty(), "level 2 renders no required card");
    assert_eq!(p2.steps[0].slots.len(), 1);
    assert_eq!(
        p2.steps[0].slots[0].id.as_str(),
        ruleset_dnd5e::slot_level_hit_die(2)
    );

    advance(&engine, &mut log, 3);
    let p3 = engine.project(&log).unwrap();
    let slots: Vec<&types::SlotView> = p3
        .steps
        .iter()
        .flat_map(|s| s.slots.iter())
        .filter(|s| s.required)
        .collect();
    assert_eq!(
        slots.len(),
        1,
        "one required slot at 3: {:?}",
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
#[allow(clippy::disallowed_methods)] // a perf check reads the clock on purpose
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
            .flat_map(|s| s["slots"].as_array().unwrap().iter())
            .filter(|s| s["required"].as_bool().unwrap())
            .count();
        assert_eq!(cards, 0, "level 2 has no required choice slot");
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

// ---- dnd-dice rows ---------------------------------------------------------

/// Ysolde's golden by hand (SRD 5.2.1): the file holds both sets in order
/// with their tags; Strength 18 + 2 = 20 (the cap, reached and not
/// exceeded) → +5, save +7 with proficiency; Con 12 + 1 = 13 → +1, HP 11;
/// the two twelves each name their own faces.
#[test]
fn ysolde_golden_keeps_the_history_and_reaches_the_cap() {
    let engine = engine();
    let log = ysolde_log(&engine);
    let roll = log
        .iter()
        .find(|d| d.slot.as_str() == "dnd5e.scores.roll")
        .unwrap();
    let Selection::Rolled(sets) = &roll.selection else {
        panic!("a rolled selection")
    };
    assert_eq!(sets.len(), 2);
    assert_eq!(sets[0].origin, types::RollOrigin::App);
    assert_eq!(sets[1].origin, types::RollOrigin::Entered);
    let fixture =
        std::fs::read_to_string(checks::workspace_root().join("checks/fixtures/ysolde.log.json"))
            .unwrap();
    assert!(fixture.contains("\"origin\": \"app\"") && fixture.contains("\"origin\": \"entered\""));
    let sheet = engine.sheet(&log).unwrap();
    assert_eq!(value(&sheet, "Ability Scores", "Strength"), "20 (+5)");
    assert_eq!(value(&sheet, "Ability Scores", "Dexterity"), "12 (+1)");
    assert_eq!(value(&sheet, "Ability Scores", "Constitution"), "13 (+1)");
    assert_eq!(value(&sheet, "Saving Throws", "Strength"), "+7");
    assert_eq!(value(&sheet, "Combat", "Hit Points"), "11");
    assert_eq!(value(&sheet, "Combat", "Armor Class"), "17");
    let detail = |label: &str| {
        sheet
            .entry("Ability Scores", label)
            .unwrap()
            .detail
            .clone()
            .unwrap_or_default()
    };
    assert_eq!(
        detail("Strength"),
        "18 (Random Generation: 6, 6, 6, 1 → 18, entered) +2 (Soldier)"
    );
    assert_eq!(
        detail("Dexterity"),
        "12 (Random Generation: 4, 4, 4, 1 → 12, entered)"
    );
    assert_eq!(
        detail("Constitution"),
        "12 (Random Generation: 5, 4, 3, 3 → 12, entered) +1 (Soldier)"
    );
    let projection = engine.project(&log).unwrap();
    assert!(projection.can_finalize, "{:#?}", projection.checklist);
}

/// Assignment multiplicity, swept: over rolled sets with repeats, each
/// total is assignable exactly as often as it was rolled, one per ability,
/// and one use too many is Illegal with the rule named; the array path's
/// by-count rule equals its old by-value behaviour on distinct values.
#[test]
fn rolled_totals_assign_as_often_as_rolled_across_a_seed_sweep() {
    let engine = engine();
    let abilities = ["str", "dex", "con", "int", "wis", "cha"];
    let spec = data()
        .scores
        .methods
        .iter()
        .find(|m| m.is_roll())
        .and_then(|m| m.roll)
        .expect("the rolling method");
    for seed in 0..40u64 {
        let mut sampler = engine_core::Sampler::new(seed.wrapping_mul(7919) + 1);
        // A set with deliberate repeats: faces drawn from a narrow range.
        let faces: Vec<Vec<u8>> = (0..6)
            .map(|_| {
                (0..4)
                    .map(|_| 1 + (sampler.pick_index(3).unwrap() as u8))
                    .collect()
            })
            .collect();
        let mut log = Vec::new();
        confirm(&engine, &mut log, "dnd5e.scores.method", one("method.roll"));
        confirm(
            &engine,
            &mut log,
            "dnd5e.scores.roll",
            Selection::Rolled(vec![types::RolledSet {
                groups: faces.clone(),
                origin: types::RollOrigin::Entered,
            }]),
        );
        let totals: Vec<u32> = faces
            .iter()
            .map(|g| {
                let mut s = g.clone();
                s.sort_unstable_by(|a, b| b.cmp(a));
                s.iter().take(spec.keep as usize).map(|f| *f as u32).sum()
            })
            .collect();
        // Legal: each rolled total used exactly as often as rolled (a
        // permutation of the totals over the abilities).
        let mut order: Vec<usize> = (0..6).collect();
        for i in (1..6).rev() {
            let j = sampler.pick_index(i + 1).unwrap();
            order.swap(i, j);
        }
        let picks: Vec<String> = order
            .iter()
            .enumerate()
            .map(|(a, &t)| score(abilities[a], totals[t]))
            .collect();
        confirm(
            &engine,
            &mut log,
            "dnd5e.scores.assign",
            many(&picks.iter().map(String::as_str).collect::<Vec<_>>()),
        );
        let p = engine.project(&log).unwrap();
        assert!(
            !p.checklist.iter().any(|e| e.step.as_str() == "scores"),
            "seed {seed}: {:?}",
            p.checklist
        );
        // Illegal: the most common total used once more than rolled.
        let most = *totals
            .iter()
            .max_by_key(|t| totals.iter().filter(|x| x == t).count())
            .unwrap();
        let count = totals.iter().filter(|t| **t == most).count();
        let mut over: Vec<String> = Vec::new();
        for (a, t) in order.iter().enumerate() {
            if over
                .iter()
                .filter(|p| p.ends_with(&format!(".{most}")))
                .count()
                <= count
                && totals[*t] != most
            {
                over.push(score(abilities[a], most));
            } else {
                over.push(score(abilities[a], totals[*t]));
            }
        }
        let used = over
            .iter()
            .filter(|p| p.ends_with(&format!(".{most}")))
            .count();
        if used > count {
            let outcome = engine
                .amend(
                    &log,
                    DecisionInput {
                        id: DecisionId::new(format!("over-{seed}")),
                        slot: SlotId::new("dnd5e.scores.assign"),
                        selection: many(&over.iter().map(String::as_str).collect::<Vec<_>>()),
                        source: DecisionSource::Player,
                    },
                )
                .unwrap();
            let engine_core::AppendOutcome::Appended(over_log) = outcome else {
                panic!()
            };
            let p = engine.project(&over_log).unwrap();
            let entry = p
                .checklist
                .iter()
                .find(|e| {
                    e.slot.as_str() == "dnd5e.scores.assign"
                        && e.severity == types::ChecklistSeverity::Illegal
                })
                .unwrap_or_else(|| {
                    panic!(
                        "seed {seed}: over-assignment not flagged: {:?}",
                        p.checklist
                    )
                });
            assert_eq!(entry.rule, "Random Generation");
            assert!(
                entry
                    .message
                    .contains(&format!("{most} assigned {used} times, rolled {count}")),
                "{}",
                entry.message
            );
        }
    }
}

/// Fold of a level-3 log whose roll slot holds a thousand sets stays under
/// the 5 ms budget.
#[test]
#[allow(clippy::disallowed_methods)] // a perf check reads the clock on purpose
fn fold_with_a_thousand_set_history_is_under_5ms() {
    let engine = engine();
    let mut log = ysolde_log(&engine);
    advance(&engine, &mut log, 2);
    advance(&engine, &mut log, 3);
    confirm(
        &engine,
        &mut log,
        &ruleset_dnd5e::slot_level_subclass(3),
        one("subclass.fighter.champion"),
    );
    // Grow the stored history to 1,000 sets by rewriting the decision in
    // place (the engine composes; here the fixture is built directly).
    let index = log
        .iter()
        .position(|d| d.slot.as_str() == "dnd5e.scores.roll")
        .unwrap();
    let Selection::Rolled(sets) = &log[index].selection else {
        panic!()
    };
    let live = sets.last().unwrap().clone();
    let mut history = vec![
        types::RolledSet {
            groups: vec![vec![1, 2, 3, 4]; 6],
            origin: types::RollOrigin::App,
        };
        999
    ];
    history.push(live);
    log[index].selection = Selection::Rolled(history);
    let before = engine.sheet(&ysolde_log(&engine)).unwrap();
    let after = engine
        .sheet(
            &log[..log
                .iter()
                .position(|d| d.slot.as_str() == "dnd5e.level.2.advance")
                .unwrap()],
        )
        .unwrap();
    assert_eq!(before, after, "the superseded sets change nothing");
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
        "1,000-set fold took {per_run:?} per run — budget is 5 ms"
    );
}

/// Rolled hit points through the real server: the gains panel carries the
/// fixed value; the unrequired hit-die card never blocks finalize; a roll
/// through the route lands in the deltas and in the abandon list; abandon
/// discards it with the level; a level finalized without a roll keeps the
/// fixed value.
#[test]
fn hit_dice_ride_the_level_up_views_and_abandon_discards_them() {
    let dir = tempfile::tempdir().unwrap();
    checks::declare_campaign(dir.path(), "dnd5e");
    let server = TestServer::spawn(dir.path());
    let client = reqwest::blocking::Client::new();
    let url = server.url.as_str();
    // Brannock through the API (a mint would sample; confirms are cheap).
    let (status, created) =
        lv::post_json(&client, url, "/api/characters", json!({"name": "Hit Die"}));
    assert_eq!(status, 200, "{created}");
    let id = created["draft"]["id"]
        .as_str()
        .or(created["id"].as_str())
        .unwrap()
        .to_string();
    let mut v = created["version"].as_u64().unwrap();
    let mut n = 0;
    for d in brannock_log(&engine()) {
        if d.slot.as_str() == "dnd5e.details.name" {
            continue;
        }
        n += 1;
        let (status, outcome) = lv::post_json(
            &client,
            url,
            &format!("/api/characters/{id}/confirm"),
            json!({"version": v, "decision": {
                "id": format!("hd-{n}"), "slot": d.slot, "selection": d.selection, "source": "player"
            }}),
        );
        assert_eq!(status, 200, "{outcome}");
        assert_eq!(outcome["outcome"], "confirmed", "{outcome}");
        v = outcome["draft"]["version"].as_u64().unwrap();
    }
    let (status, fin) = lv::post_json(
        &client,
        url,
        &format!("/api/characters/{id}/finalize"),
        json!({"version": v}),
    );
    assert_eq!(status, 200, "{fin}");
    let hp_before = fin["sheet"]["sections"]
        .as_array()
        .unwrap()
        .iter()
        .find(|s| s["title"] == "Combat")
        .unwrap()["entries"]
        .as_array()
        .unwrap()
        .iter()
        .find(|e| e["label"] == "Hit Points")
        .unwrap()["value"]
        .as_str()
        .unwrap()
        .parse::<i64>()
        .unwrap();

    let draft = lv::start_level(&client, url, &id);
    assert!(draft["projection"]["can_finalize"].as_bool().unwrap());
    let card = lv::slot_view(&draft, "dnd5e.level.2.hit-die").expect("the hit-die card");
    assert_eq!(card["required"], false);
    assert_eq!(card["kind"]["kind"], "roll");
    assert!(draft["level_up"]["gains"]
        .as_array()
        .unwrap()
        .iter()
        .any(|d| d["label"] == "Hit Points"));
    // Roll it through the route.
    let (status, rolled) = lv::post_json(
        &client,
        url,
        &format!("/api/characters/{id}/roll"),
        json!({"slot": "dnd5e.level.2.hit-die", "version": draft["version"], "decision_id": "hd-roll-1"}),
    );
    assert_eq!(status, 200, "{rolled}");
    assert_eq!(rolled["outcome"], "confirmed", "{rolled}");
    let after = &rolled["draft"];
    let history = lv::slot_view(after, "dnd5e.level.2.hit-die").unwrap()["options"].clone();
    assert_eq!(history.as_array().unwrap().len(), 1);
    assert_eq!(history[0]["badge"], "rolled");
    let face: i64 = history[0]["label"].as_str().unwrap().parse().unwrap();
    assert!((1..=10).contains(&face));
    assert!(after["projection"]["can_finalize"].as_bool().unwrap());
    // The abandon list names the hit die; the deltas carry the HP.
    let pending = after["level_up"]["pending"].as_array().unwrap();
    let hd = pending
        .iter()
        .find(|p| p["slot"] == "dnd5e.level.2.hit-die")
        .expect("the hit die in the abandon list");
    assert_eq!(hd["slot_label"], "Hit Points");
    assert_eq!(
        hd["selection_label"],
        format!("{face} (rolled, roll 1 of 1)")
    );
    assert!(after["level_up"]["deltas"]
        .as_array()
        .unwrap()
        .iter()
        .any(|d| d["label"] == "Hit Points"));
    // The gains table follows the roll: a die is an input, not a choice.
    let fixed_row = draft["level_up"]["gains"]
        .as_array()
        .unwrap()
        .iter()
        .find(|d| d["label"] == "Hit Points")
        .unwrap()
        .clone();
    let rolled_row = after["level_up"]["gains"]
        .as_array()
        .unwrap()
        .iter()
        .find(|d| d["label"] == "Hit Points")
        .unwrap()
        .clone();
    assert!(
        rolled_row["why"].as_str().unwrap().contains("rolled"),
        "{rolled_row}"
    );
    assert!(
        !fixed_row["why"].as_str().unwrap().contains("rolled"),
        "{fixed_row}"
    );
    let fixed_hp: i64 = fixed_row["new"].as_str().unwrap().parse().unwrap();
    let rolled_hp: i64 = rolled_row["new"].as_str().unwrap().parse().unwrap();
    assert_eq!(
        rolled_hp - fixed_hp,
        face - 6,
        "the row moved by roll minus fixed"
    );
    // Abandon: the file holds no hit-die decision; the sheet is untouched.
    let (status, ab) = lv::post_json(
        &client,
        url,
        &format!("/api/characters/{id}/level-up/abandon"),
        json!({"version": after["version"]}),
    );
    assert_eq!(status, 200, "{ab}");
    let doc = lv::read_doc(dir.path(), &id);
    assert!(!doc["log"]
        .as_array()
        .unwrap()
        .iter()
        .any(|d| d["slot"] == "dnd5e.level.2.hit-die"));
    // Level again and finalize at once without rolling: the fixed value.
    let draft = lv::start_level(&client, url, &id);
    let (status, fin2) = lv::post_json(
        &client,
        url,
        &format!("/api/characters/{id}/finalize"),
        json!({"version": draft["version"]}),
    );
    assert_eq!(status, 200, "{fin2}");
    assert_eq!(fin2["outcome"], "finalized", "{fin2}");
    let hp = fin2["sheet"]["sections"]
        .as_array()
        .unwrap()
        .iter()
        .find(|s| s["title"] == "Combat")
        .unwrap()["entries"]
        .as_array()
        .unwrap()
        .iter()
        .find(|e| e["label"] == "Hit Points")
        .unwrap()
        .clone();
    let con_bonus = hp["value"].as_str().unwrap().parse::<i64>().unwrap() - hp_before - 6;
    assert!((-5..=5).contains(&con_bonus), "fixed 6 + Con: {hp}");
    assert!(
        hp["detail"]
            .as_str()
            .unwrap()
            .contains("Level 2: fixed value 6 +"),
        "{hp}"
    );
}
