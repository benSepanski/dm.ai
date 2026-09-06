//! Species kind: the species slot and the internal choices a species may
//! carry — an extra skill, an Origin feat (the Human), and a choice trait
//! (the Goliath's Giant Ancestry). Each sub-slot is hidden unless the
//! chosen species grants it.

use std::sync::Arc;

use engine_core::{ApplyError, Availability, SlotRegistration};
use types::{OptionId, OptionView, SlotId, SlotViewKind, StepId};

use crate::data::{RulesData, SpeciesRecord};
use crate::mechanics::{
    describe_selection, illegal, incomplete, sel_single, Dnd5eState, SLOT_FEAT_SKILLED,
    SLOT_SPECIES, SLOT_SPECIES_ANCESTRY, SLOT_SPECIES_FEAT, SLOT_SPECIES_SKILL, STEP_ORIGIN,
};

fn option(id: &str, label: &str, summary: String, details: Vec<String>) -> OptionView {
    OptionView {
        id: OptionId::new(id),
        label: label.to_string(),
        summary,
        details,
        available: true,
        unavailable_reason: None,
        group: None,
        badge: None,
    }
}

fn chosen<'a>(data: &'a RulesData, state: &Dnd5eState) -> Option<&'a SpeciesRecord> {
    state.species.as_ref().and_then(|id| data.species(id))
}

