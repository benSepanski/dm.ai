//! Ability-score kind: the generation method (a Single over the shipped
//! method records — `dnd-dice` appends rolling as a third record) and the
//! assignment, a `Multi{6}` whose options carry their ability as the
//! group. The array method offers each array value under every ability
//! and validates one per ability and each value once; the point buy
//! offers the cost table's scores under every ability against the budget,
//! with a meter that shows true overshoot.

use std::sync::Arc;

use engine_core::{ApplyError, Availability, SlotRegistration};
use types::{MeterView, OptionId, OptionView, SlotId, SlotViewKind, StepId};

use crate::data::{RulesData, ScoreMethodRecord};
use crate::mechanics::{
    describe_selection, illegal, incomplete, parse_score_option, score_option_id, sel_multi,
    sel_single, Ability, Dnd5eState, SLOT_SCORES_ASSIGN, SLOT_SCORES_METHOD, STEP_SCORES,
};

fn method<'a>(data: &'a RulesData, state: &Dnd5eState) -> Option<&'a ScoreMethodRecord> {
    state
        .score_method
        .as_ref()
        .and_then(|id| data.score_method(id))
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
        presentation_hint: None,
        kind: Box::new(|_| SlotViewKind::Single),
        unlock: Box::new(|_| Availability::Open),
        dependents: vec![SlotId::new(SLOT_SCORES_ASSIGN)],
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

    // --- Assignment ---
    let d_opts = data.clone();
    let d_apply = data.clone();
    let d_val = data.clone();
    let d_meter = data.clone();
    let d_desc = data.clone();
    regs.push(SlotRegistration::<Dnd5eState> {
        id: SlotId::new(SLOT_SCORES_ASSIGN),
        step: StepId::new(STEP_SCORES),
        label: "Assign ability scores".into(),
        required: true,
        presentation_hint: Some("one-per-group".into()),
        kind: Box::new(|_| SlotViewKind::Multi {
            count: Ability::ALL.len() as u32,
        }),
        unlock: Box::new(|state| match state.score_method {
            Some(_) => Availability::Open,
            None => Availability::Locked {
                reason: "choose a generation method first".into(),
            },
        }),
        dependents: vec![],
        options: Box::new(move |state| {
            let Some(m) = method(&d_opts, state) else {
                return vec![];
            };
            let scores = m.offered_scores();
            let mut out = Vec::new();
            for ability in Ability::ALL {
                for score in &scores {
                    // Under an array, a value assigned to another ability
                    // is shown but not selectable here.
                    let taken_by = if m.is_array() {
                        state
                            .assignments
                            .iter()
                            .find(|(a, v)| *a != ability && v == score)
                            .map(|(a, _)| *a)
                    } else {
                        None
                    };
                    out.push(OptionView {
                        id: score_option_id(ability, *score),
                        label: score.to_string(),
                        summary: if m.is_point_buy() {
                            format!("{} points", m.cost_of(*score).unwrap_or(0))
                        } else {
                            String::new()
                        },
                        details: vec![],
                        available: taken_by.is_none(),
                        unavailable_reason: taken_by.map(|a| format!("assigned to {}", a.name())),
                        group: Some(ability.name().to_string()),
                        badge: None,
                    });
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
            let offered = m.offered_scores();
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
                    "Assign Ability Scores",
                    &format!("No score assigned to {}", missing.join(", ")),
                    &source,
                ));
            }
            if m.is_array() {
                // Each array value used once.
                let mut values: Vec<u32> = state.assignments.iter().map(|(_, v)| *v).collect();
                values.sort_unstable();
                let mut dupes: Vec<u32> = Vec::new();
                for w in values.windows(2) {
                    if w[0] == w[1] && !dupes.contains(&w[0]) {
                        dupes.push(w[0]);
                    }
                }
                if !dupes.is_empty() {
                    out.push(illegal(
                        SLOT_SCORES_ASSIGN,
                        STEP_SCORES,
                        &m.name,
                        &format!(
                            "Each array value is used exactly once ({} assigned more than once)",
                            dupes
                                .iter()
                                .map(|v| v.to_string())
                                .collect::<Vec<_>>()
                                .join(", ")
                        ),
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
                "Points",
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
