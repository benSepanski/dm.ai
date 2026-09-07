//! Ability-score kind: the generation method (a Single over the shipped
//! method records), the roll slot a rolling method opens (its decision is
//! the whole roll history — every set kept, the last one live, rendered
//! as one option per set), and the assignment, a `Multi{6}` whose options
//! carry their ability as the group. The array and the roll offer their
//! values under every ability and validate one per ability and each value
//! at most as often as offered; the point buy offers the cost table's
//! scores under every ability against the budget, with a meter that shows
//! true overshoot.

use std::sync::Arc;

use engine_core::{ApplyError, Availability, SlotRegistration};
use types::{
    check_roll_shape, MeterView, OptionId, OptionView, Selection, SlotId, SlotViewKind, StepId,
};

use crate::data::{RollSpec, RulesData, ScoreMethodRecord};
use crate::mechanics::{
    describe_selection, dropped_faces, faces_text, group_total, illegal, incomplete, origin_label,
    parse_score_option, roll_totals, score_instance_id, sel_multi, sel_single, Ability, Dnd5eState,
    SLOT_SCORES_ASSIGN, SLOT_SCORES_METHOD, SLOT_SCORES_ROLL, STEP_SCORES,
};

fn method<'a>(data: &'a RulesData, state: &Dnd5eState) -> Option<&'a ScoreMethodRecord> {
    state
        .score_method
        .as_ref()
        .and_then(|id| data.score_method(id))
}

/// The rolling method's die shape under the current state, if the chosen
/// method rolls.
fn roll_spec(data: &RulesData, state: &Dnd5eState) -> Option<RollSpec> {
    method(data, state)
        .filter(|m| m.is_roll())
        .and_then(|m| m.roll)
}

/// Points spent under a point-buy method (unknown scores cost nothing —
/// `apply` already refused them).
fn points_spent(state: &Dnd5eState, method: &ScoreMethodRecord) -> i64 {
    Ability::ALL
        .into_iter()
        .filter_map(|a| state.base_score(a))
        .map(|s| method.cost_of(s).unwrap_or(0) as i64)
        .sum()
}

/// Render-ready totals of a set: "14, 12, 12, 10, 9, 8".
fn totals_text(set: &types::RolledSet, spec: RollSpec) -> String {
    roll_totals(set, spec)
        .iter()
        .map(|t| t.to_string())
        .collect::<Vec<_>>()
        .join(", ")
}

/// The method's values with their multiplicity: how often each distinct
/// value may be assigned (once per listing in an array, once per group
/// that rolled it; unlimited under a point buy).
fn offered_counts(state: &Dnd5eState, m: &ScoreMethodRecord) -> Vec<(u32, usize)> {
    let mut out: Vec<(u32, usize)> = Vec::new();
    for v in state.offered_scores(m) {
        match out.iter_mut().find(|(value, _)| *value == v) {
            Some((_, n)) => *n += 1,
            None => out.push((v, 1)),
        }
    }
    out
}

