//! The rules-data version guard (spec req 6): older-known pins are
//! detected at load and replayed against current data; every state change
//! is an explicit route; loading and refusals never write a byte.
//!
//! Fixtures fabricate a prior shipped version ("pf2e-pc.0.0.1-test") by
//! pinning files to it on disk and passing the server's hidden test-support
//! flag `--extra-known-versions` so the binary treats it as older-known.
//! Production never passes the flag; nothing here touches shipped data.

use checks::TestServer;
use serde_json::{json, Value};

const TEST_VERSION: &str = "pf2e-pc.0.0.1-test";
const UNRECOGNIZED_VERSION: &str = "pf2e-pc.9.9.9-unrecognized";

/// Write the extra-known-versions file and return the CLI args to use it.
fn extra_versions_file(dir: &std::path::Path) -> std::path::PathBuf {
    let path = dir.join("extra-known-versions.json");
    std::fs::write(
        &path,
        json!({ "versions": { TEST_VERSION: [] } }).to_string(),
    )
    .unwrap();
    path
}

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

/// Create a draft with a name and one ancestry decision against current
/// data; returns (character id, current rules version). The server is
/// killed before returning so the file can be doctored.
fn build_fixture(dir: &std::path::Path, name: &str) -> (String, String) {
    let client = reqwest::blocking::Client::new();
    let server = TestServer::spawn(dir);
    let draft: Value = client
        .post(format!("{}/api/characters", server.url))
        .json(&json!({ "name": name }))
        .send()
        .unwrap()
        .json()
        .unwrap();
    let id = draft["id"].as_str().unwrap().to_string();
    let current = draft["rules_version"].as_str().unwrap().to_string();
    let outcome: Value = client
        .post(format!("{}/api/characters/{id}/confirm", server.url))
        .json(&json!({ "version": 1, "decision": {
            "id": format!("{id}-fixture-ancestry"), "slot": "pf2e.ancestry",
            "selection": { "kind": "option", "value": "ancestry.goblin" },
            "source": "player"
        }}))
        .send()
        .unwrap()
        .json()
        .unwrap();
    assert_eq!(
        outcome["outcome"], "confirmed",
        "fixture confirm: {outcome}"
    );
    (id, current)
}

fn character_path(dir: &std::path::Path, id: &str) -> std::path::PathBuf {
    dir.join(format!("characters/{id}.json"))
}

fn edit_doc(dir: &std::path::Path, id: &str, edit: impl FnOnce(&mut Value)) {
    let path = character_path(dir, id);
    let mut doc: Value = serde_json::from_str(&std::fs::read_to_string(&path).unwrap()).unwrap();
    edit(&mut doc);
    std::fs::write(&path, serde_json::to_string_pretty(&doc).unwrap()).unwrap();
}

fn read_doc(dir: &std::path::Path, id: &str) -> Value {
    serde_json::from_str(&std::fs::read_to_string(character_path(dir, id)).unwrap()).unwrap()
}

/// Pin the file to the fabricated prior version (and optionally finalize).
fn pin_to_test_version(dir: &std::path::Path, id: &str, finalize: bool) {
    edit_doc(dir, id, |doc| {
        doc["rules_version"] = Value::from(TEST_VERSION);
        if finalize {
            doc["state"] = Value::from("finalized");
        }
    });
}

fn post(client: &reqwest::blocking::Client, url: &str, body: Value) -> Value {
    client.post(url).json(&body).send().unwrap().json().unwrap()
}

