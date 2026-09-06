//! Crash safety: SIGKILL the real server binary at arbitrary moments during
//! a storm of confirms and clears, restart on the same data directory, and
//! assert every file still loads and no acknowledged operation was lost.
//!
//! The durable state after a kill must be exactly the last acknowledged
//! state, or that state plus the single in-flight operation (a write that
//! committed before the response made it back) — never less, never torn.

use checks::TestServer;
use serde_json::{json, Value};

/// Deterministic pseudo-randomness (no rand dependency, reproducible runs).
struct Lcg(u64);
impl Lcg {
    fn next(&mut self, bound: u64) -> u64 {
        self.0 = self
            .0
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        (self.0 >> 33) % bound
    }
}

/// The decision IDs currently occupying slots, per the server's projection.
fn decision_ids(draft: &Value) -> Vec<String> {
    let mut ids: Vec<String> = draft["projection"]["steps"]
        .as_array()
        .unwrap()
        .iter()
        .flat_map(|s| s["slots"].as_array().unwrap())
        .filter_map(|slot| slot["decision"]["id"].as_str().map(str::to_string))
        .collect();
    ids.sort();
    ids
}

/// What the storm thread learned before the server died under it.
struct StormReport {
    seq: u64,
    acked_version: u64,
    acked_ids: Vec<String>,
    /// The operation whose response never arrived — it may or may not have
    /// committed before the kill.
    in_flight: InFlight,
}

#[derive(Debug)]
enum InFlight {
    None,
    /// A confirm of this decision ID on the free-boosts slot.
    Confirm(String),
    /// A clear of the free-boosts slot.
    Clear,
}

/// A quick-build cycle under SIGKILL: the expansion is one engine
/// transaction and one durable write, so after a kill the character file
/// contains either none or ALL of what the planner committed — never a
/// torn half-expansion. A re-tap with the same request ID then returns the
/// saved (or freshly rebuilt) result and appends nothing beyond it.
#[test]
fn quick_build_under_sigkill_is_none_or_all() {
    let dir = tempfile::tempdir().unwrap();
    let client = reqwest::blocking::Client::builder()
        .timeout(std::time::Duration::from_secs(2))
        .build()
        .unwrap();

    for (cycle, delay_ms) in [0u64, 2, 5, 12].into_iter().enumerate() {
        let request_id = format!("qb-crash-{cycle}");
        let mut server = TestServer::spawn(dir.path());
        let fire = std::thread::spawn({
            let client = client.clone();
            let url = format!("{}/api/characters/quick-build", server.url);
            let request_id = request_id.clone();
            move || {
                let _ = client
                    .post(&url)
                    .json(&json!({ "request_id": request_id, "name": null }))
                    .send();
            }
        });
        std::thread::sleep(std::time::Duration::from_millis(delay_ms));
        server.kill(); // SIGKILL, possibly mid-expansion or mid-write
        fire.join().unwrap();

        // Restart: no torn files; if the quick-build character exists it
        // holds the complete expansion (the fighter build fully completes,
        // so "all of what the planner committed" means review-ready).
        let server = TestServer::spawn(dir.path());
        let roster: Value = client
            .get(format!("{}/api/roster", server.url))
            .send()
            .unwrap()
            .json()
            .unwrap();
        assert!(
            roster["problems"].as_array().unwrap().is_empty(),
            "no torn or corrupt files after a quick-build kill: {:?}",
            roster["problems"]
        );
        let id = format!("c-qb-{request_id}");
        let committed = roster["entries"]
            .as_array()
            .unwrap()
            .iter()
            .any(|e| e["id"] == id.as_str());
        if committed {
            let view: Value = client
                .get(format!("{}/api/characters/{id}", server.url))
                .send()
                .unwrap()
                .json()
                .unwrap();
            assert_eq!(view["state"], "draft");
            assert!(
                view["projection"]["can_finalize"].as_bool().unwrap(),
                "a committed quick build is all-or-nothing: the file must \
                 hold the complete expansion"
            );
        }

        // Re-tap after the crash: same request ID, saved (or rebuilt)
        // result, and a second tap appends nothing on top of it.
        let rebuilt: Value = client
            .post(format!("{}/api/characters/quick-build", server.url))
            .json(&json!({ "request_id": request_id, "name": null }))
            .send()
            .unwrap()
            .json()
            .unwrap();
        assert_eq!(rebuilt["draft"]["id"].as_str().unwrap(), id);
        assert!(rebuilt["draft"]["projection"]["can_finalize"]
            .as_bool()
            .unwrap());
        let version = rebuilt["draft"]["version"].as_u64().unwrap();
        let ids = decision_ids(&rebuilt["draft"]);
        let again: Value = client
            .post(format!("{}/api/characters/quick-build", server.url))
            .json(&json!({ "request_id": request_id, "name": null }))
            .send()
            .unwrap()
            .json()
            .unwrap();
        assert_eq!(again["draft"]["version"].as_u64().unwrap(), version);
        assert_eq!(decision_ids(&again["draft"]), ids, "re-tap appends nothing");
    }
}

