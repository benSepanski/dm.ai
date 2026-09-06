//! The campaign declaration and the system-before-version rule
//! (chargen-dnd architecture, "Campaign declaration", "System before
//! version", "Schema v5", and "Attribution follows the binary" rows).
//!
//! A campaign plays one game. An undeclared empty directory serves only
//! the shell and the declare route; declare is create-exclusive and
//! survives SIGKILL untorn; the game can change only while the campaign is
//! empty (trash and quarantine count); an undeclared directory holding
//! characters is Pathfinder 2e and never gets a declaration written; a
//! corrupt declaration refuses typed; a file from another game is refused
//! in place — reported, never loaded, never written, never moved.

use checks::TestServer;
use serde_json::{json, Value};

fn client() -> reqwest::blocking::Client {
    reqwest::blocking::Client::builder()
        .timeout(std::time::Duration::from_secs(5))
        .build()
        .unwrap()
}

fn get(client: &reqwest::blocking::Client, url: &str) -> (u16, Value) {
    let response = client.get(url).send().unwrap();
    let status = response.status().as_u16();
    (status, response.json().unwrap_or(Value::Null))
}

fn post(client: &reqwest::blocking::Client, url: &str, body: Value) -> (u16, Value) {
    let response = client.post(url).json(&body).send().unwrap();
    let status = response.status().as_u16();
    (status, response.json().unwrap_or(Value::Null))
}

fn campaign(client: &reqwest::blocking::Client, url: &str) -> Value {
    get(client, &format!("{url}/api/campaign")).1
}

fn declare(client: &reqwest::blocking::Client, url: &str, system: &str) -> (u16, Value) {
    post(
        client,
        &format!("{url}/api/campaign"),
        json!({ "system": system }),
    )
}

fn roster(client: &reqwest::blocking::Client, url: &str) -> Value {
    get(client, &format!("{url}/api/roster")).1
}

fn create(client: &reqwest::blocking::Client, url: &str, name: &str) -> (u16, Value) {
    post(
        client,
        &format!("{url}/api/characters"),
        json!({ "name": name }),
    )
}

fn declaration_path(dir: &std::path::Path) -> std::path::PathBuf {
    dir.join("campaign.json")
}

fn root_temps(dir: &std::path::Path) -> Vec<String> {
    std::fs::read_dir(dir)
        .unwrap()
        .flatten()
        .map(|e| e.file_name().to_string_lossy().to_string())
        .filter(|n| n.contains(".tmp-"))
        .collect()
}

/// The first shipped game (the harness's default).
fn first_game(client: &reqwest::blocking::Client, url: &str) -> String {
    campaign(client, url)["games"][0]["id"]
        .as_str()
        .expect("at least one shipped game")
        .to_string()
}

#[test]
fn undeclared_empty_campaign_serves_only_the_shell_and_declares_once() {
    let dir = tempfile::tempdir().unwrap();
    let client = client();
    let server = TestServer::spawn_undeclared(dir.path());
    let url = &server.url;

    let view = campaign(&client, url);
    assert!(view["system"].is_null(), "no game yet: {view}");
    assert_eq!(view["can_declare"], true);
    assert!(view["problem"].is_null());
    assert!(
        !view["games"].as_array().unwrap().is_empty(),
        "the shipped games are offered"
    );
    assert!(!view["license_lines"].as_array().unwrap().is_empty());

    // Character routes refuse typed; the roster is the empty shell.
    let (status, body) = create(&client, url, "Nobody");
    assert_eq!(status, 422, "{body}");
    assert!(body["message"]
        .as_str()
        .unwrap()
        .contains("not chosen its game"));
    let shell = roster(&client, url);
    assert!(shell["entries"].as_array().unwrap().is_empty());
    assert!(shell["classes"].as_array().unwrap().is_empty());
    assert!(
        !declaration_path(dir.path()).exists(),
        "nothing written yet"
    );

    // An unknown game refuses typed, nothing written.
    let (status, body) = declare(&client, url, "not-a-game");
    assert_eq!(status, 422, "{body}");
    assert!(!declaration_path(dir.path()).exists());

    // Declare the first shipped game: the view, the roster, and creation
    // all work without a restart.
    let game = first_game(&client, url);
    let (status, view) = declare(&client, url, &game);
    assert_eq!(status, 200, "{view}");
    assert_eq!(view["system"], game.as_str());
    assert_eq!(view["inferred"], false);
    assert_eq!(view["can_declare"], true, "still empty — may still change");
    let bytes = std::fs::read(declaration_path(dir.path())).unwrap();
    let text = String::from_utf8(bytes.clone()).unwrap();
    assert!(text.contains(&format!("\"system\": \"{game}\"")), "{text}");
    assert!(
        root_temps(dir.path()).is_empty(),
        "no stray declaration temp"
    );
    let (status, draft) = create(&client, url, "First");
    assert_eq!(status, 200, "{draft}");
    assert!(!roster(&client, url)["entries"]
        .as_array()
        .unwrap()
        .is_empty());

    // Once a character exists the game is fixed: every declare refuses
    // typed and the file is byte-identical.
    let (status, body) = declare(&client, url, &game);
    assert_eq!(status, 422, "{body}");
    assert_eq!(std::fs::read(declaration_path(dir.path())).unwrap(), bytes);
    assert_eq!(campaign(&client, url)["can_declare"], false);

    // A trashed character still fixes the game.
    let id = draft["id"].as_str().unwrap();
    client
        .delete(format!("{url}/api/characters/{id}"))
        .send()
        .unwrap();
    assert!(roster(&client, url)["entries"]
        .as_array()
        .unwrap()
        .is_empty());
    let (status, _) = declare(&client, url, &game);
    assert_eq!(status, 422, "a trashed character counts");
    assert_eq!(std::fs::read(declaration_path(dir.path())).unwrap(), bytes);
}