#[test]
fn older_known_identical_flags_and_repins_only_via_explicit_action() {
    let dir = tempfile::tempdir().unwrap();
    let (id, current) = build_fixture(dir.path(), "Ident");
    pin_to_test_version(dir.path(), &id, true);
    let extra = extra_versions_file(dir.path());
    let client = reqwest::blocking::Client::new();
    let server = TestServer::spawn_with_args(
        dir.path(),
        &["--extra-known-versions", extra.to_str().unwrap()],
    );

    // Load computes the status; nothing is written.
    let before = dir_bytes(&dir.path().join("characters"));
    let roster: Value = client
        .get(format!("{}/api/roster", server.url))
        .send()
        .unwrap()
        .json()
        .unwrap();
    let entry = &roster["entries"][0];
    assert_eq!(entry["version"]["status"], "older_known");
    assert_eq!(entry["version"]["pinned"], TEST_VERSION);
    assert_eq!(entry["version"]["outcome"]["kind"], "identical");
    let view: Value = client
        .get(format!("{}/api/characters/{id}", server.url))
        .send()
        .unwrap()
        .json()
        .unwrap();
    assert_eq!(view["state"], "finalized");
    assert_eq!(view["version_status"]["outcome"]["kind"], "identical");
    assert_eq!(
        before,
        dir_bytes(&dir.path().join("characters")),
        "computing the version status must write nothing"
    );

    // Accept is the wrong action for an identical replay — typed refusal,
    // still nothing written.
    let refusal = post(
        &client,
        &format!("{}/api/characters/{id}/version/accept", server.url),
        json!({ "version": view["version"] }),
    );
    assert_eq!(refusal["outcome"], "refused");
    assert_eq!(
        before,
        dir_bytes(&dir.path().join("characters")),
        "a refused action must write nothing"
    );

    // The explicit re-pin writes once and records itself in the file.
    let resolved = post(
        &client,
        &format!("{}/api/characters/{id}/version/repin", server.url),
        json!({ "version": view["version"] }),
    );
    assert_eq!(resolved["outcome"], "resolved", "{resolved}");
    assert_eq!(resolved["character"]["version_status"]["status"], "current");
    let doc = read_doc(dir.path(), &id);
    assert_eq!(doc["rules_version"], current);
    let event = &doc["version_history"][0];
    assert_eq!(event["action"], "re_pin");
    assert_eq!(event["from"], TEST_VERSION);
    assert_eq!(event["to"], current);
    assert_eq!(event["note"], "identical replay");
}

#[test]
fn divergent_flags_with_values_and_accept_records_prior_values() {
    let dir = tempfile::tempdir().unwrap();
    let (id, current) = build_fixture(dir.path(), "Diver");
    // Divergence fixture: the stored sheet holds a value current data does
    // not derive (as if the record changed under the old pin).
    let mut old_value = String::new();
    let mut section = String::new();
    let mut label = String::new();
    edit_doc(dir.path(), &id, |doc| {
        doc["rules_version"] = Value::from(TEST_VERSION);
        doc["state"] = Value::from("finalized");
        section = doc["sheet"]["sections"][0]["title"]
            .as_str()
            .unwrap()
            .to_string();
        let entry = &mut doc["sheet"]["sections"][0]["entries"][0];
        label = entry["label"].as_str().unwrap().to_string();
        old_value = "999 (old derivation)".to_string();
        entry["value"] = Value::from(old_value.clone());
    });
    let extra = extra_versions_file(dir.path());
    let client = reqwest::blocking::Client::new();
    let server = TestServer::spawn_with_args(
        dir.path(),
        &["--extra-known-versions", extra.to_str().unwrap()],
    );

    let before = dir_bytes(&dir.path().join("characters"));
    let view: Value = client
        .get(format!("{}/api/characters/{id}", server.url))
        .send()
        .unwrap()
        .json()
        .unwrap();
    let outcome = &view["version_status"]["outcome"];
    assert_eq!(outcome["kind"], "divergent");
    let diffs = outcome["differences"].as_array().unwrap();
    let diff = diffs
        .iter()
        .find(|d| d["section"] == section.as_str() && d["label"] == label.as_str())
        .unwrap_or_else(|| panic!("flag must name the differing value: {diffs:?}"));
    assert_eq!(diff["old"], old_value);
    let new_value = diff["new"].as_str().unwrap().to_string();
    assert_ne!(new_value, old_value);
    assert_eq!(
        before,
        dir_bytes(&dir.path().join("characters")),
        "the stored sheet must stay untouched until an explicit accept"
    );

    // Re-pin is the wrong action for a divergent replay.
    let refusal = post(
        &client,
        &format!("{}/api/characters/{id}/version/repin", server.url),
        json!({ "version": view["version"] }),
    );
    assert_eq!(refusal["outcome"], "refused");

    // Accept: re-pins, stores the new sheet, records the prior values.
    let resolved = post(
        &client,
        &format!("{}/api/characters/{id}/version/accept", server.url),
        json!({ "version": view["version"] }),
    );
    assert_eq!(resolved["outcome"], "resolved", "{resolved}");
    assert_eq!(resolved["character"]["version_status"]["status"], "current");
    let doc = read_doc(dir.path(), &id);
    assert_eq!(doc["rules_version"], current);
    let event = &doc["version_history"][0];
    assert_eq!(event["action"], "accept");
    let recorded = event["superseded_values"]
        .as_array()
        .unwrap()
        .iter()
        .find(|d| d["label"] == label.as_str())
        .expect("accept must record the superseded value in the file");
    assert_eq!(recorded["old"], old_value);
    assert_eq!(recorded["new"], new_value);
    // The stored sheet now carries the accepted (replayed) value.
    let stored = doc["sheet"]["sections"][0]["entries"][0]["value"]
        .as_str()
        .unwrap();
    assert_eq!(stored, new_value);
}

