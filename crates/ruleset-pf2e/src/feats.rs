//! Feats kind: the class feat slot and the feat-chooser slots that specific
//! heritages/ancestry feats grant (general feats, Natural Ambition's bonus
//! class feat). Chooser slots unlock from folded state, never by asking a
//! sibling module.

use std::sync::Arc;

use engine_core::{ApplyError, Availability, SlotRegistration};
use types::{OptionId, OptionView, SlotId, SlotViewKind, StepId};

use crate::data::{Effect, RulesData};
use crate::mechanics::{
    describe_selection, incomplete, prereq_description, prereq_unavailable, sel_single, Pf2eState,
    SLOT_CLASS_FEAT, SLOT_FEAT_GENERAL_FEAT, SLOT_FEAT_LORE, SLOT_HERITAGE_GENERAL_FEAT,
    SLOT_NATURAL_AMBITION, SLOT_PROFICIENCY_CHOICE,
};

const STEP: &str = crate::mechanics::STEP_CLASS;
const STEP_ANCESTRY: &str = crate::mechanics::STEP_ANCESTRY;

fn class_feat_options(
    data: &RulesData,
    state: &Pf2eState,
    exclude: &[&Option<String>],
) -> Vec<OptionView> {
    let Some(class) = &state.class else {
        return vec![];
    };
    data.class_feats
        .iter()
        .filter(|f| &f.class == class && f.level == 1)
        .map(|f| {
            let already = exclude.iter().any(|e| e.as_deref() == Some(f.id.as_str()))
                || state.bonus_class_feats.contains(&f.id);
            let mut details = vec![format!("{} · {}", f.actions, f.text)];
            if let Some(req) = &f.requirements {
                details.push(format!("Requirements (at time of use): {req}"));
            }
            OptionView {
                id: OptionId::new(&f.id),
                label: f.name.clone(),
                summary: String::new(),
                details,
                available: !already,
                unavailable_reason: already.then(|| "already selected".to_string()),
            }
        })
        .collect()
}

fn general_feat_options(data: &RulesData, state: &Pf2eState) -> Vec<OptionView> {
    data.general_feats
        .iter()
        .map(|f| {
            let unavailable = if state.chosen_general_feats.contains(&f.id) {
                Some("already selected".to_string())
            } else {
                prereq_unavailable(data, &f.prerequisites, state)
            };
            let mut details = vec![f.text.clone()];
            for p in &f.prerequisites {
                details.push(format!("Prerequisite: {}", prereq_description(data, p)));
            }
            OptionView {
                id: OptionId::new(&f.id),
                label: f.name.clone(),
                summary: String::new(),
                details,
                available: unavailable.is_none(),
                unavailable_reason: unavailable,
            }
        })
        .collect()
}

fn heritage_grants_general_feat(data: &RulesData, state: &Pf2eState) -> bool {
    state
        .heritage
        .as_ref()
        .and_then(|id| data.heritage(id))
        .map(|h| {
            h.effects.iter().any(|e| {
                matches!(e, Effect::ChooseFromCatalog { catalog, .. } if catalog == "general_feats")
            })
        })
        .unwrap_or(false)
}

fn feat_grants(data: &RulesData, state: &Pf2eState, catalog: &str) -> bool {
    state
        .ancestry_feat
        .as_ref()
        .and_then(|id| data.ancestry_feat(id))
        .map(|f| {
            f.effects
                .iter()
                .any(|e| matches!(e, Effect::ChooseFromCatalog { catalog: c, .. } if c == catalog))
        })
        .unwrap_or(false)
}

/// The (targets, rank, source label) of a ChooseProficiencyOverride effect
/// anywhere in the folded state (Canny Acumen), if any.
fn proficiency_choice_grant(state: &Pf2eState) -> Option<(Vec<String>, String, String)> {
    state.effects.iter().find_map(|e| match e {
        Effect::ChooseProficiencyOverride {
            targets,
            rank,
            source_label,
        } => Some((targets.clone(), rank.clone(), source_label.clone())),
        _ => None,
    })
}

fn apply_general_feat(
    data: &RulesData,
    state: &mut Pf2eState,
    selection: &types::Selection,
) -> Result<(), ApplyError> {
    let id = crate::mechanics::sel_single(selection)?;
    let record = data
        .general_feat(id.as_str())
        .ok_or_else(|| ApplyError::new(format!("unknown general feat '{id}'")))?;
    // Prerequisites are re-checked on apply — the server folds through
    // this same path, so a raw request cannot skip the greying rule.
    if let Some(reason) = prereq_unavailable(data, &record.prerequisites, state) {
        return Err(ApplyError::new(format!(
            "'{}' is not available: {reason}",
            record.name
        )));
    }
    state.chosen_general_feats.push(record.id.clone());
    state.effects.extend(record.effects.iter().cloned());
    Ok(())
}

