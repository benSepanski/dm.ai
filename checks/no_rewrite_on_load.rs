//! Load is read-only: the bytes in the characters directory are
//! hash-identical before and after a fresh server loads the roster and
//! opens a character. The app never rewrites or normalizes a file on load.

use checks::TestServer;
use serde_json::{json, Value};

fn dir_bytes(dir: &std::path::Path) -> Vec<(String, Vec<u8>)> {
    let mut files: Vec<(String, Vec<u8>)> = std::fs::read_dir(dir)
        .unwrap()
        .flatten()
        .map(|e| {
            (
                e.file_name().to_string_lossy().to_string(),
                std::fs::read(e.path()).unwrap(),
            )
        })
        .collect();
    files.sort();
    files
}

#[test]
fn roster_and_character_load_leave_bytes_untouched() {
    let dir = tempfile::tempdir().unwrap();
    let client = reqwest::blocking::Client::new();
    let id;
    {
        let server = TestServer::spawn(dir.path());
        let draft: Value = client
            .post(format!("{}/api/characters", server.url))
            .json(&json!({"name": "Untouched"}))
            .send()
            .unwrap()
            .json()
            .unwrap();
        id = draft["id"].as_str().unwrap().to_string();
        client
            .post(format!("{}/api/characters/{id}/confirm", server.url))
            .json(&json!({"version": 1, "decision": {
                "id": "n1", "slot": "pf2e.ancestry",
                "selection": {"kind": "option", "value": "ancestry.goblin"},
                "source": "player"
            }}))
            .send()
            .unwrap();
        // Hand-edit the file so normalization would be detectable (unusual
        // key order and whitespace survive because load never rewrites).
        let path = dir.path().join(format!("characters/{id}.json"));
        let text = std::fs::read_to_string(&path).unwrap();
        std::fs::write(&path, format!("{text}\n\n")).unwrap();
    }

    let characters_dir = dir.path().join("characters");
    let before = dir_bytes(&characters_dir);

    let server = TestServer::spawn(dir.path());
    let roster = client
        .get(format!("{}/api/roster", server.url))
        .send()
        .unwrap()
        .status();
    assert!(roster.is_success());
    let character = client
        .get(format!("{}/api/characters/{id}", server.url))
        .send()
        .unwrap()
        .status();
    assert!(character.is_success());

    let after = dir_bytes(&characters_dir);
    assert_eq!(before, after, "loading must not rewrite a single byte");
}

/// The version guard computes its flags at load — replay included — and
/// still writes nothing: a character pinned to an older known version with
/// a divergent replay is byte-identical after roster and character loads.
#[test]
fn flagged_characters_load_without_a_byte_written() {
    let dir = tempfile::tempdir().unwrap();
    let client = reqwest::blocking::Client::new();
    let id;
    {
        let server = TestServer::spawn(dir.path());
        let draft: Value = client
            .post(format!("{}/api/characters", server.url))
            .json(&json!({"name": "Flagged"}))
            .send()
            .unwrap()
            .json()
            .unwrap();
        id = draft["id"].as_str().unwrap().to_string();
        client
            .post(format!("{}/api/characters/{id}/confirm", server.url))
            .json(&json!({"version": 1, "decision": {
                "id": "f1", "slot": "pf2e.ancestry",
                "selection": {"kind": "option", "value": "ancestry.goblin"},
                "source": "player"
            }}))
            .send()
            .unwrap();
        // Pin to a fabricated prior version and diverge the stored sheet.
        let path = dir.path().join(format!("characters/{id}.json"));
        let mut doc: Value =
            serde_json::from_str(&std::fs::read_to_string(&path).unwrap()).unwrap();
        doc["rules_version"] = Value::from("pf2e-pc.0.0.1-test");
        doc["state"] = Value::from("finalized");
        doc["sheet"]["sections"][0]["entries"][0]["value"] = Value::from("999 (old)");
        std::fs::write(&path, serde_json::to_string_pretty(&doc).unwrap()).unwrap();
    }
    let extra = dir.path().join("extra-known-versions.json");
    std::fs::write(
        &extra,
        json!({"pf2e": {"versions": {"pf2e-pc.0.0.1-test": []}}}).to_string(),
    )
    .unwrap();

    let characters_dir = dir.path().join("characters");
    let before = dir_bytes(&characters_dir);

    let server = TestServer::spawn_with_args(
        dir.path(),
        &["--extra-known-versions", extra.to_str().unwrap()],
    );
    let roster: Value = client
        .get(format!("{}/api/roster", server.url))
        .send()
        .unwrap()
        .json()
        .unwrap();
    assert_eq!(
        roster["entries"][0]["version"]["status"], "older_known",
        "the fixture must actually be flagged"
    );
    let character = client
        .get(format!("{}/api/characters/{id}", server.url))
        .send()
        .unwrap()
        .status();
    assert!(character.is_success());

    let after = dir_bytes(&characters_dir);
    assert_eq!(
        before, after,
        "computing version flags (replay included) must not rewrite a byte"
    );
}
