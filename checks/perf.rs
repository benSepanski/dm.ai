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
