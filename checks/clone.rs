//! Clone rows of the roster-ergonomics architecture:
//! - fidelity: for draft and finalized sources, the clone differs from
//!   its source exactly in character ID, file identity, and the name
//!   decision (clone provenance, clone-time name) — everything else in
//!   the two documents is identical — and the clone replays verify-clean
//!   while the source file's bytes never change (creation-only writes);
//! - refusals: divergent, trashed, and quarantined sources refuse with
//!   nothing written;
//! - idempotency: a retried clone request returns the already-created
//!   character and ignores a changed name (first write wins).

use checks::TestServer;
use serde_json::{json, Value};

const NAME_SLOT: &str = "pf2e.details.name";

fn client() -> reqwest::blocking::Client {
    reqwest::blocking::Client::new()
}

fn clone_request(
    client: &reqwest::blocking::Client,
    url: &str,
    request_id: &str,
    source_id: &str,
    name: &str,
) -> (u16, Value) {
    let response = client
        .post(format!("{url}/api/characters/clone"))
        .json(&json!({"request_id": request_id, "source_id": source_id, "name": name}))
        .send()
        .unwrap();
    let status = response.status().as_u16();
    (status, response.json().unwrap_or(Value::Null))
}

/// Quick-build a complete draft and finalize it; returns its ID.
fn finalized_character(client: &reqwest::blocking::Client, url: &str, request_id: &str) -> String {
    let build: Value = client
        .post(format!("{url}/api/characters/quick-build"))
        .json(&json!({"request_id": request_id, "name": "Sourceling"}))
        .send()
        .unwrap()
        .json()
        .unwrap();
    assert!(
        build["unresolved"].as_array().unwrap().is_empty(),
        "{build}"
    );
    let id = build["draft"]["id"].as_str().unwrap().to_string();
    let version = build["draft"]["version"].as_u64().unwrap();
    let outcome: Value = client
        .post(format!("{url}/api/characters/{id}/finalize"))
        .json(&json!({"version": version}))
        .send()
        .unwrap()
        .json()
        .unwrap();
    assert_eq!(outcome["outcome"], "finalized", "{outcome}");
    id
}

fn read_doc(dir: &std::path::Path, id: &str) -> Value {
    serde_json::from_str(
        &std::fs::read_to_string(dir.join(format!("characters/{id}.json"))).unwrap(),
    )
    .unwrap()
}

fn character_count(dir: &std::path::Path) -> usize {
    std::fs::read_dir(dir.join("characters"))
        .map(|entries| entries.count())
        .unwrap_or(0)
}

/// The fidelity contract, asserted document-against-document: strip the
/// two sanctioned differences (top-level id, the name decision, the
/// sheet's name field) and the JSON documents must be EQUAL — nothing
/// else may differ, and the differences must be exactly the sanctioned
/// ones.
fn assert_fidelity(source_doc: &Value, clone_doc: &Value, clone_name: &str, request_id: &str) {
    let name_decision = |doc: &Value| -> Value {
        doc["log"]
            .as_array()
            .unwrap()
            .iter()
            .find(|d| d["slot"] == NAME_SLOT)
            .cloned()
            .expect("name decision present")
    };
    let cloned_name = name_decision(clone_doc);
    assert_eq!(cloned_name["selection"]["value"], clone_name);
    assert_eq!(cloned_name["source"], "clone");
    assert_eq!(
        cloned_name["id"],
        format!("{request_id}.clone-name"),
        "the clone-name decision ID is minted from the request"
    );
    assert_eq!(
        cloned_name["order"],
        name_decision(source_doc)["order"],
        "the re-minted name keeps the source decision's position"
    );
    assert_eq!(clone_doc["sheet"]["name"], clone_name);

    let normalize = |doc: &Value| -> Value {
        let mut doc = doc.clone();
        doc["id"] = Value::from("<id>");
        doc["sheet"]["name"] = Value::from("<name>");
        for d in doc["log"].as_array_mut().unwrap() {
            if d["slot"] == NAME_SLOT {
                *d = Value::from("<name-decision>");
            }
        }
        doc
    };
    assert_eq!(
        normalize(source_doc),
        normalize(clone_doc),
        "outside id, file, and the name decision, the documents are identical"
    );
}

#[test]
fn cloned_finalized_character_differs_only_in_id_and_name() {
    let dir = tempfile::tempdir().unwrap();
    let server = TestServer::spawn(dir.path());
    let client = client();
    let source_id = finalized_character(&client, &server.url, "clone-src-final");
    let source_bytes_before =
        std::fs::read(dir.path().join(format!("characters/{source_id}.json"))).unwrap();

    let (status, result) = clone_request(
        &client,
        &server.url,
        "fixture-final",
        &source_id,
        "Copyling",
    );
    assert_eq!(status, 200, "{result}");
    assert_eq!(result["finalized"], true);
    assert_eq!(result["name"], "Copyling");
    let clone_id = result["id"].as_str().unwrap();
    assert_eq!(clone_id, "c-cl-fixture-final");

    assert_fidelity(
        &read_doc(dir.path(), &source_id),
        &read_doc(dir.path(), clone_id),
        "Copyling",
        "fixture-final",
    );
    // Creation-only: the source file's bytes never changed.
    assert_eq!(
        std::fs::read(dir.path().join(format!("characters/{source_id}.json"))).unwrap(),
        source_bytes_before,
        "cloning never writes to the source file"
    );
    // Clones are born verify-clean.
    let (code, output) = TestServer::run_verify(dir.path(), &[]);
    assert_eq!(code, 0, "verify must pass over source and clone: {output}");
}

