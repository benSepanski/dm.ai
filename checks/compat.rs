//! Compatibility with files an earlier build wrote (dnd-dice, after two
//! defects only real data showed): `checks/fixtures/compat/<version>/` is
//! a campaign directory captured from the build that shipped that
//! rules-data version — finalized characters, a leveled one, drafts parked
//! mid-wizard — and this check opens it with today's build and walks what a
//! DM would: the flags, the values, the explicit re-pin, a level-up with a
//! rolled die, `verify`. Every future slice that changes wording or adds a
//! slot runs against these files without anyone remembering to.

use checks::TestServer;
use serde_json::{json, Value};

#[path = "leveling_helpers.rs"]
mod lv;

const FIXTURE: &str = "checks/fixtures/compat/dnd5e-srd.0.1.0";

fn copy_fixture() -> tempfile::TempDir {
    let dir = tempfile::tempdir().unwrap();
    let src = checks::workspace_root().join(FIXTURE);
    std::fs::copy(src.join("campaign.json"), dir.path().join("campaign.json")).unwrap();
    std::fs::create_dir_all(dir.path().join("characters")).unwrap();
    for entry in std::fs::read_dir(src.join("characters")).unwrap().flatten() {
        std::fs::copy(
            entry.path(),
            dir.path().join("characters").join(entry.file_name()),
        )
        .unwrap();
    }
    dir
}

fn value(sheet: &Value, section: &str, label: &str) -> Value {
    sheet["sections"]
        .as_array()
        .unwrap()
        .iter()
        .find(|s| s["title"] == section)
        .unwrap()["entries"]
        .as_array()
        .unwrap()
        .iter()
        .find(|e| e["label"] == label)
        .unwrap()
        .clone()
}