#[test]
fn declare_is_create_exclusive() {
    let dir = tempfile::tempdir().unwrap();
    let client = client();
    // A declaration written by another hand before this server saw one.
    let server = TestServer::spawn_undeclared(dir.path());
    let game = first_game(&client, &server.url);
    checks::declare_campaign(dir.path(), &game);
    let before = std::fs::read(declaration_path(dir.path())).unwrap();
    // The running server still believes the campaign is undeclared; its
    // create-exclusive write must lose to the existing file.
    let (status, body) = declare(&client, &server.url, &game);
    assert_eq!(status, 422, "{body}");
    assert!(
        body["message"].as_str().unwrap().contains("reload"),
        "{body}"
    );
    assert_eq!(std::fs::read(declaration_path(dir.path())).unwrap(), before);
    assert!(root_temps(dir.path()).is_empty());
}

#[test]
fn the_game_changes_only_while_empty_and_change_survives_a_restart() {
    let dir = tempfile::tempdir().unwrap();
    let client = client();
    let server = TestServer::spawn_undeclared(dir.path());
    let url = &server.url;
    let games: Vec<String> = campaign(&client, url)["games"]
        .as_array()
        .unwrap()
        .iter()
        .map(|g| g["id"].as_str().unwrap().to_string())
        .collect();
    let first = games[0].clone();
    let (status, _) = declare(&client, url, &first);
    assert_eq!(status, 200);
    // Re-declaring the same game on an empty campaign is a no-op success.
    let (status, view) = declare(&client, url, &first);
    assert_eq!(status, 200, "{view}");
    if let Some(second) = games.get(1) {
        // A second differing ANSWER (no `replaces`) is a race: refused.
        let (status, body) = declare(&client, url, second);
        assert_eq!(status, 422, "a racing second answer is refused: {body}");
        assert!(body["message"].as_str().unwrap().contains("reload"));
        assert_eq!(campaign(&client, url)["system"], first.as_str());
        // A deliberate change names the declaration it replaces.
        let (status, view) = post(
            &client,
            &format!("{url}/api/campaign"),
            json!({ "system": second, "replaces": first }),
        );
        assert_eq!(status, 200, "empty campaigns may change their game: {view}");
        assert_eq!(view["system"], second.as_str());
        drop(server);
        let server = TestServer::spawn_undeclared(dir.path());
        assert_eq!(campaign(&client, &server.url)["system"], second.as_str());
    }
}

