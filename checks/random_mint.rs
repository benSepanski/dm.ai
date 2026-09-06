//! Random-mint rows of the roster-ergonomics architecture:
//! - seed-sweep soundness through the real engine: for every shipped
//!   class, a sampled build fills every required slot, has an empty
//!   checklist, and finalizes — no seed lands an illegal decision or
//!   strands a set-level constraint (the Wizard curriculum);
//! - mint determinism through the real server: the same request ID mints
//!   a byte-identical character;
//! - mint variety: key slots are not constant across a seed sweep;
//! - name-pool failure fixtures: malformed pool ⇒ typed error and
//!   nothing written; empty pools map ⇒ default-pool name; typed names
//!   stand.

use checks::TestServer;
use engine_core::{Sampler, SuggestionContext};
use serde_json::{json, Value};
use types::{DecisionId, DecisionInput, DecisionSource, OptionId, Selection, SlotId};

const NAME_SLOT: &str = "pf2e.details.name";

fn engine() -> ruleset_pf2e::Pf2eEngine {
    ruleset_pf2e::engine(std::sync::Arc::new(checks::load_rules_data()))
}

/// The mint route's sampling policy, restated independently: legal
/// options only, a fresh shuffle per ask, free-text slots get a topic,
/// the name slot is left for the pool step.
fn random_source<'s>(
    sampler: &'s mut Sampler,
) -> impl FnMut(&SuggestionContext) -> Option<engine_core::SlotSuggestion> + 's {
    move |ctx: &SuggestionContext| {
        if ctx.slot.as_str() == NAME_SLOT {
            return None;
        }
        match ctx.kind {
            types::SlotViewKind::Text { .. } => Some(engine_core::SlotSuggestion::Text(
                "Wagonwright Lore".to_string(),
            )),
            _ => {
                let legal: Vec<OptionId> = ctx
                    .options
                    .iter()
                    .filter(|o| o.available)
                    .map(|o| o.id.clone())
                    .collect();
                if legal.is_empty() {
                    return None;
                }
                Some(engine_core::SlotSuggestion::Candidates(
                    sampler.shuffled(&legal),
                ))
            }
        }
    }
}

/// Expand one sampled build for a class and seed; returns the finished
/// log (name appended).
fn sample_build(
    engine: &ruleset_pf2e::Pf2eEngine,
    class_id: &str,
    seed: u64,
) -> Vec<types::Decision> {
    let mut sampler = Sampler::new(seed);
    let class = DecisionInput {
        id: DecisionId::new(format!("seed{seed}.class-pick")),
        slot: SlotId::new(ruleset_pf2e::CLASS_SLOT_ID),
        selection: Selection::Option(OptionId::new(class_id)),
        source: DecisionSource::Random,
    };
    let log = match engine.append(&[], class).expect("class applies") {
        engine_core::AppendOutcome::Appended(log) => log,
        engine_core::AppendOutcome::AlreadyPresent => unreachable!(),
    };
    let plan = {
        let mut source = random_source(&mut sampler);
        let mut plan = engine
            .expand_suggestions(
                &log,
                &mut source,
                &|slot| DecisionId::new(format!("seed{seed}.{slot}")),
                DecisionSource::Random,
            )
            .expect("expansion folds");
        // The route's refill loop, restated: generated decisions that a
        // later count-growth left short — or that a set-level validator
        // flagged (the curriculum floor) — are re-opened and resampled.
        for _ in 0..8 {
            let projection = engine.project(&plan.log).expect("projects");
            let incomplete: Vec<SlotId> = projection
                .checklist
                .iter()
                .map(|e| e.slot.clone())
                .filter(|slot| {
                    plan.log
                        .iter()
                        .any(|d| d.slot == *slot && d.source == DecisionSource::Random)
                })
                .collect();
            if incomplete.is_empty() {
                break;
            }
            let mut cleared = plan.log.clone();
            for slot in &incomplete {
                if let Ok(new_log) = engine.clear(&cleared, slot) {
                    cleared = new_log;
                }
            }
            plan = engine
                .expand_suggestions(
                    &cleared,
                    &mut source,
                    &|slot| DecisionId::new(format!("seed{seed}.{slot}")),
                    DecisionSource::Random,
                )
                .expect("re-expansion folds");
        }
        plan
    };
    assert!(
        plan.unresolved.iter().all(|u| u.slot.as_str() == NAME_SLOT),
        "{class_id} seed {seed}: only the name slot may remain after \
         sampling, got {:#?}",
        plan.unresolved
    );
    let name = DecisionInput {
        id: DecisionId::new(format!("seed{seed}.random-name")),
        slot: SlotId::new(NAME_SLOT),
        selection: Selection::Text(format!("Seedling {seed}")),
        source: DecisionSource::Random,
    };
    match engine.append(&plan.log, name).expect("name applies") {
        engine_core::AppendOutcome::Appended(log) => log,
        engine_core::AppendOutcome::AlreadyPresent => unreachable!(),
    }
}

