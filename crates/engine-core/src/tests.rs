//! Engine tests over a deliberately game-free toy ruleset: two dependent
//! single-choice slots, a distinct-pick multi slot, text slots, and a slot
//! that only exists under certain state.

use types::{
    ChecklistEntry, ChecklistSeverity, Decision, DecisionId, DecisionInput, DecisionSource,
    OptionId, OptionView, Selection, SheetEntry, SheetSection, SheetView, SlotId, SlotViewKind,
    StepId,
};

use crate::{AppendOutcome, ApplyError, Availability, Engine, EngineError, SlotRegistration};

#[derive(Default, Clone)]
struct ToyState {
    primary: Option<String>,
    secondary: Option<String>,
    picks: Vec<String>,
    name: Option<String>,
    bonus: Option<String>,
}

fn opt(id: &str) -> OptionView {
    OptionView {
        id: OptionId::new(id),
        label: id.to_uppercase(),
        summary: String::new(),
        details: vec![],
        available: true,
        unavailable_reason: None,
    }
}

fn incomplete(slot: &str, rule: &str, message: &str) -> ChecklistEntry {
    ChecklistEntry {
        severity: ChecklistSeverity::Incomplete,
        slot: SlotId::new(slot),
        step: StepId::new(if slot == "primary" || slot == "secondary" {
            "one"
        } else {
            "two"
        }),
        rule: rule.into(),
        message: message.into(),
        source: "toy".into(),
    }
}

fn selection_id(selection: &Selection) -> Result<String, ApplyError> {
    match selection {
        Selection::Option(id) => Ok(id.as_str().to_string()),
        _ => Err(ApplyError::new("expected a single option")),
    }
}