#[test]
fn keep_old_is_recorded_and_suppresses_reflagging() {
    let dir = tempfile::tempdir().unwrap();
    let (id, current) = build_fixture(dir.path(), "Keeper");
    edit_doc(dir.path(), &id, |doc| {
        doc["rules_version"] = Value::from(TEST_VERSION);
        doc["state"] = Value::from("finalized");
        doc["sheet"]["sections"][0]["entries"][0]["value"] = Value::from("999 (old derivation)");
    });
    let extra = extra_versions_file(dir.path());
    let client = reqwest::blocking::Client::new();
    let server = TestServer::spawn_with_args(
        dir.path(),
        &["--extra-known-versions", extra.to_str().unwrap()],
    );

    let view: Value = client
        .get(format!("{}/api/characters/{id}", server.url))
        .send()
        .unwrap()
        .json()
        .unwrap();
    assert_eq!(view["version_status"]["status"], "older_known");
    let resolved = post(
        &client,
        &format!("{}/api/characters/{id}/version/keep-old", server.url),
        json!({ "version": view["version"] }),
    );
    assert_eq!(resolved["outcome"], "resolved", "{resolved}");
    let status = &resolved["character"]["version_status"];
    assert_eq!(status["status"], "kept_old");
    assert_eq!(status["pinned"], TEST_VERSION);
    assert_eq!(status["evaluated_against"], current);

    // Recorded in the file: the pin is unchanged, the decision is not.
    let doc = read_doc(dir.path(), &id);
    assert_eq!(doc["rules_version"], TEST_VERSION);
    assert_eq!(doc["keep_old"]["pinned"], TEST_VERSION);
    assert_eq!(doc["keep_old"]["evaluated_against"], current);
    assert_eq!(doc["version_history"][0]["action"], "keep_old");

    // A fresh load stays unflagged (suppressed until the version changes).
    drop(server);
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
    assert_eq!(roster["entries"][0]["version"]["status"], "kept_old");
}

#[test]
fn replay_error_flags_name_the_decision_and_accept_is_refused() {
    let dir = tempfile::tempdir().unwrap();
    let (id, _) = build_fixture(dir.path(), "Broken");
    edit_doc(dir.path(), &id, |doc| {
        doc["rules_version"] = Value::from(TEST_VERSION);
        doc["state"] = Value::from("finalized");
        // The ancestry decision names a record current data does not ship.
        let log = doc["log"].as_array_mut().unwrap();
        let ancestry = log
            .iter_mut()
            .find(|d| d["slot"] == "pf2e.ancestry")
            .expect("fixture has an ancestry decision");
        ancestry["selection"]["value"] = Value::from("ancestry.withdrawn-record");
    });
    let extra = extra_versions_file(dir.path());
    let client = reqwest::blocking::Client::new();
    let server = TestServer::spawn_with_args(
        dir.path(),
        &["--extra-known-versions", extra.to_str().unwrap()],
    );

    let before = dir_bytes(&dir.path().join("characters"));
    let view: Value = client
        .get(format!("{}/api/characters/{id}", server.url))
        .send()
        .unwrap()
        .json()
        .unwrap();
    let outcome = &view["version_status"]["outcome"];
    assert_eq!(outcome["kind"], "replay_error");
    assert_eq!(
        outcome["failing_decision"],
        format!("{id}-fixture-ancestry"),
        "the flag must name the failing decision"
    );
    assert_eq!(outcome["slot"], "pf2e.ancestry");

    // Accept is unavailable; the refusal names the failing decision.
    let refusal = post(
        &client,
        &format!("{}/api/characters/{id}/version/accept", server.url),
        json!({ "version": view["version"] }),
    );
    assert_eq!(refusal["outcome"], "refused");
    assert!(refusal["message"]
        .as_str()
        .unwrap()
        .contains(&format!("{id}-fixture-ancestry")));
    assert_eq!(
        before,
        dir_bytes(&dir.path().join("characters")),
        "flagging and refusing must write nothing"
    );

    // Keep-old remains available for the finalized character.
    let resolved = post(
        &client,
        &format!("{}/api/characters/{id}/version/keep-old", server.url),
        json!({ "version": view["version"] }),
    );
    assert_eq!(resolved["outcome"], "resolved", "{resolved}");
    assert_eq!(
        resolved["character"]["version_status"]["status"],
        "kept_old"
    );
}