const SEEDS: std::ops::Range<u64> = 0..8;

/// One shared sweep: every (class, seed) build, computed once and reused
/// by the soundness and variety tests — sampling through the real engine
/// is the expensive part, and the suite rides a 20 s wall-time ceiling.
fn sweep() -> &'static Vec<(String, u64, Vec<types::Decision>)> {
    static SWEEP: std::sync::OnceLock<Vec<(String, u64, Vec<types::Decision>)>> =
        std::sync::OnceLock::new();
    SWEEP.get_or_init(|| {
        let engine = engine();
        let mut out = Vec::new();
        for class_id in shipped_class_ids(&engine) {
            for seed in SEEDS {
                let log = sample_build(&engine, &class_id, seed);
                out.push((class_id.clone(), seed, log));
            }
        }
        out
    })
}

/// Every shipped class, every seed: full fill, empty checklist,
/// finalizable, every generated decision marked as generated. This is the
/// no-stranded-constraint row: the Wizard's curriculum floor must survive
/// uniform sampling via bounded resampling.
#[test]
fn sampled_builds_are_sound_for_every_shipped_class_across_seeds() {
    let engine = engine();
    let classes: std::collections::BTreeSet<&str> =
        sweep().iter().map(|(c, _, _)| c.as_str()).collect();
    assert!(
        classes.len() >= 2,
        "expected fighter and wizard, got {classes:?}"
    );
    for (class_id, seed, log) in sweep() {
        {
            let projection = engine.project(log).expect("sampled log projects");
            assert!(
                projection.checklist.is_empty(),
                "{class_id} seed {seed}: non-empty checklist: {:#?}",
                projection.checklist
            );
            assert!(
                projection.can_finalize,
                "{class_id} seed {seed}: must be finalizable"
            );
            assert!(
                log.iter().all(|d| d.source == DecisionSource::Random),
                "{class_id} seed {seed}: every decision carries generated provenance"
            );
            engine.sheet(log).expect("sampled log derives a sheet");
        }
    }
}

fn shipped_class_ids(engine: &ruleset_pf2e::Pf2eEngine) -> Vec<String> {
    let projection = engine.project(&[]).expect("empty log projects");
    projection
        .steps
        .iter()
        .flat_map(|s| s.slots.iter())
        .filter(|slot| slot.id.as_str() == ruleset_pf2e::CLASS_SLOT_ID)
        .flat_map(|slot| slot.options.iter())
        .filter(|o| o.available)
        .map(|o| o.id.as_str().to_string())
        .collect()
}

/// Variety: across the sweep, key slots see at least two distinct
/// selections — the sampler is not pinned to any fixed build (the
/// published suggestion included). With 8 seeds and 4+ options per
/// listed slot, a constant pick is a code bug, not bad luck.
#[test]
fn sampled_builds_vary_across_seeds() {
    let classes: std::collections::BTreeSet<&str> =
        sweep().iter().map(|(c, _, _)| c.as_str()).collect();
    for class_id in classes {
        for watched in ["pf2e.ancestry", "pf2e.background"] {
            let mut seen = std::collections::BTreeSet::new();
            for (_, _, log) in sweep().iter().filter(|(c, _, _)| c == class_id) {
                let selection = log
                    .iter()
                    .find(|d| d.slot.as_str() == watched)
                    .map(|d| format!("{:?}", d.selection))
                    .unwrap_or_default();
                seen.insert(selection);
            }
            assert!(
                seen.len() >= 2,
                "{class_id}: slot {watched} was constant across {} seeds — \
                 the sampler is pinned",
                SEEDS.end
            );
        }
    }
}

// ---- Through the real server ----

fn client() -> reqwest::blocking::Client {
    reqwest::blocking::Client::new()
}

fn mint(client: &reqwest::blocking::Client, url: &str, body: Value) -> (u16, Value) {
    let response = client
        .post(format!("{url}/api/characters/random-mint"))
        .json(&body)
        .send()
        .unwrap();
    let status = response.status().as_u16();
    (status, response.json().unwrap_or(Value::Null))
}

fn character_files(dir: &std::path::Path) -> Vec<std::path::PathBuf> {
    let characters = dir.join("characters");
    if !characters.exists() {
        return Vec::new();
    }
    let mut files: Vec<_> = std::fs::read_dir(characters)
        .unwrap()
        .map(|e| e.unwrap().path())
        .collect();
    files.sort();
    files
}