fn toy_engine() -> Engine<ToyState> {
    let steps = vec![
        (StepId::new("one"), "Step One".to_string()),
        (StepId::new("two"), "Step Two".to_string()),
    ];
    let slots = vec![
        SlotRegistration::<ToyState> {
            id: SlotId::new("primary"),
            step: StepId::new("one"),
            label: "Primary".into(),
            required: true,
            presentation_hint: None,
            kind: Box::new(|_| SlotViewKind::Single),
            unlock: Box::new(|_| Availability::Open),
            dependents: vec![SlotId::new("secondary"), SlotId::new("bonus")],
            options: Box::new(|_| vec![opt("a"), opt("b")]),
            apply: Box::new(|s, d| {
                let id = selection_id(&d.selection)?;
                if id != "a" && id != "b" {
                    return Err(ApplyError::new(format!("unknown option {id}")));
                }
                s.primary = Some(id);
                Ok(())
            }),
            validate: Box::new(|s, _| {
                if s.primary.is_none() {
                    vec![incomplete("primary", "Primary", "choose a primary")]
                } else {
                    vec![]
                }
            }),
            describe: Box::new(|sel| format!("{sel:?}")),
        },
        SlotRegistration::<ToyState> {
            id: SlotId::new("secondary"),
            step: StepId::new("one"),
            label: "Secondary".into(),
            required: true,
            presentation_hint: None,
            kind: Box::new(|_| SlotViewKind::Single),
            unlock: Box::new(|s| match s.primary {
                Some(_) => Availability::Open,
                None => Availability::Locked {
                    reason: "choose a primary first".into(),
                },
            }),
            dependents: vec![],
            // Catalog derives from primary: a -> a1/a2, b -> b1.
            options: Box::new(|s| match s.primary.as_deref() {
                Some("a") => vec![opt("a1"), opt("a2")],
                Some("b") => vec![opt("b1")],
                _ => vec![],
            }),
            apply: Box::new(|s, d| {
                let id = selection_id(&d.selection)?;
                let valid = match s.primary.as_deref() {
                    Some("a") => id == "a1" || id == "a2",
                    Some("b") => id == "b1",
                    _ => false,
                };
                if !valid {
                    return Err(ApplyError::new(format!(
                        "option {id} is not in the catalog for this primary"
                    )));
                }
                s.secondary = Some(id);
                Ok(())
            }),
            validate: Box::new(|s, _| {
                if s.primary.is_some() && s.secondary.is_none() {
                    vec![incomplete("secondary", "Secondary", "choose a secondary")]
                } else {
                    vec![]
                }
            }),
            describe: Box::new(|sel| format!("{sel:?}")),
        },
        SlotRegistration::<ToyState> {
            id: SlotId::new("picks"),
            step: StepId::new("two"),
            label: "Picks".into(),
            required: true,
            presentation_hint: None,
            kind: Box::new(|_| SlotViewKind::Multi { count: 2 }),
            unlock: Box::new(|_| Availability::Open),
            dependents: vec![],
            options: Box::new(|_| vec![opt("x"), opt("y"), opt("z")]),
            apply: Box::new(|s, d| {
                // Duplicates and partial picks apply fine (flagged by
                // validate); unknown options are structural rejections.
                let Selection::Options(ids) = &d.selection else {
                    return Err(ApplyError::new("expected a multi selection"));
                };
                for id in ids {
                    if !["x", "y", "z"].contains(&id.as_str()) {
                        return Err(ApplyError::new(format!("unknown option {id}")));
                    }
                }
                s.picks = ids.iter().map(|i| i.as_str().to_string()).collect();
                Ok(())
            }),
            validate: Box::new(|s, d| {
                let mut out = vec![];
                if d.is_none() || s.picks.len() < 2 {
                    let left = 2 - s.picks.len().min(2);
                    out.push(incomplete(
                        "picks",
                        "Picks",
                        &format!("{} pick(s) left", left.max(1)),
                    ));
                }
                let mut seen = std::collections::BTreeSet::new();
                if s.picks.iter().any(|p| !seen.insert(p.clone())) {
                    out.push(ChecklistEntry {
                        severity: ChecklistSeverity::Illegal,
                        slot: SlotId::new("picks"),
                        step: StepId::new("two"),
                        rule: "Distinct picks".into(),
                        message: "picks must be different".into(),
                        source: "toy".into(),
                    });
                }
                out
            }),
            describe: Box::new(|sel| format!("{sel:?}")),
        },
        SlotRegistration::<ToyState> {
            id: SlotId::new("name"),
            step: StepId::new("two"),
            label: "Name".into(),
            required: true,
            presentation_hint: None,
            kind: Box::new(|_| SlotViewKind::Text { multiline: false }),
            unlock: Box::new(|_| Availability::Open),
            dependents: vec![],
            options: Box::new(|_| vec![]),
            apply: Box::new(|s, d| {
                let Selection::Text(t) = &d.selection else {
                    return Err(ApplyError::new("expected text"));
                };
                s.name = Some(t.clone());
                Ok(())
            }),
            validate: Box::new(|s, _| {
                if s.name.as_deref().unwrap_or("").is_empty() {
                    vec![incomplete("name", "Name", "name required")]
                } else {
                    vec![]
                }
            }),
            describe: Box::new(|sel| format!("{sel:?}")),
        },
        // Exists only when primary == b.
        SlotRegistration::<ToyState> {
            id: SlotId::new("bonus"),
            step: StepId::new("two"),
            label: "Bonus".into(),
            required: false,
            presentation_hint: None,
            kind: Box::new(|_| SlotViewKind::Single),
            unlock: Box::new(|s| match s.primary.as_deref() {
                Some("b") => Availability::Open,
                _ => Availability::Hidden,
            }),
            dependents: vec![],
            options: Box::new(|_| vec![opt("bx")]),
            apply: Box::new(|s, d| {
                s.bonus = Some(selection_id(&d.selection)?);
                Ok(())
            }),
            validate: Box::new(|_, _| vec![]),
            describe: Box::new(|sel| format!("{sel:?}")),
        },
    ];
    Engine::new(
        steps,
        slots,
        Box::new(ToyState::default),
        Box::new(|s: &ToyState| SheetView {
            name: s.name.clone().unwrap_or_default(),
            summary: vec![format!(
                "{}/{}",
                s.primary.clone().unwrap_or_default(),
                s.secondary.clone().unwrap_or_default()
            )],
            sections: vec![SheetSection {
                title: "Picks".into(),
                entries: vec![SheetEntry {
                    label: "count".into(),
                    value: s.picks.len().to_string(),
                    detail: None,
                }],
            }],
        }),
    )
}

fn input(id: &str, slot: &str, selection: Selection) -> DecisionInput {
    DecisionInput {
        id: DecisionId::new(id),
        slot: SlotId::new(slot),
        selection,
        source: DecisionSource::Player,
    }
}

fn one(id: &str, slot: &str, option: &str) -> DecisionInput {
    input(id, slot, Selection::Option(OptionId::new(option)))
}

fn append(engine: &Engine<ToyState>, log: &[Decision], i: DecisionInput) -> Vec<Decision> {
    match engine.append(log, i).expect("append accepted") {
        AppendOutcome::Appended(l) => l,
        AppendOutcome::AlreadyPresent => panic!("unexpected duplicate"),
    }
}

