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
    assert_eq!(doc["schema_version"], 5);
    assert_eq!(doc["rules_version"], "pf2e-pc.0.4.0");
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
        upgraded["schema_version"], 5,
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

// ---- level-up: the prefix invariant, prefix immutability, schema v4 ----

#[path = "leveling_helpers.rs"]
mod leveling;
use leveling::{
    character, complete_level, confirm_option, finalized_fighter, post_json, read_doc, slot_view,
    start_level,
};

fn prefix_bytes(doc: &Value) -> (String, String) {
    let marker = doc["finalized_through"].as_u64().unwrap() as usize;
    let prefix: Vec<Value> = doc["log"].as_array().unwrap()[..marker].to_vec();
    (
        serde_json::to_string(&prefix).unwrap(),
        serde_json::to_string(&doc["sheet"]).unwrap(),
    )
}

/// Prefix invariant + immutability: across start, every pending confirm,
/// load, and abandon, `log[..finalized_through]` and `sheet` bytes never
/// change; after abandon the file equals the pre-start file except the
/// monotonic version counter; only finalize-pending moves marker and
/// sheet, together. The old sheet stays authoritative on every view.
#[test]
fn pending_levels_never_touch_the_finalized_prefix_or_sheet() {
    let dir = tempfile::tempdir().unwrap();
    let client = client();
    let server = TestServer::spawn(dir.path());
    let url = server.url.as_str();
    let id = finalized_fighter(&client, url, "prefix-inv");
    let before = read_doc(dir.path(), &id);
    assert_eq!(before["schema_version"], 5);
    assert_eq!(
        before["finalized_through"].as_u64().unwrap() as usize,
        before["log"].as_array().unwrap().len()
    );
    let (prefix0, sheet0) = prefix_bytes(&before);

    let pending = start_level(&client, url, &id);
    let started = read_doc(dir.path(), &id);
    assert_eq!(
        prefix_bytes(&started),
        (prefix0.clone(), sheet0.clone()),
        "start moved the prefix or sheet"
    );
    assert_eq!(started["finalized_through"], before["finalized_through"]);
    assert_eq!(
        started["log"].as_array().unwrap().len(),
        before["log"].as_array().unwrap().len() + 1,
        "start appended exactly the advance"
    );

    // A confirm into the tail: the file's sheet bytes are identical.
    let feat = slot_view(&pending, "pf2e.level.2.class-feat").unwrap();
    let option = feat["options"]
        .as_array()
        .unwrap()
        .iter()
        .find(|o| o["available"] == true)
        .unwrap()["id"]
        .as_str()
        .unwrap()
        .to_string();
    let confirmed = confirm_option(
        &client,
        url,
        &id,
        pending["version"].as_u64().unwrap(),
        "inv-cf",
        "pf2e.level.2.class-feat",
        &option,
    );
    assert_eq!(confirmed["outcome"], "confirmed", "{confirmed}");
    let mid = read_doc(dir.path(), &id);
    assert_eq!(
        prefix_bytes(&mid),
        (prefix0.clone(), sheet0.clone()),
        "a tail confirm touched the prefix or sheet"
    );
    // Every view still carries the finalized sheet.
    let view = character(&client, url, &id);
    assert_eq!(view["state"], "leveling");
    assert_eq!(serde_json::to_string(&view["sheet"]).unwrap(), sheet0);
    assert!(view["sheet"]["summary"][0]
        .as_str()
        .unwrap()
        .contains("Fighter 1"));
    let roster = client
        .get(format!("{url}/api/roster"))
        .send()
        .unwrap()
        .json::<Value>()
        .unwrap();
    assert_eq!(roster["entries"][0]["state"]["state"], "leveling");
    assert!(roster["entries"][0]["summary"]
        .as_str()
        .unwrap()
        .contains("Fighter 1"));

    // Abandon: the file equals the pre-start file except the version.
    let (status, abandoned) = post_json(
        &client,
        url,
        &format!("/api/characters/{id}/level-up/abandon"),
        json!({"version": confirmed["draft"]["version"]}),
    );
    assert_eq!(status, 200, "{abandoned}");
    let mut after = read_doc(dir.path(), &id);
    let mut expected = before.clone();
    assert!(after["draft_version"].as_u64() > before["draft_version"].as_u64());
    after["draft_version"] = Value::Null;
    expected["draft_version"] = Value::Null;
    after["current_step"] = Value::Null;
    expected["current_step"] = Value::Null;
    assert_eq!(
        after, expected,
        "abandon restores the pre-start file (modulo version and cursor)"
    );

    // Finalize-pending moves marker and sheet together, once.
    let leveled = complete_level(&client, url, &id);
    let doc = read_doc(dir.path(), &id);
    assert_eq!(
        doc["finalized_through"].as_u64().unwrap() as usize,
        doc["log"].as_array().unwrap().len()
    );
    assert_ne!(
        serde_json::to_string(&doc["sheet"]).unwrap(),
        sheet0,
        "finalize re-derived the sheet"
    );
    assert_eq!(
        serde_json::to_string(&doc["sheet"]).unwrap(),
        serde_json::to_string(&leveled["sheet"]).unwrap()
    );
    let (prefix1, _) = prefix_bytes(&doc);
    assert!(
        prefix1.starts_with(&prefix0[..prefix0.len() - 1]),
        "the old prefix is a prefix of the new one"
    );
    // Clones are born verify-clean and the whole roster verifies.
    let (code, output) = TestServer::run_verify(dir.path(), &[]);
    assert_eq!(code, 0, "{output}");
}

