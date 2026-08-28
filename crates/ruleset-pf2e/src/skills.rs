//! Skills kind: the class skill choice, the trained-skill picks, the
//! skill-chooser slots granted by heritage/ancestry feats, and the
//! replacement slots the PF2e "already trained" rule opens on collisions.

use std::sync::Arc;

use engine_core::{ApplyError, Availability, SlotRegistration};
use types::{OptionId, OptionView, SlotId, SlotViewKind, StepId};

use crate::data::{Effect, RulesData};
use crate::mechanics::{
    describe_selection, illegal, incomplete, sel_multi, sel_single, Attribute, Pf2eState,
    SkillChoice, SLOT_CLASS_SKILL, SLOT_FEAT_SKILLS, SLOT_HERITAGE_SKILLS, SLOT_REPLACEMENT_1,
    SLOT_REPLACEMENT_2, SLOT_REPLACEMENT_3, SLOT_TRAINED_SKILLS,
};

const STEP: &str = crate::mechanics::STEP_CLASS;
const STEP_ANCESTRY: &str = crate::mechanics::STEP_ANCESTRY;

/// Options: all skills, with already-trained (by other sources) unavailable.
fn skill_options(data: &RulesData, state: &Pf2eState, own_slot: &str) -> Vec<OptionView> {
    let resolution = state.skill_resolution();
    data.skills
        .iter()
        .map(|s| {
            let trained_by = resolution
                .trained
                .iter()
                .find(|(id, _)| *id == s.id)
                .map(|(_, source)| source.clone());
            // A skill trained by this very slot's earlier picks stays
            // "available" so re-projection of the same selection is stable.
            let own = state
                .skill_choices
                .iter()
                .any(|c| c.slot == own_slot && c.skills.contains(&s.id))
                || (own_slot == SLOT_CLASS_SKILL
                    && state.class_skill_choice.as_deref() == Some(s.id.as_str()));
            let blocked = trained_by.filter(|_| !own);
            OptionView {
                id: OptionId::new(&s.id),
                label: s.name.clone(),
                summary: format!("{} ({})", s.name, s.attribute.abbrev()),
                details: vec![],
                available: blocked.is_none(),
                unavailable_reason: blocked
                    .map(|source| format!("already trained (from {source})")),
            }
        })
        .collect()
}

fn choose_skills_grant(
    data: &RulesData,
    state: &Pf2eState,
    from_heritage: bool,
) -> Option<(u32, String)> {
    let effects: &[Effect] = if from_heritage {
        &data.heritage(state.heritage.as_ref()?)?.effects
    } else {
        &data.ancestry_feat(state.ancestry_feat.as_ref()?)?.effects
    };
    effects.iter().find_map(|e| match e {
        Effect::ChooseSkills {
            count,
            source_label,
        } => Some((*count, source_label.clone())),
        _ => None,
    })
}

/// The Fighter trains 3 + Int additional skills.
fn additional_skill_count(data: &RulesData, state: &Pf2eState) -> Option<u32> {
    let class = data.class(state.class.as_ref()?)?;
    let int = state.modifier(Attribute::Int);
    Some((class.additional_skills_base as i32 + int).max(0) as u32)
}

