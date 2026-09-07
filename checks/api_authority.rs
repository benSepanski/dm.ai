//! Server authority: a raw HTTP confirm of an illegal decision (bypassing
//! the wizard UI entirely) is rejected and appends nothing, and finalize
//! is blocked with every gap listed while the checklist is non-empty.

use checks::TestServer;
use serde_json::{json, Value};

fn confirm_raw(client: &reqwest::blocking::Client, url: &str, id: &str, body: Value) -> Value {
    client
        .post(format!("{url}/api/characters/{id}/confirm"))
        .json(&body)
        .send()
        .unwrap()
        .json()
        .unwrap()
}

#[test]
fn illegal_confirms_are_rejected_and_append_nothing() {
    let dir = tempfile::tempdir().unwrap();
    let server = TestServer::spawn(dir.path());
    let client = reqwest::blocking::Client::new();
    let draft: Value = client
        .post(format!("{}/api/characters", server.url))
        .json(&json!({"name": "Authority"}))
        .send()
        .unwrap()
        .json()
        .unwrap();
    let id = draft["id"].as_str().unwrap();
    let mut version = draft["version"].as_u64().unwrap();

    // 1. Locked slot: a heritage before any ancestry exists.
    let outcome = confirm_raw(
        &client,
        &server.url,
        id,
        json!({"version": version, "decision": {
            "id": "x1", "slot": "pf2e.ancestry.heritage",
            "selection": {"kind": "option", "value": "heritage.dwarf.rock"},
            "source": "player"
        }}),
    );
    assert_eq!(outcome["outcome"], "rejected");
    assert_eq!(
        outcome["draft"]["version"].as_u64().unwrap(),
        version,
        "a rejection must not change the draft"
    );

    // Choose an ancestry legitimately.
    let outcome = confirm_raw(
        &client,
        &server.url,
        id,
        json!({"version": version, "decision": {
            "id": "x2", "slot": "pf2e.ancestry",
            "selection": {"kind": "option", "value": "ancestry.elf"},
            "source": "player"
        }}),
    );
    assert_eq!(outcome["outcome"], "confirmed");
    version = outcome["draft"]["version"].as_u64().unwrap();

    // 2. Cross-catalog: a dwarf heritage on an elf.
    let outcome = confirm_raw(
        &client,
        &server.url,
        id,
        json!({"version": version, "decision": {
            "id": "x3", "slot": "pf2e.ancestry.heritage",
            "selection": {"kind": "option", "value": "heritage.dwarf.rock"},
            "source": "player"
        }}),
    );
    assert_eq!(outcome["outcome"], "rejected");
    let reasons = outcome["reasons"].as_array().unwrap();
    assert!(!reasons.is_empty());
    assert!(reasons[0]["message"]
        .as_str()
        .unwrap()
        .contains("does not belong"));

    // 3. Unknown option ID.
    let outcome = confirm_raw(
        &client,
        &server.url,
        id,
        json!({"version": version, "decision": {
            "id": "x4", "slot": "pf2e.ancestry.heritage",
            "selection": {"kind": "option", "value": "heritage.totally-fake"},
            "source": "player"
        }}),
    );
    assert_eq!(outcome["outcome"], "rejected");

    // 4. An unavailable option: Adapted Cantrip needs a spellcasting class
    // feature no Fighter has — the server refuses it even though a raw
    // client can name it.
    let outcome = confirm_raw(
        &client,
        &server.url,
        id,
        json!({"version": version, "decision": {
            "id": "x5", "slot": "pf2e.ancestry.feat",
            "selection": {"kind": "option", "value": "feat.ancestry.human.adapted-cantrip"},
            "source": "player"
        }}),
    );
    assert_eq!(outcome["outcome"], "rejected");

    // The draft is exactly one decision (plus the name) further along.
    let character: Value = client
        .get(format!("{}/api/characters/{id}", server.url))
        .send()
        .unwrap()
        .json()
        .unwrap();
    assert_eq!(character["version"].as_u64().unwrap(), version);
}