/// `verify` names a tampered pending decision, a moved marker with a
/// stale sheet, and a malformed tail (no advance at its head / two
/// advances); each is a finding, never a quarantine — the finalized
/// prefix still loads.
#[test]
fn verify_reports_tampered_pending_levels_and_malformed_tails() {
    let dir = tempfile::tempdir().unwrap();
    let client = client();
    let id;
    {
        let server = TestServer::spawn(dir.path());
        id = finalized_fighter(&client, &server.url, "verify-tail");
        let pending = start_level(&client, &server.url, &id);
        let feat = slot_view(&pending, "pf2e.level.2.class-feat").unwrap();
        let option = feat["options"]
            .as_array()
            .unwrap()
            .iter()
            .find(|o| o["available"] == true)
            .unwrap()["id"]
            .as_str()
            .unwrap()
            .to_string();
        let c = confirm_option(
            &client,
            &server.url,
            &id,
            pending["version"].as_u64().unwrap(),
            "vt-cf",
            "pf2e.level.2.class-feat",
            &option,
        );
        assert_eq!(c["outcome"], "confirmed");
    }
    let path = dir.path().join(format!("characters/{id}.json"));
    let clean = std::fs::read_to_string(&path).unwrap();
    let (code, _) = TestServer::run_verify(dir.path(), &[]);
    assert_eq!(code, 0, "a healthy pending level verifies");

    // (a) A tampered pending decision: point the class feat at a wizard feat.
    let mut doc: Value = serde_json::from_str(&clean).unwrap();
    let last = doc["log"].as_array().unwrap().len() - 1;
    doc["log"][last]["selection"]["value"] = Value::from("feat.class.wizard.conceal-spell");
    std::fs::write(&path, serde_json::to_string_pretty(&doc).unwrap()).unwrap();
    let (code, out) = TestServer::run_verify(dir.path(), &[]);
    assert_ne!(code, 0, "{out}");
    assert!(out.contains("TAIL-BROKE"), "{out}");

    // (b) A moved marker with a stale sheet.
    let mut doc: Value = serde_json::from_str(&clean).unwrap();
    doc["finalized_through"] = Value::from(doc["log"].as_array().unwrap().len());
    std::fs::write(&path, serde_json::to_string_pretty(&doc).unwrap()).unwrap();
    let (code, out) = TestServer::run_verify(dir.path(), &[]);
    assert_ne!(code, 0, "{out}");
    assert!(out.contains("DIVERGED"), "{out}");

    // (c) A tail whose head is not an advance.
    let mut doc: Value = serde_json::from_str(&clean).unwrap();
    let marker = doc["finalized_through"].as_u64().unwrap() as usize;
    let log = doc["log"].as_array_mut().unwrap();
    log.remove(marker);
    std::fs::write(&path, serde_json::to_string_pretty(&doc).unwrap()).unwrap();
    let (code, out) = TestServer::run_verify(dir.path(), &[]);
    assert_ne!(code, 0, "{out}");
    assert!(out.contains("TAIL-BAD"), "{out}");
    // It still loads (the prefix is intact) — no quarantine.
    let server = TestServer::spawn(dir.path());
    let roster: Value = client
        .get(format!("{}/api/roster", server.url))
        .send()
        .unwrap()
        .json()
        .unwrap();
    assert!(
        roster["problems"].as_array().unwrap().is_empty(),
        "{roster}"
    );
    assert_eq!(roster["entries"].as_array().unwrap().len(), 1);
    // A marker past the log's end IS structural corruption: quarantined.
    drop(server);
    let mut doc: Value = serde_json::from_str(&clean).unwrap();
    doc["finalized_through"] = Value::from(999);
    std::fs::write(&path, serde_json::to_string_pretty(&doc).unwrap()).unwrap();
    let server = TestServer::spawn(dir.path());
    let roster: Value = client
        .get(format!("{}/api/roster", server.url))
        .send()
        .unwrap()
        .json()
        .unwrap();
    assert_eq!(roster["problems"].as_array().unwrap().len(), 1, "{roster}");
}

