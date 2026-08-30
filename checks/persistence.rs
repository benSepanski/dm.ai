//! Persistence contract: versioned round-trip, unknown/newer schema
//! rejection, quarantine of corrupt files while the roster loads, and
//! deletes landing in trash/ (never unlinked).

use checks::TestServer;
use serde_json::{json, Value};

fn client() -> reqwest::blocking::Client {
    reqwest::blocking::Client::new()
}

fn create_character(client: &reqwest::blocking::Client, url: &str, name: &str) -> Value {
    client
        .post(format!("{url}/api/characters"))
        .json(&json!({ "name": name }))
        .send()
        .unwrap()
        .json()
        .unwrap()
}

fn confirm(
    client: &reqwest::blocking::Client,
    url: &str,
    id: &str,
    version: u64,
    decision_id: &str,
    slot: &str,
    selection: Value,
) -> Value {
    client
        .post(format!("{url}/api/characters/{id}/confirm"))
        .json(&json!({
            "version": version,
            "decision": {
                "id": decision_id,
                "slot": slot,
                "selection": selection,
                "source": "player"
            }
        }))
        .send()
        .unwrap()
        .json()
        .unwrap()
}

#[test]
fn documents_round_trip_a_versioned_schema() {
    let dir = tempfile::tempdir().unwrap();
    let client = client();
    let id;
    {
        let server = TestServer::spawn(dir.path());
        let draft = create_character(&client, &server.url, "RoundTrip");
        id = draft["id"].as_str().unwrap().to_string();
        let outcome = confirm(
            &client,
            &server.url,
            &id,
            1,
            "d1",
            "pf2e.ancestry",
            json!({"kind": "option", "value": "ancestry.dwarf"}),
        );
        assert_eq!(outcome["outcome"], "confirmed");
    }

    // The document on disk carries the schema version and parses.
    let path = dir.path().join(format!("characters/{id}.json"));
    let doc: Value = serde_json::from_str(&std::fs::read_to_string(&path).unwrap()).unwrap();
    assert_eq!(doc["schema_version"], 3);
    assert_eq!(doc["rules_version"], "pf2e-pc.0.3.1");
    assert_eq!(doc["log"].as_array().unwrap().len(), 2); // name + ancestry

    // A fresh server round-trips it.
    let server = TestServer::spawn(dir.path());
    let character: Value = client
        .get(format!("{}/api/characters/{id}", server.url))
        .send()
        .unwrap()
        .json()
        .unwrap();
    assert_eq!(character["state"], "draft");
}

/// Storage schema discipline (architecture: chargen-content, extended by
/// roster-ergonomics): an old-schema file reads, is never rewritten by
/// loading, and upgrades to the current schema on its first ordinary
/// write. Exercised for v1 (the oldest readable schema).
#[test]
fn v1_documents_read_untouched_and_upgrade_on_first_write() {
    let dir = tempfile::tempdir().unwrap();
    let client = client();
    let id;
    {
        let server = TestServer::spawn(dir.path());
        let draft = create_character(&client, &server.url, "Elder");
        id = draft["id"].as_str().unwrap().to_string();
    }

    // Rewind the on-disk document to schema v1 (v2 is structurally v1 plus
    // the `suggested` source value, which this file doesn't use).
    let path = dir.path().join(format!("characters/{id}.json"));
    let mut doc: Value = serde_json::from_str(&std::fs::read_to_string(&path).unwrap()).unwrap();
    doc["schema_version"] = Value::from(1);
    std::fs::write(&path, serde_json::to_string_pretty(&doc).unwrap()).unwrap();
    let v1_bytes = std::fs::read(&path).unwrap();

    // Loading the roster and the character rewrites nothing.
    {
        let server = TestServer::spawn(dir.path());
        let character: Value = client
            .get(format!("{}/api/characters/{id}", server.url))
            .send()
            .unwrap()
            .json()
            .unwrap();
        assert_eq!(character["state"], "draft", "v1 file must load");
        assert_eq!(
            std::fs::read(&path).unwrap(),
            v1_bytes,
            "loading a v1 file must not rewrite it"
        );

        // First ordinary write upgrades the stored document to v2.
        let outcome = confirm(
            &client,
            &server.url,
            &id,
            1,
            "d-upgrade",
            "pf2e.ancestry",
            json!({"kind": "option", "value": "ancestry.dwarf"}),
        );
        assert_eq!(outcome["outcome"], "confirmed");
    }
    let upgraded: Value = serde_json::from_str(&std::fs::read_to_string(&path).unwrap()).unwrap();
    assert_eq!(
        upgraded["schema_version"], 3,
        "first write after load upgrades v1 to the current schema"
    );
}