/// Quick-build server authority: raw requests the planner cannot honor are
/// rejected and append nothing, and both quick-build routes are wizard
/// writes under the version guard.
#[test]
fn raw_quick_build_requests_are_validated_and_append_nothing() {
    let dir = tempfile::tempdir().unwrap();
    let server = TestServer::spawn(dir.path());
    let client = reqwest::blocking::Client::new();

    // 1. A malformed request ID (path-traversal shaped) is refused outright
    // and creates no file.
    let response = client
        .post(format!("{}/api/characters/quick-build", server.url))
        .json(&json!({ "request_id": "../evil", "name": null }))
        .send()
        .unwrap();
    assert_eq!(response.status().as_u16(), 422);
    let response = client
        .post(format!("{}/api/characters/quick-build", server.url))
        .json(&json!({ "request_id": "", "name": null }))
        .send()
        .unwrap();
    assert_eq!(response.status().as_u16(), 422);
    let roster: Value = client
        .get(format!("{}/api/roster", server.url))
        .send()
        .unwrap()
        .json()
        .unwrap();
    assert!(
        roster["entries"].as_array().unwrap().is_empty(),
        "a rejected quick-build must append nothing"
    );

    // 2. A legitimate quick build lands review-ready, NOT finalized; the
    // server computed the expansion natively (nothing illegal persisted).
    let built: Value = client
        .post(format!("{}/api/characters/quick-build", server.url))
        .json(&json!({ "request_id": "auth-qb-1", "name": null }))
        .send()
        .unwrap()
        .json()
        .unwrap();
    let id = built["draft"]["id"].as_str().unwrap().to_string();
    let version = built["draft"]["version"].as_u64().unwrap();
    assert!(built["draft"]["projection"]["can_finalize"]
        .as_bool()
        .unwrap());
    let view: Value = client
        .get(format!("{}/api/characters/{id}", server.url))
        .send()
        .unwrap()
        .json()
        .unwrap();
    assert_eq!(
        view["state"], "draft",
        "quick build never finalizes on its own"
    );

    // 3. A malformed fill request is refused; fill on a finalized character
    // is refused; neither writes a byte.
    let response = client
        .post(format!("{}/api/characters/{id}/fill-remaining", server.url))
        .json(&json!({ "request_id": "bad id!", "version": version }))
        .send()
        .unwrap();
    assert_eq!(response.status().as_u16(), 422);
    let finalized: Value = client
        .post(format!("{}/api/characters/{id}/finalize", server.url))
        .json(&json!({ "version": version }))
        .send()
        .unwrap()
        .json()
        .unwrap();
    assert_eq!(finalized["outcome"], "finalized", "{finalized}");
    let before = std::fs::read(dir.path().join(format!("characters/{id}.json"))).unwrap();
    let response = client
        .post(format!("{}/api/characters/{id}/fill-remaining", server.url))
        .json(&json!({ "request_id": "auth-fill-1", "version": version + 1 }))
        .send()
        .unwrap();
    assert_eq!(response.status().as_u16(), 422);
    let after = std::fs::read(dir.path().join(format!("characters/{id}.json"))).unwrap();
    assert_eq!(before, after, "a refused fill must append nothing");
}

/// Quick-build routes are wizard writes for the version guard: a draft on
/// an older known rules-data version rejects fill-remaining with the flag
/// (409) and writes nothing — the --extra-known-versions fixture pattern
/// from checks/version_guard.rs.
#[test]
fn fill_remaining_is_rejected_on_a_version_flagged_draft() {
    const TEST_VERSION: &str = "pf2e-pc.0.0.1-test";
    let dir = tempfile::tempdir().unwrap();
    let client = reqwest::blocking::Client::new();

    // Build a draft against current data, then pin its file to a fabricated
    // prior version.
    let id;
    {
        let server = TestServer::spawn(dir.path());
        let draft: Value = client
            .post(format!("{}/api/characters", server.url))
            .json(&json!({ "name": "Flagged" }))
            .send()
            .unwrap()
            .json()
            .unwrap();
        id = draft["id"].as_str().unwrap().to_string();
    }
    let path = dir.path().join(format!("characters/{id}.json"));
    let mut doc: Value = serde_json::from_str(&std::fs::read_to_string(&path).unwrap()).unwrap();
    doc["rules_version"] = Value::from(TEST_VERSION);
    std::fs::write(&path, serde_json::to_string_pretty(&doc).unwrap()).unwrap();
    let extra = dir.path().join("extra-known-versions.json");
    std::fs::write(
        &extra,
        json!({ "pf2e": { "versions": { TEST_VERSION: [] } } }).to_string(),
    )
    .unwrap();

    let server = TestServer::spawn_with_args(
        dir.path(),
        &["--extra-known-versions", extra.to_str().unwrap()],
    );
    let before = std::fs::read(&path).unwrap();
    let response = client
        .post(format!("{}/api/characters/{id}/fill-remaining", server.url))
        .json(&json!({ "request_id": "flagged-fill-1", "version": 1 }))
        .send()
        .unwrap();
    assert_eq!(
        response.status().as_u16(),
        409,
        "fill-remaining is a wizard write under the version guard"
    );
    let body: Value = response.json().unwrap();
    assert_eq!(body["status"]["status"], "older_known");
    assert_eq!(
        before,
        std::fs::read(&path).unwrap(),
        "a rejected wizard write must append nothing"
    );
}