pub fn registrations(data: &Arc<RulesData>) -> Vec<SlotRegistration<Pf2eState>> {
    let mut regs = Vec::new();

    // --- Class skill choice (Acrobatics or Athletics) ---
    let d = data.clone();
    let d_apply = data.clone();
    let d_desc = data.clone();
    regs.push(SlotRegistration::<Pf2eState> {
        id: SlotId::new(SLOT_CLASS_SKILL),
        step: StepId::new(STEP),
        label: "Class skill".into(),
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
        options: Box::new(move |state| {
            let Some(c) = state.class.as_ref().and_then(|id| d.class(id)) else {
                return vec![];
            };
            c.class_skill_choice
                .iter()
                .filter_map(|id| d.skill(id))
                .map(|s| OptionView {
                    id: OptionId::new(&s.id),
                    label: s.name.clone(),
                    summary: format!("Trained ({})", s.attribute.abbrev()),
                    details: vec![],
                    available: true,
                    unavailable_reason: None,
                })
                .collect()
        }),
        apply: Box::new(move |state, decision| {
            let id = sel_single(&decision.selection)?;
            let Some(c) = state.class.as_ref().and_then(|cid| d_apply.class(cid)) else {
                return Err(ApplyError::new("choose a class first"));
            };
            if !c.class_skill_choice.iter().any(|s| s == id.as_str()) {
                return Err(ApplyError::new(format!(
                    "'{id}' is not one of the class's skill options"
                )));
            }
            state.class_skill_choice = Some(id.as_str().to_string());
            Ok(())
        }),
        validate: Box::new(|state, decision| {
            if state.class.is_some() && decision.is_none() {
                vec![incomplete(
                    SLOT_CLASS_SKILL,
                    STEP,
                    "Skills",
                    "Choose Acrobatics or Athletics",
                    "from Class",
                )]
            } else {
                vec![]
            }
        }),
        meters: Box::new(|_, _| vec![]),
        describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
    });

    // --- Additional trained skills (3 + Int) ---
    let d = data.clone();
    let d_kind = data.clone();
    let d_apply = data.clone();
    let d_val = data.clone();
    let d_desc = data.clone();
    regs.push(SlotRegistration::<Pf2eState> {
        id: SlotId::new(SLOT_TRAINED_SKILLS),
        step: StepId::new(STEP),
        label: "Trained skills".into(),
        required: true,
        presentation_hint: None,
        kind: Box::new(move |state| SlotViewKind::Multi {
            count: additional_skill_count(&d_kind, state).unwrap_or(3),
        }),
        unlock: Box::new(|state| match state.class {
            Some(_) => Availability::Open,
            None => Availability::Locked {
                reason: "choose a class first".into(),
            },
        }),
        dependents: vec![
            SlotId::new(SLOT_REPLACEMENT_1),
            SlotId::new(SLOT_REPLACEMENT_2),
            SlotId::new(SLOT_REPLACEMENT_3),
        ],
        options: Box::new(move |state| skill_options(&d, state, SLOT_TRAINED_SKILLS)),
        apply: Box::new(move |state, decision| {
            let ids = sel_multi(&decision.selection)?;
            for id in ids {
                if d_apply.skill(id.as_str()).is_none() {
                    return Err(ApplyError::new(format!("unknown skill '{id}'")));
                }
            }
            state.skill_choices.push(SkillChoice {
                slot: SLOT_TRAINED_SKILLS,
                source: "Fighter".into(),
                skills: ids.iter().map(|i| i.as_str().to_string()).collect(),
            });
            Ok(())
        }),
        validate: Box::new(move |state, decision| {
            let Some(expected) = additional_skill_count(&d_val, state) else {
                return vec![];
            };
            let picked = state
                .skill_choices
                .iter()
                .filter(|c| c.slot == SLOT_TRAINED_SKILLS)
                .map(|c| c.skills.len())
                .sum::<usize>();
            let mut out = Vec::new();
            if decision.is_none() || picked < expected as usize {
                let left = expected as usize - picked.min(expected as usize);
                out.push(incomplete(
                    SLOT_TRAINED_SKILLS,
                    STEP,
                    "Skills",
                    &format!("{} skill choice(s) left", left.max(1)),
                    "from Class",
                ));
            } else if picked > expected as usize {
                out.push(illegal(
                    SLOT_TRAINED_SKILLS,
                    STEP,
                    "Skills",
                    &format!(
                        "{picked} skills selected but only {expected} allowed (did Intelligence change?)"
                    ),
                    "from Class",
                ));
            }
            for (slot, skill) in state.skill_resolution().illegal_choice_dupes {
                if slot == SLOT_TRAINED_SKILLS {
                    out.push(illegal(
                        SLOT_TRAINED_SKILLS,
                        STEP,
                        "Skills",
                        &format!(
                            "{} is already trained — pick a different skill",
                            d_val
                                .skill(&skill)
                                .map(|s| s.name.clone())
                                .unwrap_or(skill)
                        ),
                        "from Class",
                    ));
                }
            }
            out
        }),
        meters: Box::new(|_, _| vec![]),
        describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
    });

    // --- Heritage skill chooser (Skilled Human) ---
    regs.push(chooser_slot(
        data,
        SLOT_HERITAGE_SKILLS,
        STEP_ANCESTRY,
        "Skill (heritage)",
        true,
    ));
    // --- Ancestry-feat skill chooser (Natural Skill) ---
    regs.push(chooser_slot(
        data,
        SLOT_FEAT_SKILLS,
        STEP_ANCESTRY,
        "Skills (ancestry feat)",
        false,
    ));

    // --- Replacement slots ---
    for (i, slot_id) in [SLOT_REPLACEMENT_1, SLOT_REPLACEMENT_2, SLOT_REPLACEMENT_3]
        .into_iter()
        .enumerate()
    {
        regs.push(replacement_slot(data, slot_id, i));
    }

    regs
}

