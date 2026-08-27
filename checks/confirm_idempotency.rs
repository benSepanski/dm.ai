//! Confirm idempotency + concurrency: a replayed decision ID appends
//! nothing (even with a stale version — the crash-retry case), and a
//! confirm against a stale draft version returns a conflict carrying the
//! current draft state.

use checks::TestServer;
use serde_json::{json, Value};

fn decision(id: &str, slot: &str, value: &str) -> Value {
    json!({
        "id": id,
        "slot": slot,
        "selection": {"kind": "option", "value": value},
        "source": "player"
    })
}

fn log_len(draft: &Value) -> usize {
    // Count the decisions visible across slots (one per occupied slot).
    draft["projection"]["steps"]
        .as_array()
        .unwrap()
        .iter()
        .flat_map(|s| s["slots"].as_array().unwrap())
        .filter(|slot| !slot["decision"].is_null())
        .count()
}

#[test]
fn replayed_decision_ids_append_nothing() {
    let dir = tempfile::tempdir().unwrap();
    let server = TestServer::spawn(dir.path());
    let client = reqwest::blocking::Client::new();
    let draft: Value = client
        .post(format!("{}/api/characters", server.url))
        .json(&json!({"name": "Idem"}))
        .send()
        .unwrap()
        .json()
        .unwrap();
    let id = draft["id"].as_str().unwrap();
    let confirm_url = format!("{}/api/characters/{id}/confirm", server.url);

    let first: Value = client
        .post(&confirm_url)
        .json(&json!({"version": 1, "decision": decision("dup", "pf2e.ancestry", "ancestry.elf")}))
        .send()
        .unwrap()
        .json()
        .unwrap();
    assert_eq!(first["outcome"], "confirmed");
    let version_after = first["draft"]["version"].as_u64().unwrap();
    let len_after = log_len(&first["draft"]);

    // Retry with the same decision ID and the ORIGINAL (now stale) version —
    // exactly what a client does after a crash between save and ack.
    let retry: Value = client
        .post(&confirm_url)
        .json(&json!({"version": 1, "decision": decision("dup", "pf2e.ancestry", "ancestry.elf")}))
        .send()
        .unwrap()
        .json()
        .unwrap();
    assert_eq!(
        retry["outcome"], "confirmed",
        "a replayed ID is success, not conflict"
    );
    assert_eq!(retry["draft"]["version"].as_u64().unwrap(), version_after);
    assert_eq!(log_len(&retry["draft"]), len_after, "nothing was appended");
}

#[test]
fn stale_confirms_conflict_with_current_state() {
    let dir = tempfile::tempdir().unwrap();
    let server = TestServer::spawn(dir.path());
    let client = reqwest::blocking::Client::new();
    let draft: Value = client
        .post(format!("{}/api/characters", server.url))
        .json(&json!({"name": "Stale"}))
        .send()
        .unwrap()
        .json()
        .unwrap();
    let id = draft["id"].as_str().unwrap();
    let confirm_url = format!("{}/api/characters/{id}/confirm", server.url);

    // Tab A confirms at version 1.
    let a: Value = client
        .post(&confirm_url)
        .json(&json!({"version": 1, "decision": decision("a1", "pf2e.ancestry", "ancestry.dwarf")}))
        .send()
        .unwrap()
        .json()
        .unwrap();
    assert_eq!(a["outcome"], "confirmed");

    // Tab B, still on version 1, tries a different decision: conflict, and
    // the response carries the current draft so the tab can reload.
    let b: Value = client
        .post(&confirm_url)
        .json(&json!({"version": 1, "decision": decision("b1", "pf2e.background", "background.warrior")}))
        .send()
        .unwrap()
        .json()
        .unwrap();
    assert_eq!(
        b["outcome"], "conflict",
        "stale version must not interleave"
    );
    assert_eq!(
        b["current"]["version"].as_u64(),
        a["draft"]["version"].as_u64(),
        "conflict carries current state"
    );
    // And nothing from tab B entered the log.
    assert_eq!(log_len(&b["current"]), log_len(&a["draft"]));
}