#[test]
fn finalize_is_blocked_while_the_checklist_is_nonempty() {
    let dir = tempfile::tempdir().unwrap();
    let server = TestServer::spawn(dir.path());
    let client = reqwest::blocking::Client::new();
    let draft: Value = client
        .post(format!("{}/api/characters", server.url))
        .json(&json!({"name": "Blocked"}))
        .send()
        .unwrap()
        .json()
        .unwrap();
    let id = draft["id"].as_str().unwrap();
    let version = draft["version"].as_u64().unwrap();

    let outcome: Value = client
        .post(format!("{}/api/characters/{id}/finalize", server.url))
        .json(&json!({"version": version}))
        .send()
        .unwrap()
        .json()
        .unwrap();
    assert_eq!(outcome["outcome"], "blocked");
    let reasons = outcome["reasons"].as_array().unwrap();
    assert!(
        reasons.len() >= 4,
        "every gap is listed (ancestry, background, class, boosts…): {reasons:?}"
    );
    // Still a draft afterwards.
    let character: Value = client
        .get(format!("{}/api/characters/{id}", server.url))
        .send()
        .unwrap()
        .json()
        .unwrap();
    assert_eq!(character["state"], "draft");
}

// ---- level-up route authority (level-up architecture) ----

#[path = "leveling_helpers.rs"]
mod leveling;
use leveling::{
    character, complete_level, confirm_option, finalized_fighter, post_json, slot_view, start_level,
};

