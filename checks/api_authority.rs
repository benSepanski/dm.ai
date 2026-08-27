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