#[test]
fn empty_log_projects_with_incompletes_and_locks() {
    let engine = toy_engine();
    let projection = engine.project(&[]).unwrap();
    assert!(!projection.can_finalize);
    assert!(projection
        .checklist
        .iter()
        .all(|e| e.severity == ChecklistSeverity::Incomplete));
    let one = &projection.steps[0];
    let secondary = one
        .slots
        .iter()
        .find(|s| s.id.as_str() == "secondary")
        .unwrap();
    assert_eq!(
        secondary.locked_reason.as_deref(),
        Some("choose a primary first")
    );
    // Hidden slot is absent entirely.
    assert!(projection
        .steps
        .iter()
        .flat_map(|s| &s.slots)
        .all(|s| s.id.as_str() != "bonus"));
}

#[test]
fn append_is_idempotent_and_one_decision_per_slot() {
    let engine = toy_engine();
    let log = append(&engine, &[], one("d1", "primary", "a"));
    // Same decision ID again: idempotent success, nothing appended.
    assert_eq!(
        engine.append(&log, one("d1", "primary", "a")).unwrap(),
        AppendOutcome::AlreadyPresent
    );
    // New ID, same slot: rejected — clear first.
    let err = engine.append(&log, one("d2", "primary", "b")).unwrap_err();
    assert!(matches!(err, EngineError::InvalidDecision { .. }));
}

#[test]
fn locked_and_structurally_invalid_confirms_reject() {
    let engine = toy_engine();
    // Secondary is locked before primary.
    let err = engine
        .append(&[], one("d1", "secondary", "a1"))
        .unwrap_err();
    assert!(matches!(err, EngineError::InvalidDecision { .. }));
    // Unknown option is a structural rejection.
    let log = append(&engine, &[], one("d1", "primary", "a"));
    let err = engine
        .append(&log, one("d2", "secondary", "zzz"))
        .unwrap_err();
    assert!(matches!(err, EngineError::InvalidDecision { .. }));
    // Unknown slot.
    let err = engine.append(&log, one("d3", "nope", "a")).unwrap_err();
    assert!(matches!(err, EngineError::UnknownSlot { .. }));
}

#[test]
fn illegal_states_confirm_but_block_finalize() {
    let engine = toy_engine();
    let log = append(
        &engine,
        &[],
        input(
            "d1",
            "picks",
            Selection::Options(vec![OptionId::new("x"), OptionId::new("x")]),
        ),
    );
    let projection = engine.project(&log).unwrap();
    let illegal: Vec<_> = projection
        .checklist
        .iter()
        .filter(|e| e.severity == ChecklistSeverity::Illegal)
        .collect();
    assert_eq!(illegal.len(), 1);
    assert_eq!(illegal[0].rule, "Distinct picks");
    assert!(!projection.can_finalize);
}

#[test]
fn complete_draft_can_finalize() {
    let engine = toy_engine();
    let mut log = append(&engine, &[], one("d1", "primary", "a"));
    log = append(&engine, &log, one("d2", "secondary", "a2"));
    log = append(
        &engine,
        &log,
        input(
            "d3",
            "picks",
            Selection::Options(vec![OptionId::new("x"), OptionId::new("y")]),
        ),
    );
    log = append(
        &engine,
        &log,
        input("d4", "name", Selection::Text("Toy".into())),
    );
    let projection = engine.project(&log).unwrap();
    assert!(
        projection.can_finalize,
        "checklist: {:?}",
        projection.checklist
    );
    assert_eq!(projection.sheet.name, "Toy");
}

#[test]
fn clearing_cascades_to_dependents_and_renumbers() {
    let engine = toy_engine();
    let mut log = append(&engine, &[], one("d1", "primary", "b"));
    log = append(&engine, &log, one("d2", "secondary", "b1"));
    log = append(&engine, &log, one("d3", "bonus", "bx"));
    log = append(
        &engine,
        &log,
        input("d4", "name", Selection::Text("T".into())),
    );

    let preview = engine.clear_preview(&log, &SlotId::new("primary")).unwrap();
    let cleared_slots: Vec<&str> = preview.cleared.iter().map(|c| c.slot.as_str()).collect();
    assert_eq!(cleared_slots, vec!["primary", "secondary", "bonus"]);

    let cleared = engine.clear(&log, &SlotId::new("primary")).unwrap();
    assert_eq!(cleared.len(), 1);
    assert_eq!(cleared[0].slot.as_str(), "name");
    assert_eq!(cleared[0].order, 0, "survivors renumber densely");
    // The bonus slot is hidden again after its parent cleared.
    let projection = engine.project(&cleared).unwrap();
    assert!(projection
        .steps
        .iter()
        .flat_map(|s| &s.slots)
        .all(|s| s.id.as_str() != "bonus"));
}