/// Every refusal the pending-level representation demands, through the
/// real server, each writing nothing: a second start returns the existing
/// tail; start on a creation draft and at the cap refuses; a raw advance
/// confirm, a second advance in a tail, an amend/clear below the marker,
/// and fill-remaining during a tail all refuse; a confirm after abandon or
/// finalize is rejected even when its decision ID once existed; draft
/// versions never reset across abandon.
#[test]
fn level_up_routes_refuse_everything_below_the_marker_and_out_of_order() {
    let dir = tempfile::tempdir().unwrap();
    let server = TestServer::spawn(dir.path());
    let client = reqwest::blocking::Client::new();
    let url = server.url.as_str();

    // Start on a creation draft: refused.
    let (_, draft) = post_json(
        &client,
        url,
        "/api/characters",
        json!({"name": "Unfinished"}),
    );
    let draft_id = draft["id"].as_str().unwrap();
    let (status, body) = post_json(
        &client,
        url,
        &format!("/api/characters/{draft_id}/level-up"),
        json!({"version": 1}),
    );
    assert_eq!(status, 422, "{body}");

    let id = finalized_fighter(&client, url, "auth-lvl");
    let pending = start_level(&client, url, &id);
    let started_version = pending["version"].as_u64().unwrap();

    // A second start (any version) lands in the existing pending level.
    let (status, again) = post_json(
        &client,
        url,
        &format!("/api/characters/{id}/level-up"),
        json!({"version": 999}),
    );
    assert_eq!(status, 200, "{again}");
    assert_eq!(again["outcome"], "started");
    assert_eq!(
        again["draft"]["version"].as_u64().unwrap(),
        started_version,
        "no second advance"
    );

    // A raw advance confirm and a second advance in the tail: refused.
    for slot in ["pf2e.level.3.advance", "pf2e.level.2.advance"] {
        let (status, body) = post_json(
            &client,
            url,
            &format!("/api/characters/{id}/confirm"),
            json!({"version": started_version, "decision": {
                "id": format!("raw-{slot}"), "slot": slot,
                "selection": {"kind": "option", "value": "advance.3"},
                "source": "player"
            }}),
        );
        assert_eq!(status, 422, "{slot}: {body}");
    }

    // Below the marker: confirm, amend, clear all refuse.
    let (status, body) = post_json(
        &client,
        url,
        &format!("/api/characters/{id}/confirm"),
        json!({"version": started_version, "decision": {
            "id": "below-confirm", "slot": "pf2e.ancestry",
            "selection": {"kind": "option", "value": "ancestry.elf"}, "source": "player"
        }}),
    );
    assert_eq!(status, 422, "{body}");
    let (status, body) = post_json(
        &client,
        url,
        &format!("/api/characters/{id}/amend"),
        json!({"version": started_version, "decision": {
            "id": "below-amend", "slot": "pf2e.ancestry",
            "selection": {"kind": "option", "value": "ancestry.elf"}, "source": "player"
        }}),
    );
    assert_eq!(status, 422, "{body}");
    let (status, body) = post_json(
        &client,
        url,
        &format!("/api/characters/{id}/clear"),
        json!({"version": started_version, "slot": "pf2e.ancestry"}),
    );
    assert_eq!(status, 422, "{body}");

    // Fill-remaining during a tail: refused.
    let (status, body) = post_json(
        &client,
        url,
        &format!("/api/characters/{id}/fill-remaining"),
        json!({"request_id": "fill-in-tail", "version": started_version}),
    );
    assert_eq!(status, 422, "{body}");

    // Confirm a tail choice, then abandon: the version keeps climbing, and
    // the confirmed decision's ID is no longer a success.
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
        started_version,
        "tail-cf",
        "pf2e.level.2.class-feat",
        &option,
    );
    assert_eq!(confirmed["outcome"], "confirmed", "{confirmed}");
    let version_after_confirm = confirmed["draft"]["version"].as_u64().unwrap();
    let (status, abandoned) = post_json(
        &client,
        url,
        &format!("/api/characters/{id}/level-up/abandon"),
        json!({"version": version_after_confirm}),
    );
    assert_eq!(status, 200, "{abandoned}");
    assert_eq!(abandoned["outcome"], "abandoned");
    let after_abandon = abandoned["character"]["version"].as_u64().unwrap();
    assert!(
        after_abandon > version_after_confirm,
        "versions are monotonic across abandon ({after_abandon} > {version_after_confirm})"
    );
    // The stale tab's retry (same decision ID, old version) is refused —
    // the finalized-no-tail refusal precedes the ID-present success path.
    let retry = confirm_option(
        &client,
        url,
        &id,
        version_after_confirm,
        "tail-cf",
        "pf2e.level.2.class-feat",
        &option,
    );
    assert!(
        retry["outcome"].is_null(),
        "a confirm after abandon is refused, not confirmed: {retry}"
    );
    // Abandon with nothing pending: refused.
    let (status, body) = post_json(
        &client,
        url,
        &format!("/api/characters/{id}/level-up/abandon"),
        json!({"version": after_abandon}),
    );
    assert_eq!(status, 422, "{body}");

    // Level to the cap; then start refuses, typed; a retried tail confirm
    // after finalize is refused too.
    let view = complete_level(&client, url, &id);
    assert_eq!(view["state"], "finalized");
    let view = complete_level(&client, url, &id);
    assert!(view["next_level"].is_null(), "at the cap: {view}");
    let (status, body) = post_json(
        &client,
        url,
        &format!("/api/characters/{id}/level-up"),
        json!({"version": view["version"]}),
    );
    assert_eq!(status, 422, "{body}");
    assert!(body["message"].as_str().unwrap().contains("higher levels"));
    let retry = confirm_option(
        &client,
        url,
        &id,
        1,
        format!("{id}-lvl-1-pf2e.level.3.general-feat").as_str(),
        "pf2e.level.3.general-feat",
        "feat.general.toughness",
    );
    assert!(
        retry["outcome"].is_null(),
        "confirm after finalize is refused: {retry}"
    );
    let final_view = character(&client, url, &id);
    assert!(final_view["sheet"]["summary"][0]
        .as_str()
        .unwrap()
        .contains("Fighter 3"));
}