/// The two roster-ergonomics write paths under SIGKILL: a random mint and
/// a clone are each one durable write, so a kill leaves either nothing or
/// the complete character — never a torn file — and the retried request
/// converges on exactly one character.
#[test]
fn random_mint_and_clone_under_sigkill_are_none_or_all() {
    let dir = tempfile::tempdir().unwrap();
    let client = reqwest::blocking::Client::builder()
        .timeout(std::time::Duration::from_secs(2))
        .build()
        .unwrap();

    // A stable clone source, created before any killing starts.
    let source_id;
    {
        let server = TestServer::spawn(dir.path());
        let build: Value = client
            .post(format!("{}/api/characters/quick-build", server.url))
            .json(&json!({ "request_id": "crash-clone-src", "name": "Crash Source" }))
            .send()
            .unwrap()
            .json()
            .unwrap();
        source_id = build["draft"]["id"].as_str().unwrap().to_string();
    }

    for (cycle, delay_ms) in [0u64, 6].into_iter().enumerate() {
        let mint_request = format!("mint-crash-{cycle}");
        let clone_request = format!("clone-crash-{cycle}");
        let mut server = TestServer::spawn(dir.path());
        let fire = std::thread::spawn({
            let client = client.clone();
            let mint_url = format!("{}/api/characters/random-mint", server.url);
            let clone_url = format!("{}/api/characters/clone", server.url);
            let mint_request = mint_request.clone();
            let clone_request = clone_request.clone();
            let source_id = source_id.clone();
            move || {
                let _ = client
                    .post(&mint_url)
                    .json(&json!({ "request_id": mint_request, "class_id": null, "name": null }))
                    .send();
                let _ = client
                    .post(&clone_url)
                    .json(
                        &json!({ "request_id": clone_request, "source_id": source_id,
                                   "name": "Crash Copy" }),
                    )
                    .send();
            }
        });
        std::thread::sleep(std::time::Duration::from_millis(delay_ms));
        server.kill(); // SIGKILL, possibly mid-expansion or mid-write
        fire.join().unwrap();

        let server = TestServer::spawn(dir.path());
        let roster: Value = client
            .get(format!("{}/api/roster", server.url))
            .send()
            .unwrap()
            .json()
            .unwrap();
        assert!(
            roster["problems"].as_array().unwrap().is_empty(),
            "no torn or corrupt files after a mint/clone kill: {:?}",
            roster["problems"]
        );

        // Retry both; each must converge on exactly one character.
        let mint: Value = client
            .post(format!("{}/api/characters/random-mint", server.url))
            .json(&json!({ "request_id": mint_request, "class_id": null, "name": null }))
            .send()
            .unwrap()
            .json()
            .unwrap();
        assert_eq!(
            mint["draft"]["id"].as_str().unwrap(),
            format!("c-rn-{mint_request}")
        );
        assert!(mint["draft"]["projection"]["can_finalize"]
            .as_bool()
            .unwrap());
        let clone: Value = client
            .post(format!("{}/api/characters/clone", server.url))
            .json(
                &json!({ "request_id": clone_request, "source_id": source_id,
                           "name": "Crash Copy" }),
            )
            .send()
            .unwrap()
            .json()
            .unwrap();
        assert_eq!(
            clone["id"].as_str().unwrap(),
            format!("c-cl-{clone_request}")
        );
        let expected = 1 /* source */ + 2 * (cycle as u64 + 1);
        let roster: Value = client
            .get(format!("{}/api/roster", server.url))
            .send()
            .unwrap()
            .json()
            .unwrap();
        assert_eq!(
            roster["entries"].as_array().unwrap().len() as u64,
            expected,
            "each cycle nets exactly one mint and one clone"
        );
    }
}

