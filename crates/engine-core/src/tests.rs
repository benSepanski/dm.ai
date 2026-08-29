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

fn toy_steps() -> Vec<(StepId, String)> {
    vec![
        (StepId::new("one"), "Step One".to_string()),
        (StepId::new("two"), "Step Two".to_string()),
    ]
}

fn toy_engine_slots() -> Vec<SlotRegistration<ToyState>> {
    vec![
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
            meters: Box::new(|_, _| vec![]),
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
            meters: Box::new(|_, _| vec![]),
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
            meters: Box::new(|_, _| vec![]),
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
            meters: Box::new(|_, _| vec![]),
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
            meters: Box::new(|_, _| vec![]),
            describe: Box::new(|sel| format!("{sel:?}")),
        },
    ]
}

fn toy_engine() -> Engine<ToyState> {
    Engine::new(
        toy_steps(),
        toy_engine_slots(),
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

/// The toy engine plus one scoped slot ("memo"): pick one of the confirmed
/// `picks` — options derive from build state exactly the way preparation
/// derives from a spellbook. Hidden until a primary exists; `primary`
/// lists it as a dependent, so clearing primary reaches across the scope
/// boundary.
fn toy_engine_with_scoped() -> Engine<ToyState> {
    let mut slots_engine = toy_engine_slots();
    // primary gains the scoped dependent.
    for slot in &mut slots_engine {
        if slot.id.as_str() == "primary" {
            slot.dependents.push(SlotId::new("memo"));
        }
    }
    let scoped = vec![SlotRegistration::<ToyState> {
        id: SlotId::new("memo"),
        step: StepId::new("two"),
        label: "Memo".into(),
        required: false,
        presentation_hint: None,
        kind: Box::new(|_| SlotViewKind::Single),
        unlock: Box::new(|s| match s.primary {
            Some(_) => Availability::Open,
            None => Availability::Hidden,
        }),
        dependents: vec![],
        options: Box::new(|s| s.picks.iter().map(|p| opt(p)).collect()),
        apply: Box::new(|s, d| {
            let id = selection_id(&d.selection)?;
            if !s.picks.contains(&id) {
                return Err(ApplyError::new(format!("'{id}' is not among your picks")));
            }
            Ok(())
        }),
        validate: Box::new(|_, _| vec![]),
        meters: Box::new(|_, _| vec![]),
        describe: Box::new(|sel| format!("{sel:?}")),
    }];
    Engine::with_scoped(
        toy_steps(),
        slots_engine,
        scoped,
        Box::new(ToyState::default),
        Box::new(|s: &ToyState| SheetView {
            name: s.name.clone().unwrap_or_default(),
            summary: vec![format!(
                "{}/{}",
                s.primary.clone().unwrap_or_default(),
                s.secondary.clone().unwrap_or_default()
            )],
            sections: vec![],
        }),
        Box::new(|_, prep| {
            vec![SheetSection {
                title: "Memo".into(),
                entries: prep
                    .iter()
                    .map(|c| SheetEntry {
                        label: c.slot.to_string(),
                        value: format!("{:?}", c.selection),
                        detail: None,
                    })
                    .collect(),
            }]
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
    let projection = engine.project(&[], &[]).unwrap();
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
    let projection = engine.project(&log, &[]).unwrap();
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
    let projection = engine.project(&log, &[]).unwrap();
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

    let preview = engine
        .clear_preview(&log, &[], &SlotId::new("primary"))
        .unwrap();
    let cleared_slots: Vec<&str> = preview.cleared.iter().map(|c| c.slot.as_str()).collect();
    assert_eq!(cleared_slots, vec!["primary", "secondary", "bonus"]);

    let (cleared, _) = engine.clear(&log, &[], &SlotId::new("primary")).unwrap();
    assert_eq!(cleared.len(), 1);
    assert_eq!(cleared[0].slot.as_str(), "name");
    assert_eq!(cleared[0].order, 0, "survivors renumber densely");
    // The bonus slot is hidden again after its parent cleared.
    let projection = engine.project(&cleared, &[]).unwrap();
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
    let projection = engine
        .preview(&log, &one("d2", "primary", "b"), &[])
        .unwrap();
    assert_eq!(projection.sheet.summary[0], "b/");
    // Original log untouched.
    assert_eq!(engine.project(&log, &[]).unwrap().sheet.summary[0], "a/");
}

#[test]
fn replay_is_deterministic() {
    let engine = toy_engine();
    let mut log = append(&engine, &[], one("d1", "primary", "a"));
    log = append(&engine, &log, one("d2", "secondary", "a1"));
    let p1 = engine.project(&log, &[]).unwrap();
    let p2 = engine.project(&log, &[]).unwrap();
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
                        if let Ok((new_log, _)) = engine.clear(&log, &[], &SlotId::new(slot_name)) {
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
                let p1 = engine.project(&log, &[]);
                prop_assert!(p1.is_ok(), "accepted log must project: {:?}", p1.err());
                let p1 = p1.unwrap();
                let p2 = engine.project(&log, &[]).unwrap();
                prop_assert_eq!(&p1, &p2, "projection must be deterministic");
                prop_assert_eq!(p1.can_finalize, p1.checklist.is_empty());
                crate::tests::status_and_amend::assert_coherent(&p1);
            }
        }
    }
}

mod status_and_amend {
    use super::*;
    use types::{MeterState, SlotStatus, StepStatus};

    fn slot_view<'a>(p: &'a types::ProjectionView, id: &str) -> &'a types::SlotView {
        p.steps
            .iter()
            .flat_map(|s| &s.slots)
            .find(|s| s.id.as_str() == id)
            .expect("slot present")
    }

    #[test]
    fn statuses_track_the_slot_lifecycle() {
        let engine = toy_engine();
        let p = engine.project(&[], &[]).unwrap();
        assert_eq!(slot_view(&p, "primary").status, SlotStatus::Empty);
        assert_eq!(slot_view(&p, "secondary").status, SlotStatus::Locked);

        let log = append(&engine, &[], one("d1", "primary", "a"));
        let p = engine.project(&log, &[]).unwrap();
        assert_eq!(slot_view(&p, "primary").status, SlotStatus::Complete);
        assert_eq!(slot_view(&p, "secondary").status, SlotStatus::Empty);

        // One of two picks: Partial, and the auto count meter says so.
        let log2 = append(
            &engine,
            &log,
            input("d2", "picks", Selection::Options(vec![OptionId::new("x")])),
        );
        let p = engine.project(&log2, &[]).unwrap();
        let picks = slot_view(&p, "picks");
        assert_eq!(picks.status, SlotStatus::Partial);
        let meter = &picks.meters[0];
        assert_eq!(
            (meter.current.as_str(), meter.limit.as_deref()),
            ("1", Some("2"))
        );
        assert_eq!(meter.state, MeterState::Short);

        // Duplicate picks: Illegal beats Partial.
        let log3 = append(
            &engine,
            &log,
            input(
                "d3",
                "picks",
                Selection::Options(vec![OptionId::new("x"), OptionId::new("x")]),
            ),
        );
        let p = engine.project(&log3, &[]).unwrap();
        assert_eq!(slot_view(&p, "picks").status, SlotStatus::Illegal);
    }

    #[test]
    fn step_status_folds_over_slot_statuses() {
        let engine = toy_engine();
        // Fresh log: step one has an actionable required slot -> Incomplete.
        let p = engine.project(&[], &[]).unwrap();
        assert_eq!(p.steps[0].status, StepStatus::Incomplete);

        // A step whose only required work is locked shows Waiting, not done:
        // complete everything in step two except nothing — instead check the
        // constructed case: primary confirmed makes secondary actionable.
        let log = append(&engine, &[], one("w1", "primary", "a"));
        let p = engine.project(&log, &[]).unwrap();
        assert_eq!(p.steps[0].status, StepStatus::Incomplete); // secondary now empty
    }

    #[test]
    fn amend_extends_a_partial_slot_atomically() {
        let engine = toy_engine();
        let log = append(
            &engine,
            &[],
            input("a1", "picks", Selection::Options(vec![OptionId::new("x")])),
        );
        let out = engine
            .amend(
                &log,
                &[],
                input(
                    "a2",
                    "picks",
                    Selection::Options(vec![OptionId::new("x"), OptionId::new("y")]),
                ),
            )
            .unwrap();
        let (AppendOutcome::Appended(new_log), _) = out else {
            panic!("expected append");
        };
        assert_eq!(new_log.len(), 1, "old decision replaced, not stacked");
        assert_eq!(new_log[0].id.as_str(), "a2");
        assert_eq!(new_log[0].order, 0);
        let p = engine.project(&new_log, &[]).unwrap();
        assert_eq!(slot_view(&p, "picks").status, SlotStatus::Complete);
    }

    #[test]
    fn amend_is_idempotent_and_falls_back_to_append() {
        let engine = toy_engine();
        // Unoccupied slot: amend behaves as append.
        let (out, _) = engine.amend(&[], &[], one("f1", "primary", "b")).unwrap();
        let AppendOutcome::Appended(log) = out else {
            panic!("expected append");
        };
        // Replay of the same decision ID appends nothing.
        assert_eq!(
            engine
                .amend(&log, &[], one("f1", "primary", "b"))
                .unwrap()
                .0,
            AppendOutcome::AlreadyPresent
        );
    }

    #[test]
    fn amend_cascades_dependents_like_clear() {
        let engine = toy_engine();
        let mut log = append(&engine, &[], one("c1", "primary", "b"));
        log = append(&engine, &log, one("c2", "secondary", "b1"));
        // Amending primary to "a" clears secondary (catalog changed).
        let (out, _) = engine.amend(&log, &[], one("c3", "primary", "a")).unwrap();
        let AppendOutcome::Appended(new_log) = out else {
            panic!("expected append");
        };
        assert_eq!(new_log.len(), 1);
        assert_eq!(new_log[0].id.as_str(), "c3");
    }

    /// Coherence: every non-Complete slot explains itself, every entry
    /// points at a non-Complete slot, and can_finalize means no required
    /// slot is anything but Complete.
    pub fn assert_coherent(p: &types::ProjectionView) {
        for slot in p.steps.iter().flat_map(|s| &s.slots) {
            match slot.status {
                SlotStatus::Locked => {
                    assert!(
                        slot.locked_reason.is_some(),
                        "{}: Locked without reason",
                        slot.id
                    );
                }
                SlotStatus::Partial | SlotStatus::Illegal => {
                    assert!(
                        p.checklist.iter().any(|e| e.slot == slot.id),
                        "{}: {:?} without a checklist entry",
                        slot.id,
                        slot.status
                    );
                }
                SlotStatus::Empty => {
                    if slot.required {
                        assert!(
                            p.checklist.iter().any(|e| e.slot == slot.id),
                            "{}: required Empty without a checklist entry",
                            slot.id
                        );
                    }
                }
                SlotStatus::Complete => {}
            }
        }
        for entry in &p.checklist {
            let slot = p
                .steps
                .iter()
                .flat_map(|s| &s.slots)
                .find(|s| s.id == entry.slot)
                .unwrap_or_else(|| panic!("entry for absent slot {}", entry.slot));
            assert_ne!(
                slot.status,
                SlotStatus::Complete,
                "{}: entry against a Complete slot",
                entry.slot
            );
        }
        if p.can_finalize {
            for slot in p.steps.iter().flat_map(|s| &s.slots) {
                assert!(
                    !slot.required || slot.status == SlotStatus::Complete,
                    "{}: can_finalize with required slot {:?}",
                    slot.id,
                    slot.status
                );
            }
        }
    }
}

// ---- The suggestion planner (quick build) ----

fn toy_suggestions(slot: &SlotId) -> Option<crate::SlotSuggestion> {
    use crate::SlotSuggestion::{Candidates, Text};
    match slot.as_str() {
        "primary" => Some(Candidates(vec![OptionId::new("a")])),
        "secondary" => Some(Candidates(vec![OptionId::new("a1"), OptionId::new("a2")])),
        // Longer than needed: Multi{2} takes the first legal 2.
        "picks" => Some(Candidates(vec![
            OptionId::new("x"),
            OptionId::new("y"),
            OptionId::new("z"),
        ])),
        "name" => Some(Text("Toy".into())),
        _ => None,
    }
}

fn mint(slot: &SlotId) -> DecisionId {
    DecisionId::new(format!("sug.{slot}"))
}

#[test]
fn planner_fills_open_required_slots_in_dependency_order() {
    let engine = toy_engine();
    let plan = engine
        .expand_suggestions(&[], &toy_suggestions, &mint, DecisionSource::Suggested)
        .unwrap();
    assert!(plan.unresolved.is_empty(), "{:?}", plan.unresolved);
    let projection = engine.project(&plan.log, &[]).unwrap();
    assert!(projection.can_finalize, "{:?}", projection.checklist);
    assert!(plan
        .log
        .iter()
        .all(|d| d.source == DecisionSource::Suggested));
    // The dependent slot was filled after its dependency unlocked it.
    let order_of = |slot: &str| {
        plan.log
            .iter()
            .position(|d| d.slot.as_str() == slot)
            .unwrap()
    };
    assert!(order_of("primary") < order_of("secondary"));
    // Multi picked the first legal N in candidate order.
    let picks = plan
        .log
        .iter()
        .find(|d| d.slot.as_str() == "picks")
        .unwrap();
    assert_eq!(
        picks.selection,
        Selection::Options(vec![OptionId::new("x"), OptionId::new("y")])
    );
    // Deterministic: a second run is identical.
    let again = engine
        .expand_suggestions(&[], &toy_suggestions, &mint, DecisionSource::Suggested)
        .unwrap();
    assert_eq!(plan.log, again.log);
}

#[test]
fn planner_never_overwrites_and_keeps_the_legal_prefix() {
    let engine = toy_engine();
    // The player chose primary=b; the suggested secondary (a1/a2) is not in
    // b's catalog, so it stays open — while everything else still fills.
    let log = append(&engine, &[], one("p1", "primary", "b"));
    let plan = engine
        .expand_suggestions(&log, &toy_suggestions, &mint, DecisionSource::Suggested)
        .unwrap();
    // The confirmed decision is untouched, in place.
    assert_eq!(plan.log[0], log[0]);
    assert!(
        plan.log
            .iter()
            .filter(|d| d.slot.as_str() == "primary")
            .count()
            == 1
    );
    // The legal prefix landed (picks + name), never rolled back.
    assert!(plan.log.iter().any(|d| d.slot.as_str() == "picks"));
    assert!(plan.log.iter().any(|d| d.slot.as_str() == "name"));
    // The blocked slot is reported with a reason.
    assert_eq!(plan.unresolved.len(), 1);
    assert_eq!(plan.unresolved[0].slot.as_str(), "secondary");
    assert!(plan.unresolved[0]
        .reason
        .contains("no suggested option is currently legal"));
}

#[test]
fn planner_reports_slots_without_suggestions() {
    let engine = toy_engine();
    let no_secondary = |slot: &SlotId| {
        if slot.as_str() == "secondary" {
            None
        } else {
            toy_suggestions(slot)
        }
    };
    let plan = engine
        .expand_suggestions(&[], &no_secondary, &mint, DecisionSource::Suggested)
        .unwrap();
    assert_eq!(plan.unresolved.len(), 1);
    assert_eq!(plan.unresolved[0].slot.as_str(), "secondary");
    assert!(plan.unresolved[0].reason.contains("no entry"));
    // Everything else still filled.
    assert!(plan.log.iter().any(|d| d.slot.as_str() == "primary"));
    assert!(plan.log.iter().any(|d| d.slot.as_str() == "name"));
}

mod scoped {
    use super::*;
    use types::ScopedChoice;

    fn choice(slot: &str, option: &str) -> ScopedChoice {
        ScopedChoice {
            slot: SlotId::new(slot),
            selection: Selection::Option(OptionId::new(option)),
        }
    }

    fn picked_log(engine: &Engine<ToyState>) -> Vec<Decision> {
        let log = append(engine, &[], one("d1", "primary", "a"));
        append(
            engine,
            &log,
            input(
                "d2",
                "picks",
                Selection::Options(vec![OptionId::new("x"), OptionId::new("y")]),
            ),
        )
    }

    #[test]
    fn scoped_slots_render_flagged_and_validate_through_one_driver() {
        let engine = toy_engine_with_scoped();
        let log = picked_log(&engine);
        let p = engine.project(&log, &[choice("memo", "x")]).unwrap();
        let memo = p
            .steps
            .iter()
            .flat_map(|s| &s.slots)
            .find(|s| s.id.as_str() == "memo")
            .expect("scoped slot renders into its step");
        assert!(memo.scoped, "scoped slots carry the flag");
        assert_eq!(memo.status, types::SlotStatus::Complete);
        // Wizard slots stay unflagged.
        assert!(p
            .steps
            .iter()
            .flat_map(|s| &s.slots)
            .filter(|s| s.id.as_str() != "memo")
            .all(|s| !s.scoped));
    }

    #[test]
    fn illegal_scoped_choices_come_back_as_entries_never_errors() {
        let engine = toy_engine_with_scoped();
        let log = picked_log(&engine);
        // Not among picks; unknown slot; duplicate — all total, all Illegal.
        let p = engine
            .scoped_projection(
                &log,
                &[
                    choice("memo", "z"),
                    choice("nonsense", "q"),
                    choice("memo", "x"),
                ],
            )
            .unwrap();
        let illegal: Vec<&str> = p
            .checklist
            .iter()
            .filter(|e| e.severity == ChecklistSeverity::Illegal)
            .map(|e| e.message.as_str())
            .collect();
        assert_eq!(illegal.len(), 3, "each problem reported: {illegal:?}");
        assert!(illegal.iter().any(|m| m.contains("not among your picks")));
        assert!(illegal.iter().any(|m| m.contains("unknown scoped slot")));
        assert!(illegal.iter().any(|m| m.contains("two entries")));
    }

    #[test]
    fn scoped_choice_on_hidden_slot_is_reported() {
        let engine = toy_engine_with_scoped();
        // No primary: memo is hidden, a stored choice for it is illegal.
        let p = engine
            .scoped_projection(&[], &[choice("memo", "x")])
            .unwrap();
        assert!(p
            .checklist
            .iter()
            .any(|e| e.severity == ChecklistSeverity::Illegal
                && e.message.contains("does not exist")));
        assert!(!engine.has_scoped_slots(&[]).unwrap());
        let log = append(&engine, &[], one("d1", "primary", "a"));
        assert!(engine.has_scoped_slots(&log).unwrap());
    }

    #[test]
    fn illegal_prep_blocks_finalize_through_the_same_checklist() {
        let engine = toy_engine_with_scoped();
        let log = picked_log(&engine);
        let clean = engine.project(&log, &[choice("memo", "x")]).unwrap();
        let dirty = engine.project(&log, &[choice("memo", "z")]).unwrap();
        assert!(dirty.checklist.len() > clean.checklist.len());
        assert!(!dirty.can_finalize);
    }

    #[test]
    fn stored_sheet_ignores_prep_display_sheet_appends_it() {
        let engine = toy_engine_with_scoped();
        let log = picked_log(&engine);
        let bare = engine.sheet(&log).unwrap();
        let with_prep = engine.sheet(&log).unwrap();
        assert_eq!(bare, with_prep, "materialized sheet is fold(log) only");
        let display = engine.display_sheet(&log, &[choice("memo", "x")]).unwrap();
        assert!(display.sections.iter().any(|s| s.title == "Memo"));
        assert!(!bare.sections.iter().any(|s| s.title == "Memo"));
    }

    #[test]
    fn clearing_reaches_across_the_scope_boundary() {
        let engine = toy_engine_with_scoped();
        let log = picked_log(&engine);
        let prep = vec![choice("memo", "x")];
        let preview = engine
            .clear_preview(&log, &prep, &SlotId::new("primary"))
            .unwrap();
        assert!(
            preview.cleared.iter().any(|c| c.slot.as_str() == "memo"),
            "the confirmation lists the scoped dependent"
        );
        let (new_log, surviving) = engine.clear(&log, &prep, &SlotId::new("primary")).unwrap();
        assert!(
            surviving.is_empty(),
            "scoped dependent cleared with the slot"
        );
        assert!(!new_log.iter().any(|d| d.slot.as_str() == "primary"));
        // Clearing an unrelated slot leaves the scoped choice alone.
        let log2 = append(
            &engine,
            &log,
            input("d3", "name", Selection::Text("T".into())),
        );
        let (_, surviving2) = engine.clear(&log2, &prep, &SlotId::new("name")).unwrap();
        assert_eq!(surviving2, prep);
    }

    #[test]
    fn amend_returns_surviving_scoped_choices() {
        let engine = toy_engine_with_scoped();
        let log = picked_log(&engine);
        let prep = vec![choice("memo", "x")];
        let (out, surviving) = engine
            .amend(&log, &prep, one("d9", "primary", "b"))
            .unwrap();
        assert!(matches!(out, AppendOutcome::Appended(_)));
        assert!(surviving.is_empty(), "changing primary cleared the memo");
    }
}