// ---- dnd-dice: the roll route and the origin rules ------------------------

/// Shared 5.5e setup: a declared campaign, a draft, the rolling method.
fn rolling_draft(client: &reqwest::blocking::Client, url: &str, name: &str) -> (String, u64) {
    let draft: Value = client
        .post(format!("{url}/api/characters"))
        .json(&json!({"name": name}))
        .send()
        .unwrap()
        .json()
        .unwrap();
    let id = draft["id"].as_str().unwrap().to_string();
    let version = draft["version"].as_u64().unwrap();
    let outcome = confirm_raw(
        client,
        url,
        &id,
        json!({"version": version, "decision": {
            "id": format!("{name}-method"), "slot": "dnd5e.scores.method",
            "selection": {"kind": "option", "value": "method.roll"},
            "source": "player"
        }}),
    );
    assert_eq!(outcome["outcome"], "confirmed", "{outcome}");
    (id, outcome["draft"]["version"].as_u64().unwrap())
}

fn roll_raw(client: &reqwest::blocking::Client, url: &str, id: &str, body: Value) -> (u16, Value) {
    let response = client
        .post(format!("{url}/api/characters/{id}/roll"))
        .json(&body)
        .send()
        .unwrap();
    let status = response.status().as_u16();
    (status, response.json().unwrap_or(Value::Null))
}

fn amend_raw(client: &reqwest::blocking::Client, url: &str, id: &str, body: Value) -> (u16, Value) {
    let response = client
        .post(format!("{url}/api/characters/{id}/amend"))
        .json(&body)
        .send()
        .unwrap();
    let status = response.status().as_u16();
    (status, response.json().unwrap_or(Value::Null))
}

fn slot_of(draft: &Value, slot: &str) -> Value {
    draft["projection"]["steps"]
        .as_array()
        .unwrap()
        .iter()
        .flat_map(|s| s["slots"].as_array().unwrap().iter())
        .find(|s| s["id"] == slot)
        .cloned()
        .unwrap_or(Value::Null)
}

fn history_badges(draft: &Value) -> Vec<String> {
    slot_of(draft, "dnd5e.scores.roll")["options"]
        .as_array()
        .map(|o| {
            o.iter()
                .map(|x| x["badge"].as_str().unwrap_or("").to_string())
                .collect()
        })
        .unwrap_or_default()
}

fn entered(groups: Vec<Vec<u8>>) -> Value {
    json!({"groups": groups, "origin": "entered"})
}

fn six_groups(face: u8) -> Vec<Vec<u8>> {
    vec![vec![face; 4]; 6]
}

