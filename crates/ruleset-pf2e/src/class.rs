//! Class kind: the class slot and its key-attribute boost.

use std::sync::Arc;

use engine_core::{ApplyError, Availability, SlotRegistration};
use types::{OptionId, OptionView, SlotId, SlotViewKind, StepId};

use crate::data::RulesData;
use crate::mechanics::{
    describe_selection, incomplete, sel_attribute, sel_single, Pf2eState, SLOT_CLASS,
    SLOT_CLASS_FEAT, SLOT_CLASS_SKILL, SLOT_KEY_ATTRIBUTE, SLOT_KIT, SLOT_NATURAL_AMBITION,
    SLOT_SCHOOL, SLOT_SPELLBOOK_CANTRIPS, SLOT_SPELLBOOK_RANK1, SLOT_THESIS, SLOT_TRAINED_SKILLS,
};

const STEP: &str = crate::mechanics::STEP_CLASS;

pub fn registrations(data: &Arc<RulesData>) -> Vec<SlotRegistration<Pf2eState>> {
    let mut regs = Vec::new();

    // --- Class ---
    let d = data.clone();
    let d_apply = data.clone();
    let d_desc = data.clone();
    regs.push(SlotRegistration::<Pf2eState> {
        id: SlotId::new(SLOT_CLASS),
        step: StepId::new(STEP),
        label: "Class".into(),
        required: true,
        presentation_hint: None,
        kind: Box::new(|_| SlotViewKind::Single),
        unlock: Box::new(|_| Availability::Open),
        dependents: vec![
            SlotId::new(SLOT_KEY_ATTRIBUTE),
            SlotId::new(SLOT_CLASS_FEAT),
            SlotId::new(SLOT_CLASS_SKILL),
            SlotId::new(SLOT_TRAINED_SKILLS),
            SlotId::new(SLOT_KIT),
            SlotId::new(SLOT_NATURAL_AMBITION),
            // Spellcasting build choices die with the class.
            SlotId::new(SLOT_THESIS),
            SlotId::new(SLOT_SCHOOL),
            SlotId::new(SLOT_SPELLBOOK_CANTRIPS),
            SlotId::new(SLOT_SPELLBOOK_RANK1),
        ],
        options: Box::new(move |_| {
            d.classes
                .iter()
                .map(|c| OptionView {
                    id: OptionId::new(&c.id),
                    label: c.name.clone(),
                    summary: c.text.clone(),
                    details: vec![
                        format!(
                            "Key attribute: {}",
                            c.key_attribute_choice
                                .iter()
                                .map(|a| a.name())
                                .collect::<Vec<_>>()
                                .join(" or ")
                        ),
                        format!("{} HP per level", c.hp_per_level),
                        format!(
                            "Features: {}",
                            c.features
                                .iter()
                                .map(|f| f.name.as_str())
                                .collect::<Vec<_>>()
                                .join(", ")
                        ),
                    ],
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
                .class(id.as_str())
                .ok_or_else(|| ApplyError::new(format!("unknown class '{id}'")))?;
            state.class = Some(record.id.clone());
            state.class_name = Some(record.name.clone());
            Ok(())
        }),
        validate: Box::new(|state, _| {
            if state.class.is_none() {
                vec![incomplete(
                    SLOT_CLASS,
                    STEP,
                    "Class",
                    "Choose a class",
                    "character creation",
                )]
            } else {
                vec![]
            }
        }),
        meters: Box::new(|_, _| vec![]),
        describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
    });

    // --- Key attribute ---
    let d = data.clone();
    let d_apply = data.clone();
    let d_desc = data.clone();
    regs.push(SlotRegistration::<Pf2eState> {
        id: SlotId::new(SLOT_KEY_ATTRIBUTE),
        step: StepId::new(STEP),
        label: "Key attribute".into(),
        required: true,
        presentation_hint: Some("attribute-boosts".into()),
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
            c.key_attribute_choice
                .iter()
                .map(|attr| OptionView {
                    id: attr.option_id(),
                    label: attr.name().to_string(),
                    summary: "Gains this class's boost".into(),
                    details: vec![],
                    available: true,
                    unavailable_reason: None,
                    group: None,
                    badge: None,
                })
                .collect()
        }),
        apply: Box::new(move |state, decision| {
            let attr = sel_attribute(&decision.selection)?;
            if let Some(c) = state.class.as_ref().and_then(|id| d_apply.class(id)) {
                if !c.key_attribute_choice.contains(&attr) {
                    return Err(ApplyError::new(format!(
                        "{} is not a key attribute option for this class",
                        attr.name()
                    )));
                }
            }
            state.key_attribute = Some(attr);
            state.boost_batches.insert("class".into(), vec![attr]);
            Ok(())
        }),
        validate: Box::new(|state, decision| {
            if state.class.is_some() && decision.is_none() {
                vec![incomplete(
                    SLOT_KEY_ATTRIBUTE,
                    STEP,
                    "Key attribute",
                    "Choose your key attribute (it gains a boost)",
                    "from Class",
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
