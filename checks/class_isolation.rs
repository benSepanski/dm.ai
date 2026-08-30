//! Class isolation (architecture: chargen-wizard): class identity never
//! lives in shared code. Two guards over the same must-never:
//! (1) no shipped record's display name appears as a string literal in
//!     ruleset source — class-specific anything is a data lookup;
//! (2) one class's vocabulary never appears in another class's projection
//!     or sheet (sole sanctioned exception: the class-picker catalog).
//! Both grow automatically with every shipped record and class.

use engine_core::AppendOutcome;
use types::{Decision, DecisionId, DecisionInput, DecisionSource, Selection, SlotId, SlotViewKind};

/// Every shipped record display name, as a quoted source literal.
fn shipped_names() -> Vec<String> {
    let data = checks::load_rules_data();
    let mut names: Vec<String> = Vec::new();
    names.extend(data.ancestries.iter().map(|r| r.name.clone()));
    names.extend(data.heritages.iter().map(|r| r.name.clone()));
    names.extend(data.ancestry_feats.iter().map(|r| r.name.clone()));
    names.extend(data.backgrounds.iter().map(|r| r.name.clone()));
    names.extend(data.classes.iter().map(|r| r.name.clone()));
    names.extend(data.class_feats.iter().map(|r| r.name.clone()));
    names.extend(data.general_feats.iter().map(|r| r.name.clone()));
    names.extend(data.spells.spells.iter().map(|r| r.name.clone()));
    names.extend(data.spells.theses.iter().map(|r| r.name.clone()));
    names.extend(data.spells.schools.iter().map(|r| r.name.clone()));
    names.extend(data.skills.iter().map(|r| r.name.clone()));
    names.extend(data.equipment.kits.iter().map(|r| r.name.clone()));
    names.sort();
    names.dedup();
    names
}

#[test]
fn no_shipped_record_name_is_a_ruleset_source_literal() {
    let names = shipped_names();
    let src_dir = checks::workspace_root().join("crates/ruleset-pf2e/src");
    let mut violations = Vec::new();
    for entry in std::fs::read_dir(&src_dir).unwrap().flatten() {
        let path = entry.path();
        if path.extension().is_none_or(|e| e != "rs") {
            continue;
        }
        // Tests may name records (goldens do); shipped code may not.
        if path.file_name().is_some_and(|n| n == "tests.rs") {
            continue;
        }
        let text = std::fs::read_to_string(&path).unwrap();
        for name in &names {
            let literal = format!("\"{name}\"");
            if text.contains(&literal) {
                violations.push(format!(
                    "{}: contains the shipped record name {literal} as a source \
                     literal — resolve it from the record instead",
                    path.file_name().unwrap().to_string_lossy()
                ));
            }
        }
    }
    assert!(
        violations.is_empty(),
        "class-specific identity must be a data lookup, never a literal:\n  {}",
        violations.join("\n  ")
    );
}

fn engine() -> ruleset_pf2e::Pf2eEngine {
    ruleset_pf2e::engine(std::sync::Arc::new(checks::load_rules_data()))
}

