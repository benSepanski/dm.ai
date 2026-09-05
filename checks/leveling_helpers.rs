//! Level-up HTTP helpers shared by the leveling rows — included as a module
//! by each check that drives the real server (`#[path]`), since the checks
//! lib carries no HTTP or JSON dependencies.

// ---- Level-up HTTP helpers shared by the leveling rows ----
//
// Every leveling check drives the real server the way the UI does: quick
// build → finalize → level-up → confirm the level's slots → finalize.

#![allow(dead_code)]

use serde_json::{json, Value};

/// POST a JSON body; returns (status, body-or-null).
pub fn post_json(
    client: &reqwest::blocking::Client,
    url: &str,
    path: &str,
    body: Value,
) -> (u16, Value) {
    let response = client
        .post(format!("{url}{path}"))
        .json(&body)
        .send()
        .expect("request");
    let status = response.status().as_u16();
    (status, response.json().unwrap_or(Value::Null))
}

pub fn get_json(client: &reqwest::blocking::Client, url: &str, path: &str) -> Value {
    client
        .get(format!("{url}{path}"))
        .send()
        .expect("request")
        .json()
        .unwrap_or(Value::Null)
}

/// A finalized level-1 quick-build Fighter; returns its ID.
pub fn finalized_fighter(
    client: &reqwest::blocking::Client,
    url: &str,
    request_id: &str,
) -> String {
    let (status, build) = post_json(
        client,
        url,
        "/api/characters/quick-build",
        json!({ "request_id": request_id, "name": format!("Leveler {request_id}") }),
    );
    assert_eq!(status, 200, "{build}");
    let id = build["draft"]["id"].as_str().unwrap().to_string();
    let version = build["draft"]["version"].as_u64().unwrap();
    let (status, outcome) = post_json(
        client,
        url,
        &format!("/api/characters/{id}/finalize"),
        json!({ "version": version }),
    );
    assert_eq!(status, 200, "{outcome}");
    assert_eq!(outcome["outcome"], "finalized", "{outcome}");
    id
}

/// The character view by ID.
pub fn character(client: &reqwest::blocking::Client, url: &str, id: &str) -> Value {
    get_json(client, url, &format!("/api/characters/{id}"))
}

/// Start (or resume) a level-up; returns the pending level's draft view.
pub fn start_level(client: &reqwest::blocking::Client, url: &str, id: &str) -> Value {
    let view = character(client, url, id);
    let version = view["version"]
        .as_u64()
        .or_else(|| view["draft"]["version"].as_u64())
        .expect("version");
    let (status, outcome) = post_json(
        client,
        url,
        &format!("/api/characters/{id}/level-up"),
        json!({ "version": version }),
    );
    assert_eq!(status, 200, "{outcome}");
    assert_eq!(outcome["outcome"], "started", "{outcome}");
    outcome["draft"].clone()
}

/// The slot view for a slot ID within a draft view.
pub fn slot_view(draft: &Value, slot: &str) -> Option<Value> {
    draft["projection"]["steps"]
        .as_array()?
        .iter()
        .flat_map(|s| s["slots"].as_array().cloned().unwrap_or_default())
        .find(|sl| sl["id"] == slot)
}

/// Confirm one option in a slot; returns the confirm outcome.
pub fn confirm_option(
    client: &reqwest::blocking::Client,
    url: &str,
    id: &str,
    version: u64,
    decision_id: &str,
    slot: &str,
    option: &str,
) -> Value {
    let (_, outcome) = post_json(
        client,
        url,
        &format!("/api/characters/{id}/confirm"),
        json!({ "version": version, "decision": {
            "id": decision_id, "slot": slot,
            "selection": { "kind": "option", "value": option },
            "source": "player"
        }}),
    );
    outcome
}

/// Fill every open slot of a pending level with its first available option
/// (Multi slots: the first `count` available), then finalize the level.
/// Returns the finalized character view.
pub fn complete_level(client: &reqwest::blocking::Client, url: &str, id: &str) -> Value {
    let mut draft = start_level(client, url, id);
    let mut n = 0;
    loop {
        let open: Vec<Value> = draft["projection"]["steps"]
            .as_array()
            .unwrap()
            .iter()
            .flat_map(|s| s["slots"].as_array().cloned().unwrap_or_default())
            .filter(|sl| sl["decision"].is_null() && sl["required"] == true)
            .collect();
        let Some(slot) = open.first() else { break };
        let slot_id = slot["id"].as_str().unwrap().to_string();
        let available: Vec<String> = slot["options"]
            .as_array()
            .unwrap()
            .iter()
            .filter(|o| o["available"] == true)
            .map(|o| o["id"].as_str().unwrap().to_string())
            .collect();
        let selection = match slot["kind"]["kind"].as_str() {
            Some("multi") => {
                let count = slot["kind"]["count"].as_u64().unwrap_or(1) as usize;
                json!({ "kind": "options", "value": available.iter().take(count).collect::<Vec<_>>() })
            }
            _ => {
                json!({ "kind": "option", "value": available.first().expect("an available option") })
            }
        };
        n += 1;
        let (status, outcome) = post_json(
            client,
            url,
            &format!("/api/characters/{id}/confirm"),
            json!({ "version": draft["version"], "decision": {
                "id": format!("{id}-lvl-{n}-{slot_id}"), "slot": slot_id,
                "selection": selection, "source": "player"
            }}),
        );
        assert_eq!(status, 200, "{outcome}");
        assert_eq!(outcome["outcome"], "confirmed", "{outcome}");
        draft = outcome["draft"].clone();
    }
    let (status, outcome) = post_json(
        client,
        url,
        &format!("/api/characters/{id}/finalize"),
        json!({ "version": draft["version"] }),
    );
    assert_eq!(status, 200, "{outcome}");
    assert_eq!(outcome["outcome"], "finalized", "{outcome}");
    character(client, url, id)
}

/// The stored document as JSON.
pub fn read_doc(dir: &std::path::Path, id: &str) -> Value {
    serde_json::from_str(
        &std::fs::read_to_string(dir.join(format!("characters/{id}.json"))).unwrap(),
    )
    .unwrap()
}
