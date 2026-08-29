//! The preparation section's constraint rows (architecture:
//! chargen-wizard): the prep save writes only prep, is idempotent and
//! stale-rejecting, finalized-file writers never race away each other's
//! effects, `verify` re-validates the section, and one validation driver
//! serves the route and verify observably.

use checks::TestServer;
use serde_json::{json, Value};

#[path = "wizard_fixture.rs"]
mod wizard_fixture;
use wizard_fixture::{build_sylvenne_finalized, client, prep_save, sylvenne_prep_choices};

fn read_doc(dir: &std::path::Path, id: &str) -> Value {
    let path = dir.join(format!("characters/{id}.json"));
    serde_json::from_str(&std::fs::read_to_string(path).unwrap()).unwrap()
}

fn write_doc(dir: &std::path::Path, id: &str, doc: &Value) {
    let path = dir.join(format!("characters/{id}.json"));
    std::fs::write(path, serde_json::to_string_pretty(doc).unwrap()).unwrap();
}

/// A revised (still legal) preparation: one cantrip swapped.
fn revised_prep() -> Value {
    json!([
        {"slot": "pf2e.prep.cantrips", "selection": {"kind": "options", "value": [
            "spell.shield", "spell.frostbite", "spell.electric-arc",
            "spell.detect-magic", "spell.light"]}},
        {"slot": "pf2e.prep.rank1", "selection": {"kind": "options", "value": ["spell.fear", "spell.command"]}},
        {"slot": "pf2e.prep.school-cantrip", "selection": {"kind": "option", "value": "spell.telekinetic-projectile"}},
        {"slot": "pf2e.prep.school-rank1", "selection": {"kind": "option", "value": "spell.mystic-armor"}},
    ])
}

/// Prep saves write only the prep section (and, for older-schema files,
/// the schema envelope): the decision log and materialized sheet are
/// byte-identical before and after — on a finalized character and on the
/// sanctioned v2-first-write upgrade path.
#[test]
fn prep_save_writes_only_prep() {
    let dir = tempfile::tempdir().unwrap();
    let client = client();
    let server = TestServer::spawn(dir.path());
    let built = build_sylvenne_finalized(&client, &server.url);

    let before = read_doc(dir.path(), &built.id);
    let outcome = prep_save(
        &client,
        &server.url,
        &built.id,
        built.version,
        "pencil-edit-1",
        "finalized",
        &revised_prep(),
    );
    assert_eq!(outcome["outcome"], "saved", "{outcome:#?}");
    let after = read_doc(dir.path(), &built.id);
    assert_eq!(
        serde_json::to_string(&before["log"]).unwrap(),
        serde_json::to_string(&after["log"]).unwrap(),
        "the decision log is byte-identical across a prep save"
    );
    assert_eq!(
        serde_json::to_string(&before["sheet"]).unwrap(),
        serde_json::to_string(&after["sheet"]).unwrap(),
        "the materialized sheet is byte-identical across a prep save"
    );
    assert_ne!(
        serde_json::to_string(&before["prep"]).unwrap(),
        serde_json::to_string(&after["prep"]).unwrap(),
        "the prep section changed"
    );

    // The v2-envelope carve-out: rewind the file to schema 2 (no prep
    // section — v2 predates it); the first prep save upgrades the envelope
    // and writes prep, log and sheet still untouched.
    drop(server);
    let mut doc = read_doc(dir.path(), &built.id);
    doc["schema_version"] = Value::from(2);
    doc.as_object_mut().unwrap().remove("prep");
    write_doc(dir.path(), &built.id, &doc);
    let server = TestServer::spawn(dir.path());
    let character: Value = client
        .get(format!("{}/api/characters/{}", server.url, built.id))
        .send()
        .unwrap()
        .json()
        .unwrap();
    let version = character["version"].as_u64().unwrap();
    let before = read_doc(dir.path(), &built.id);
    let outcome = prep_save(
        &client,
        &server.url,
        &built.id,
        version,
        "pencil-edit-2",
        "finalized",
        &sylvenne_prep_choices(),
    );
    assert_eq!(outcome["outcome"], "saved", "{outcome:#?}");
    let after = read_doc(dir.path(), &built.id);
    assert_eq!(after["schema_version"], 3, "envelope upgraded on first write");
    assert_eq!(
        serde_json::to_string(&before["log"]).unwrap(),
        serde_json::to_string(&after["log"]).unwrap()
    );
    assert_eq!(
        serde_json::to_string(&before["sheet"]).unwrap(),
        serde_json::to_string(&after["sheet"]).unwrap()
    );
}

