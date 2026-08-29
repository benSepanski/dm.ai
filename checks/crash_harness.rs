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
