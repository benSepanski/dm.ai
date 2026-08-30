//! Quick build (spec req 7, architecture rows verbatim):
//! - the suggested build folds clean on an empty draft: zero illegal
//!   entries, an empty checklist, and a finalizable character (a data lint
//!   through the real engine — a bad block cannot ship);
//! - fill-remaining preserves confirmed work: every pre-existing log entry
//!   is byte-identical after the fill, and a blocked suggestion keeps the
//!   legal prefix and names the unresolved slots — never a rollback.

use checks::TestServer;
use serde_json::{json, Value};

// ---- Data lint through the real engine (native, no server) ----

#[test]
fn suggested_build_folds_clean_with_empty_checklist_and_finalizes() {
    let data = std::sync::Arc::new(checks::load_rules_data());
    let builds = ruleset_pf2e::suggested_builds(&data);
    assert!(
        builds.iter().any(|(id, _)| id == "class.fighter"),
        "class.fighter must ship a suggested build"
    );
    let engine = ruleset_pf2e::engine(data);
    for (class_id, map) in &builds {
        let plan = engine
            .expand_suggestions(
                &[],
                &|slot| map.get(slot).cloned(),
                &|slot| types::DecisionId::new(format!("lint.{slot}")),
                types::DecisionSource::Suggested,
            )
            .unwrap_or_else(|e| panic!("{class_id}: suggested build must expand: {e}"));
        assert!(
            plan.unresolved.is_empty(),
            "{class_id}: the suggested build left required slots unresolved \
             on an empty draft: {:#?}",
            plan.unresolved
        );
        let projection = engine
            .project(&plan.log)
            .unwrap_or_else(|e| panic!("{class_id}: expanded log must project: {e}"));
        assert!(
            !projection
                .checklist
                .iter()
                .any(|e| e.severity == types::ChecklistSeverity::Illegal),
            "{class_id}: zero illegal entries required: {:#?}",
            projection.checklist
        );
        assert!(
            projection.checklist.is_empty(),
            "{class_id}: the expanded build must have an empty checklist: {:#?}",
            projection.checklist
        );
        assert!(
            projection.can_finalize,
            "{class_id}: the expanded build must be finalizable"
        );
        assert!(
            plan.log
                .iter()
                .all(|d| d.source == types::DecisionSource::Suggested),
            "{class_id}: every planner decision carries the Suggested source"
        );

        // Deterministic: a second expansion is identical.
        let again = engine
            .expand_suggestions(
                &[],
                &|slot| map.get(slot).cloned(),
                &|slot| types::DecisionId::new(format!("lint.{slot}")),
                types::DecisionSource::Suggested,
            )
            .unwrap();
        assert_eq!(
            plan.log, again.log,
            "{class_id}: expansion must be deterministic"
        );
    }
}

// ---- Fill-remaining through the real server ----

fn create_draft(client: &reqwest::blocking::Client, url: &str, name: &str) -> Value {
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
    decision: Value,
) -> Value {
    let outcome: Value = client
        .post(format!("{url}/api/characters/{id}/confirm"))
        .json(&json!({ "version": version, "decision": decision }))
        .send()
        .unwrap()
        .json()
        .unwrap();
    assert_eq!(outcome["outcome"], "confirmed", "{outcome}");
    outcome
}

fn read_log(dir: &std::path::Path, id: &str) -> Vec<Value> {
    let path = dir.join(format!("characters/{id}.json"));
    let doc: Value = serde_json::from_str(&std::fs::read_to_string(path).unwrap()).unwrap();
    doc["log"].as_array().unwrap().clone()
}