#[test]
fn roll_route_records_app_dice_and_refuses_forged_origins() {
    let dir = tempfile::tempdir().unwrap();
    checks::declare_campaign(dir.path(), "dnd5e");
    let server = TestServer::spawn(dir.path());
    let client = reqwest::blocking::Client::new();
    let url = &server.url;
    let (id, version) = rolling_draft(&client, url, "Ysolde");
    let file = dir.path().join(format!("characters/{id}.json"));

    // Before any roll: the roll slot is open and empty, the assignment
    // locked behind it.
    let view: Value = client
        .get(format!("{url}/api/characters/{id}"))
        .send()
        .unwrap()
        .json()
        .unwrap();
    assert_eq!(slot_of(&view, "dnd5e.scores.roll")["status"], "empty");
    assert_eq!(slot_of(&view, "dnd5e.scores.roll")["kind"]["kind"], "roll");
    assert_eq!(slot_of(&view, "dnd5e.scores.assign")["status"], "locked");

    // 1. The app rolls: one set, tagged rolled, on a d6 shape.
    let (status, outcome) = roll_raw(
        &client,
        url,
        &id,
        json!({"slot": "dnd5e.scores.roll", "version": version, "decision_id": "r1"}),
    );
    assert_eq!(status, 200, "{outcome}");
    assert_eq!(outcome["outcome"], "confirmed", "{outcome}");
    let draft = &outcome["draft"];
    assert_eq!(history_badges(draft), vec!["rolled"]);
    let v1 = draft["version"].as_u64().unwrap();
    let doc: Value = serde_json::from_str(&std::fs::read_to_string(&file).unwrap()).unwrap();
    let roll = doc["log"]
        .as_array()
        .unwrap()
        .iter()
        .find(|d| d["slot"] == "dnd5e.scores.roll")
        .unwrap();
    assert_eq!(roll["selection"]["kind"], "rolled");
    let sets = roll["selection"]["value"].as_array().unwrap();
    assert_eq!(sets.len(), 1);
    assert_eq!(sets[0]["origin"], "app");
    let groups = sets[0]["groups"].as_array().unwrap();
    assert_eq!(groups.len(), 6);
    for g in groups {
        let faces = g.as_array().unwrap();
        assert_eq!(faces.len(), 4);
        assert!(faces.iter().all(|f| (1..=6).contains(&f.as_u64().unwrap())));
    }

    // 2. A retry with the same decision id and the stale version returns
    // the recorded roll, appends nothing, bumps nothing.
    let (status, retry) = roll_raw(
        &client,
        url,
        &id,
        json!({"slot": "dnd5e.scores.roll", "version": version, "decision_id": "r1"}),
    );
    assert_eq!(status, 200);
    assert_eq!(retry["outcome"], "confirmed");
    assert_eq!(retry["draft"]["version"].as_u64().unwrap(), v1);
    assert_eq!(history_badges(&retry["draft"]).len(), 1);

    // 3. A second roll appends: two sets, the first superseded.
    let (_, second) = roll_raw(
        &client,
        url,
        &id,
        json!({"slot": "dnd5e.scores.roll", "version": v1, "decision_id": "r2"}),
    );
    assert_eq!(second["outcome"], "confirmed", "{second}");
    assert_eq!(history_badges(&second["draft"]), vec!["rolled", "rolled"]);
    let history = slot_of(&second["draft"], "dnd5e.scores.roll")["options"].clone();
    assert_eq!(history[0]["available"], false);
    assert_eq!(history[1]["available"], true);
    let v2 = second["draft"]["version"].as_u64().unwrap();

    // 4. A client claiming the app's tag is refused typed; the file is
    // byte-identical.
    let before = std::fs::read(&file).unwrap();
    let (status, refused) = amend_raw(
        &client,
        url,
        &id,
        json!({"version": v2, "decision": {
            "id": "forged", "slot": "dnd5e.scores.roll",
            "selection": {"kind": "rolled", "value": [{"groups": six_groups(6), "origin": "app"}]},
            "source": "player"
        }}),
    );
    assert_eq!(status, 422, "{refused}");
    assert!(refused["message"].as_str().unwrap().contains("roll route"));
    assert_eq!(std::fs::read(&file).unwrap(), before);

    // 5. Entered dice append onto the stored history (the request carries
    // only the new set; M + N = 3), tagged entered.
    let (status, appended) = amend_raw(
        &client,
        url,
        &id,
        json!({"version": v2, "decision": {
            "id": "e1", "slot": "dnd5e.scores.roll",
            "selection": {"kind": "rolled", "value": [entered(vec![
                vec![6, 5, 3, 1], vec![4, 4, 4, 1], vec![5, 4, 3, 3],
                vec![4, 3, 3, 2], vec![3, 3, 3, 1], vec![6, 1, 1, 1]
            ])]},
            "source": "player"
        }}),
    );
    assert_eq!(status, 200);
    assert_eq!(appended["outcome"], "confirmed", "{appended}");
    assert_eq!(
        history_badges(&appended["draft"]),
        vec!["rolled", "rolled", "entered"]
    );
    let v3 = appended["draft"]["version"].as_u64().unwrap();
    // Two sets at once keep their order, both entered.
    let (_, two) = amend_raw(
        &client,
        url,
        &id,
        json!({"version": v3, "decision": {
            "id": "e2", "slot": "dnd5e.scores.roll",
            "selection": {"kind": "rolled", "value": [
                entered(six_groups(2)), entered(six_groups(3))
            ]},
            "source": "player"
        }}),
    );
    assert_eq!(two["outcome"], "confirmed", "{two}");
    assert_eq!(history_badges(&two["draft"]).len(), 5);
    let v4 = two["draft"]["version"].as_u64().unwrap();

    // 6. An out-of-shape entry is rejected, nothing appended.
    let (status, bad) = amend_raw(
        &client,
        url,
        &id,
        json!({"version": v4, "decision": {
            "id": "e3", "slot": "dnd5e.scores.roll",
            "selection": {"kind": "rolled", "value": [entered(vec![
                vec![6, 5, 3, 7], vec![4, 4, 4, 1], vec![5, 4, 3, 3],
                vec![4, 3, 3, 2], vec![3, 3, 3, 1], vec![6, 1, 1, 1]
            ])]},
            "source": "player"
        }}),
    );
    assert_eq!(status, 200);
    assert_eq!(bad["outcome"], "rejected", "{bad}");
    assert!(bad["reasons"][0]["message"]
        .as_str()
        .unwrap()
        .contains("6-sided"));
    assert_eq!(history_badges(&bad["draft"]).len(), 5);

    // 7. The roll route refuses a non-roll slot, a hidden slot, and a
    // stale version; nothing is written.
    let before = std::fs::read(&file).unwrap();
    let (status, not_dice) = roll_raw(
        &client,
        url,
        &id,
        json!({"slot": "dnd5e.scores.method", "version": v4, "decision_id": "r3"}),
    );
    assert_eq!(status, 422, "{not_dice}");
    assert!(not_dice["message"]
        .as_str()
        .unwrap()
        .contains("record dice"));
    let (status, absent) = roll_raw(
        &client,
        url,
        &id,
        json!({"slot": "dnd5e.level.2.hit-die", "version": v4, "decision_id": "r4"}),
    );
    assert_eq!(status, 422, "{absent}");
    let (status, stale) = roll_raw(
        &client,
        url,
        &id,
        json!({"slot": "dnd5e.scores.roll", "version": v4 - 1, "decision_id": "r5"}),
    );
    assert_eq!(status, 200);
    assert_eq!(stale["outcome"], "conflict", "{stale}");
    assert_eq!(std::fs::read(&file).unwrap(), before);

    // 8. A finalized character refuses the roll route.
    let (status, mint) = {
        let response = client
            .post(format!("{url}/api/characters/random-mint"))
            .json(&json!({"request_id": "mint-for-roll", "class_id": null, "name": "Done"}))
            .send()
            .unwrap();
        (
            response.status().as_u16(),
            response.json::<Value>().unwrap(),
        )
    };
    assert_eq!(status, 200, "{mint}");
    let done = mint["draft"]["id"].as_str().unwrap().to_string();
    let dv = mint["draft"]["version"].as_u64().unwrap();
    let fin: Value = client
        .post(format!("{url}/api/characters/{done}/finalize"))
        .json(&json!({"version": dv}))
        .send()
        .unwrap()
        .json()
        .unwrap();
    assert_eq!(fin["outcome"], "finalized", "{fin}");
    let (status, locked) = roll_raw(
        &client,
        url,
        &done,
        json!({"slot": "dnd5e.scores.roll", "version": dv + 1, "decision_id": "r6"}),
    );
    assert_eq!(status, 422, "{locked}");
}