#[test]
fn files_from_the_previous_build_open_flag_identical_repin_and_level() {
    let dir = copy_fixture();
    let server = TestServer::spawn(dir.path());
    let client = reqwest::blocking::Client::new();
    let url = server.url.as_str();

    // Every character is flagged as an older known version with an
    // identical replay — a wording change is not a divergence — and
    // nothing is quarantined or refused.
    let roster = lv::get_json(&client, url, "/api/roster");
    assert!(
        roster["problems"].as_array().unwrap().is_empty(),
        "{roster}"
    );
    let entries = roster["entries"].as_array().unwrap();
    assert_eq!(entries.len(), 4, "{roster}");
    for e in entries {
        assert_eq!(e["version"]["status"], "older_known", "{e}");
        assert_eq!(e["version"]["pinned"], "dnd5e-srd.0.1.0", "{e}");
        assert_eq!(
            e["version"]["outcome"]["kind"], "identical",
            "a breakdown reworded is not a divergence: {e}"
        );
    }
    let by_name = |name: &str| -> String {
        entries
            .iter()
            .find(|e| e["name"] == name)
            .unwrap_or_else(|| panic!("no {name} in {roster}"))["id"]
            .as_str()
            .unwrap()
            .to_string()
    };
    let brannock = by_name("Brannock");
    let sylvenne = by_name("Sylvenne");
    let parked = by_name("Parked");

    // Values as the earlier build derived them; the stored breakdown is
    // still the earlier build's wording until re-pin.
    let view = lv::character(&client, url, &brannock);
    assert_eq!(view["state"], "finalized");
    assert_eq!(value(&view["sheet"], "Combat", "Hit Points")["value"], "12");
    assert_eq!(
        value(&view["sheet"], "Combat", "Hit Points")["detail"],
        "10 + 2 Con"
    );
    let view2 = lv::character(&client, url, &sylvenne);
    assert_eq!(
        value(&view2["sheet"], "Combat", "Hit Points")["value"],
        "20"
    );

    // The explicit re-pin stores today's wording with the same values.
    let (status, resolved) = lv::post_json(
        &client,
        url,
        &format!("/api/characters/{brannock}/version/repin"),
        json!({"version": view["version"]}),
    );
    assert_eq!(status, 200, "{resolved}");
    assert_eq!(resolved["outcome"], "resolved", "{resolved}");
    let hp = value(&resolved["character"]["sheet"], "Combat", "Hit Points");
    assert_eq!(hp["value"], "12");
    assert!(
        hp["detail"]
            .as_str()
            .unwrap()
            .starts_with("Fighter: 10 hit points at level 1"),
        "{hp}"
    );
    let (_, resolved) = lv::post_json(
        &client,
        url,
        &format!("/api/characters/{sylvenne}/version/repin"),
        json!({"version": view2["version"]}),
    );
    assert_eq!(resolved["outcome"], "resolved", "{resolved}");
    assert_eq!(
        value(&resolved["character"]["sheet"], "Combat", "Hit Points")["value"],
        "20"
    );

    // Level the earlier build's level-2 character to 3 with a rolled die:
    // the gains explanation names this level only, never the ones before.
    let draft = lv::start_level(&client, url, &sylvenne);
    let hp_row = |d: &Value| -> Value {
        d["level_up"]["gains"]
            .as_array()
            .unwrap()
            .iter()
            .find(|r| r["label"] == "Hit Points")
            .cloned()
            .unwrap_or(Value::Null)
    };
    let why = hp_row(&draft)["why"].as_str().unwrap_or("").to_string();
    assert!(why.starts_with("Fighter:"), "{why}");
    assert!(
        !why.contains("Level 1") && !why.contains("Level 2"),
        "{why}"
    );
    let chosen = lv::confirm_option(
        &client,
        url,
        &sylvenne,
        draft["version"].as_u64().unwrap(),
        "compat-choose",
        "dnd5e.level.3.hit-points",
        "hp.roll",
    );
    assert_eq!(chosen["outcome"], "confirmed", "{chosen}");
    let (status, rolled) = lv::post_json(
        &client,
        url,
        &format!("/api/characters/{sylvenne}/roll"),
        json!({"slot": "dnd5e.level.3.hit-die", "version": chosen["draft"]["version"], "decision_id": "compat-roll"}),
    );
    assert_eq!(status, 200, "{rolled}");
    let why = hp_row(&rolled["draft"])["why"]
        .as_str()
        .unwrap()
        .to_string();
    assert!(why.contains("Level 3: rolled"), "{why}");
    assert!(
        !why.contains("Level 1") && !why.contains("Level 2"),
        "{why}"
    );
    let sub = lv::confirm_option(
        &client,
        url,
        &sylvenne,
        rolled["draft"]["version"].as_u64().unwrap(),
        "compat-subclass",
        "dnd5e.level.3.subclass",
        "subclass.fighter.champion",
    );
    assert_eq!(sub["outcome"], "confirmed", "{sub}");
    let (_, fin) = lv::post_json(
        &client,
        url,
        &format!("/api/characters/{sylvenne}/finalize"),
        json!({"version": sub["draft"]["version"]}),
    );
    assert_eq!(fin["outcome"], "finalized", "{fin}");
    let hp3 = value(&fin["sheet"], "Combat", "Hit Points");
    let total: i64 = hp3["value"].as_str().unwrap().parse().unwrap();
    assert!((23..=32).contains(&total), "20 + roll + 2: {hp3}");
    assert!(hp3["detail"].as_str().unwrap().contains("Level 3: rolled"));

    // A draft parked at the ability-score step by the earlier build
    // resumes after re-pin, and the rolling method is now offered.
    let flagged = lv::character(&client, url, &parked);
    assert_eq!(flagged["state"], "flagged_draft", "{flagged}");
    let (_, resolved) = lv::post_json(
        &client,
        url,
        &format!("/api/characters/{parked}/version/repin"),
        json!({"version": flagged["version"]}),
    );
    assert_eq!(resolved["outcome"], "resolved", "{resolved}");
    let draft = lv::character(&client, url, &parked);
    assert_eq!(draft["state"], "draft", "{draft}");
    let method = lv::slot_view(&draft, "dnd5e.scores.method").expect("method card");
    assert!(method["options"]
        .as_array()
        .unwrap()
        .iter()
        .any(|o| o["id"] == "method.roll"));

    // verify: nothing broken, nothing diverged.
    drop(server);
    let (code, out) = TestServer::run_verify(dir.path(), &[]);
    assert_eq!(code, 0, "{out}");
}