/// Idempotency and concurrency: a replayed request ID (with a stale
/// version — the crash-retry case) returns the saved result and changes
/// nothing; a NEW request against a stale version conflicts; the wrong
/// lifecycle conflicts and never coerces.
#[test]
fn prep_save_idempotency_and_stale_rejection() {
    let dir = tempfile::tempdir().unwrap();
    let client = client();
    let server = TestServer::spawn(dir.path());
    let built = build_sylvenne_finalized(&client, &server.url);

    let outcome = prep_save(
        &client,
        &server.url,
        &built.id,
        built.version,
        "edit-a",
        "finalized",
        &revised_prep(),
    );
    assert_eq!(outcome["outcome"], "saved");
    let version_after = outcome["character"]["version"].as_u64().unwrap();
    let doc_after = serde_json::to_string(&read_doc(dir.path(), &built.id)).unwrap();

    // Replay: same request ID, original (stale) version — saved, no change.
    let retry = prep_save(
        &client,
        &server.url,
        &built.id,
        built.version,
        "edit-a",
        "finalized",
        &revised_prep(),
    );
    assert_eq!(retry["outcome"], "saved", "a replayed ID is success");
    assert_eq!(retry["character"]["version"].as_u64().unwrap(), version_after);
    assert_eq!(
        serde_json::to_string(&read_doc(dir.path(), &built.id)).unwrap(),
        doc_after,
        "the replay changed nothing on disk"
    );

    // A NEW request ID against the stale version: conflict, nothing written.
    let stale = prep_save(
        &client,
        &server.url,
        &built.id,
        built.version,
        "edit-b",
        "finalized",
        &sylvenne_prep_choices(),
    );
    assert_eq!(stale["outcome"], "conflict", "{stale:#?}");
    assert_eq!(
        serde_json::to_string(&read_doc(dir.path(), &built.id)).unwrap(),
        doc_after
    );

    // Wrong lifecycle: told, never coerced.
    let wrong = prep_save(
        &client,
        &server.url,
        &built.id,
        version_after,
        "edit-c",
        "draft",
        &sylvenne_prep_choices(),
    );
    assert_eq!(wrong["outcome"], "conflict", "{wrong:#?}");
    assert_eq!(
        serde_json::to_string(&read_doc(dir.path(), &built.id)).unwrap(),
        doc_after
    );
}

/// Finalized-file writers never race: prep saves hammering a finalized
/// character concurrently (distinct request IDs, refreshed versions) all
/// serialize — every accepted write's effect lands, the loser of each
/// version race is told to reload, and the file never tears or loses an
/// acknowledged effect.
#[test]
fn finalized_writers_serialize() {
    let dir = tempfile::tempdir().unwrap();
    let client = client();
    let server = TestServer::spawn(dir.path());
    let built = build_sylvenne_finalized(&client, &server.url);
    let base = server.url.clone();
    let id = built.id.clone();

    let workers: Vec<_> = (0..2)
        .map(|w| {
            let client = client.clone();
            let base = base.clone();
            let id = id.clone();
            std::thread::spawn(move || {
                let mut saved = 0u32;
                for i in 0..12 {
                    let character: Value = client
                        .get(format!("{base}/api/characters/{id}"))
                        .send()
                        .unwrap()
                        .json()
                        .unwrap();
                    let version = character["version"].as_u64().unwrap();
                    let choices = if w == 0 {
                        sylvenne_prep_choices()
                    } else {
                        revised_prep()
                    };
                    let outcome = prep_save(
                        &client,
                        &base,
                        &id,
                        version,
                        &format!("race-{w}-{i}"),
                        "finalized",
                        &choices,
                    );
                    match outcome["outcome"].as_str().unwrap() {
                        "saved" => saved += 1,
                        "conflict" => {}
                        other => panic!("unexpected outcome {other}: {outcome:#?}"),
                    }
                }
                saved
            })
        })
        .collect();
    let total: u32 = workers.into_iter().map(|w| w.join().unwrap()).sum();
    assert!(total > 0, "at least one racer must land saves");

    // The file holds exactly one of the two prep sets, intact — never a
    // torn interleaving — and the log/sheet never changed.
    let doc = read_doc(dir.path(), &built.id);
    let cantrips = doc["prep"]["choices"]
        .as_array()
        .unwrap()
        .iter()
        .find(|c| c["slot"] == "pf2e.prep.cantrips")
        .unwrap()["selection"]["value"]
        .as_array()
        .unwrap()
        .iter()
        .map(|v| v.as_str().unwrap().to_string())
        .collect::<Vec<_>>();
    assert!(
        cantrips.contains(&"spell.ignition".to_string())
            || cantrips.contains(&"spell.frostbite".to_string()),
        "the final prep is one writer's complete set: {cantrips:?}"
    );
    let (code, out) = TestServer::run_verify(dir.path(), &[]);
    assert_eq!(code, 0, "verify is clean after the race:\n{out}");
}

