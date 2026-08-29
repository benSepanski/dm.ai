//! Background kind: the background slot and its two boosts (one constrained
//! choice, one free — one batch, so they must differ).

use std::sync::Arc;

use engine_core::{ApplyError, Availability, SlotRegistration};
use types::{OptionId, OptionView, SlotId, SlotViewKind, StepId};

use crate::data::{BackgroundRecord, RulesData};
use crate::mechanics::{
    attribute_options, describe_selection, illegal, incomplete, lore_name_from_text, sel_attribute,
    sel_single, sel_text, Pf2eState, SkillGrant, SLOT_BACKGROUND, SLOT_BACKGROUND_BOOST_CHOICE,
    SLOT_BACKGROUND_BOOST_FREE, SLOT_BACKGROUND_LORE, SLOT_BACKGROUND_SKILL, SLOT_REPLACEMENT_1,
    SLOT_REPLACEMENT_2, SLOT_REPLACEMENT_3,
};

const STEP: &str = crate::mechanics::STEP_BACKGROUND;

/// The chosen background, when it opens the given sub-choice.
fn background_with_skill_choice<'a>(
    data: &'a RulesData,
    state: &Pf2eState,
) -> Option<&'a BackgroundRecord> {
    state
        .background
        .as_ref()
        .and_then(|id| data.background(id))
        .filter(|b| !b.skill_choice.is_empty())
}