pub fn registrations(data: &Arc<RulesData>) -> Vec<SlotRegistration<Pf2eState>> {
    let mut regs = Vec::new();

    // --- The class feat ---
    let d = data.clone();
    let d_apply = data.clone();
    let d_desc = data.clone();
    regs.push(SlotRegistration::<Pf2eState> {
        id: SlotId::new(SLOT_CLASS_FEAT),
        step: StepId::new(STEP),
        label: "Class feat".into(),
        required: true,
        presentation_hint: None,
        kind: Box::new(|_| SlotViewKind::Single),
        unlock: Box::new(|state| match state.class {
            Some(_) => Availability::Open,
            None => Availability::Locked {
                reason: "choose a class first".into(),
            },
        }),
        dependents: vec![],
        options: Box::new(move |state| class_feat_options(&d, state, &[])),
        apply: Box::new(move |state, decision| {
            let id = sel_single(&decision.selection)?;
            let record = d_apply
                .class_feat(id.as_str())
                .ok_or_else(|| ApplyError::new(format!("unknown class feat '{id}'")))?;
            if state.class.as_deref() != Some(record.class.as_str()) {
                return Err(ApplyError::new(format!(
                    "feat '{}' does not belong to the chosen class",
                    record.name
                )));
            }
            state.class_feat = Some(record.id.clone());
            Ok(())
        }),
        validate: Box::new(|state, decision| {
            if state.class.is_some() && decision.is_none() {
                vec![incomplete(
                    SLOT_CLASS_FEAT,
                    STEP,
                    "Class feat",
                    "Choose a level-1 class feat",
                    "from Class",
                )]
            } else {
                vec![]
            }
        }),
        meters: Box::new(|_, _| vec![]),
        describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
    });

    // --- Heritage-granted general feat (Versatile Human) ---
    let d = data.clone();
    let d_unlock = data.clone();
    let d_apply = data.clone();
    let d_val = data.clone();
    let d_desc = data.clone();
    regs.push(SlotRegistration::<Pf2eState> {
        id: SlotId::new(SLOT_HERITAGE_GENERAL_FEAT),
        step: StepId::new(STEP_ANCESTRY),
        label: "General feat (heritage)".into(),
        required: true,
        presentation_hint: None,
        kind: Box::new(|_| SlotViewKind::Single),
        unlock: Box::new(move |state| {
            if heritage_grants_general_feat(&d_unlock, state) {
                Availability::Open
            } else {
                Availability::Hidden
            }
        }),
        // A chosen general feat can carry a ChooseLore or proficiency-
        // choice effect; those picks die with the feat.
        dependents: vec![
            SlotId::new(SLOT_FEAT_LORE),
            SlotId::new(SLOT_PROFICIENCY_CHOICE),
        ],
        options: Box::new(move |state| general_feat_options(&d, state)),
        apply: Box::new(move |state, decision| {
            apply_general_feat(&d_apply, state, &decision.selection)
        }),
        validate: Box::new(move |state, decision| {
            if heritage_grants_general_feat(&d_val, state) && decision.is_none() {
                vec![incomplete(
                    SLOT_HERITAGE_GENERAL_FEAT,
                    STEP_ANCESTRY,
                    "Heritage",
                    "Choose the general feat your heritage grants",
                    "from Heritage",
                )]
            } else {
                vec![]
            }
        }),
        meters: Box::new(|_, _| vec![]),
        describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
    });

    // --- Ancestry-feat-granted general feat (General Training) ---
    let d = data.clone();
    let d_unlock = data.clone();
    let d_apply = data.clone();
    let d_val = data.clone();
    let d_desc = data.clone();
    regs.push(SlotRegistration::<Pf2eState> {
        id: SlotId::new(SLOT_FEAT_GENERAL_FEAT),
        step: StepId::new(STEP_ANCESTRY),
        label: "General feat (ancestry feat)".into(),
        required: true,
        presentation_hint: None,
        kind: Box::new(|_| SlotViewKind::Single),
        unlock: Box::new(move |state| {
            if feat_grants(&d_unlock, state, "general_feats") {
                Availability::Open
            } else {
                Availability::Hidden
            }
        }),
        // Same as the heritage-granted slot: a ChooseLore- or proficiency-
        // choice-carrying feat's picks die with the feat.
        dependents: vec![
            SlotId::new(SLOT_FEAT_LORE),
            SlotId::new(SLOT_PROFICIENCY_CHOICE),
        ],
        options: Box::new(move |state| general_feat_options(&d, state)),
        apply: Box::new(move |state, decision| {
            apply_general_feat(&d_apply, state, &decision.selection)
        }),
        validate: Box::new(move |state, decision| {
            if feat_grants(&d_val, state, "general_feats") && decision.is_none() {
                vec![incomplete(
                    SLOT_FEAT_GENERAL_FEAT,
                    STEP_ANCESTRY,
                    "Ancestry feat",
                    "Choose the general feat your ancestry feat grants",
                    "from Ancestry feat",
                )]
            } else {
                vec![]
            }
        }),
        meters: Box::new(|_, _| vec![]),
        describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
    });

    // --- Proficiency-override target (Canny Acumen) ---
    let d_desc = data.clone();
    regs.push(SlotRegistration::<Pf2eState> {
        id: SlotId::new(SLOT_PROFICIENCY_CHOICE),
        step: StepId::new(STEP_ANCESTRY),
        label: "Proficiency choice".into(),
        required: true,
        presentation_hint: None,
        kind: Box::new(|_| SlotViewKind::Single),
        unlock: Box::new(move |state| {
            if proficiency_choice_grant(state).is_some() {
                Availability::Open
            } else {
                Availability::Hidden
            }
        }),
        dependents: vec![],
        options: Box::new(move |state| {
            let Some((targets, rank, source)) = proficiency_choice_grant(state) else {
                return vec![];
            };
            targets
                .iter()
                .map(|t| {
                    let mut label = t.clone();
                    if let Some(first) = label.get_mut(0..1) {
                        first.make_ascii_uppercase();
                    }
                    OptionView {
                        id: OptionId::new(format!("prof.{t}")),
                        label,
                        summary: format!("becomes {rank} · from {source}"),
                        details: vec![],
                        available: true,
                        unavailable_reason: None,
                    }
                })
                .collect()
        }),
        apply: Box::new(move |state, decision| {
            let id = sel_single(&decision.selection)?;
            let Some((targets, rank, _)) = proficiency_choice_grant(state) else {
                return Err(ApplyError::new(
                    "no feat granting a proficiency choice is selected",
                ));
            };
            let target = id
                .as_str()
                .strip_prefix("prof.")
                .ok_or_else(|| ApplyError::new(format!("unknown proficiency option '{id}'")))?;
            if !targets.iter().any(|t| t == target) {
                return Err(ApplyError::new(format!(
                    "'{target}' is not one of the feat's proficiency choices"
                )));
            }
            state.effects.push(Effect::ProficiencyOverride {
                target: target.to_string(),
                rank,
            });
            Ok(())
        }),
        validate: Box::new(move |state, decision| {
            match (proficiency_choice_grant(state), decision) {
                (Some((_, _, source)), None) => vec![incomplete(
                    SLOT_PROFICIENCY_CHOICE,
                    STEP_ANCESTRY,
                    "General feat",
                    &format!("Choose which proficiency {source} improves"),
                    &format!("from {source}"),
                )],
                _ => vec![],
            }
        }),
        meters: Box::new(|_, _| vec![]),
        describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
    });

    // --- Natural Ambition's bonus class feat ---
    let d = data.clone();
    let d_unlock = data.clone();
    let d_apply = data.clone();
    let d_val = data.clone();
    let d_desc = data.clone();
    regs.push(SlotRegistration::<Pf2eState> {
        id: SlotId::new(SLOT_NATURAL_AMBITION),
        step: StepId::new(STEP_ANCESTRY),
        label: "Bonus class feat (Natural Ambition)".into(),
        required: true,
        presentation_hint: None,
        kind: Box::new(|_| SlotViewKind::Single),
        unlock: Box::new(move |state| {
            if !feat_grants(&d_unlock, state, "class_feats") {
                Availability::Hidden
            } else if state.class.is_none() {
                Availability::Locked {
                    reason: "choose a class first".into(),
                }
            } else {
                Availability::Open
            }
        }),
        dependents: vec![],
        options: Box::new(move |state| {
            let exclude = [&state.class_feat];
            class_feat_options(&d, state, &exclude)
        }),
        apply: Box::new(move |state, decision| {
            let id = sel_single(&decision.selection)?;
            let record = d_apply
                .class_feat(id.as_str())
                .ok_or_else(|| ApplyError::new(format!("unknown class feat '{id}'")))?;
            state.bonus_class_feats.push(record.id.clone());
            Ok(())
        }),
        validate: Box::new(move |state, decision| {
            let mut out = Vec::new();
            if feat_grants(&d_val, state, "class_feats") && state.class.is_some() {
                if decision.is_none() {
                    out.push(incomplete(
                        SLOT_NATURAL_AMBITION,
                        STEP_ANCESTRY,
                        "Ancestry feat",
                        "Choose the bonus class feat from Natural Ambition",
                        "from Ancestry feat",
                    ));
                } else if state
                    .bonus_class_feats
                    .iter()
                    .any(|f| state.class_feat.as_ref() == Some(f))
                {
                    out.push(crate::mechanics::illegal(
                        SLOT_NATURAL_AMBITION,
                        STEP_ANCESTRY,
                        "Ancestry feat",
                        "Natural Ambition's feat must differ from your class feat",
                        "from Ancestry feat",
                    ));
                }
            }
            out
        }),
        meters: Box::new(|_, _| vec![]),
        describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
    });

    regs
}