/// Seeds stay at draw time: the same seed, character, and decision id
/// reproduce the faces across two copies of a campaign; a different seed
/// or the operating system differ; the campaign view says when dice are
/// seeded; no seed reaches any file.
#[test]
fn seeded_dice_reproduce_across_copies_and_wear_the_badge() {
    let client = reqwest::blocking::Client::new();
    let base = tempfile::tempdir().unwrap();
    checks::declare_campaign(base.path(), "dnd5e");
    let (id, version) = {
        let server = TestServer::spawn(base.path());
        rolling_draft(&client, &server.url, "Reproducible")
    };
    // Three copies of the same campaign: the same character id everywhere.
    let copy = |name: &str| {
        let dir = tempfile::tempdir().unwrap();
        let _ = name;
        for entry in std::fs::read_dir(base.path()).unwrap().flatten() {
            let path = entry.path();
            let target = dir.path().join(entry.file_name());
            if path.is_dir() {
                std::fs::create_dir_all(&target).unwrap();
                for f in std::fs::read_dir(&path).unwrap().flatten() {
                    std::fs::copy(f.path(), target.join(f.file_name())).unwrap();
                }
            } else if entry.file_name() != "server.lock" && entry.file_name() != "server.lock.stale"
            {
                std::fs::copy(&path, &target).unwrap();
            }
        }
        dir
    };
    let second_faces: std::cell::RefCell<Option<Value>> = std::cell::RefCell::new(None);
    let faces_under = |dir: &std::path::Path, args: &[&str]| -> (bool, Value) {
        let server = TestServer::spawn_with_args(dir, args);
        let campaign: Value = client
            .get(format!("{}/api/campaign", server.url))
            .send()
            .unwrap()
            .json()
            .unwrap();
        let (status, outcome) = roll_raw(
            &client,
            &server.url,
            &id,
            json!({"slot": "dnd5e.scores.roll", "version": version, "decision_id": "rep-r1"}),
        );
        assert_eq!(status, 200, "{outcome}");
        assert_eq!(outcome["outcome"], "confirmed", "{outcome}");
        let doc: Value = serde_json::from_str(
            &std::fs::read_to_string(dir.join(format!("characters/{id}.json"))).unwrap(),
        )
        .unwrap();
        let faces = doc["log"]
            .as_array()
            .unwrap()
            .iter()
            .find(|d| d["slot"] == "dnd5e.scores.roll")
            .unwrap()["selection"]["value"][0]["groups"]
            .clone();
        if args == ["--dice-seed", "7"] && second_faces.borrow().is_none() {
            // In the first seeded copy, a second roll under a new id.
            let v = outcome["draft"]["version"].as_u64().unwrap();
            let (_, again) = roll_raw(
                &client,
                &server.url,
                &id,
                json!({"slot": "dnd5e.scores.roll", "version": v, "decision_id": "rep-r2"}),
            );
            assert_eq!(again["outcome"], "confirmed", "{again}");
            let doc: Value = serde_json::from_str(
                &std::fs::read_to_string(dir.join(format!("characters/{id}.json"))).unwrap(),
            )
            .unwrap();
            let sets = doc["log"]
                .as_array()
                .unwrap()
                .iter()
                .find(|d| d["slot"] == "dnd5e.scores.roll")
                .unwrap()["selection"]["value"]
                .clone();
            assert_eq!(sets.as_array().unwrap().len(), 2);
            *second_faces.borrow_mut() = Some(sets[1]["groups"].clone());
        }
        (campaign["seeded_dice"].as_bool().unwrap(), faces)
    };
    let a = copy("a");
    let b = copy("b");
    let c = copy("c");
    let d = copy("d");
    let (badge_a, faces_a) = faces_under(a.path(), &["--dice-seed", "7"]);
    let second_faces = second_faces.borrow().clone();
    let (badge_b, faces_b) = faces_under(b.path(), &["--dice-seed", "7"]);
    let (badge_c, faces_c) = faces_under(c.path(), &["--dice-seed", "8"]);
    let (badge_d, faces_d) = faces_under(d.path(), &[]);
    assert!(badge_a && badge_b && badge_c, "seeded servers say so");
    assert!(!badge_d, "an unseeded server wears no badge");
    assert_eq!(
        faces_a, faces_b,
        "same seed, character, decision: same faces"
    );
    assert_ne!(faces_a, faces_c, "a different seed differs");
    assert_ne!(faces_a, faces_d, "the operating system differs");
    // A different decision id under the same seed is an independent stream
    // (rolled in copy a's session, above).
    assert_ne!(
        second_faces.as_ref().expect("a second roll in copy a"),
        &faces_a
    );
    // No seed reaches any file written under the flag.
    for dir in [a.path(), b.path(), c.path()] {
        for entry in walk(dir) {
            let text = std::fs::read_to_string(&entry).unwrap_or_default();
            assert!(
                !text.to_lowercase().contains("seed"),
                "{} mentions a seed",
                entry.display()
            );
        }
    }
    // The seeded campaign verifies clean.
    let (code, out) = TestServer::run_verify(a.path(), &[]);
    assert_eq!(code, 0, "{out}");
}

fn walk(dir: &std::path::Path) -> Vec<std::path::PathBuf> {
    let mut out = Vec::new();
    let mut stack = vec![dir.to_path_buf()];
    while let Some(d) = stack.pop() {
        for entry in std::fs::read_dir(&d).unwrap().flatten() {
            let p = entry.path();
            if p.is_dir() {
                stack.push(p);
            } else {
                out.push(p);
            }
        }
    }
    out
}
