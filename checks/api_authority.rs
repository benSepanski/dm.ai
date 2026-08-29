//! Server authority: a raw HTTP confirm of an illegal decision (bypassing
//! the wizard UI entirely) is rejected and appends nothing, and finalize
//! is blocked with every gap listed while the checklist is non-empty.

use checks::TestServer;
use serde_json::{json, Value};

fn confirm_raw(client: &reqwest::blocking::Client, url: &str, id: &str, body: Value) -> Value {
    client
        .post(format!("{url}/api/characters/{id}/confirm"))
        .json(&body)
        .send()
        .unwrap()
        .json()
        .unwrap()
}

#[test]
fn illegal_confirms_are_rejected_and_append_nothing() {
    let dir = tempfile::tempdir().unwrap();
    let server = TestServer::spawn(dir.path());
    let client = reqwest::blocking::Client::new();
    let draft: Value = client
        .post(format!("{}/api/characters", server.url))
        .json(&json!({"name": "Authority"}))
        .send()
        .unwrap()
        .json()
        .unwrap();
    let id = draft["id"].as_str().unwrap();
    let mut version = draft["version"].as_u64().unwrap();

    // 1. Locked slot: a heritage before any ancestry exists.
    let outcome = confirm_raw(
        &client,
        &server.url,
        id,
        json!({"version": version, "decision": {
            "id": "x1", "slot": "pf2e.ancestry.heritage",
            "selection": {"kind": "option", "value": "heritage.dwarf.rock"},
            "source": "player"
        }}),
    );
    assert_eq!(outcome["outcome"], "rejected");
    assert_eq!(
        outcome["draft"]["version"].as_u64().unwrap(),
        version,
        "a rejection must not change the draft"
    );

    // Choose an ancestry legitimately.
    let outcome = confirm_raw(
        &client,
        &server.url,
        id,
        json!({"version": version, "decision": {
            "id": "x2", "slot": "pf2e.ancestry",
            "selection": {"kind": "option", "value": "ancestry.elf"},
            "source": "player"
        }}),
    );
    assert_eq!(outcome["outcome"], "confirmed");
    version = outcome["draft"]["version"].as_u64().unwrap();

    // 2. Cross-catalog: a dwarf heritage on an elf.
    let outcome = confirm_raw(
        &client,
        &server.url,
        id,
        json!({"version": version, "decision": {
            "id": "x3", "slot": "pf2e.ancestry.heritage",
            "selection": {"kind": "option", "value": "heritage.dwarf.rock"},
            "source": "player"
        }}),
    );
    assert_eq!(outcome["outcome"], "rejected");
    let reasons = outcome["reasons"].as_array().unwrap();
    assert!(!reasons.is_empty());
    assert!(reasons[0]["message"]
        .as_str()
        .unwrap()
        .contains("does not belong"));

    // 3. Unknown option ID.
    let outcome = confirm_raw(
        &client,
        &server.url,
        id,
        json!({"version": version, "decision": {
            "id": "x4", "slot": "pf2e.ancestry.heritage",
            "selection": {"kind": "option", "value": "heritage.totally-fake"},
            "source": "player"
        }}),
    );
    assert_eq!(outcome["outcome"], "rejected");

    // 4. An unavailable option: Adapted Cantrip needs a spellcasting class
    // feature no Fighter has — the server refuses it even though a raw
    // client can name it.
    let outcome = confirm_raw(
        &client,
        &server.url,
        id,
        json!({"version": version, "decision": {
            "id": "x5", "slot": "pf2e.ancestry.feat",
            "selection": {"kind": "option", "value": "feat.ancestry.human.adapted-cantrip"},
            "source": "player"
        }}),
    );
    assert_eq!(outcome["outcome"], "rejected");

    // The draft is exactly one decision (plus the name) further along.
    let character: Value = client
        .get(format!("{}/api/characters/{id}", server.url))
        .send()
        .unwrap()
        .json()
        .unwrap();
    assert_eq!(character["version"].as_u64().unwrap(), version);
}