#[test]
fn kill_dash_nine_loses_no_acknowledged_confirm() {
    let dir = tempfile::tempdir().unwrap();
    let client = reqwest::blocking::Client::builder()
        .timeout(std::time::Duration::from_secs(2))
        .build()
        .unwrap();
    let mut rng = Lcg(0xD1CE_D1CE);

    // Create the draft in a first, clean server run.
    let id;
    {
        let server = TestServer::spawn(dir.path());
        let draft: Value = client
            .post(format!("{}/api/characters", server.url))
            .json(&json!({"name": "Crashproof"}))
            .send()
            .unwrap()
            .json()
            .unwrap();
        id = draft["id"].as_str().unwrap().to_string();
    }

    let mut seq = 0u64;
    for _cycle in 0..4 {
        let mut server = TestServer::spawn(dir.path());
        let get_url = format!("{}/api/characters/{id}", server.url);

        // Ground truth after restart is whatever the disk says now.
        let current: Value = client.get(&get_url).send().unwrap().json().unwrap();
        let version = current["version"].as_u64().unwrap();

        let deadline = rng.next(120) + 40; // 40-160 ms of storm before the kill
        let storm = std::thread::spawn({
            let client = client.clone();
            let confirm_url = format!("{}/api/characters/{id}/confirm", server.url);
            let clear_url = format!("{}/api/characters/{id}/clear", server.url);
            let start_ids = decision_ids(&current);
            let mut seq = seq;
            move || {
                let mut report = StormReport {
                    seq,
                    acked_version: version,
                    acked_ids: start_ids,
                    in_flight: InFlight::None,
                };
                let mut version = version;
                loop {
                    seq += 1;
                    report.seq = seq;
                    let decision_id = format!("storm-{seq}");
                    let outcome: Result<Value, ()> = client
                        .post(&confirm_url)
                        .json(&json!({"version": version, "decision": {
                            "id": decision_id,
                            "slot": "pf2e.boosts.free",
                            "selection": {"kind": "options", "value": ["attr.str", "attr.dex", "attr.con", "attr.int"]},
                            "source": "player"
                        }}))
                        .send()
                        .map_err(drop)
                        .and_then(|r| r.json().map_err(drop));
                    match outcome {
                        Ok(o) if o["outcome"] == "confirmed" => {
                            version = o["draft"]["version"].as_u64().unwrap();
                            report.acked_version = version;
                            report.acked_ids = decision_ids(&o["draft"]);
                        }
                        Ok(_) => {}
                        Err(()) => {
                            report.in_flight = InFlight::Confirm(decision_id);
                            break;
                        }
                    }
                    let outcome: Result<Value, ()> = client
                        .post(&clear_url)
                        .json(&json!({"version": version, "slot": "pf2e.boosts.free"}))
                        .send()
                        .map_err(drop)
                        .and_then(|r| r.json().map_err(drop));
                    match outcome {
                        Ok(o) if o["outcome"] == "cleared" => {
                            version = o["draft"]["version"].as_u64().unwrap();
                            report.acked_version = version;
                            report.acked_ids = decision_ids(&o["draft"]);
                        }
                        Ok(_) => {}
                        Err(()) => {
                            report.in_flight = InFlight::Clear;
                            break;
                        }
                    }
                }
                report
            }
        });

        std::thread::sleep(std::time::Duration::from_millis(deadline));
        server.kill(); // SIGKILL, mid-storm

        let report = storm.join().unwrap();
        seq = report.seq;

        // Restart and compare the durable state against the contract.
        let server = TestServer::spawn(dir.path());
        let roster: Value = client
            .get(format!("{}/api/roster", server.url))
            .send()
            .unwrap()
            .json()
            .unwrap();
        assert!(
            roster["problems"].as_array().unwrap().is_empty(),
            "no torn or corrupt files after a kill: {:?}",
            roster["problems"]
        );
        let current: Value = client
            .get(format!("{}/api/characters/{id}", server.url))
            .send()
            .unwrap()
            .json()
            .unwrap();
        let observed_version = current["version"].as_u64().unwrap();
        let observed_ids = decision_ids(&current);

        let acked = (report.acked_version, report.acked_ids.clone());
        let with_in_flight = match &report.in_flight {
            InFlight::None => None,
            InFlight::Confirm(did) => {
                let mut ids = report.acked_ids.clone();
                ids.push(did.clone());
                ids.sort();
                Some((report.acked_version + 1, ids))
            }
            InFlight::Clear => {
                let ids = report
                    .acked_ids
                    .iter()
                    .filter(|i| !i.starts_with("storm-"))
                    .cloned()
                    .collect();
                Some((report.acked_version + 1, ids))
            }
        };
        let observed = (observed_version, observed_ids);
        assert!(
            observed == acked || Some(&observed) == with_in_flight.as_ref(),
            "durable state after kill is neither the acked state nor \
             acked+in-flight:\n observed {observed:?}\n acked {acked:?}\n \
             in-flight {:?} -> {with_in_flight:?}",
            report.in_flight
        );
    }
}