#[test]
fn cloned_draft_resumes_at_the_same_step_and_diverges_independently() {
    let dir = tempfile::tempdir().unwrap();
    let server = TestServer::spawn(dir.path());
    let client = client();
    // A mid-wizard draft: created with a name, one confirmed choice.
    let draft: Value = client
        .post(format!("{}/api/characters", server.url))
        .json(&json!({"name": "Forkful"}))
        .send()
        .unwrap()
        .json()
        .unwrap();
    let source_id = draft["id"].as_str().unwrap().to_string();
    let confirm: Value = client
        .post(format!("{}/api/characters/{source_id}/confirm", server.url))
        .json(&json!({"version": 1, "decision": {
            "id": "fork-ancestry", "slot": "pf2e.ancestry",
            "selection": {"kind": "option", "value": "ancestry.dwarf"},
            "source": "player"
        }}))
        .send()
        .unwrap()
        .json()
        .unwrap();
    assert_eq!(confirm["outcome"], "confirmed");

    let (status, result) = clone_request(
        &client,
        &server.url,
        "fixture-draft",
        &source_id,
        "Forkful B",
    );
    assert_eq!(status, 200, "{result}");
    assert_eq!(result["finalized"], false);
    let clone_id = result["id"].as_str().unwrap().to_string();
    assert_fidelity(
        &read_doc(dir.path(), &source_id),
        &read_doc(dir.path(), &clone_id),
        "Forkful B",
        "fixture-draft",
    );

    // Divergence: a confirm in the clone never touches the source.
    let source_bytes =
        std::fs::read(dir.path().join(format!("characters/{source_id}.json"))).unwrap();
    let clone_doc = read_doc(dir.path(), &clone_id);
    let clone_version = clone_doc["draft_version"].as_u64().unwrap();
    let confirm: Value = client
        .post(format!("{}/api/characters/{clone_id}/confirm", server.url))
        .json(&json!({"version": clone_version, "decision": {
            "id": "fork-heritage", "slot": "pf2e.ancestry.heritage",
            "selection": {"kind": "option", "value": "heritage.dwarf.rock"},
            "source": "player"
        }}))
        .send()
        .unwrap()
        .json()
        .unwrap();
    assert_eq!(confirm["outcome"], "confirmed", "{confirm}");
    assert_eq!(
        std::fs::read(dir.path().join(format!("characters/{source_id}.json"))).unwrap(),
        source_bytes,
        "the clone's writes never bleed into the source"
    );
}

#[test]
fn divergent_sources_refuse_to_clone() {
    let dir = tempfile::tempdir().unwrap();
    let client = client();
    let source_id;
    {
        let server = TestServer::spawn(dir.path());
        source_id = finalized_character(&client, &server.url, "clone-src-tampered");
    }
    // Tamper with the stored sheet while no server runs.
    let path = dir.path().join(format!("characters/{source_id}.json"));
    let mut doc: Value = serde_json::from_str(&std::fs::read_to_string(&path).unwrap()).unwrap();
    doc["sheet"]["name"] = Value::from("Hand-Edited");
    std::fs::write(&path, serde_json::to_string_pretty(&doc).unwrap()).unwrap();

    let server = TestServer::spawn(dir.path());
    let before = character_count(dir.path());
    let (status, result) =
        clone_request(&client, &server.url, "fixture-tampered", &source_id, "Copy");
    assert_eq!(status, 422, "{result}");
    assert!(
        result["message"].as_str().unwrap().contains("verify"),
        "the refusal points at verify: {result}"
    );
    assert_eq!(character_count(dir.path()), before, "nothing was written");
}

#[test]
fn trashed_and_quarantined_sources_refuse_to_clone() {
    let dir = tempfile::tempdir().unwrap();
    let server = TestServer::spawn(dir.path());
    let client = client();
    let source_id = finalized_character(&client, &server.url, "clone-src-gone");

    // Trash it through the app.
    let deleted = client
        .delete(format!("{}/api/characters/{source_id}", server.url))
        .send()
        .unwrap();
    assert!(deleted.status().is_success());
    let before = character_count(dir.path());
    let (status, result) =
        clone_request(&client, &server.url, "fixture-trashed", &source_id, "Copy");
    assert_eq!(status, 404, "a trashed source is not found: {result}");
    assert_eq!(character_count(dir.path()), before);

    // A quarantined (corrupt) file refuses typed.
    std::fs::write(
        dir.path().join("characters/c-broken.json"),
        "{ not json at all",
    )
    .unwrap();
    let (status, result) =
        clone_request(&client, &server.url, "fixture-corrupt", "c-broken", "Copy");
    assert_eq!(status, 422, "{result}");
    assert!(
        result["message"].as_str().unwrap().contains("quarantined"),
        "{result}"
    );
    assert_eq!(
        character_count(dir.path()),
        before + 1,
        "only the corrupt file itself"
    );
}

#[test]
fn clone_retries_return_the_first_write_and_ignore_new_names() {
    let dir = tempfile::tempdir().unwrap();
    let server = TestServer::spawn(dir.path());
    let client = client();
    let source_id = finalized_character(&client, &server.url, "clone-src-retry");

    let (status, first) = clone_request(
        &client,
        &server.url,
        "fixture-retry",
        &source_id,
        "First Name",
    );
    assert_eq!(status, 200, "{first}");
    let before = character_count(dir.path());
    // The retry carries a DIFFERENT name — first write wins.
    let (status, retry) = clone_request(
        &client,
        &server.url,
        "fixture-retry",
        &source_id,
        "Second Name",
    );
    assert_eq!(status, 200, "{retry}");
    assert_eq!(retry["id"], first["id"]);
    assert_eq!(retry["name"], "First Name");
    assert_eq!(character_count(dir.path()), before, "no second clone");
}