/// Quick-build server authority: raw requests the planner cannot honor are
/// rejected and append nothing, and both quick-build routes are wizard
/// writes under the version guard.
#[test]
fn raw_quick_build_requests_are_validated_and_append_nothing() {
    let dir = tempfile::tempdir().unwrap();
    let server = TestServer::spawn(dir.path());
    let client = reqwest::blocking::Client::new();

    // 1. A malformed request ID (path-traversal shaped) is refused outright
    // and creates no file.
    let response = client
        .post(format!("{}/api/characters/quick-build", server.url))
        .json(&json!({ "request_id": "../evil", "name": null }))
        .send()
        .unwrap();
    assert_eq!(response.status().as_u16(), 422);
    let response = client
        .post(format!("{}/api/characters/quick-build", server.url))
        .json(&json!({ "request_id": "", "name": null }))
        .send()
        .unwrap();
    assert_eq!(response.status().as_u16(), 422);
    let roster: Value = client
        .get(format!("{}/api/roster", server.url))
        .send()
        .unwrap()
        .json()
        .unwrap();
    assert!(
        roster["entries"].as_array().unwrap().is_empty(),
        "a rejected quick-build must append nothing"
    );

    // 2. A legitimate quick build lands review-ready, NOT finalized; the
    // server computed the expansion natively (nothing illegal persisted).
    let built: Value = client
        .post(format!("{}/api/characters/quick-build", server.url))
        .json(&json!({ "request_id": "auth-qb-1", "name": null }))
        .send()
        .unwrap()
        .json()
        .unwrap();
    let id = built["draft"]["id"].as_str().unwrap().to_string();
    let version = built["draft"]["version"].as_u64().unwrap();
    assert!(built["draft"]["projection"]["can_finalize"]
        .as_bool()
        .unwrap());
    let view: Value = client
        .get(format!("{}/api/characters/{id}", server.url))
        .send()
        .unwrap()
        .json()
        .unwrap();
    assert_eq!(
        view["state"], "draft",
        "quick build never finalizes on its own"
    );

    // 3. A malformed fill request is refused; fill on a finalized character
    // is refused; neither writes a byte.
    let response = client
        .post(format!("{}/api/characters/{id}/fill-remaining", server.url))
        .json(&json!({ "request_id": "bad id!", "version": version }))
        .send()
        .unwrap();
    assert_eq!(response.status().as_u16(), 422);
    let finalized: Value = client
        .post(format!("{}/api/characters/{id}/finalize", server.url))
        .json(&json!({ "version": version }))
        .send()
        .unwrap()
        .json()
        .unwrap();
    assert_eq!(finalized["outcome"], "finalized", "{finalized}");
    let before = std::fs::read(dir.path().join(format!("characters/{id}.json"))).unwrap();
    let response = client
        .post(format!("{}/api/characters/{id}/fill-remaining", server.url))
        .json(&json!({ "request_id": "auth-fill-1", "version": version + 1 }))
        .send()
        .unwrap();
    assert_eq!(response.status().as_u16(), 422);
    let after = std::fs::read(dir.path().join(format!("characters/{id}.json"))).unwrap();
    assert_eq!(before, after, "a refused fill must append nothing");
}

/// Quick-build routes are wizard writes for the version guard: a draft on
/// an older known rules-data version rejects fill-remaining with the flag
/// (409) and writes nothing — the --extra-known-versions fixture pattern
/// from checks/version_guard.rs.
#[test]
fn fill_remaining_is_rejected_on_a_version_flagged_draft() {
    const TEST_VERSION: &str = "pf2e-pc.0.0.1-test";
    let dir = tempfile::tempdir().unwrap();
    let client = reqwest::blocking::Client::new();

    // Build a draft against current data, then pin its file to a fabricated
    // prior version.
    let id;
    {
        let server = TestServer::spawn(dir.path());
        let draft: Value = client
            .post(format!("{}/api/characters", server.url))
            .json(&json!({ "name": "Flagged" }))
            .send()
            .unwrap()
            .json()
            .unwrap();
        id = draft["id"].as_str().unwrap().to_string();
    }
    let path = dir.path().join(format!("characters/{id}.json"));
    let mut doc: Value = serde_json::from_str(&std::fs::read_to_string(&path).unwrap()).unwrap();
    doc["rules_version"] = Value::from(TEST_VERSION);
    std::fs::write(&path, serde_json::to_string_pretty(&doc).unwrap()).unwrap();
    let extra = dir.path().join("extra-known-versions.json");
    std::fs::write(
        &extra,
        json!({ "versions": { TEST_VERSION: [] } }).to_string(),
    )
    .unwrap();

    let server = TestServer::spawn_with_args(
        dir.path(),
        &["--extra-known-versions", extra.to_str().unwrap()],
    );
    let before = std::fs::read(&path).unwrap();
    let response = client
        .post(format!("{}/api/characters/{id}/fill-remaining", server.url))
        .json(&json!({ "request_id": "flagged-fill-1", "version": 1 }))
        .send()
        .unwrap();
    assert_eq!(
        response.status().as_u16(),
        409,
        "fill-remaining is a wizard write under the version guard"
    );
    let body: Value = response.json().unwrap();
    assert_eq!(body["status"]["status"], "older_known");
    assert_eq!(
        before,
        std::fs::read(&path).unwrap(),
        "a rejected wizard write must append nothing"
    );
}