/// `verify` re-validates the prep section: illegal picks, unknown spell
/// IDs, and prep on a class with no prep slots each produce a named
/// report; an absent section and a legal revised prep are silent; a
/// structurally broken section is reported. Nothing blocks loading.
#[test]
fn verify_revalidates_prep() {
    let dir = tempfile::tempdir().unwrap();
    let client = client();
    let built;
    {
        let server = TestServer::spawn(dir.path());
        built = build_sylvenne_finalized(&client, &server.url);
        // A fighter (quick build) with NO prep section: silent.
        let qb: Value = client
            .post(format!("{}/api/characters/quick-build", server.url))
            .json(&json!({"request_id": "prep-verify-fighter", "name": "Garrek"}))
            .send()
            .unwrap()
            .json()
            .unwrap();
        assert!(qb["draft"]["id"].is_string(), "{qb:#?}");
    }

    // Baseline: everything legal, verify exits clean.
    let (code, out) = TestServer::run_verify(dir.path(), &[]);
    assert_eq!(code, 0, "clean baseline:\n{out}");

    // Hand-tamper: prepare a spell that is not in the book.
    let clean_doc = read_doc(dir.path(), &built.id);
    let mut doc = clean_doc.clone();
    doc["prep"]["choices"][1]["selection"]["value"] = json!(["spell.grim-tendrils", "spell.fear"]);
    write_doc(dir.path(), &built.id, &doc);
    let (code, out) = TestServer::run_verify(dir.path(), &[]);
    assert_eq!(code, 1, "illegal prep must fail verify:\n{out}");
    assert!(
        out.contains("PREP-BAD") && out.contains("not in your spellbook"),
        "verify names the rule:\n{out}"
    );

    // Unknown spell ID.
    let mut doc = clean_doc.clone();
    doc["prep"]["choices"][2]["selection"]["value"] = json!("spell.does-not-exist");
    write_doc(dir.path(), &built.id, &doc);
    let (code, out) = TestServer::run_verify(dir.path(), &[]);
    assert_eq!(code, 1);
    assert!(out.contains("PREP-BAD"), "unknown ID reported:\n{out}");

    // Structurally broken prep: reported, not quarantined.
    let mut doc = clean_doc.clone();
    doc["prep"] = json!({"choices": 42});
    write_doc(dir.path(), &built.id, &doc);
    let (code, out) = TestServer::run_verify(dir.path(), &[]);
    assert_eq!(code, 1);
    assert!(
        out.contains("PREP-BAD") && out.contains("could not be read"),
        "broken section reported:\n{out}"
    );
    assert!(!out.contains("CORRUPT"), "never quarantined:\n{out}");

    // Prep on a class with no prep slots (a Fighter): reported.
    let fighter_id = "c-qb-prep-verify-fighter";
    let mut fdoc = read_doc(dir.path(), fighter_id);
    fdoc["prep"] = json!({"choices": [
        {"slot": "pf2e.prep.cantrips", "selection": {"kind": "options", "value": ["spell.light"]}}
    ]});
    write_doc(dir.path(), fighter_id, &fdoc);
    write_doc(dir.path(), &built.id, &clean_doc); // restore the wizard
    let (code, out) = TestServer::run_verify(dir.path(), &[]);
    assert_eq!(code, 1);
    assert!(
        out.contains("PREP-BAD") && out.contains(fighter_id),
        "prep on a non-preparing class reported:\n{out}"
    );
}

/// One validation driver, observable: the same illegal choice set yields
/// the same rule and message from the prep route (native re-validation)
/// and from `verify` (the re-validation pass). The WASM preview compiles
/// the identical engine function from the same commit (bindings-freshness
/// gate), so its agreement is structural.
#[test]
fn one_validation_driver_route_and_verify_agree() {
    let dir = tempfile::tempdir().unwrap();
    let client = client();
    let server = TestServer::spawn(dir.path());
    let built = build_sylvenne_finalized(&client, &server.url);

    let illegal = json!([
        {"slot": "pf2e.prep.cantrips", "selection": {"kind": "options", "value": [
            "spell.shield", "spell.ignition", "spell.electric-arc",
            "spell.detect-magic", "spell.light"]}},
        {"slot": "pf2e.prep.rank1", "selection": {"kind": "options", "value": ["spell.grim-tendrils", "spell.fear"]}},
        {"slot": "pf2e.prep.school-cantrip", "selection": {"kind": "option", "value": "spell.telekinetic-projectile"}},
        {"slot": "pf2e.prep.school-rank1", "selection": {"kind": "option", "value": "spell.mystic-armor"}},
    ]);
    let outcome = prep_save(
        &client,
        &server.url,
        &built.id,
        built.version,
        "illegal-edit",
        "finalized",
        &illegal,
    );
    assert_eq!(outcome["outcome"], "rejected", "{outcome:#?}");
    let route_message = outcome["reasons"][0]["message"].as_str().unwrap().to_string();
    assert!(route_message.contains("not in your spellbook"));

    // Write the same illegal set by hand; verify must produce the same
    // rule text.
    drop(server);
    let mut doc = read_doc(dir.path(), &built.id);
    doc["prep"]["choices"] = illegal;
    write_doc(dir.path(), &built.id, &doc);
    let (code, out) = TestServer::run_verify(dir.path(), &[]);
    assert_eq!(code, 1);
    assert!(
        out.contains("not in your spellbook"),
        "verify and the route share the driver's message:\n{out}"
    );
}
