//! Asserted perf budget: the derivation fold of a complete level-1 log runs
//! in under 5 ms native (architecture doc, performance budgets). The WASM
//! copy is same-order and hand-checked at review.

use types::Decision;

#[test]
#[allow(clippy::disallowed_methods)] // timing a budget needs a clock
fn fold_of_complete_log_is_under_5ms() {
    let engine = ruleset_pf2e::engine(std::sync::Arc::new(checks::load_rules_data()));
    let log: Vec<Decision> = serde_json::from_str(
        &std::fs::read_to_string(checks::workspace_root().join("checks/fixtures/torvald.log.json"))
            .unwrap(),
    )
    .unwrap();

    // Warm up, then measure the full derivation (fold + sheet) many times.
    for _ in 0..10 {
        let _ = engine.sheet(&log).unwrap();
    }
    let runs = 100;
    let start = std::time::Instant::now();
    for _ in 0..runs {
        std::hint::black_box(engine.sheet(std::hint::black_box(&log)).unwrap());
    }
    let per_run = start.elapsed() / runs;
    assert!(
        per_run < std::time::Duration::from_millis(5),
        "derivation fold took {per_run:?} per run — budget is 5 ms"
    );
}

/// chargen-wizard: the full Wizard projection — fold + validation + sheet
/// over the full spell catalog — rides the same 5 ms budget.
#[test]
#[allow(clippy::disallowed_methods)] // timing a budget needs a clock
fn wizard_projection_is_under_5ms() {
    use types::{Selection, SlotId};
    let engine = ruleset_pf2e::engine(std::sync::Arc::new(checks::load_rules_data()));
    let mut log: Vec<Decision> = Vec::new();
    let mut n = 0u32;
    let mut confirm = |log: &mut Vec<Decision>, slot: &str, selection: Selection| {
        n += 1;
        let input = types::DecisionInput {
            id: types::DecisionId::new(format!("perf-{n}")),
            slot: SlotId::new(slot),
            selection,
            source: types::DecisionSource::Player,
        };
        match engine.append(log, input) {
            Ok(engine_core::AppendOutcome::Appended(new_log)) => *log = new_log,
            other => panic!("perf fixture confirm on '{slot}' rejected: {other:?}"),
        }
    };
    let one = |id: &str| Selection::Option(types::OptionId::new(id));
    let many =
        |ids: &[&str]| Selection::Options(ids.iter().map(|i| types::OptionId::new(*i)).collect());
    confirm(&mut log, "pf2e.ancestry", one("ancestry.elf"));
    confirm(
        &mut log,
        "pf2e.ancestry.heritage",
        one("heritage.elf.arctic"),
    );
    confirm(&mut log, "pf2e.class", one("class.wizard"));
    confirm(&mut log, "pf2e.class.key-attribute", one("attr.int"));
    confirm(
        &mut log,
        "pf2e.class.thesis",
        one("thesis.spell-substitution"),
    );
    confirm(&mut log, "pf2e.class.school", one("school.battle-magic"));
    confirm(
        &mut log,
        "pf2e.class.spellbook.cantrips",
        many(&[
            "spell.caustic-blast",
            "spell.detect-magic",
            "spell.electric-arc",
            "spell.figment",
            "spell.frostbite",
            "spell.gouging-claw",
            "spell.ignition",
            "spell.light",
            "spell.message",
            "spell.shield",
        ]),
    );
    confirm(
        &mut log,
        "pf2e.class.spellbook.rank1",
        many(&[
            "spell.command",
            "spell.fear",
            "spell.grease",
            "spell.jump",
            "spell.sleep",
            "spell.breathe-fire",
            "spell.force-barrage",
        ]),
    );

    for _ in 0..10 {
        let _ = engine.project(&log).unwrap();
    }
    let runs = 100;
    let start = std::time::Instant::now();
    for _ in 0..runs {
        std::hint::black_box(engine.project(std::hint::black_box(&log)).unwrap());
    }
    let per_run = start.elapsed() / runs;
    assert!(
        per_run < std::time::Duration::from_millis(5),
        "wizard projection took {per_run:?} per run — budget is 5 ms"
    );
}

/// roster-ergonomics: a random mint — request to saved draft, driven
/// through the real server the way the idempotency harness drives it —
/// lands in under 250 ms over shipped data (architecture, performance
/// budgets). Measured across several mints so one warm-up outlier can't
/// pass or fail it alone.
#[test]
#[allow(clippy::disallowed_methods)] // timing a budget needs a clock
fn random_mint_is_under_250ms() {
    let dir = tempfile::tempdir().unwrap();
    let server = checks::TestServer::spawn(dir.path());
    let client = reqwest::blocking::Client::new();
    let mint = |request_id: &str| {
        let response = client
            .post(format!("{}/api/characters/random-mint", server.url))
            .json(&serde_json::json!({
                "request_id": request_id, "class_id": null, "name": null
            }))
            .send()
            .unwrap();
        assert!(response.status().is_success());
    };
    mint("perf-warmup");
    let runs = 5u32;
    let start = std::time::Instant::now();
    for i in 0..runs {
        mint(&format!("perf-mint-{i}"));
    }
    let per_run = start.elapsed() / runs;
    assert!(
        per_run < std::time::Duration::from_millis(250),
        "a random mint took {per_run:?} — budget is 250 ms"
    );
}