#[test]
fn newer_schema_versions_are_refused() {
    let dir = tempfile::tempdir().unwrap();
    std::fs::create_dir_all(dir.path().join("characters")).unwrap();
    std::fs::write(
        dir.path().join("characters/future.json"),
        json!({ "schema_version": 99, "id": "future" }).to_string(),
    )
    .unwrap();
    let (code, stderr) = TestServer::spawn_expect_failure(dir.path());
    assert_eq!(code, 2, "server must refuse to open: {stderr}");
    assert!(
        stderr.contains("newer"),
        "refusal must explain the downgrade guard: {stderr}"
    );
}

#[test]
fn corrupt_files_quarantine_while_the_roster_loads() {
    let dir = tempfile::tempdir().unwrap();
    let client = client();
    {
        let server = TestServer::spawn(dir.path());
        create_character(&client, &server.url, "Survivor");
    }
    std::fs::write(dir.path().join("characters/broken.json"), "{ not json").unwrap();

    let server = TestServer::spawn(dir.path());
    let roster: Value = client
        .get(format!("{}/api/roster", server.url))
        .send()
        .unwrap()
        .json()
        .unwrap();
    assert_eq!(
        roster["entries"].as_array().unwrap().len(),
        1,
        "the healthy character loads"
    );
    let problems = roster["problems"].as_array().unwrap();
    assert_eq!(problems.len(), 1);
    assert_eq!(problems[0]["file"], "broken.json");
    assert!(problems[0]["message"]
        .as_str()
        .unwrap()
        .contains("quarantined"));
    // The file was renamed aside, not deleted.
    assert!(!dir.path().join("characters/broken.json").exists());
    let quarantined: Vec<_> = std::fs::read_dir(dir.path().join("quarantine"))
        .unwrap()
        .flatten()
        .collect();
    assert_eq!(quarantined.len(), 1);
}

#[test]
fn deletes_land_in_trash_with_timestamped_names() {
    let dir = tempfile::tempdir().unwrap();
    let client = client();
    let server = TestServer::spawn(dir.path());
    let draft = create_character(&client, &server.url, "Doomed");
    let id = draft["id"].as_str().unwrap();

    let status = client
        .delete(format!("{}/api/characters/{id}", server.url))
        .send()
        .unwrap()
        .status();
    assert_eq!(status.as_u16(), 204);

    assert!(!dir.path().join(format!("characters/{id}.json")).exists());
    let trash: Vec<String> = std::fs::read_dir(dir.path().join("trash"))
        .unwrap()
        .flatten()
        .map(|e| e.file_name().to_string_lossy().to_string())
        .collect();
    assert_eq!(trash.len(), 1);
    assert!(
        trash[0].starts_with(&format!("{id}-")),
        "trash name '{}' must be the character plus a timestamp",
        trash[0]
    );

    // Gone from the roster; recoverable by hand.
    let roster: Value = client
        .get(format!("{}/api/roster", server.url))
        .send()
        .unwrap()
        .json()
        .unwrap();
    assert!(roster["entries"].as_array().unwrap().is_empty());
}

#[test]
fn second_instance_on_the_same_data_dir_refuses() {
    let dir = tempfile::tempdir().unwrap();
    let _server = TestServer::spawn(dir.path());
    let (code, stderr) = TestServer::spawn_expect_failure(dir.path());
    assert_eq!(code, 3, "second instance must refuse: {stderr}");
    assert!(
        stderr.contains("already being served"),
        "refusal names the live instance: {stderr}"
    );
}

/// The second-instance guard's stale-lock recovery: a lockfile whose pid is
/// dead (here: a pid far above any OS pid range) must be reclaimed, not
/// refused. Kept as an explicit test because the test harnesses now clean
/// their own stale locks on kill, so restarts no longer exercise this path.
#[test]
fn stale_lock_with_dead_pid_is_reclaimed() {
    let dir = tempfile::tempdir().unwrap();
    std::fs::write(
        dir.path().join("server.lock"),
        "2000000000\nhttp://127.0.0.1:1\n",
    )
    .unwrap();
    let server = TestServer::spawn(dir.path());
    let roster: Value = client()
        .get(format!("{}/api/roster", server.url))
        .send()
        .unwrap()
        .json()
        .unwrap();
    assert!(roster["entries"].as_array().unwrap().is_empty());
}