/// level-up: the four transitions under SIGKILL — start-level, a confirm
/// into the tail, finalize-pending, abandon — each leave a loadable file
/// in exactly the prior or the next state: the marker and stored sheet
/// move only together (finalize), or not at all.
#[test]
fn level_transitions_under_sigkill_are_prior_or_next_state() {
    #[path = "leveling_helpers.rs"]
    mod leveling;
    let dir = tempfile::tempdir().unwrap();
    let client = reqwest::blocking::Client::builder()
        .timeout(std::time::Duration::from_secs(2))
        .build()
        .unwrap();
    let id;
    {
        let server = TestServer::spawn(dir.path());
        id = leveling::finalized_fighter(&client, &server.url, "crash-lvl");
    }
    let invariant = |doc: &Value| {
        let marker = doc["finalized_through"].as_u64().unwrap() as usize;
        let len = doc["log"].as_array().unwrap().len();
        assert!(marker <= len);
        (marker, len, serde_json::to_string(&doc["sheet"]).unwrap())
    };
    let baseline = invariant(&leveling::read_doc(dir.path(), &id));

    for (cycle, delay_ms) in [0u64, 5].into_iter().enumerate() {
        let mut server = TestServer::spawn(dir.path());
        let fire = std::thread::spawn({
            let client = client.clone();
            let url = server.url.clone();
            let id = id.clone();
            move || {
                // Start (idempotent), then a confirm, then abandon: whatever
                // the kill interrupts, the file is one of the states. Every
                // call may die under the kill — none may panic this thread.
                let get = |path: &str| -> Option<Value> {
                    client.get(format!("{url}{path}")).send().ok()?.json().ok()
                };
                let post = |path: &str, body: Value| -> Option<Value> {
                    client
                        .post(format!("{url}{path}"))
                        .json(&body)
                        .send()
                        .ok()?
                        .json()
                        .ok()
                };
                let Some(view) = get(&format!("/api/characters/{id}")) else {
                    return;
                };
                let version = view["version"]
                    .as_u64()
                    .or_else(|| view["draft"]["version"].as_u64())
                    .unwrap_or(1);
                let _ = post(
                    &format!("/api/characters/{id}/level-up"),
                    json!({"version": version}),
                );
                let Some(view) = get(&format!("/api/characters/{id}")) else {
                    return;
                };
                if let Some(draft) = view.get("draft") {
                    if let Some(feat) = leveling::slot_view(draft, "pf2e.level.2.class-feat") {
                        if let Some(o) = feat["options"]
                            .as_array()
                            .and_then(|a| a.iter().find(|o| o["available"] == true))
                        {
                            let _ = post(
                                &format!("/api/characters/{id}/confirm"),
                                json!({"version": draft["version"], "decision": {
                                    "id": format!("crash-cf-{cycle}"), "slot": "pf2e.level.2.class-feat",
                                    "selection": {"kind": "option", "value": o["id"]}, "source": "player"
                                }}),
                            );
                        }
                    }
                    let Some(view) = get(&format!("/api/characters/{id}")) else {
                        return;
                    };
                    let v = view["draft"]["version"].as_u64().unwrap_or(1);
                    let _ = post(
                        &format!("/api/characters/{id}/level-up/abandon"),
                        json!({"version": v}),
                    );
                }
            }
        });
        std::thread::sleep(std::time::Duration::from_millis(delay_ms));
        server.kill();
        fire.join().unwrap();

        let doc = leveling::read_doc(dir.path(), &id);
        let (marker, len, sheet) = invariant(&doc);
        // Never a moved marker with the old sheet, never a pending tail
        // with a re-derived sheet: the stored sheet is always the
        // baseline's (only finalize-pending would move it, and none ran).
        assert_eq!(
            marker, baseline.0,
            "start/confirm/abandon never move the marker"
        );
        assert_eq!(
            sheet, baseline.2,
            "the stored sheet never moves outside finalize"
        );
        assert!(len >= marker);
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
        // Leave the character clean for the next cycle.
        let view = leveling::character(&client, &server.url, &id);
        if view["state"] == "leveling" {
            let v = view["draft"]["version"].as_u64().unwrap();
            let (status, _) = leveling::post_json(
                &client,
                &server.url,
                &format!("/api/characters/{id}/level-up/abandon"),
                json!({"version": v}),
            );
            assert_eq!(status, 200);
        }
    }

    // Finalize-pending under SIGKILL, once per remaining level (2 and 3):
    // either the prior file (marker + sheet as before) or the leveled file
    // (marker at the log's end and a re-derived sheet) — never a hybrid.
    // A cycle that did not land is finished by an ordinary retry, so each
    // cycle ends one level higher.
    for (cycle, delay_ms) in [0u64, 4].into_iter().enumerate() {
        let level = cycle as u64 + 2;
        let mut server = TestServer::spawn(dir.path());
        let before = invariant(&leveling::read_doc(dir.path(), &id));
        let pending = leveling::start_level(&client, &server.url, &id);
        let mut draft = pending;
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
            let o = slot["options"]
                .as_array()
                .unwrap()
                .iter()
                .find(|o| o["available"] == true)
                .unwrap()["id"]
                .as_str()
                .unwrap()
                .to_string();
            n += 1;
            let c = leveling::confirm_option(
                &client,
                &server.url,
                &id,
                draft["version"].as_u64().unwrap(),
                &format!("fin-{cycle}-{n}"),
                &slot_id,
                &o,
            );
            assert_eq!(c["outcome"], "confirmed", "{c}");
            draft = c["draft"].clone();
        }
        let version = draft["version"].as_u64().unwrap();
        let fire = std::thread::spawn({
            let client = client.clone();
            let url = server.url.clone();
            let id = id.clone();
            move || {
                // May die under the kill — must not panic this thread.
                let _ = client
                    .post(format!("{url}/api/characters/{id}/finalize"))
                    .json(&json!({"version": version}))
                    .send();
            }
        });
        std::thread::sleep(std::time::Duration::from_millis(delay_ms));
        server.kill();
        fire.join().unwrap();
        let doc = leveling::read_doc(dir.path(), &id);
        let (marker, len, sheet) = invariant(&doc);
        let server = TestServer::spawn(dir.path());
        if marker == len {
            assert_ne!(
                sheet, before.2,
                "finalized: marker and sheet moved together"
            );
        } else {
            assert_eq!(
                sheet, before.2,
                "not finalized: the stored sheet is untouched"
            );
            assert_eq!(marker, before.0);
            let view = leveling::character(&client, &server.url, &id);
            let v = view["draft"]["version"].as_u64().unwrap();
            let (status, out) = leveling::post_json(
                &client,
                &server.url,
                &format!("/api/characters/{id}/finalize"),
                json!({"version": v}),
            );
            assert_eq!(status, 200, "{out}");
            assert_eq!(out["outcome"], "finalized");
        }
        let view = leveling::character(&client, &server.url, &id);
        assert!(
            view["sheet"]["summary"][0]
                .as_str()
                .unwrap()
                .contains(&format!("Fighter {level}")),
            "{}",
            view["sheet"]["summary"][0]
        );
    }
    let (code, output) = TestServer::run_verify(dir.path(), &[]);
    assert_eq!(code, 0, "{output}");
}