#[test]
fn undeclared_campaign_with_characters_is_pf2e_and_never_written() {
    let dir = tempfile::tempdir().unwrap();
    let client = client();
    let id;
    {
        let server = TestServer::spawn(dir.path());
        let (_, draft) = create(&client, &server.url, "Elder");
        id = draft["id"].as_str().unwrap().to_string();
    }
    // A pre-slice directory: characters, no declaration.
    std::fs::rename(
        declaration_path(dir.path()),
        dir.path().join("campaign.json.moved-aside"),
    )
    .unwrap();
    let file = dir.path().join(format!("characters/{id}.json"));
    let before = std::fs::read(&file).unwrap();

    let server = TestServer::spawn_undeclared(dir.path());
    let url = &server.url;
    let view = campaign(&client, url);
    assert_eq!(view["system"], "pf2e", "{view}");
    assert_eq!(view["inferred"], true);
    assert_eq!(view["can_declare"], false);
    assert!(view["problem"].is_null());
    let entries = roster(&client, url)["entries"].as_array().unwrap().clone();
    assert_eq!(
        entries.len(),
        1,
        "the character loads under the inferred game"
    );
    let (status, _) = get(&client, &format!("{url}/api/characters/{id}"));
    assert_eq!(status, 200);
    // No declaration appears after loads, and declare refuses either game.
    assert!(!declaration_path(dir.path()).exists());
    for game in ["pf2e", "dnd5e"] {
        let (status, body) = declare(&client, url, game);
        assert_eq!(status, 422, "{body}");
    }
    assert!(!declaration_path(dir.path()).exists());
    assert_eq!(
        std::fs::read(&file).unwrap(),
        before,
        "loading rewrites nothing"
    );
    drop(server);
    // `verify` writes nothing either.
    let (code, out) = TestServer::run_verify(dir.path(), &[]);
    assert_eq!(code, 0, "{out}");
    assert!(!declaration_path(dir.path()).exists());
    assert!(root_temps(dir.path()).is_empty());
}

#[test]
fn corrupt_declaration_refuses_typed_and_verify_names_it() {
    let dir = tempfile::tempdir().unwrap();
    let client = client();
    std::fs::create_dir_all(dir.path()).unwrap();
    std::fs::write(declaration_path(dir.path()), "{ not json").unwrap();
    let before = std::fs::read(declaration_path(dir.path())).unwrap();
    let server = TestServer::spawn_undeclared(dir.path());
    let url = &server.url;
    let view = campaign(&client, url);
    assert!(view["system"].is_null());
    let problem = view["problem"].as_str().expect("problem named");
    assert!(problem.contains("campaign.json"), "{problem}");
    assert!(
        problem.contains("schema_version"),
        "names the fix: {problem}"
    );
    let (status, _) = create(&client, url, "Nobody");
    assert_eq!(status, 422);
    assert!(roster(&client, url)["entries"]
        .as_array()
        .unwrap()
        .is_empty());
    assert_eq!(std::fs::read(declaration_path(dir.path())).unwrap(), before);
    drop(server);
    let (code, out) = TestServer::run_verify(dir.path(), &[]);
    assert_eq!(code, 1, "{out}");
    assert!(out.contains("CAMPAIGN"), "{out}");
    assert_eq!(std::fs::read(declaration_path(dir.path())).unwrap(), before);
}

/// A character document of another game, built from a real PF2e file so
/// it is structurally valid.
fn foreign_document(dir: &std::path::Path, system: &str, pin: &str) -> (String, Vec<u8>) {
    let client = client();
    let id;
    {
        let server = TestServer::spawn(dir);
        let (_, draft) = create(&client, &server.url, "Visitor");
        id = draft["id"].as_str().unwrap().to_string();
    }
    let path = dir.join(format!("characters/{id}.json"));
    let mut doc: Value = serde_json::from_str(&std::fs::read_to_string(&path).unwrap()).unwrap();
    doc["system"] = Value::from(system);
    doc["rules_version"] = Value::from(pin);
    std::fs::write(&path, serde_json::to_string_pretty(&doc).unwrap()).unwrap();
    (id, std::fs::read(&path).unwrap())
}

#[test]
fn undeclared_directory_holding_a_foreign_file_reports_a_missing_declaration() {
    let dir = tempfile::tempdir().unwrap();
    let client = client();
    let (id, bytes) = foreign_document(dir.path(), "dnd5e", "dnd5e-srd.0.1.0");
    std::fs::rename(
        declaration_path(dir.path()),
        dir.path().join("campaign.json.moved-aside"),
    )
    .unwrap();
    let server = TestServer::spawn_undeclared(dir.path());
    let url = &server.url;
    let view = campaign(&client, url);
    assert!(view["system"].is_null(), "no inference to PF2e: {view}");
    let problem = view["problem"].as_str().expect("missing declaration named");
    assert!(problem.contains(&format!("{id}.json")), "{problem}");
    assert!(problem.contains("dnd5e"), "{problem}");
    assert!(problem.contains("campaign.json"), "{problem}");
    let shell = roster(&client, url);
    assert!(shell["entries"].as_array().unwrap().is_empty());
    let (status, _) = get(&client, &format!("{url}/api/characters/{id}"));
    assert_eq!(status, 422);
    assert!(!declaration_path(dir.path()).exists());
    let file = dir.path().join(format!("characters/{id}.json"));
    assert_eq!(std::fs::read(&file).unwrap(), bytes, "file untouched");
    assert!(!dir.path().join("quarantine").exists(), "never moved");
}