fn chooser_slot(
    data: &Arc<RulesData>,
    slot_id: &'static str,
    step: &'static str,
    label: &str,
    from_heritage: bool,
) -> SlotRegistration<Pf2eState> {
    let d = data.clone();
    let d_kind = data.clone();
    let d_unlock = data.clone();
    let d_apply = data.clone();
    let d_val = data.clone();
    let d_desc = data.clone();
    SlotRegistration::<Pf2eState> {
        id: SlotId::new(slot_id),
        step: StepId::new(step),
        label: label.to_string(),
        required: true,
        presentation_hint: None,
        kind: Box::new(
            move |state| match choose_skills_grant(&d_kind, state, from_heritage) {
                Some((1, _)) | None => SlotViewKind::Single,
                Some((count, _)) => SlotViewKind::Multi { count },
            },
        ),
        unlock: Box::new(
            move |state| match choose_skills_grant(&d_unlock, state, from_heritage) {
                Some(_) => Availability::Open,
                None => Availability::Hidden,
            },
        ),
        dependents: vec![],
        options: Box::new(move |state| skill_options(&d, state, slot_id)),
        apply: Box::new(move |state, decision| {
            let Some((count, source)) = choose_skills_grant(&d_apply, state, from_heritage) else {
                return Err(ApplyError::new("nothing grants this skill choice"));
            };
            let ids: Vec<String> = match &decision.selection {
                types::Selection::Option(id) => vec![id.as_str().to_string()],
                types::Selection::Options(ids) => {
                    ids.iter().map(|i| i.as_str().to_string()).collect()
                }
                _ => return Err(ApplyError::new("expected skill option(s)")),
            };
            if ids.len() > count as usize {
                return Err(ApplyError::new(format!(
                    "at most {count} skill(s) may be chosen here"
                )));
            }
            for id in &ids {
                if d_apply.skill(id).is_none() {
                    return Err(ApplyError::new(format!("unknown skill '{id}'")));
                }
            }
            state.skill_choices.push(SkillChoice {
                slot: slot_id,
                source,
                skills: ids,
            });
            Ok(())
        }),
        validate: Box::new(move |state, decision| {
            let Some((count, source)) = choose_skills_grant(&d_val, state, from_heritage) else {
                return vec![];
            };
            let picked = state
                .skill_choices
                .iter()
                .filter(|c| c.slot == slot_id)
                .map(|c| c.skills.len())
                .sum::<usize>();
            let mut out = Vec::new();
            if decision.is_none() || picked < count as usize {
                out.push(incomplete(
                    slot_id,
                    step,
                    "Skills",
                    &format!(
                        "{} skill choice(s) left",
                        (count as usize) - picked.min(count as usize)
                    ),
                    &format!("from {source}"),
                ));
            }
            for (slot, skill) in state.skill_resolution().illegal_choice_dupes {
                if slot == slot_id {
                    out.push(illegal(
                        slot_id,
                        step,
                        "Skills",
                        &format!(
                            "{} is already trained — pick a different skill",
                            d_val.skill(&skill).map(|s| s.name.clone()).unwrap_or(skill)
                        ),
                        &format!("from {source}"),
                    ));
                }
            }
            out
        }),
        meters: Box::new(|_, _| vec![]),
        describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
    }
}

fn replacement_slot(
    data: &Arc<RulesData>,
    slot_id: &'static str,
    index: usize,
) -> SlotRegistration<Pf2eState> {
    let d = data.clone();
    let d_apply = data.clone();
    let d_val = data.clone();
    let d_desc = data.clone();
    SlotRegistration::<Pf2eState> {
        id: SlotId::new(slot_id),
        step: StepId::new(STEP),
        label: "Replacement skill".to_string(),
        required: true,
        presentation_hint: None,
        kind: Box::new(|_| SlotViewKind::Single),
        unlock: Box::new(move |state| {
            let collisions = state.skill_resolution().collisions;
            if collisions.len() > index {
                Availability::Open
            } else {
                Availability::Hidden
            }
        }),
        dependents: vec![],
        options: Box::new(move |state| skill_options(&d, state, slot_id)),
        apply: Box::new(move |state, decision| {
            let id = sel_single(&decision.selection)?;
            if d_apply.skill(id.as_str()).is_none() {
                return Err(ApplyError::new(format!("unknown skill '{id}'")));
            }
            state.skill_choices.push(SkillChoice {
                slot: slot_id,
                source: "replacement (already trained)".into(),
                skills: vec![id.as_str().to_string()],
            });
            Ok(())
        }),
        validate: Box::new(move |state, decision| {
            let collisions = state.skill_resolution().collisions;
            let mut out = Vec::new();
            if collisions.len() > index && decision.is_none() {
                out.push(incomplete(
                    slot_id,
                    STEP,
                    "Skills",
                    &format!(
                        "You're already trained in the skill granted by {} — choose a replacement skill",
                        collisions[index]
                    ),
                    &format!("from {}", collisions[index]),
                ));
            }
            for (slot, skill) in state.skill_resolution().illegal_choice_dupes {
                if slot == slot_id {
                    out.push(illegal(
                        slot_id,
                        STEP,
                        "Skills",
                        &format!(
                            "{} is already trained — pick a different skill",
                            d_val.skill(&skill).map(|s| s.name.clone()).unwrap_or(skill)
                        ),
                        "replacement",
                    ));
                }
            }
            out
        }),
        meters: Box::new(|_, _| vec![]),
        describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
    }
}