fn background_with_player_lore<'a>(
    data: &'a RulesData,
    state: &Pf2eState,
) -> Option<&'a BackgroundRecord> {
    state
        .background
        .as_ref()
        .and_then(|id| data.background(id))
        .filter(|b| b.lore_player_named)
}

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
            SlotId::new(SLOT_BACKGROUND_SKILL),
            SlotId::new(SLOT_BACKGROUND_LORE),
            SlotId::new(SLOT_REPLACEMENT_1),
            SlotId::new(SLOT_REPLACEMENT_2),
            SlotId::new(SLOT_REPLACEMENT_3),
        ],
        options: Box::new(move |_| {
            d.backgrounds
                .iter()
                .map(|b| {
                    let skill_part = if b.skill_choice.is_empty() {
                        d.skill(&b.skill)
                            .map(|s| s.name.clone())
                            .unwrap_or_default()
                    } else {
                        format!(
                            "your choice of {}",
                            b.skill_choice
                                .iter()
                                .filter_map(|id| d.skill(id))
                                .map(|s| s.name.clone())
                                .collect::<Vec<_>>()
                                .join(" or ")
                        )
                    };
                    let lore_part = if b.lore_player_named {
                        "a Lore you name".to_string()
                    } else {
                        b.lore.clone()
                    };
                    let feat_part = if b.skill_feat_by_choice.is_empty() {
                        b.skill_feat.clone()
                    } else {
                        "follows your skill choice".to_string()
                    };
                    OptionView {
                        id: OptionId::new(&b.id),
                        label: b.name.clone(),
                        summary: b.text.clone(),
                        details: vec![
                            format!(
                                "Boosts: {} or {}, plus one free",
                                b.boost_choice.first().map(|a| a.name()).unwrap_or_default(),
                                b.boost_choice.get(1).map(|a| a.name()).unwrap_or_default()
                            ),
                            format!("Trained: {skill_part}, {lore_part}"),
                            format!("Skill feat: {feat_part}"),
                        ],
                        available: true,
                        unavailable_reason: None,
                    }
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
            // deterministically. (Insert, not push.) An empty skill means
            // the training comes from the sub-choice slot instead.
            if !record.skill.is_empty() {
                state.skill_grants.insert(
                    0,
                    SkillGrant {
                        skill: record.skill.clone(),
                        source: format!("Background: {}", record.name),
                    },
                );
            }
            // A player-named Lore lands via the text sub-choice slot.
            if !record.lore.is_empty() && !record.lore_player_named {
                state
                    .lores
                    .push((record.lore.clone(), format!("Background: {}", record.name)));
            }
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

    // --- Background skill sub-choice (Scholar pattern) ---
    // Exists only while a background with a skill_choice list is chosen;
    // clearing/changing the background clears it via the dependents
    // cascade. The pick lands as a fixed grant, so it feeds the same
    // collision/replacement machinery as a fixed background skill.
    let d = data.clone();
    let d_unlock = data.clone();
    let d_apply = data.clone();
    let d_val = data.clone();
    let d_desc = data.clone();
    regs.push(SlotRegistration::<Pf2eState> {
        id: SlotId::new(SLOT_BACKGROUND_SKILL),
        step: StepId::new(STEP),
        label: "Background skill".into(),
        required: true,
        presentation_hint: None,
        kind: Box::new(|_| SlotViewKind::Single),
        unlock: Box::new(move |state| {
            if background_with_skill_choice(&d_unlock, state).is_some() {
                Availability::Open
            } else {
                Availability::Hidden
            }
        }),
        dependents: vec![
            SlotId::new(SLOT_REPLACEMENT_1),
            SlotId::new(SLOT_REPLACEMENT_2),
            SlotId::new(SLOT_REPLACEMENT_3),
        ],
        options: Box::new(move |state| {
            let Some(b) = background_with_skill_choice(&d, state) else {
                return vec![];
            };
            b.skill_choice
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
            let Some(record) = background_with_skill_choice(&d_apply, state) else {
                return Err(ApplyError::new("the chosen background has no skill choice"));
            };
            if !record.skill_choice.iter().any(|s| s == id.as_str()) {
                return Err(ApplyError::new(format!(
                    "'{id}' is not one of the background's skill options"
                )));
            }
            state.background_skill_choice = Some(id.as_str().to_string());
            state.skill_grants.insert(
                0,
                SkillGrant {
                    skill: id.as_str().to_string(),
                    source: format!("Background: {}", record.name),
                },
            );
            Ok(())
        }),
        validate: Box::new(move |state, decision| {
            if background_with_skill_choice(&d_val, state).is_some() && decision.is_none() {
                vec![incomplete(
                    SLOT_BACKGROUND_SKILL,
                    STEP,
                    "Background",
                    "Choose the skill your background trains",
                    "from Background",
                )]
            } else {
                vec![]
            }
        }),
        meters: Box::new(|_, _| vec![]),
        describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
    });

    // --- Player-named background Lore (Nomad pattern) ---
    let d_unlock = data.clone();
    let d_apply = data.clone();
    let d_val = data.clone();
    let d_desc = data.clone();
    regs.push(SlotRegistration::<Pf2eState> {
        id: SlotId::new(SLOT_BACKGROUND_LORE),
        step: StepId::new(STEP),
        label: "Background Lore".into(),
        required: true,
        presentation_hint: None,
        kind: Box::new(|_| SlotViewKind::Text { multiline: false }),
        unlock: Box::new(move |state| {
            if background_with_player_lore(&d_unlock, state).is_some() {
                Availability::Open
            } else {
                Availability::Hidden
            }
        }),
        dependents: vec![],
        options: Box::new(|_| vec![]),
        apply: Box::new(move |state, decision| {
            let Some(record) = background_with_player_lore(&d_apply, state) else {
                return Err(ApplyError::new(
                    "the chosen background has no player-named Lore",
                ));
            };
            let lore = lore_name_from_text(sel_text(&decision.selection)?)?;
            state
                .lores
                .push((lore, format!("Background: {}", record.name)));
            Ok(())
        }),
        validate: Box::new(move |state, decision| {
            if background_with_player_lore(&d_val, state).is_some() && decision.is_none() {
                vec![incomplete(
                    SLOT_BACKGROUND_LORE,
                    STEP,
                    "Background",
                    "Name the Lore skill your background trains",
                    "from Background",
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