#[test]
fn fill_remaining_preserves_confirmed_entries_byte_identical() {
    let dir = tempfile::tempdir().unwrap();
    let server = TestServer::spawn(dir.path());
    let client = reqwest::blocking::Client::new();
    let draft = create_draft(&client, &server.url, "Halfway");
    let id = draft["id"].as_str().unwrap().to_string();
    let mut version = draft["version"].as_u64().unwrap();

    // Hand-confirm choices, one of them diverging from the suggestion
    // (background boost Con where the build suggests Str).
    for (did, slot, value) in [
        ("h1", "pf2e.ancestry", "ancestry.human"),
        ("h2", "pf2e.background", "background.warrior"),
        ("h3", "pf2e.boosts.background-choice", "attr.con"),
    ] {
        let outcome = confirm(
            &client,
            &server.url,
            &id,
            version,
            json!({ "id": did, "slot": slot,
                    "selection": { "kind": "option", "value": value },
                    "source": "player" }),
        );
        version = outcome["draft"]["version"].as_u64().unwrap();
    }
    let before = read_log(dir.path(), &id);

    let outcome: Value = client
        .post(format!("{}/api/characters/{id}/fill-remaining", server.url))
        .json(&json!({ "request_id": "fill-preserve-1", "version": version }))
        .send()
        .unwrap()
        .json()
        .unwrap();
    assert_eq!(outcome["outcome"], "filled", "{outcome}");
    assert_eq!(
        outcome["unresolved"].as_array().unwrap().len(),
        0,
        "adapting around the confirmed choices must complete: {}",
        outcome["unresolved"]
    );
    assert!(
        outcome["draft"]["projection"]["can_finalize"]
            .as_bool()
            .unwrap(),
        "the filled draft is review-ready"
    );

    // Every pre-existing log entry is byte-identical, in place, as a prefix.
    let after = read_log(dir.path(), &id);
    assert!(after.len() > before.len(), "the fill appended decisions");
    assert_eq!(
        &after[..before.len()],
        &before[..],
        "confirmed work must never move under fill-remaining"
    );
    // Appended entries carry the suggested source; confirmed ones stay player.
    for entry in &after[before.len()..] {
        assert_eq!(entry["source"], "suggested");
    }
    for entry in &after[..before.len()] {
        assert_eq!(entry["source"], "player");
    }
}

#[test]
fn blocked_suggestions_keep_the_legal_prefix_and_name_the_remainder() {
    let dir = tempfile::tempdir().unwrap();
    let server = TestServer::spawn(dir.path());
    let client = reqwest::blocking::Client::new();
    let draft = create_draft(&client, &server.url, "Stubborn");
    let id = draft["id"].as_str().unwrap().to_string();
    let version = draft["version"].as_u64().unwrap();

    // A confirmed Dwarf blocks the Human-anchored heritage and ancestry-feat
    // suggestions; everything else must still fill (never all-or-nothing).
    let outcome = confirm(
        &client,
        &server.url,
        &id,
        version,
        json!({ "id": "s1", "slot": "pf2e.ancestry",
                "selection": { "kind": "option", "value": "ancestry.dwarf" },
                "source": "player" }),
    );
    let version = outcome["draft"]["version"].as_u64().unwrap();
    let before = read_log(dir.path(), &id);

    let outcome: Value = client
        .post(format!("{}/api/characters/{id}/fill-remaining", server.url))
        .json(&json!({ "request_id": "fill-blocked-1", "version": version }))
        .send()
        .unwrap()
        .json()
        .unwrap();
    assert_eq!(outcome["outcome"], "filled", "{outcome}");
    let unresolved: Vec<&str> = outcome["unresolved"]
        .as_array()
        .unwrap()
        .iter()
        .map(|u| u["slot"].as_str().unwrap())
        .collect();
    assert!(
        unresolved.contains(&"pf2e.ancestry.heritage"),
        "the response must name the blocked heritage slot: {unresolved:?}"
    );
    assert!(
        unresolved.contains(&"pf2e.ancestry.feat"),
        "the response must name the blocked ancestry-feat slot: {unresolved:?}"
    );
    for u in outcome["unresolved"].as_array().unwrap() {
        assert!(
            !u["reason"].as_str().unwrap().is_empty(),
            "every unresolved slot carries a reason"
        );
    }

    // The legal prefix was persisted — no rollback: the file grew, the
    // confirmed dwarf decision is byte-identical, and the checklist shows
    // exactly the unresolved remainder (no illegal entries).
    let after = read_log(dir.path(), &id);
    assert!(
        after.len() > before.len(),
        "the legal prefix must be persisted, not rolled back"
    );
    assert_eq!(&after[..before.len()], &before[..]);
    let checklist = outcome["draft"]["projection"]["checklist"]
        .as_array()
        .unwrap();
    assert!(
        checklist.iter().all(|e| e["severity"] != "illegal"),
        "a fill never persists an illegal entry: {checklist:?}"
    );
    assert!(
        checklist
            .iter()
            .any(|e| e["slot"] == "pf2e.ancestry.heritage"),
        "the unresolved slots surface on the ordinary checklist"
    );
    assert_eq!(
        outcome["draft"]["projection"]["can_finalize"], false,
        "a partial fill is not finalizable"
    );
}