#[test]
fn wizard_writes_on_a_flagged_draft_are_rejected_with_the_flag() {
    let dir = tempfile::tempdir().unwrap();
    let (id, _) = build_fixture(dir.path(), "Stalled");
    pin_to_test_version(dir.path(), &id, false);
    let extra = extra_versions_file(dir.path());
    let client = reqwest::blocking::Client::new();
    let server = TestServer::spawn_with_args(
        dir.path(),
        &["--extra-known-versions", extra.to_str().unwrap()],
    );

    // The draft opens blocked: no projection, stored sheet plus the flag.
    let view: Value = client
        .get(format!("{}/api/characters/{id}", server.url))
        .send()
        .unwrap()
        .json()
        .unwrap();
    assert_eq!(view["state"], "flagged_draft");
    assert_eq!(view["status"]["status"], "older_known");
    let version = view["version"].as_u64().unwrap();

    let before = dir_bytes(&dir.path().join("characters"));
    // Every wizard write is refused with the flag attached (409).
    let confirm = client
        .post(format!("{}/api/characters/{id}/confirm", server.url))
        .json(&json!({ "version": version, "decision": {
            "id": "vg-blocked", "slot": "pf2e.background",
            "selection": { "kind": "option", "value": "background.warrior" },
            "source": "player"
        }}))
        .send()
        .unwrap();
    assert_eq!(confirm.status().as_u16(), 409);
    let body: Value = confirm.json().unwrap();
    assert_eq!(body["status"]["status"], "older_known");
    let step = client
        .post(format!("{}/api/characters/{id}/step", server.url))
        .json(&json!({ "version": version, "step": "ancestry" }))
        .send()
        .unwrap();
    assert_eq!(step.status().as_u16(), 409);
    let finalize = client
        .post(format!("{}/api/characters/{id}/finalize", server.url))
        .json(&json!({ "version": version }))
        .send()
        .unwrap();
    assert_eq!(finalize.status().as_u16(), 409);
    assert_eq!(
        before,
        dir_bytes(&dir.path().join("characters")),
        "rejected wizard writes must append nothing"
    );

    // Resolution (identical replay: re-pin) unblocks the wizard.
    let resolved = post(
        &client,
        &format!("{}/api/characters/{id}/version/repin", server.url),
        json!({ "version": version }),
    );
    assert_eq!(resolved["outcome"], "resolved", "{resolved}");
    assert_eq!(resolved["character"]["state"], "draft");
    let new_version = resolved["character"]["version"].as_u64().unwrap();
    let confirm: Value = client
        .post(format!("{}/api/characters/{id}/confirm", server.url))
        .json(&json!({ "version": new_version, "decision": {
            "id": "vg-unblocked", "slot": "pf2e.background",
            "selection": { "kind": "option", "value": "background.warrior" },
            "source": "player"
        }}))
        .send()
        .unwrap()
        .json()
        .unwrap();
    assert_eq!(confirm["outcome"], "confirmed", "{confirm}");
}

#[test]
fn draft_replay_error_resolves_by_reopening_the_failing_cascade() {
    let dir = tempfile::tempdir().unwrap();
    let (id, current) = build_fixture(dir.path(), "Reopen");
    edit_doc(dir.path(), &id, |doc| {
        doc["rules_version"] = Value::from(TEST_VERSION);
        let log = doc["log"].as_array_mut().unwrap();
        let ancestry = log
            .iter_mut()
            .find(|d| d["slot"] == "pf2e.ancestry")
            .unwrap();
        ancestry["selection"]["value"] = Value::from("ancestry.withdrawn-record");
    });
    let extra = extra_versions_file(dir.path());
    let client = reqwest::blocking::Client::new();
    let server = TestServer::spawn_with_args(
        dir.path(),
        &["--extra-known-versions", extra.to_str().unwrap()],
    );

    // The flag lists exactly what resolving would reopen.
    let view: Value = client
        .get(format!("{}/api/characters/{id}", server.url))
        .send()
        .unwrap()
        .json()
        .unwrap();
    assert_eq!(view["state"], "flagged_draft");
    let outcome = &view["status"]["outcome"];
    assert_eq!(outcome["kind"], "replay_error");
    let would_reopen = outcome["would_reopen"].as_array().unwrap();
    assert!(
        would_reopen.iter().any(|c| c["slot"] == "pf2e.ancestry"),
        "the flag must list the reopened slots: {would_reopen:?}"
    );

    // Accept is refused; resolve-errors clears the cascade, re-pins, and
    // records the cleared decisions verbatim.
    let refusal = post(
        &client,
        &format!("{}/api/characters/{id}/version/accept", server.url),
        json!({ "version": view["version"] }),
    );
    assert_eq!(refusal["outcome"], "refused");
    let resolved = post(
        &client,
        &format!("{}/api/characters/{id}/version/resolve-errors", server.url),
        json!({ "version": view["version"] }),
    );
    assert_eq!(resolved["outcome"], "resolved", "{resolved}");
    let character = &resolved["character"];
    assert_eq!(character["state"], "draft");
    assert_eq!(character["version_status"]["status"], "current");
    // The name decision survived; the broken ancestry decision is gone and
    // its slot is open again on the checklist.
    let doc = read_doc(dir.path(), &id);
    assert_eq!(doc["rules_version"], current);
    assert!(doc["log"]
        .as_array()
        .unwrap()
        .iter()
        .all(|d| d["slot"] != "pf2e.ancestry"));
    let event = &doc["version_history"][0];
    assert_eq!(event["action"], "resolve_replay_error");
    assert!(event["cleared_decisions"]
        .as_array()
        .unwrap()
        .iter()
        .any(|d| d["slot"] == "pf2e.ancestry"
            && d["selection"]["value"] == "ancestry.withdrawn-record"));
}