pub fn registrations(data: &Arc<RulesData>) -> Vec<SlotRegistration<Dnd5eState>> {
    let mut regs = Vec::new();

    // --- Method ---
    let d = data.clone();
    let d_apply = data.clone();
    let d_desc = data.clone();
    regs.push(SlotRegistration::<Dnd5eState> {
        id: SlotId::new(SLOT_SCORES_METHOD),
        step: StepId::new(STEP_SCORES),
        label: "Generation method".into(),
        required: true,
        presentation_hint: Box::new(|_| None),
        kind: Box::new(|_| SlotViewKind::Single),
        unlock: Box::new(|_| Availability::Open),
        dependents: vec![
            SlotId::new(SLOT_SCORES_ROLL),
            SlotId::new(SLOT_SCORES_ASSIGN),
        ],
        options: Box::new(move |_| {
            d.scores
                .methods
                .iter()
                .map(|m| OptionView {
                    id: OptionId::new(&m.id),
                    label: m.name.clone(),
                    summary: m.text.clone(),
                    details: if m.is_point_buy() {
                        vec![format!(
                            "Costs: {}",
                            m.offered_scores()
                                .iter()
                                .map(|s| format!("{s} = {}", m.cost_of(*s).unwrap_or(0)))
                                .collect::<Vec<_>>()
                                .join(", ")
                        )]
                    } else if let (true, Some(r)) = (m.is_roll(), m.roll) {
                        vec![format!(
                            "The app rolls for you, or you enter your own dice: {} sets of {}d{}, \
                             keeping the highest {}. Every roll is kept in your record.",
                            r.sets, r.dice, r.sides, r.keep
                        )]
                    } else {
                        vec![]
                    },
                    available: true,
                    unavailable_reason: None,
                    group: None,
                    badge: None,
                })
                .collect()
        }),
        apply: Box::new(move |state, decision| {
            let id = sel_single(&decision.selection)?;
            let record = d_apply
                .score_method(id.as_str())
                .ok_or_else(|| ApplyError::new(format!("unknown score method '{id}'")))?;
            state.score_method = Some(record.id.clone());
            Ok(())
        }),
        validate: Box::new(|state, _| {
            if state.score_method.is_none() {
                vec![incomplete(
                    SLOT_SCORES_METHOD,
                    STEP_SCORES,
                    "Ability Scores",
                    "Choose how to generate your ability scores",
                    "character creation",
                )]
            } else {
                vec![]
            }
        }),
        meters: Box::new(|_, _| vec![]),
        describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
    });

    // --- Roll (the rolling method's recorded input) ---
    let d_kind = data.clone();
    let d_unlock = data.clone();
    let d_opts = data.clone();
    let d_apply = data.clone();
    let d_val = data.clone();
    let d_desc = data.clone();
    regs.push(SlotRegistration::<Dnd5eState> {
        id: SlotId::new(SLOT_SCORES_ROLL),
        step: StepId::new(STEP_SCORES),
        label: "Roll ability scores".into(),
        required: true,
        presentation_hint: Box::new(|_| None),
        kind: Box::new(move |state| {
            // The shape sizes the entry grid; a hidden slot still reports
            // the method's shape when one is known.
            let spec = roll_spec(&d_kind, state).unwrap_or(RollSpec {
                sides: 6,
                dice: 4,
                keep: 3,
                sets: 6,
            });
            SlotViewKind::Roll {
                sides: spec.sides,
                dice: spec.dice,
                groups: spec.sets,
            }
        }),
        unlock: Box::new(move |state| match roll_spec(&d_unlock, state) {
            Some(_) => Availability::Open,
            None => Availability::Hidden,
        }),
        dependents: vec![SlotId::new(SLOT_SCORES_ASSIGN)],
        // The history, one entry per set, render-ready: totals as the
        // label, the faces with the dropped die in the details, the
        // origin as the badge, the live set the only available one.
        options: Box::new(move |state| {
            let Some(spec) = roll_spec(&d_opts, state) else {
                return vec![];
            };
            let last = state.rolled_sets.len();
            state
                .rolled_sets
                .iter()
                .enumerate()
                .map(|(i, set)| {
                    let live = i + 1 == last;
                    OptionView {
                        id: OptionId::new(format!("set.{}", i + 1)),
                        label: totals_text(set, spec),
                        summary: if live {
                            format!("Set {} of {last} — live; assign these", i + 1)
                        } else {
                            format!("Set {} of {last} — superseded", i + 1)
                        },
                        details: set
                            .groups
                            .iter()
                            .map(|g| {
                                let dropped = dropped_faces(g, spec);
                                if dropped.is_empty() {
                                    format!("{} → {}", faces_text(g), group_total(g, spec))
                                } else {
                                    format!(
                                        "{} → {} (dropped {})",
                                        faces_text(g),
                                        group_total(g, spec),
                                        faces_text(&dropped)
                                    )
                                }
                            })
                            .collect(),
                        available: live,
                        unavailable_reason: (!live).then(|| "superseded by a later roll".into()),
                        group: None,
                        badge: Some(origin_label(set.origin).into()),
                    }
                })
                .collect()
        }),
        apply: Box::new(move |state, decision| {
            let Selection::Rolled(sets) = &decision.selection else {
                return Err(ApplyError::new("expected rolled dice"));
            };
            let spec = roll_spec(&d_apply, state)
                .ok_or_else(|| ApplyError::new("choose the rolling method before rolling"))?;
            check_roll_shape(spec.sides, spec.dice, spec.sets, sets).map_err(ApplyError::new)?;
            state.rolled_sets = sets.clone();
            Ok(())
        }),
        validate: Box::new(move |state, _| {
            let Some(m) = method(&d_val, state).filter(|m| m.is_roll()) else {
                return vec![];
            };
            if state.rolled_sets.is_empty() {
                vec![incomplete(
                    SLOT_SCORES_ROLL,
                    STEP_SCORES,
                    &m.name,
                    "Roll your ability scores, or enter the dice you rolled",
                    &format!("from {}", m.name),
                )]
            } else {
                vec![]
            }
        }),
        meters: Box::new(|_, _| vec![]),
        describe: Box::new(move |sel| match sel {
            Selection::Rolled(sets) => {
                let spec = d_desc
                    .scores
                    .methods
                    .iter()
                    .find_map(|m| m.roll)
                    .unwrap_or(RollSpec {
                        sides: 6,
                        dice: 4,
                        keep: 3,
                        sets: 6,
                    });
                match sets.last() {
                    Some(live) => format!(
                        "{} ({}, set {} of {})",
                        totals_text(live, spec),
                        origin_label(live.origin),
                        sets.len(),
                        sets.len()
                    ),
                    None => "no sets".into(),
                }
            }
            other => describe_selection(&d_desc, other),
        }),
    });

    // --- Assignment ---
    let d_opts = data.clone();
    let d_unlock = data.clone();
    let d_apply = data.clone();
    let d_val = data.clone();
    let d_meter = data.clone();
    let d_desc = data.clone();
    let d_hint = data.clone();
    regs.push(SlotRegistration::<Dnd5eState> {
        id: SlotId::new(SLOT_SCORES_ASSIGN),
        step: StepId::new(STEP_SCORES),
        label: "Assign ability scores".into(),
        required: true,
        // A fixed pool of values (array, roll) places by tap; a point buy
        // steps each ability through the cost table.
        presentation_hint: Box::new(move |state| match method(&d_hint, state) {
            Some(m) if m.is_point_buy() => Some("assign-budget".into()),
            Some(_) => Some("assign-pool".into()),
            None => None,
        }),
        kind: Box::new(|_| SlotViewKind::Multi {
            count: Ability::ALL.len() as u32,
        }),
        unlock: Box::new(move |state| match method(&d_unlock, state) {
            None => Availability::Locked {
                reason: "choose a generation method first".into(),
            },
            Some(m) if m.is_roll() && state.rolled_sets.is_empty() => Availability::Locked {
                reason: "roll your ability scores first".into(),
            },
            Some(_) => Availability::Open,
        }),
        dependents: vec![],
        options: Box::new(move |state| {
            let Some(m) = method(&d_opts, state) else {
                return vec![];
            };
            let counts = offered_counts(state, m);
            let mut out = Vec::new();
            for ability in Ability::ALL {
                for (score, offered) in &counts {
                    // Under an array or a roll, a value is available for
                    // this ability while its assignments elsewhere have
                    // not used up every listing of it. A value offered
                    // more than once is one option per listing (a value
                    // rolled twice is two chips in the tray), the extra
                    // listings carrying an instance suffix on the id.
                    let taken_by: Vec<Ability> = if m.is_point_buy() {
                        vec![]
                    } else {
                        state
                            .assignments
                            .iter()
                            .filter(|(a, v)| *a != ability && v == score)
                            .map(|(a, _)| *a)
                            .collect()
                    };
                    let available = taken_by.len() < *offered;
                    for instance in 1..=*offered {
                        out.push(OptionView {
                            id: score_instance_id(ability, *score, instance),
                            label: score.to_string(),
                            summary: if m.is_point_buy() {
                                format!("{} points", m.cost_of(*score).unwrap_or(0))
                            } else {
                                String::new()
                            },
                            details: vec![],
                            available,
                            unavailable_reason: (!available).then(|| {
                                format!(
                                    "assigned to {}",
                                    taken_by
                                        .iter()
                                        .map(|a| a.name())
                                        .collect::<Vec<_>>()
                                        .join(", ")
                                )
                            }),
                            group: Some(ability.name().to_string()),
                            badge: None,
                        });
                    }
                }
            }
            out
        }),
        apply: Box::new(move |state, decision| {
            let ids = sel_multi(&decision.selection)?;
            let Some(m) = method(&d_apply, state) else {
                return Err(ApplyError::new(
                    "choose a generation method before assigning scores",
                ));
            };
            let offered = state.offered_scores(m);
            let mut picks = Vec::new();
            for id in ids {
                let (ability, value) = parse_score_option(id)
                    .ok_or_else(|| ApplyError::new(format!("'{id}' is not a score option")))?;
                if !offered.contains(&value) {
                    return Err(ApplyError::new(format!(
                        "{} does not offer a score of {value}",
                        m.name
                    )));
                }
                picks.push((ability, value));
            }
            state.assignments = picks;
            Ok(())
        }),
        validate: Box::new(move |state, decision| {
            let Some(m) = method(&d_val, state) else {
                return vec![];
            };
            let source = format!("from {}", m.name);
            let mut out = Vec::new();
            if decision.is_none() || state.assignments.is_empty() {
                out.push(incomplete(
                    SLOT_SCORES_ASSIGN,
                    STEP_SCORES,
                    "Ability Scores",
                    "Assign a score to each of the six abilities",
                    &source,
                ));
                return out;
            }
            // Exactly one pick per ability.
            let mut missing = Vec::new();
            for ability in Ability::ALL {
                let n = state
                    .assignments
                    .iter()
                    .filter(|(a, _)| *a == ability)
                    .count();
                if n == 0 {
                    missing.push(ability.name());
                } else if n > 1 {
                    out.push(illegal(
                        SLOT_SCORES_ASSIGN,
                        STEP_SCORES,
                        "Assign Ability Scores",
                        &format!(
                            "{} has {n} scores assigned — each ability takes exactly one",
                            ability.name()
                        ),
                        &source,
                    ));
                }
            }
            if !missing.is_empty() {
                out.push(incomplete(
                    SLOT_SCORES_ASSIGN,
                    STEP_SCORES,
                    "Ability Scores",
                    &format!("No score assigned to {}", missing.join(", ")),
                    &source,
                ));
            }
            if m.is_array() || m.is_roll() {
                // Each offered value used at most as often as offered: an
                // array lists each value once; a roll offers a total once
                // per group that rolled it.
                let counts = offered_counts(state, m);
                let mut over: Vec<String> = Vec::new();
                for (value, offered) in &counts {
                    let used = state
                        .assignments
                        .iter()
                        .filter(|(_, v)| v == value)
                        .count();
                    if used > *offered {
                        over.push(if m.is_array() {
                            value.to_string()
                        } else {
                            format!("{value} assigned {used} times, rolled {offered}")
                        });
                    }
                }
                if !over.is_empty() {
                    out.push(illegal(
                        SLOT_SCORES_ASSIGN,
                        STEP_SCORES,
                        &m.name,
                        &if m.is_array() {
                            format!(
                                "Each array value is used exactly once ({} assigned more than once)",
                                over.join(", ")
                            )
                        } else {
                            format!(
                                "Each rolled total is used as often as it was rolled ({})",
                                over.join("; ")
                            )
                        },
                        &source,
                    ));
                }
            }
            if m.is_point_buy() {
                let spent = points_spent(state, m);
                if spent > m.budget as i64 {
                    out.push(illegal(
                        SLOT_SCORES_ASSIGN,
                        STEP_SCORES,
                        "Point Cost",
                        &format!("You've spent {spent} points but the budget is {}", m.budget),
                        &source,
                    ));
                }
            }
            out
        }),
        // The always-on budget gauge for a point buy: what remains, and
        // Exceeded (negative, never clamped) once overspent.
        meters: Box::new(move |state, _| match method(&d_meter, state) {
            Some(m) if m.is_point_buy() => vec![MeterView::budget(
                "Points left",
                points_spent(state, m),
                m.budget as i64,
                |v| v.to_string(),
            )],
            _ => vec![],
        }),
        describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
    });

    regs
}
