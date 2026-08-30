//! Skills kind: the class skill choice, the trained-skill picks, and the
//! skill-chooser slots granted by heritage/ancestry feats. Ownership
//! policy (see `Pf2eState::skill_resolution`): fixed grants own a skill
//! and its attribution; a grant or class skill landing on an
//! already-trained skill converts into one extra free trained pick, and a
//! free pick landing on an owned skill re-judges in place.

use std::sync::Arc;

use engine_core::{ApplyError, Availability, SlotRegistration};
use types::{OptionId, OptionView, SlotId, SlotViewKind, StepId};

use crate::data::{Effect, RulesData};
use crate::mechanics::{
    describe_selection, illegal, incomplete, lore_name_from_text, sel_multi, sel_single, sel_text,
    Attribute, Pf2eState, SkillChoice, SLOT_CLASS_SKILL, SLOT_FEAT_LORE, SLOT_FEAT_SKILLS,
    SLOT_HERITAGE_SKILLS, SLOT_TRAINED_SKILLS,
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
                group: None,
                badge: None,
            }
        })
        .collect()
}

/// (count, source label, from-restriction) of the ChooseSkills effect the
/// heritage or ancestry feat carries, if any. An empty `from` means any
/// skill; non-empty restricts the chooser to that subset (Hold Mark).
fn choose_skills_grant(
    data: &RulesData,
    state: &Pf2eState,
    from_heritage: bool,
) -> Option<(u32, String, Vec<String>)> {
    let effects: &[Effect] = if from_heritage {
        &data.heritage(state.heritage.as_ref()?)?.effects
    } else {
        &data.ancestry_feat(state.ancestry_feat.as_ref()?)?.effects
    };
    effects.iter().find_map(|e| match e {
        Effect::ChooseSkills {
            count,
            source_label,
            from,
        } => Some((*count, source_label.clone(), from.clone())),
        _ => None,
    })
}

/// The source label of a ChooseLore effect anywhere in the folded state
/// (heritage, ancestry feat, or a chosen general feat), if any.
fn choose_lore_grant(state: &Pf2eState) -> Option<String> {
    state.effects.iter().find_map(|e| match e {
        Effect::ChooseLore { source_label } => Some(source_label.clone()),
        _ => None,
    })
}

/// The class's additional trained skills: its base count plus Int, plus
/// one per redundant grant/class-skill (the "select another skill
/// instead" rule).
fn additional_skill_count(data: &RulesData, state: &Pf2eState) -> Option<u32> {
    let class = data.class(state.class.as_ref()?)?;
    let int = state.modifier(Attribute::Int);
    let extra = state.skill_resolution().extra_free_picks.len() as i32;
    Some((class.additional_skills_base as i32 + int + extra).max(0) as u32)
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
                    group: None,
                    badge: None,
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
                    "Choose your class skill",
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
        dependents: vec![],
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
                source: state.class_name.clone().unwrap_or_else(|| "Class".into()),
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
                let extras = state.skill_resolution().extra_free_picks;
                let bonus_note = if extras.is_empty() {
                    String::new()
                } else {
                    format!(
                        " (includes {} extra: {} trains a skill you already have)",
                        extras.len(),
                        extras.join(", ")
                    )
                };
                out.push(incomplete(
                    SLOT_TRAINED_SKILLS,
                    STEP,
                    "Skills",
                    &format!("{} skill choice(s) left{bonus_note}", left.max(1)),
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
            for (slot, skill, owner) in state.skill_resolution().illegal_choice_dupes {
                if slot == SLOT_TRAINED_SKILLS {
                    out.push(illegal(
                        SLOT_TRAINED_SKILLS,
                        STEP,
                        "Skills",
                        &format!(
                            "{} now comes from {owner} — pick a different skill",
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

    // --- Player-named Lore from a feat (Gnome Obsession pattern) ---
    // A ChooseLore effect anywhere in the folded state (heritage, ancestry
    // feat, or chosen general feat) opens this text slot; the typed name
    // lands trained as "<Typed> Lore", same mechanics as the background
    // Lore. At most one ChooseLore effect per build (data convention).
    let d_desc = data.clone();
    regs.push(SlotRegistration::<Pf2eState> {
        id: SlotId::new(SLOT_FEAT_LORE),
        step: StepId::new(STEP_ANCESTRY),
        label: "Lore (feat)".into(),
        required: true,
        presentation_hint: None,
        kind: Box::new(|_| SlotViewKind::Text { multiline: false }),
        unlock: Box::new(|state| match choose_lore_grant(state) {
            Some(_) => Availability::Open,
            None => Availability::Hidden,
        }),
        dependents: vec![],
        options: Box::new(|_| vec![]),
        apply: Box::new(|state, decision| {
            let Some(source) = choose_lore_grant(state) else {
                return Err(ApplyError::new("nothing grants a Lore to name"));
            };
            let lore = lore_name_from_text(sel_text(&decision.selection)?)?;
            state.lores.push((lore, source));
            Ok(())
        }),
        validate: Box::new(|state, decision| match choose_lore_grant(state) {
            Some(source) if decision.is_none() => vec![incomplete(
                SLOT_FEAT_LORE,
                STEP_ANCESTRY,
                "Skills",
                &format!("Name the Lore skill from {source}"),
                &format!("from {source}"),
            )],
            _ => vec![],
        }),
        meters: Box::new(|_, _| vec![]),
        describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
    });

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
                Some((1, _, _)) | None => SlotViewKind::Single,
                Some((count, _, _)) => SlotViewKind::Multi { count },
            },
        ),
        unlock: Box::new(
            move |state| match choose_skills_grant(&d_unlock, state, from_heritage) {
                Some(_) => Availability::Open,
                None => Availability::Hidden,
            },
        ),
        dependents: vec![],
        options: Box::new(move |state| {
            let opts = skill_options(&d, state, slot_id);
            // A non-empty from-restriction narrows the catalog to the
            // listed subset (greying rules unchanged).
            match choose_skills_grant(&d, state, from_heritage) {
                Some((_, _, from)) if !from.is_empty() => opts
                    .into_iter()
                    .filter(|o| from.iter().any(|s| s == o.id.as_str()))
                    .collect(),
                _ => opts,
            }
        }),
        apply: Box::new(move |state, decision| {
            let Some((count, source, from)) = choose_skills_grant(&d_apply, state, from_heritage)
            else {
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
                if !from.is_empty() && !from.contains(id) {
                    return Err(ApplyError::new(format!(
                        "'{id}' is not one of the skills this choice offers"
                    )));
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
            let Some((count, source, _)) = choose_skills_grant(&d_val, state, from_heritage) else {
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
            for (slot, skill, owner) in state.skill_resolution().illegal_choice_dupes {
                if slot == slot_id {
                    out.push(illegal(
                        slot_id,
                        step,
                        "Skills",
                        &format!(
                            "{} now comes from {owner} — pick a different skill",
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