#[test]
fn wrong_drawer_is_refused_in_place() {
    let dir = tempfile::tempdir().unwrap();
    let client = client();
    let (id, bytes) = foreign_document(dir.path(), "dnd5e", "dnd5e-srd.0.1.0");
    let file = dir.path().join(format!("characters/{id}.json"));
    let server = TestServer::spawn(dir.path());
    let url = &server.url;
    let view = roster(&client, url);
    assert!(view["entries"].as_array().unwrap().is_empty());
    let problems = view["problems"].as_array().unwrap();
    assert_eq!(problems.len(), 1, "{problems:?}");
    let message = problems[0]["message"].as_str().unwrap();
    assert!(message.contains("5.5e"), "names the file's game: {message}");
    assert!(
        message.contains("Pathfinder"),
        "names the campaign's game: {message}"
    );
    assert!(message.contains("untouched"), "{message}");
    assert!(
        !problems[0]["message"]
            .as_str()
            .unwrap()
            .contains("quarantined"),
        "refused in place, not quarantined"
    );
    let (status, body) = get(&client, &format!("{url}/api/characters/{id}"));
    assert_eq!(status, 422, "{body}");
    assert_eq!(std::fs::read(&file).unwrap(), bytes, "never written");
    assert!(!dir.path().join("quarantine").exists(), "never moved");
    // The version guard never saw it (a foreign file has no version status).
    drop(server);
    let (_, out) = TestServer::run_verify(dir.path(), &[]);
    assert!(out.contains("not loaded"), "{out}");
    assert!(
        !out.contains("UNKNOWN"),
        "system check runs before the version guard: {out}"
    );
    assert_eq!(std::fs::read(&file).unwrap(), bytes);
}

#[test]
fn system_field_disagreeing_with_a_registered_pin_is_refused_in_place() {
    let dir = tempfile::tempdir().unwrap();
    let client = client();
    let (id, bytes) = foreign_document(dir.path(), "dnd5e", "pf2e-pc.0.4.0");
    let file = dir.path().join(format!("characters/{id}.json"));
    let server = TestServer::spawn(dir.path());
    let view = roster(&client, &server.url);
    let problems = view["problems"].as_array().unwrap();
    assert_eq!(problems.len(), 1, "{problems:?}");
    assert!(problems[0]["message"]
        .as_str()
        .unwrap()
        .contains("pins rules-data version"));
    assert_eq!(std::fs::read(&file).unwrap(), bytes);
    assert!(!dir.path().join("quarantine").exists());
}

#[test]
fn unregistered_pin_prefix_reads_as_pf2e_and_is_version_unknown() {
    let dir = tempfile::tempdir().unwrap();
    let client = client();
    let id;
    {
        let server = TestServer::spawn(dir.path());
        let (_, draft) = create(&client, &server.url, "Odd");
        id = draft["id"].as_str().unwrap().to_string();
    }
    let path = dir.path().join(format!("characters/{id}.json"));
    let mut doc: Value = serde_json::from_str(&std::fs::read_to_string(&path).unwrap()).unwrap();
    doc.as_object_mut().unwrap().remove("system");
    doc["rules_version"] = Value::from("foo-bar.1.0.0");
    std::fs::write(&path, serde_json::to_string_pretty(&doc).unwrap()).unwrap();
    let bytes = std::fs::read(&path).unwrap();
    let server = TestServer::spawn(dir.path());
    let view = roster(&client, &server.url);
    let entries = view["entries"].as_array().unwrap();
    assert_eq!(entries.len(), 1, "loads as PF2e: {view}");
    assert_eq!(entries[0]["version"]["status"], "unknown");
    assert_eq!(std::fs::read(&path).unwrap(), bytes);
}