#[test]
fn finalize_is_blocked_while_the_checklist_is_nonempty() {
    let dir = tempfile::tempdir().unwrap();
    let server = TestServer::spawn(dir.path());
    let client = reqwest::blocking::Client::new();
    let draft: Value = client
        .post(format!("{}/api/characters", server.url))
        .json(&json!({"name": "Blocked"}))
        .send()
        .unwrap()
        .json()
        .unwrap();
    let id = draft["id"].as_str().unwrap();
    let version = draft["version"].as_u64().unwrap();

    let outcome: Value = client
        .post(format!("{}/api/characters/{id}/finalize", server.url))
        .json(&json!({"version": version}))
        .send()
        .unwrap()
        .json()
        .unwrap();
    assert_eq!(outcome["outcome"], "blocked");
    let reasons = outcome["reasons"].as_array().unwrap();
    assert!(
        reasons.len() >= 4,
        "every gap is listed (ancestry, background, class, boosts…): {reasons:?}"
    );
    // Still a draft afterwards.
    let character: Value = client
        .get(format!("{}/api/characters/{id}", server.url))
        .send()
        .unwrap()
        .json()
        .unwrap();
    assert_eq!(character["state"], "draft");
}

// ---- chargen-wizard: server authority over the prep route ----

#[path = "wizard_fixture.rs"]
mod wizard_fixture;

/// Raw prep requests bypassing the UI are re-validated natively and
/// rejected — not-in-book, overfilled rank, non-curriculum in the school
/// slot, and prep on a class with no prep slots — and each rejection
/// changes nothing on disk.
#[test]
fn raw_illegal_prep_is_rejected_and_writes_nothing() {
    let dir = tempfile::tempdir().unwrap();
    let client = wizard_fixture::client();
    let server = TestServer::spawn(dir.path());
    let built = wizard_fixture::build_sylvenne_finalized(&client, &server.url);
    let path = dir.path().join(format!("characters/{}.json", built.id));
    let bytes_before = std::fs::read(&path).unwrap();

    let cases: Vec<(&str, Value)> = vec![
        (
            "not in the spellbook",
            json!([{"slot": "pf2e.prep.rank1",
                    "selection": {"kind": "options", "value": ["spell.grim-tendrils", "spell.fear"]}}]),
        ),
        (
            "overfilled rank",
            json!([{"slot": "pf2e.prep.rank1",
                    "selection": {"kind": "options", "value": ["spell.fear", "spell.command", "spell.sleep"]}}]),
        ),
        (
            "non-curriculum in the school slot",
            json!([{"slot": "pf2e.prep.school-rank1",
                    "selection": {"kind": "option", "value": "spell.sleep"}}]),
        ),
        (
            "unknown scoped slot",
            json!([{"slot": "pf2e.prep.rank9",
                    "selection": {"kind": "option", "value": "spell.fear"}}]),
        ),
    ];
    for (i, (label, choices)) in cases.iter().enumerate() {
        let outcome = wizard_fixture::prep_save(
            &client,
            &server.url,
            &built.id,
            built.version,
            &format!("raw-{i}"),
            "finalized",
            choices,
        );
        assert_eq!(outcome["outcome"], "rejected", "{label}: {outcome:#?}");
        assert!(
            !outcome["reasons"].as_array().unwrap().is_empty(),
            "{label}: rejection names its rules"
        );
        assert_eq!(
            std::fs::read(&path).unwrap(),
            bytes_before,
            "{label}: a rejection writes nothing"
        );
    }

    // Prep on a class with no prep slots (a Fighter): rejected too.
    let qb: Value = client
        .post(format!("{}/api/characters/quick-build", server.url))
        .json(&json!({"request_id": "authority-fighter", "name": "Garrek"}))
        .send()
        .unwrap()
        .json()
        .unwrap();
    let fid = qb["draft"]["id"].as_str().unwrap();
    let fversion = qb["draft"]["version"].as_u64().unwrap();
    let outcome = wizard_fixture::prep_save(
        &client,
        &server.url,
        fid,
        fversion,
        "raw-fighter",
        "draft",
        &json!([{"slot": "pf2e.prep.cantrips",
                 "selection": {"kind": "options", "value": ["spell.light"]}}]),
    );
    assert_eq!(
        outcome["outcome"], "rejected",
        "a Fighter has no preparation: {outcome:#?}"
    );
}
