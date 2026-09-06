//! Feats kind: the Fighting Style feat slot (the class's level-1 feature
//! whose choice is a feat record) and the skills-or-tools chooser a held
//! feat opens (Skilled). Chooser slots unlock from folded state, never by
//! asking a sibling module.

use std::sync::Arc;

use engine_core::{ApplyError, Availability, SlotRegistration};
use types::{OptionId, OptionView, SlotId, SlotViewKind, StepId};

use crate::data::RulesData;
use crate::mechanics::{
    describe_selection, illegal, incomplete, sel_multi, sel_single, Dnd5eState, SLOT_CLASS_STYLE,
    SLOT_FEAT_SKILLED, STEP_CLASS_CHOICES, STEP_ORIGIN,
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

/// The name of the feat granting the skills-or-tools chooser, when held.
fn skilled_feat_name(data: &RulesData, state: &Dnd5eState) -> Option<String> {
    state
        .feats(data)
        .into_iter()
        .filter_map(|(id, _, _)| data.feat(&id))
        .find(|f| f.skill_or_tool_choices() > 0)
        .map(|f| f.name.clone())
}

pub fn registrations(data: &Arc<RulesData>) -> Vec<SlotRegistration<Dnd5eState>> {
    let mut regs = Vec::new();

    // --- Fighting Style ---
    let d_unlock = data.clone();
    let d_opts = data.clone();
    let d_apply = data.clone();
    let d_val = data.clone();
    let d_desc = data.clone();
    regs.push(SlotRegistration::<Dnd5eState> {
        id: SlotId::new(SLOT_CLASS_STYLE),
        step: StepId::new(STEP_CLASS_CHOICES),
        label: "Fighting style".into(),
        required: true,
        presentation_hint: None,
        kind: Box::new(|_| SlotViewKind::Single),
        unlock: Box::new(move |state| {
            match state.class.as_ref().and_then(|id| d_unlock.class(id)) {
                Some(c) if c.fighting_style_feature.is_some() => Availability::Open,
                Some(_) => Availability::Hidden,
                None => Availability::Locked {
                    reason: "choose a class first".into(),
                },
            }
        }),
        dependents: vec![],
        options: Box::new(move |_| {
            d_opts
                .feats
                .iter()
                .filter(|f| f.is_fighting_style())
                .map(|f| option(&f.id, &f.name, f.text.clone(), vec![]))
                .collect()
        }),
        apply: Box::new(move |state, decision| {
            let id = sel_single(&decision.selection)?;
            let Some(c) = state.class.as_ref().and_then(|id| d_apply.class(id)) else {
                return Err(ApplyError::new("choose a class before its fighting style"));
            };
            if c.fighting_style_feature.is_none() {
                return Err(ApplyError::new(format!(
                    "{} does not grant a fighting style",
                    c.name
                )));
            }
            let feat = d_apply
                .feat(id.as_str())
                .ok_or_else(|| ApplyError::new(format!("unknown feat '{id}'")))?;
            if !feat.is_fighting_style() {
                return Err(ApplyError::new(format!(
                    "{} is not a Fighting Style feat",
                    feat.name
                )));
            }
            state.fighting_style = Some(feat.id.clone());
            Ok(())
        }),
        validate: Box::new(move |state, decision| {
            let Some(c) = state.class.as_ref().and_then(|id| d_val.class(id)) else {
                return vec![];
            };
            let Some(feature) = c
                .fighting_style_feature
                .as_ref()
                .and_then(|id| c.feature(id))
            else {
                return vec![];
            };
            if decision.is_none() || state.fighting_style.is_none() {
                vec![incomplete(
                    SLOT_CLASS_STYLE,
                    STEP_CLASS_CHOICES,
                    &feature.name,
                    &format!("Choose a {} feat", feature.name),
                    &format!("from {}", c.name),
                )]
            } else {
                vec![]
            }
        }),
        meters: Box::new(|_, _| vec![]),
        describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
    });

    // --- Skills-or-tools chooser (Skilled) ---
    let d_kind = data.clone();
    let d_unlock = data.clone();
    let d_opts = data.clone();
    let d_apply = data.clone();
    let d_val = data.clone();
    let d_desc = data.clone();
    regs.push(SlotRegistration::<Dnd5eState> {
        id: SlotId::new(SLOT_FEAT_SKILLED),
        step: StepId::new(STEP_ORIGIN),
        label: "Feat skills and tools".into(),
        required: true,
        presentation_hint: None,
        kind: Box::new(move |state| SlotViewKind::Multi {
            count: state.skilled_pick_count(&d_kind),
        }),
        unlock: Box::new(move |state| {
            if state.skilled_pick_count(&d_unlock) > 0 {
                Availability::Open
            } else {
                Availability::Hidden
            }
        }),
        dependents: vec![],
        options: Box::new(move |state| {
            let skills = state.skill_proficiencies(&d_opts);
            let tools = state.tool_proficiencies(&d_opts);
            let feat = skilled_feat_name(&d_opts, state).unwrap_or_default();
            let mut out = Vec::new();
            for s in &d_opts.skills {
                let mut o = option(
                    &s.id,
                    &s.name,
                    format!("{} skill", s.ability.name()),
                    vec![],
                );
                o.group = Some("Skills".into());
                if let Some(p) = skills.iter().find(|p| p.id == s.id && p.source != feat) {
                    o.available = false;
                    o.unavailable_reason = Some(format!("already proficient from {}", p.source));
                }
                out.push(o);
            }
            for t in &d_opts.equipment.tools {
                let mut o = option(&t.id, &t.name, t.text.clone(), vec![]);
                o.group = Some("Tools".into());
                if let Some(p) = tools.iter().find(|p| p.id == t.id && p.source != feat) {
                    o.available = false;
                    o.unavailable_reason = Some(format!("already proficient from {}", p.source));
                }
                out.push(o);
            }
            out
        }),
        apply: Box::new(move |state, decision| {
            let ids = sel_multi(&decision.selection)?;
            if state.skilled_pick_count(&d_apply) == 0 {
                return Err(ApplyError::new("no held feat grants skill or tool choices"));
            }
            for id in ids {
                if d_apply.skill(id.as_str()).is_none() && d_apply.tool(id.as_str()).is_none() {
                    return Err(ApplyError::new(format!(
                        "'{id}' is neither a skill nor a tool"
                    )));
                }
            }
            state.skilled_picks = ids.iter().map(|i| i.as_str().to_string()).collect();
            Ok(())
        }),
        validate: Box::new(move |state, decision| {
            let count = state.skilled_pick_count(&d_val) as usize;
            if count == 0 {
                return vec![];
            }
            let feat = skilled_feat_name(&d_val, state).unwrap_or_default();
            let source = format!("from {feat}");
            let mut out = Vec::new();
            if decision.is_none() || state.skilled_picks.len() < count {
                out.push(incomplete(
                    SLOT_FEAT_SKILLED,
                    STEP_ORIGIN,
                    &feat,
                    &format!(
                        "{} skill or tool choice(s) left",
                        count - state.skilled_picks.len().min(count)
                    ),
                    &source,
                ));
            }
            if state.skilled_picks.len() > count {
                out.push(illegal(
                    SLOT_FEAT_SKILLED,
                    STEP_ORIGIN,
                    &feat,
                    &format!("Choose exactly {count} skills or tools"),
                    &source,
                ));
            }
            let mut sorted = state.skilled_picks.clone();
            sorted.sort();
            sorted.dedup();
            if sorted.len() != state.skilled_picks.len() {
                out.push(illegal(
                    SLOT_FEAT_SKILLED,
                    STEP_ORIGIN,
                    &feat,
                    "Each skill or tool can be chosen only once",
                    &source,
                ));
            }
            let skills = state.skill_proficiencies(&d_val);
            let tools = state.tool_proficiencies(&d_val);
            for pick in &state.skilled_picks {
                let owner = skills
                    .iter()
                    .chain(tools.iter())
                    .find(|p| p.id == *pick && p.source != feat);
                if let Some(p) = owner {
                    let name = d_val
                        .skill(pick)
                        .map(|s| s.name.clone())
                        .or_else(|| d_val.tool(pick).map(|t| t.name.clone()))
                        .unwrap_or_else(|| pick.clone());
                    out.push(illegal(
                        SLOT_FEAT_SKILLED,
                        STEP_ORIGIN,
                        &feat,
                        &format!(
                            "{name} is already granted by {} — choose a different one",
                            p.source
                        ),
                        &source,
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