#[test]
fn stale_resolution_requests_conflict() {
    let dir = tempfile::tempdir().unwrap();
    let (id, _) = build_fixture(dir.path(), "Stale");
    pin_to_test_version(dir.path(), &id, true);
    let extra = extra_versions_file(dir.path());
    let client = reqwest::blocking::Client::new();
    let server = TestServer::spawn_with_args(
        dir.path(),
        &["--extra-known-versions", extra.to_str().unwrap()],
    );
    let outcome = post(
        &client,
        &format!("{}/api/characters/{id}/version/repin", server.url),
        json!({ "version": 999 }),
    );
    assert_eq!(outcome["outcome"], "conflict");
}

#[test]
fn verify_distinguishes_older_known_from_unknown() {
    let dir = tempfile::tempdir().unwrap();
    let (ident_id, _) = build_fixture(dir.path(), "VerifyIdent");
    pin_to_test_version(dir.path(), &ident_id, true);
    let extra = extra_versions_file(dir.path());
    let args = ["--extra-known-versions", extra.to_str().unwrap()];

    // Older-known + identical alone must not fail verify.
    let (code, out) = TestServer::run_verify(dir.path(), &args);
    assert!(
        out.contains("OLD-IDENT") && out.contains(TEST_VERSION),
        "verify must name the older known pin: {out}"
    );
    assert_eq!(
        code, 0,
        "older-known + identical must not fail verify: {out}"
    );

    // An unknown pin is distinguished and fails.
    edit_doc(dir.path(), &ident_id, |doc| {
        doc["rules_version"] = Value::from(UNRECOGNIZED_VERSION);
    });
    let (code, out) = TestServer::run_verify(dir.path(), &args);
    assert_eq!(code, 1);
    assert!(
        out.contains("UNKNOWN") && out.contains("replay impossible"),
        "unknown version must say replay is impossible: {out}"
    );
    assert!(!out.contains("OLD-IDENT"), "{out}");

    // Older-known + divergent reports the values and fails.
    edit_doc(dir.path(), &ident_id, |doc| {
        doc["rules_version"] = Value::from(TEST_VERSION);
        doc["sheet"]["sections"][0]["entries"][0]["value"] = Value::from("999 (old derivation)");
    });
    let (code, out) = TestServer::run_verify(dir.path(), &args);
    assert_eq!(code, 1);
    assert!(
        out.contains("OLD-DIVER") && out.contains("999 (old derivation)"),
        "divergent replay must report per-value diffs: {out}"
    );

    // Older-known + replay-error names the failing decision and fails.
    edit_doc(dir.path(), &ident_id, |doc| {
        doc["sheet"]["sections"][0]["entries"][0]["value"] = Value::from("999 (old derivation)");
        let log = doc["log"].as_array_mut().unwrap();
        let ancestry = log
            .iter_mut()
            .find(|d| d["slot"] == "pf2e.ancestry")
            .unwrap();
        ancestry["selection"]["value"] = Value::from("ancestry.withdrawn-record");
    });
    let (code, out) = TestServer::run_verify(dir.path(), &args);
    assert_eq!(code, 1);
    assert!(
        out.contains("OLD-BROKE") && out.contains(&format!("{ident_id}-fixture-ancestry")),
        "replay error must name the failing decision: {out}"
    );
}