pub fn registrations(data: &Arc<RulesData>) -> Vec<SlotRegistration<Dnd5eState>> {
    let mut regs = Vec::new();

    // --- Species ---
    let d = data.clone();
    let d_apply = data.clone();
    let d_desc = data.clone();
    regs.push(SlotRegistration::<Dnd5eState> {
        id: SlotId::new(SLOT_SPECIES),
        step: StepId::new(STEP_ORIGIN),
        label: "Species".into(),
        required: true,
        presentation_hint: None,
        kind: Box::new(|_| SlotViewKind::Single),
        unlock: Box::new(|_| Availability::Open),
        dependents: vec![
            SlotId::new(SLOT_SPECIES_SKILL),
            SlotId::new(SLOT_SPECIES_FEAT),
            SlotId::new(SLOT_SPECIES_ANCESTRY),
        ],
        options: Box::new(move |_| {
            d.species
                .iter()
                .map(|s| {
                    let mut details: Vec<String> = s
                        .traits
                        .iter()
                        .map(|t| format!("{}: {}", t.name, t.text))
                        .collect();
                    if let Some(ct) = &s.choice_trait {
                        details.push(format!("{}: {}", ct.name, ct.text));
                    }
                    let mut summary = format!("{} · Speed {} ft.", s.size, s.speed);
                    if let Some(dv) = s.darkvision {
                        summary.push_str(&format!(" · Darkvision {dv} ft."));
                    }
                    option(&s.id, &s.name, summary, details)
                })
                .collect()
        }),
        apply: Box::new(move |state, decision| {
            let id = sel_single(&decision.selection)?;
            let record = d_apply
                .species(id.as_str())
                .ok_or_else(|| ApplyError::new(format!("unknown species '{id}'")))?;
            state.species = Some(record.id.clone());
            Ok(())
        }),
        validate: Box::new(|state, _| {
            if state.species.is_none() {
                vec![incomplete(
                    SLOT_SPECIES,
                    STEP_ORIGIN,
                    "Species",
                    "Choose a species",
                    "character creation",
                )]
            } else {
                vec![]
            }
        }),
        meters: Box::new(|_, _| vec![]),
        describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
    });

    // --- Species skill (the Human's Skillful) ---
    let d_unlock = data.clone();
    let d_opts = data.clone();
    let d_apply = data.clone();
    let d_val = data.clone();
    let d_desc = data.clone();
    regs.push(SlotRegistration::<Dnd5eState> {
        id: SlotId::new(SLOT_SPECIES_SKILL),
        step: StepId::new(STEP_ORIGIN),
        label: "Species skill".into(),
        required: true,
        presentation_hint: None,
        kind: Box::new(|_| SlotViewKind::Single),
        unlock: Box::new(move |state| {
            if chosen(&d_unlock, state).is_some_and(|s| s.skill_choices > 0) {
                Availability::Open
            } else {
                Availability::Hidden
            }
        }),
        dependents: vec![],
        options: Box::new(move |state| {
            let Some(sp) = chosen(&d_opts, state) else {
                return vec![];
            };
            let granted: Vec<_> = state
                .skill_proficiencies(&d_opts)
                .into_iter()
                .filter(|p| p.source != sp.name)
                .collect();
            d_opts
                .skills
                .iter()
                .map(|s| {
                    let mut o = option(
                        &s.id,
                        &s.name,
                        format!("{} skill", s.ability.name()),
                        vec![],
                    );
                    if let Some(p) = granted.iter().find(|p| p.id == s.id) {
                        o.available = false;
                        o.unavailable_reason =
                            Some(format!("already proficient from {}", p.source));
                    }
                    o
                })
                .collect()
        }),
        apply: Box::new(move |state, decision| {
            let id = sel_single(&decision.selection)?;
            if !chosen(&d_apply, state).is_some_and(|s| s.skill_choices > 0) {
                return Err(ApplyError::new("the chosen species grants no skill choice"));
            }
            if d_apply.skill(id.as_str()).is_none() {
                return Err(ApplyError::new(format!("unknown skill '{id}'")));
            }
            state.species_skill = Some(id.as_str().to_string());
            Ok(())
        }),
        validate: Box::new(move |state, decision| {
            let Some(sp) = chosen(&d_val, state).filter(|s| s.skill_choices > 0) else {
                return vec![];
            };
            let mut out = Vec::new();
            if decision.is_none() || state.species_skill.is_none() {
                out.push(incomplete(
                    SLOT_SPECIES_SKILL,
                    STEP_ORIGIN,
                    "Skill Proficiencies",
                    "Choose the skill your species grants",
                    &format!("from {}", sp.name),
                ));
            }
            if let Some(skill) = &state.species_skill {
                if let Some(owner) = state
                    .skill_proficiencies(&d_val)
                    .into_iter()
                    .find(|p| p.id == *skill && p.source != sp.name)
                {
                    out.push(illegal(
                        SLOT_SPECIES_SKILL,
                        STEP_ORIGIN,
                        "Skill Proficiencies",
                        &format!(
                            "{} is already granted by {} — choose a different skill",
                            d_val.skill(skill).map(|s| s.name.as_str()).unwrap_or(skill),
                            owner.source
                        ),
                        &format!("from {}", sp.name),
                    ));
                }
            }
            out
        }),
        meters: Box::new(|_, _| vec![]),
        describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
    });

    // --- Species Origin feat (the Human's Versatile) ---
    let d_unlock = data.clone();
    let d_opts = data.clone();
    let d_apply = data.clone();
    let d_val = data.clone();
    let d_desc = data.clone();
    regs.push(SlotRegistration::<Dnd5eState> {
        id: SlotId::new(SLOT_SPECIES_FEAT),
        step: StepId::new(STEP_ORIGIN),
        label: "Species origin feat".into(),
        required: true,
        presentation_hint: None,
        kind: Box::new(|_| SlotViewKind::Single),
        unlock: Box::new(move |state| {
            if chosen(&d_unlock, state).is_some_and(|s| s.origin_feat_choice) {
                Availability::Open
            } else {
                Availability::Hidden
            }
        }),
        dependents: vec![SlotId::new(SLOT_FEAT_SKILLED)],
        options: Box::new(move |state| {
            let background = state
                .background
                .as_ref()
                .and_then(|id| d_opts.background(id));
            d_opts
                .feats
                .iter()
                .filter(|f| f.is_origin())
                .map(|f| {
                    let mut o = option(&f.id, &f.name, String::new(), vec![f.text.clone()]);
                    if let Some(b) = background.filter(|b| b.feat == f.id) {
                        o.available = false;
                        o.unavailable_reason = Some(format!("already granted by {}", b.name));
                    }
                    o
                })
                .collect()
        }),
        apply: Box::new(move |state, decision| {
            let id = sel_single(&decision.selection)?;
            if !chosen(&d_apply, state).is_some_and(|s| s.origin_feat_choice) {
                return Err(ApplyError::new("the chosen species grants no Origin feat"));
            }
            let feat = d_apply
                .feat(id.as_str())
                .ok_or_else(|| ApplyError::new(format!("unknown feat '{id}'")))?;
            if !feat.is_origin() {
                return Err(ApplyError::new(format!(
                    "{} is not an Origin feat",
                    feat.name
                )));
            }
            state.species_feat = Some(feat.id.clone());
            Ok(())
        }),
        validate: Box::new(move |state, decision| {
            let Some(sp) = chosen(&d_val, state).filter(|s| s.origin_feat_choice) else {
                return vec![];
            };
            let mut out = Vec::new();
            if decision.is_none() || state.species_feat.is_none() {
                out.push(incomplete(
                    SLOT_SPECIES_FEAT,
                    STEP_ORIGIN,
                    "Origin Feat",
                    "Choose the Origin feat your species grants",
                    &format!("from {}", sp.name),
                ));
            }
            if let (Some(feat), Some(b)) = (
                &state.species_feat,
                state
                    .background
                    .as_ref()
                    .and_then(|id| d_val.background(id)),
            ) {
                if b.feat == *feat {
                    out.push(illegal(
                        SLOT_SPECIES_FEAT,
                        STEP_ORIGIN,
                        "Origin Feat",
                        &format!(
                            "{} is already granted by {} — choose a different feat",
                            d_val.feat(feat).map(|f| f.name.as_str()).unwrap_or(feat),
                            b.name
                        ),
                        &format!("from {}", sp.name),
                    ));
                }
            }
            out
        }),
        meters: Box::new(|_, _| vec![]),
        describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
    });

    // --- Choice trait (the Goliath's Giant Ancestry) ---
    let d_unlock = data.clone();
    let d_opts = data.clone();
    let d_apply = data.clone();
    let d_val = data.clone();
    let d_desc = data.clone();
    regs.push(SlotRegistration::<Dnd5eState> {
        id: SlotId::new(SLOT_SPECIES_ANCESTRY),
        step: StepId::new(STEP_ORIGIN),
        label: "Species trait choice".into(),
        required: true,
        presentation_hint: None,
        kind: Box::new(|_| SlotViewKind::Single),
        unlock: Box::new(move |state| {
            if chosen(&d_unlock, state).is_some_and(|s| s.choice_trait.is_some()) {
                Availability::Open
            } else {
                Availability::Hidden
            }
        }),
        dependents: vec![],
        options: Box::new(move |state| {
            let Some(ct) = chosen(&d_opts, state).and_then(|s| s.choice_trait.as_ref()) else {
                return vec![];
            };
            ct.options
                .iter()
                .map(|o| {
                    let mut view = option(&o.id, &o.name, o.text.clone(), vec![]);
                    view.group = Some(ct.name.clone());
                    view
                })
                .collect()
        }),
        apply: Box::new(move |state, decision| {
            let id = sel_single(&decision.selection)?;
            let Some(ct) = chosen(&d_apply, state).and_then(|s| s.choice_trait.as_ref()) else {
                return Err(ApplyError::new("the chosen species has no trait choice"));
            };
            if !ct.options.iter().any(|o| o.id == id.as_str()) {
                return Err(ApplyError::new(format!(
                    "'{id}' is not one of the {} options",
                    ct.name
                )));
            }
            state.species_ancestry = Some(id.as_str().to_string());
            Ok(())
        }),
        validate: Box::new(move |state, decision| {
            let Some(sp) = chosen(&d_val, state).filter(|s| s.choice_trait.is_some()) else {
                return vec![];
            };
            let ct = sp.choice_trait.as_ref().expect("filtered above");
            if decision.is_none() || state.species_ancestry.is_none() {
                vec![incomplete(
                    SLOT_SPECIES_ANCESTRY,
                    STEP_ORIGIN,
                    &ct.name,
                    &format!("Choose your {} benefit", ct.name),
                    &format!("from {}", sp.name),
                )]
            } else {
                vec![]
            }
        }),
        meters: Box::new(|_, _| vec![]),
        describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
    });

    regs
}