#[test]
fn preview_is_stateless_and_replaces_in_place() {
    let engine = toy_engine();
    let log = append(&engine, &[], one("d1", "primary", "a"));
    let projection = engine.preview(&log, &one("d2", "primary", "b")).unwrap();
    assert_eq!(projection.sheet.summary[0], "b/");
    // Original log untouched.
    assert_eq!(engine.project(&log).unwrap().sheet.summary[0], "a/");
}

#[test]
fn replay_is_deterministic() {
    let engine = toy_engine();
    let mut log = append(&engine, &[], one("d1", "primary", "a"));
    log = append(&engine, &log, one("d2", "secondary", "a1"));
    let p1 = engine.project(&log).unwrap();
    let p2 = engine.project(&log).unwrap();
    assert_eq!(p1, p2);
    assert_eq!(engine.sheet(&log).unwrap(), p1.sheet);
}

mod random_walk {
    use super::*;
    use proptest::prelude::*;

    /// One step of a random wizard session.
    #[derive(Debug, Clone)]
    enum Op {
        Confirm { slot: usize, choice: usize },
        Clear { slot: usize },
    }

    fn op_strategy() -> impl Strategy<Value = Op> {
        prop_oneof![
            (0usize..5, 0usize..3).prop_map(|(slot, choice)| Op::Confirm { slot, choice }),
            (0usize..5).prop_map(|slot| Op::Clear { slot }),
        ]
    }

    const SLOTS: &[&str] = &["primary", "secondary", "picks", "name", "bonus"];

    fn selection_for(slot: &str, choice: usize) -> Selection {
        match slot {
            "primary" => Selection::Option(OptionId::new(["a", "b"][choice % 2])),
            "secondary" => Selection::Option(OptionId::new(["a1", "a2", "b1"][choice % 3])),
            "picks" => {
                let all = ["x", "y", "z"];
                Selection::Options(vec![
                    OptionId::new(all[choice % 3]),
                    OptionId::new(all[(choice + 1) % 3]),
                ])
            }
            "name" => Selection::Text(format!("N{choice}")),
            "bonus" => Selection::Option(OptionId::new("bx")),
            _ => unreachable!(),
        }
    }

    proptest! {
        /// Whatever a session does, the projection never breaks its
        /// invariants: dense chronological order, at most one decision per
        /// slot, deterministic replay, and can_finalize iff empty checklist.
        #[test]
        fn projection_invariants_hold(ops in proptest::collection::vec(op_strategy(), 0..40)) {
            let engine = toy_engine();
            let mut log: Vec<Decision> = vec![];
            for (i, op) in ops.iter().enumerate() {
                match op {
                    Op::Confirm { slot, choice } => {
                        let slot_name = SLOTS[slot % SLOTS.len()];
                        let input = input(
                            &format!("d{i}"),
                            slot_name,
                            selection_for(slot_name, *choice),
                        );
                        // Rejections are fine; accepted appends must fold.
                        if let Ok(AppendOutcome::Appended(new_log)) = engine.append(&log, input) {
                            log = new_log;
                        }
                    }
                    Op::Clear { slot } => {
                        let slot_name = SLOTS[slot % SLOTS.len()];
                        if let Ok(new_log) = engine.clear(&log, &SlotId::new(slot_name)) {
                            log = new_log;
                        }
                    }
                }

                // Invariants after every step.
                let orders: Vec<u32> = log.iter().map(|d| d.order).collect();
                prop_assert_eq!(&orders, &(0..log.len() as u32).collect::<Vec<_>>());
                let mut slots_seen = std::collections::BTreeSet::new();
                for d in &log {
                    prop_assert!(slots_seen.insert(d.slot.clone()), "two decisions in one slot");
                }
                let p1 = engine.project(&log);
                prop_assert!(p1.is_ok(), "accepted log must project: {:?}", p1.err());
                let p1 = p1.unwrap();
                let p2 = engine.project(&log).unwrap();
                prop_assert_eq!(&p1, &p2, "projection must be deterministic");
                prop_assert_eq!(p1.can_finalize, p1.checklist.is_empty());
            }
        }
    }
}