/// Build a complete, legal character of the given class through the real
/// engine: the class's suggested build when it ships one, else a
/// first-fit walk over the open required slots (catalog order — the
/// rank-1 spell catalog sorts curriculum spells first, so the walk stays
/// legal).
fn complete_character(engine: &ruleset_pf2e::Pf2eEngine, class_id: &str) -> Vec<Decision> {
    let data = checks::load_rules_data();
    let mut log: Vec<Decision> = Vec::new();
    let mut n = 0u32;
    let mut append = |log: &mut Vec<Decision>, slot: &str, selection: Selection| {
        n += 1;
        let input = DecisionInput {
            id: DecisionId::new(format!("iso-{n}")),
            slot: SlotId::new(slot),
            selection,
            source: DecisionSource::Player,
        };
        // Amend covers both fresh confirms and re-fills of partial slots
        // (dynamic counts grow as the walk raises Int).
        match engine.amend(log, input) {
            Ok(AppendOutcome::Appended(new_log)) => *log = new_log,
            other => panic!("isolation walk confirm on '{slot}' rejected: {other:?}"),
        }
    };
    append(
        &mut log,
        "pf2e.class",
        Selection::Option(types::OptionId::new(class_id)),
    );

    if let Some((_, map)) = ruleset_pf2e::suggested_builds(&data)
        .into_iter()
        .find(|(id, _)| id == class_id)
    {
        let plan = engine
            .expand_suggestions(
                &log,
                &|slot| map.get(slot).cloned(),
                &|slot| DecisionId::new(format!("iso-qb.{slot}")),
                DecisionSource::Suggested,
            )
            .expect("suggested build expands");
        assert!(plan.unresolved.is_empty(), "{:#?}", plan.unresolved);
        return plan.log;
    }

    // First-fit walk until every required slot resolves.
    loop {
        let p = engine.project(&log).expect("walk log projects");
        if p.can_finalize {
            return log;
        }
        let mut progressed = false;
        for slot in p.steps.iter().flat_map(|s| &s.slots) {
            let open = slot.locked_reason.is_none()
                && slot.required
                && matches!(
                    slot.status,
                    types::SlotStatus::Empty | types::SlotStatus::Partial
                );
            if !open {
                continue;
            }
            let selection = match &slot.kind {
                SlotViewKind::Single => slot
                    .options
                    .iter()
                    .find(|o| o.available)
                    .map(|o| Selection::Option(o.id.clone())),
                SlotViewKind::Multi { count } => {
                    let picks: Vec<types::OptionId> = slot
                        .options
                        .iter()
                        .filter(|o| o.available)
                        .take(*count as usize)
                        .map(|o| o.id.clone())
                        .collect();
                    (picks.len() == *count as usize).then_some(Selection::Options(picks))
                }
                SlotViewKind::List => Some(Selection::Options(vec![])),
                SlotViewKind::Text { .. } => Some(Selection::Text("T".into())),
            };
            if let Some(selection) = selection {
                append(&mut log, slot.id.as_str(), selection);
                progressed = true;
                break;
            }
        }
        assert!(
            progressed,
            "isolation walk stuck for {class_id}: {:#?}",
            engine.project(&log).unwrap().checklist
        );
    }
}

/// One class's vocabulary never leaks into another's projection or sheet.
#[test]
fn no_cross_class_vocabulary_in_projections() {
    let engine = engine();
    let data = checks::load_rules_data();
    let classes: Vec<(String, String)> = data
        .classes
        .iter()
        .map(|c| (c.id.clone(), c.name.clone()))
        .collect();
    for (class_id, class_name) in &classes {
        let log = complete_character(&engine, class_id);
        let mut projection = engine.project(&log).expect("complete character projects");
        assert!(projection.can_finalize, "{class_name} walk is complete");
        // The class-picker catalog legitimately lists every class.
        for step in &mut projection.steps {
            for slot in &mut step.slots {
                if slot.id.as_str() == "pf2e.class" {
                    slot.options.clear();
                }
            }
        }
        let rendered = serde_json::to_string(&projection).unwrap();
        for (other_id, other_name) in &classes {
            if other_id == class_id {
                continue;
            }
            assert!(
                !rendered.contains(other_name.as_str()),
                "a {class_name}'s projection mentions '{other_name}'"
            );
            assert!(
                !rendered.contains(other_id.as_str()),
                "a {class_name}'s projection references '{other_id}'"
            );
        }
    }
}

/// Meter semantics live in the `MeterView` constructors (requirement /
/// exact / budget) so a meter's displayed numbers and its state can never
/// disagree — "3 of 2" on a satisfied minimum was a real bug. No code
/// outside the types crate may build a `MeterView` literal.
#[test]
fn meters_are_built_only_through_their_constructors() {
    let root = checks::workspace_root();
    let mut violations = Vec::new();
    for dir in [
        "crates/engine-core",
        "crates/ruleset-pf2e",
        "crates/server",
        "crates/wasm",
    ] {
        let mut stack = vec![root.join(dir)];
        while let Some(d) = stack.pop() {
            for entry in std::fs::read_dir(&d).into_iter().flatten().flatten() {
                let path = entry.path();
                if path.is_dir() {
                    if path.file_name().is_some_and(|n| n == "target") {
                        continue;
                    }
                    stack.push(path);
                } else if path.extension().is_some_and(|e| e == "rs") {
                    let src = std::fs::read_to_string(&path).unwrap();
                    if src.contains("MeterView {") {
                        violations.push(path.display().to_string());
                    }
                }
            }
        }
    }
    assert!(
        violations.is_empty(),
        "raw MeterView literal outside crates/types (use MeterView::requirement / \
         ::exact / ::budget so display and state stay coherent): {violations:?}"
    );
}