#[test]
fn v4_files_load_byte_identical_and_gain_their_system_on_first_write() {
    let dir = tempfile::tempdir().unwrap();
    let client = client();
    let id;
    {
        let server = TestServer::spawn(dir.path());
        let (_, draft) = create(&client, &server.url, "Elder");
        id = draft["id"].as_str().unwrap().to_string();
    }
    let path = dir.path().join(format!("characters/{id}.json"));
    let mut doc: Value = serde_json::from_str(&std::fs::read_to_string(&path).unwrap()).unwrap();
    doc.as_object_mut().unwrap().remove("system");
    doc["schema_version"] = Value::from(4);
    std::fs::write(&path, serde_json::to_string_pretty(&doc).unwrap()).unwrap();
    let v4_bytes = std::fs::read(&path).unwrap();
    let server = TestServer::spawn(dir.path());
    let url = &server.url;
    let (status, _) = get(&client, &format!("{url}/api/characters/{id}"));
    assert_eq!(status, 200);
    assert_eq!(
        std::fs::read(&path).unwrap(),
        v4_bytes,
        "load rewrites nothing"
    );
    let (status, outcome) = post(
        &client,
        &format!("{url}/api/characters/{id}/confirm"),
        json!({ "version": 1, "decision": {
            "id": "d-v5", "slot": "pf2e.ancestry",
            "selection": {"kind": "option", "value": "ancestry.dwarf"},
            "source": "player" } }),
    );
    assert_eq!(status, 200, "{outcome}");
    assert_eq!(outcome["outcome"], "confirmed");
    let upgraded: Value = serde_json::from_str(&std::fs::read_to_string(&path).unwrap()).unwrap();
    assert_eq!(upgraded["schema_version"], 5);
    assert_eq!(upgraded["system"], "pf2e");
}

#[test]
fn v6_files_are_refused() {
    let dir = tempfile::tempdir().unwrap();
    std::fs::create_dir_all(dir.path().join("characters")).unwrap();
    std::fs::write(
        dir.path().join("characters/future.json"),
        json!({ "schema_version": 6, "id": "future" }).to_string(),
    )
    .unwrap();
    let (code, stderr) = TestServer::spawn_expect_failure(dir.path());
    assert_eq!(code, 2, "{stderr}");
    assert!(stderr.contains("newer"), "{stderr}");
}

/// Declare under SIGKILL: the declaration is absent, or complete and
/// valid — never torn; stray temps are swept on the next start.
#[test]
fn declare_under_sigkill_is_never_torn() {
    let client = reqwest::blocking::Client::builder()
        .timeout(std::time::Duration::from_secs(2))
        .build()
        .unwrap();
    for delay_ms in [0u64, 1, 2, 4, 8] {
        let dir = tempfile::tempdir().unwrap();
        let mut server = TestServer::spawn_undeclared(dir.path());
        let game = first_game(&client, &server.url);
        let fire = std::thread::spawn({
            let client = client.clone();
            let url = format!("{}/api/campaign", server.url);
            let game = game.clone();
            move || {
                let _ = client.post(&url).json(&json!({ "system": game })).send();
            }
        });
        std::thread::sleep(std::time::Duration::from_millis(delay_ms));
        server.kill();
        fire.join().unwrap();

        let server = TestServer::spawn_undeclared(dir.path());
        let view = campaign(&client, &server.url);
        assert!(view["problem"].is_null(), "never torn: {view}");
        let on_disk = declaration_path(dir.path()).exists();
        if on_disk {
            assert_eq!(view["system"], game.as_str());
            let text = std::fs::read_to_string(declaration_path(dir.path())).unwrap();
            let parsed: Value = serde_json::from_str(&text).expect("complete json");
            assert_eq!(parsed["system"], game.as_str());
        } else {
            assert!(view["system"].is_null());
        }
        assert!(root_temps(dir.path()).is_empty(), "stray temps swept");
    }
}

/// Attribution follows the binary: the campaign view carries every
/// shipped license paragraph, identical on an undeclared directory and on
/// a campaign of each shipped game.
#[test]
fn attribution_follows_the_binary() {
    let client = client();
    let dir = tempfile::tempdir().unwrap();
    let server = TestServer::spawn_undeclared(dir.path());
    let undeclared = campaign(&client, &server.url);
    let lines = undeclared["license_lines"].as_array().unwrap().clone();
    assert!(lines.len() >= 3, "every shipped notice: {lines:?}");
    let joined = lines
        .iter()
        .map(|l| l.as_str().unwrap())
        .collect::<Vec<_>>()
        .join("\n");
    assert!(joined.contains("ORC License"), "{joined}");
    let games: Vec<String> = undeclared["games"]
        .as_array()
        .unwrap()
        .iter()
        .map(|g| g["id"].as_str().unwrap().to_string())
        .collect();
    drop(server);
    for game in games {
        let dir = tempfile::tempdir().unwrap();
        let server = TestServer::spawn_undeclared(dir.path());
        let (status, view) = declare(&client, &server.url, &game);
        assert_eq!(status, 200, "{view}");
        assert_eq!(
            view["license_lines"].as_array().unwrap(),
            &lines,
            "{game}: the notices never depend on the open campaign"
        );
    }
}