/// Same request ID ⇒ byte-identical character file, on independent
/// servers over independent data dirs. The request ID is the entropy.
#[test]
fn same_request_mints_the_identical_character() {
    let request = json!({"request_id": "determinism-fixture", "class_id": null, "name": null});
    let mut bytes = Vec::new();
    for _ in 0..2 {
        let dir = tempfile::tempdir().unwrap();
        let server = TestServer::spawn(dir.path());
        let (status, result) = mint(&client(), &server.url, request.clone());
        assert_eq!(status, 200, "{result}");
        let files = character_files(dir.path());
        assert_eq!(files.len(), 1);
        bytes.push(std::fs::read(&files[0]).unwrap());
    }
    assert_eq!(
        bytes[0], bytes[1],
        "the same request ID must mint the identical character"
    );
}

/// A typed name is a player decision the generator never overwrites.
#[test]
fn typed_names_stand() {
    let dir = tempfile::tempdir().unwrap();
    let server = TestServer::spawn(dir.path());
    let (status, result) = mint(
        &client(),
        &server.url,
        json!({"request_id": "typed-name-fixture", "class_id": null, "name": "Handpicked"}),
    );
    assert_eq!(status, 200, "{result}");
    let file: Value =
        serde_json::from_str(&std::fs::read_to_string(&character_files(dir.path())[0]).unwrap())
            .unwrap();
    let name_decision = file["log"]
        .as_array()
        .unwrap()
        .iter()
        .find(|d| d["slot"] == NAME_SLOT)
        .expect("name decision present");
    assert_eq!(name_decision["selection"]["value"], "Handpicked");
    assert_eq!(name_decision["source"], "player");
}

/// A malformed pools file (the default pool included) fails the mint with
/// a typed error naming the file; nothing is written; the server keeps
/// serving.
#[test]
fn malformed_pool_fails_typed_and_writes_nothing() {
    let dir = tempfile::tempdir().unwrap();
    let pools = dir.path().join("broken-pools.json");
    std::fs::write(&pools, "{ this is not json").unwrap();
    let data_dir = dir.path().join("campaign");
    std::fs::create_dir_all(&data_dir).unwrap();
    let server = TestServer::spawn_with_args(&data_dir, &["--name-pools", pools.to_str().unwrap()]);
    let (status, result) = mint(
        &client(),
        &server.url,
        json!({"request_id": "broken-pools-fixture", "class_id": null, "name": null}),
    );
    assert_eq!(status, 422, "{result}");
    let message = result["message"].as_str().unwrap();
    assert!(
        message.contains("broken-pools.json") && message.contains("malformed"),
        "the error names the file: {message}"
    );
    assert!(
        character_files(&data_dir).is_empty(),
        "a failed mint writes nothing"
    );
    // The server survives: the roster still answers.
    let roster: Value = client()
        .get(format!("{}/api/roster", server.url))
        .send()
        .unwrap()
        .json()
        .unwrap();
    assert!(roster["entries"].as_array().unwrap().is_empty());
}

/// An empty pools map (no per-ancestry pools at all) silently falls back
/// to the default pool.
#[test]
fn missing_ancestry_pools_fall_back_to_the_default_pool() {
    let dir = tempfile::tempdir().unwrap();
    let pools = dir.path().join("default-only.json");
    std::fs::write(
        &pools,
        json!({"default": ["Fallbackia"], "pools": {}}).to_string(),
    )
    .unwrap();
    let data_dir = dir.path().join("campaign");
    std::fs::create_dir_all(&data_dir).unwrap();
    let server = TestServer::spawn_with_args(&data_dir, &["--name-pools", pools.to_str().unwrap()]);
    let (status, result) = mint(
        &client(),
        &server.url,
        json!({"request_id": "fallback-fixture", "class_id": null, "name": null}),
    );
    assert_eq!(status, 200, "{result}");
    let file: Value =
        serde_json::from_str(&std::fs::read_to_string(&character_files(&data_dir)[0]).unwrap())
            .unwrap();
    let name_decision = file["log"]
        .as_array()
        .unwrap()
        .iter()
        .find(|d| d["slot"] == NAME_SLOT)
        .expect("name decision present");
    assert_eq!(name_decision["selection"]["value"], "Fallbackia");
    assert_eq!(name_decision["source"], "random");
}

/// An unknown class refuses, typed, and writes nothing.
#[test]
fn unknown_class_refuses_and_writes_nothing() {
    let dir = tempfile::tempdir().unwrap();
    let server = TestServer::spawn(dir.path());
    let (status, result) = mint(
        &client(),
        &server.url,
        json!({"request_id": "bad-class-fixture", "class_id": "class.bard", "name": null}),
    );
    assert_eq!(status, 422, "{result}");
    assert!(result["message"]
        .as_str()
        .unwrap()
        .contains("unknown class"));
    assert!(character_files(dir.path()).is_empty());
}