/// Schema v4: a v3 finalized file AND a v3 mid-wizard draft load untouched
/// (the marker fixed up to the log length / 0), resume at the same step,
/// and upgrade to v4 on first write; v5 is refused (existing row).
#[test]
fn v3_documents_read_untouched_with_the_marker_fixed_up() {
    let dir = tempfile::tempdir().unwrap();
    let client = client();
    let (draft_id, final_id);
    {
        let server = TestServer::spawn(dir.path());
        let draft = create_character(&client, &server.url, "ElderDraft");
        draft_id = draft["id"].as_str().unwrap().to_string();
        let outcome = confirm(
            &client,
            &server.url,
            &draft_id,
            1,
            "d-v3",
            "pf2e.ancestry",
            json!({"kind": "option", "value": "ancestry.dwarf"}),
        );
        assert_eq!(outcome["outcome"], "confirmed");
        final_id = finalized_fighter(&client, &server.url, "elder-final");
    }
    // Rewind both files to v3: drop the marker field.
    for id in [&draft_id, &final_id] {
        let path = dir.path().join(format!("characters/{id}.json"));
        let mut doc: Value =
            serde_json::from_str(&std::fs::read_to_string(&path).unwrap()).unwrap();
        doc["schema_version"] = Value::from(3);
        doc.as_object_mut().unwrap().remove("finalized_through");
        std::fs::write(&path, serde_json::to_string_pretty(&doc).unwrap()).unwrap();
    }
    let draft_bytes =
        std::fs::read(dir.path().join(format!("characters/{draft_id}.json"))).unwrap();
    let final_bytes =
        std::fs::read(dir.path().join(format!("characters/{final_id}.json"))).unwrap();
    let server = TestServer::spawn(dir.path());
    let url = server.url.as_str();
    let draft_view = character(&client, url, &draft_id);
    assert_eq!(
        draft_view["state"], "draft",
        "a v3 draft resumes as a draft"
    );
    let final_view = character(&client, url, &final_id);
    assert_eq!(final_view["state"], "finalized");
    assert_eq!(
        final_view["next_level"], 2,
        "a v3 finalized file is level 1 with a level-up available"
    );
    assert_eq!(
        std::fs::read(dir.path().join(format!("characters/{draft_id}.json"))).unwrap(),
        draft_bytes,
        "load rewrote the v3 draft"
    );
    assert_eq!(
        std::fs::read(dir.path().join(format!("characters/{final_id}.json"))).unwrap(),
        final_bytes,
        "load rewrote the v3 finalized file"
    );
    // First writes upgrade: a confirm on the draft, a level start on the finalized.
    let outcome = confirm(
        &client,
        url,
        &draft_id,
        draft_view["version"].as_u64().unwrap(),
        "d-up",
        "pf2e.ancestry.heritage",
        json!({"kind": "option", "value": "heritage.dwarf.rock"}),
    );
    assert_eq!(outcome["outcome"], "confirmed", "{outcome}");
    assert_eq!(read_doc(dir.path(), &draft_id)["schema_version"], 5);
    assert_eq!(read_doc(dir.path(), &draft_id)["finalized_through"], 0);
    start_level(&client, url, &final_id);
    let doc = read_doc(dir.path(), &final_id);
    assert_eq!(doc["schema_version"], 5);
    assert_eq!(
        doc["finalized_through"].as_u64().unwrap() as usize + 1,
        doc["log"].as_array().unwrap().len()
    );
}
