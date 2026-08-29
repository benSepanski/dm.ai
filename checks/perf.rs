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

/// chargen-wizard: the full wizard projection — fold + scoped prep
/// validation + sheet — rides inside the same 5 ms budget (architecture:
/// scoped validation is asserted within the fold budget's headroom).
#[test]
#[allow(clippy::disallowed_methods)] // timing a budget needs a clock
fn wizard_fold_with_prep_is_under_5ms() {
    use types::{ScopedChoice, Selection, SlotId};
    let engine = ruleset_pf2e::engine(std::sync::Arc::new(checks::load_rules_data()));
    // Build the golden wizard log through the engine (no fixture file: the
    // wizard log is authored in checks/replay.rs; here a compact rebuild).
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
    confirm(
        &mut log,
        "pf2e.ancestry.feat",
        one("feat.ancestry.elf.unwavering-mien"),
    );
    confirm(&mut log, "pf2e.boosts.ancestry-free", many(&["attr.wis"]));
    confirm(&mut log, "pf2e.background", one("background.artisan"));
    confirm(&mut log, "pf2e.boosts.background-choice", one("attr.int"));
    confirm(&mut log, "pf2e.boosts.background-free", one("attr.cha"));
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
        ]),
    );
    confirm(
        &mut log,
        "pf2e.class.spellbook.curriculum",
        many(&["spell.breathe-fire", "spell.force-barrage"]),
    );
    let prep = vec![
        ScopedChoice {
            slot: SlotId::new("pf2e.prep.cantrips"),
            selection: many(&[
                "spell.shield",
                "spell.ignition",
                "spell.electric-arc",
                "spell.detect-magic",
                "spell.light",
            ]),
        },
        ScopedChoice {
            slot: SlotId::new("pf2e.prep.rank1"),
            selection: many(&["spell.fear", "spell.command"]),
        },
        ScopedChoice {
            slot: SlotId::new("pf2e.prep.school-cantrip"),
            selection: one("spell.telekinetic-projectile"),
        },
        ScopedChoice {
            slot: SlotId::new("pf2e.prep.school-rank1"),
            selection: one("spell.mystic-armor"),
        },
    ];

    for _ in 0..10 {
        let _ = engine.project(&log, &prep).unwrap();
    }
    let runs = 100;
    let start = std::time::Instant::now();
    for _ in 0..runs {
        std::hint::black_box(
            engine
                .project(std::hint::black_box(&log), std::hint::black_box(&prep))
                .unwrap(),
        );
    }
    let per_run = start.elapsed() / runs;
    assert!(
        per_run < std::time::Duration::from_millis(5),
        "wizard projection with prep took {per_run:?} per run — budget is 5 ms"
    );
}