// ---- Leveled seed sweep (level-up architecture): test-only random leveling ----
//
// The satisfiability and cross-level-prerequisite rows in one: for every
// shipped class and a seed sweep, a minted character advances level by
// level to the cap through the same sampler and planner, each level's
// slots fillable, the checklist empty at each finalize, and the file
// verify-clean. At least one seed takes a prerequisite-bearing level-2
// feat. No route and no UI exist for this — it is harness machinery.

fn level_randomly(
    engine: &ruleset_pf2e::Pf2eEngine,
    sampler: &mut Sampler,
    log: &[types::Decision],
    level: u32,
    tag: &str,
) -> Vec<types::Decision> {
    let advance = DecisionInput {
        id: DecisionId::new(format!("{tag}.level-{level}.advance")),
        slot: SlotId::new(ruleset_pf2e::slot_level_advance(level)),
        selection: Selection::Option(OptionId::new(format!("advance.{level}"))),
        source: DecisionSource::Player,
    };
    let log = match engine.append(log, advance).expect("advance applies") {
        engine_core::AppendOutcome::Appended(log) => log,
        engine_core::AppendOutcome::AlreadyPresent => unreachable!(),
    };
    let mut source = random_source(sampler);
    let mut plan = engine
        .expand_suggestions(
            &log,
            &mut source,
            &|slot| DecisionId::new(format!("{tag}.level-{level}.{slot}")),
            DecisionSource::Random,
        )
        .expect("level expansion folds");
    for _ in 0..8 {
        let projection = engine.project(&plan.log).expect("projects");
        let flagged: Vec<SlotId> = projection
            .checklist
            .iter()
            .map(|e| e.slot.clone())
            .filter(|slot| {
                plan.log
                    .iter()
                    .any(|d| d.slot == *slot && d.source == DecisionSource::Random)
            })
            .collect();
        if flagged.is_empty() {
            break;
        }
        let mut cleared = plan.log.clone();
        for slot in &flagged {
            if let Ok(new_log) = engine.clear(&cleared, slot) {
                cleared = new_log;
            }
        }
        plan = engine
            .expand_suggestions(
                &cleared,
                &mut source,
                &|slot| DecisionId::new(format!("{tag}.level-{level}.{slot}")),
                DecisionSource::Random,
            )
            .expect("re-expansion folds");
    }
    assert!(
        plan.unresolved.is_empty(),
        "level {level} left slots unresolved: {:#?}",
        plan.unresolved
    );
    plan.log
}

#[test]
fn minted_characters_level_randomly_to_the_cap_across_seeds() {
    let engine = engine();
    let data = checks::load_rules_data();
    let cap = data.max_advancement_level();
    let mut took_prerequisite_feat = false;
    for (class_id, seed, base) in sweep() {
        let mut sampler = Sampler::new(seed.wrapping_mul(7919));
        let mut log = base.clone();
        for level in 2..=cap {
            log = level_randomly(
                &engine,
                &mut sampler,
                &log,
                level,
                &format!("{class_id}-{seed}"),
            );
            let projection = engine.project(&log).expect("leveled log projects");
            assert!(
                projection.checklist.is_empty(),
                "{class_id} seed {seed} level {level}: checklist not empty: {:#?}",
                projection.checklist
            );
            assert!(projection.can_finalize);
            let state = engine.fold(&log).unwrap();
            assert_eq!(state.level() as u32, level);
        }
        // Cross-level prerequisites: did this seed take a level-2 feat that
        // carries a prerequisite (judged against the leveled state)?
        for d in &log {
            if let Selection::Option(id) = &d.selection {
                let has_prereq = data
                    .general_feat(id.as_str())
                    .map(|f| !f.prerequisites.is_empty())
                    .or_else(|| {
                        data.class_feat(id.as_str())
                            .map(|f| !f.prerequisites.is_empty())
                    })
                    .unwrap_or(false);
                if has_prereq && d.slot.as_str().starts_with("pf2e.level.") {
                    took_prerequisite_feat = true;
                }
            }
        }
        // Every level boundary is a complete character (the history seam).
        for (index, d) in log.iter().enumerate() {
            if ruleset_pf2e::advance_level_of(d.slot.as_str()).is_some() {
                assert!(engine.project(&log[..index]).unwrap().can_finalize);
            }
        }
    }
    assert!(
        took_prerequisite_feat,
        "no swept build took a prerequisite-bearing level-up feat"
    );
}
