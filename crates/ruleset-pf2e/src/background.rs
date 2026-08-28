//! Background kind: the background slot and its two boosts (one constrained
//! choice, one free — one batch, so they must differ).

use std::sync::Arc;

use engine_core::{ApplyError, Availability, SlotRegistration};
use types::{OptionId, OptionView, SlotId, SlotViewKind, StepId};

use crate::data::RulesData;
use crate::mechanics::{
    attribute_options, describe_selection, illegal, incomplete, sel_attribute, sel_single,
    Pf2eState, SkillGrant, SLOT_BACKGROUND, SLOT_BACKGROUND_BOOST_CHOICE,
    SLOT_BACKGROUND_BOOST_FREE, SLOT_REPLACEMENT_1, SLOT_REPLACEMENT_2, SLOT_REPLACEMENT_3,
};

const STEP: &str = crate::mechanics::STEP_BACKGROUND;

pub fn registrations(data: &Arc<RulesData>) -> Vec<SlotRegistration<Pf2eState>> {
    let mut regs = Vec::new();

    // --- Background ---
    let d = data.clone();
    let d_apply = data.clone();
    let d_desc = data.clone();
    regs.push(SlotRegistration::<Pf2eState> {
        id: SlotId::new(SLOT_BACKGROUND),
        step: StepId::new(STEP),
        label: "Background".into(),
        required: true,
        presentation_hint: None,
        kind: Box::new(|_| SlotViewKind::Single),
        unlock: Box::new(|_| Availability::Open),
        dependents: vec![
            SlotId::new(SLOT_BACKGROUND_BOOST_CHOICE),
            SlotId::new(SLOT_BACKGROUND_BOOST_FREE),
            SlotId::new(SLOT_REPLACEMENT_1),
            SlotId::new(SLOT_REPLACEMENT_2),
            SlotId::new(SLOT_REPLACEMENT_3),
        ],
        options: Box::new(move |_| {
            d.backgrounds
                .iter()
                .map(|b| OptionView {
                    id: OptionId::new(&b.id),
                    label: b.name.clone(),
                    summary: b.text.clone(),
                    details: vec![
                        format!(
                            "Boosts: {} or {}, plus one free",
                            b.boost_choice.first().map(|a| a.name()).unwrap_or_default(),
                            b.boost_choice.get(1).map(|a| a.name()).unwrap_or_default()
                        ),
                        format!(
                            "Trained: {}, {}",
                            d.skill(&b.skill)
                                .map(|s| s.name.clone())
                                .unwrap_or_default(),
                            b.lore
                        ),
                        format!("Skill feat: {}", b.skill_feat),
                    ],
                    available: true,
                    unavailable_reason: None,
                })
                .collect()
        }),
        apply: Box::new(move |state, decision| {
            let id = sel_single(&decision.selection)?;
            let record = d_apply
                .background(id.as_str())
                .ok_or_else(|| ApplyError::new(format!("unknown background '{id}'")))?;
            state.background = Some(record.id.clone());
            // Canonical precedence: the background grant goes first in the
            // grant list regardless of log order, so collisions resolve
            // deterministically. (Insert, not push.)
            state.skill_grants.insert(
                0,
                SkillGrant {
                    skill: record.skill.clone(),
                    source: format!("Background: {}", record.name),
                },
            );
            state
                .lores
                .push((record.lore.clone(), format!("Background: {}", record.name)));
            Ok(())
        }),
        validate: Box::new(|state, _| {
            if state.background.is_none() {
                vec![incomplete(
                    SLOT_BACKGROUND,
                    STEP,
                    "Background",
                    "Choose a background",
                    "character creation",
                )]
            } else {
                vec![]
            }
        }),
        meters: Box::new(|_, _| vec![]),
        describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
    });

    // --- Constrained background boost ---
    let d = data.clone();
    let d_desc = data.clone();
    regs.push(SlotRegistration::<Pf2eState> {
        id: SlotId::new(SLOT_BACKGROUND_BOOST_CHOICE),
        step: StepId::new(STEP),
        label: "Background boost".into(),
        required: true,
        presentation_hint: Some("attribute-boosts".into()),
        kind: Box::new(|_| SlotViewKind::Single),
        unlock: Box::new(|state| match state.background {
            Some(_) => Availability::Open,
            None => Availability::Locked {
                reason: "choose a background first".into(),
            },
        }),
        dependents: vec![],
        options: Box::new(move |state| {
            let Some(b) = state.background.as_ref().and_then(|id| d.background(id)) else {
                return vec![];
            };
            b.boost_choice
                .iter()
                .map(|attr| OptionView {
                    id: attr.option_id(),
                    label: attr.name().to_string(),
                    summary: String::new(),
                    details: vec![],
                    available: true,
                    unavailable_reason: None,
                })
                .collect()
        }),
        apply: Box::new(|state, decision| {
            let attr = sel_attribute(&decision.selection)?;
            state
                .boost_batches
                .entry("background".into())
                .or_default()
                .insert(0, attr);
            Ok(())
        }),
        validate: Box::new(|state, decision| {
            if state.background.is_some() && decision.is_none() {
                vec![incomplete(
                    SLOT_BACKGROUND_BOOST_CHOICE,
                    STEP,
                    "Attribute boosts",
                    "Choose the background's constrained boost",
                    "from Background",
                )]
            } else {
                vec![]
            }
        }),
        meters: Box::new(|_, _| vec![]),
        describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
    });

    // --- Free background boost ---
    let d_desc = data.clone();
    regs.push(SlotRegistration::<Pf2eState> {
        id: SlotId::new(SLOT_BACKGROUND_BOOST_FREE),
        step: StepId::new(STEP),
        label: "Background free boost".into(),
        required: true,
        presentation_hint: Some("attribute-boosts".into()),
        kind: Box::new(|_| SlotViewKind::Single),
        unlock: Box::new(|state| match state.background {
            Some(_) => Availability::Open,
            None => Availability::Locked {
                reason: "choose a background first".into(),
            },
        }),
        dependents: vec![],
        options: Box::new(|state| {
            let batch = state
                .boost_batches
                .get("background")
                .cloned()
                .unwrap_or_default();
            attribute_options(move |attr| {
                // Kept short: this renders inside <option> text.
                if batch.first() == Some(&attr) {
                    Some("already has the background's other boost".to_string())
                } else {
                    None
                }
            })
        }),
        apply: Box::new(|state, decision| {
            let attr = sel_attribute(&decision.selection)?;
            state
                .boost_batches
                .entry("background".into())
                .or_default()
                .push(attr);
            Ok(())
        }),
        validate: Box::new(|state, decision| {
            let mut out = Vec::new();
            if state.background.is_some() && decision.is_none() {
                out.push(incomplete(
                    SLOT_BACKGROUND_BOOST_FREE,
                    STEP,
                    "Attribute boosts",
                    "Choose the background's free boost",
                    "from Background",
                ));
            }
            let batch = state
                .boost_batches
                .get("background")
                .cloned()
                .unwrap_or_default();
            let mut sorted = batch.clone();
            sorted.sort();
            let mut deduped = sorted.clone();
            deduped.dedup();
            if sorted.len() != deduped.len() {
                out.push(illegal(
                    SLOT_BACKGROUND_BOOST_FREE,
                    STEP,
                    "Attribute boosts",
                    "Boosts gained at the same time must go to different attributes",
                    "from Background",
                ));
            }
            out
        }),
        meters: Box::new(|_, _| vec![]),
        describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
    });

    regs
}
