//! Details: free-text slots. Only the name is required.

use std::sync::Arc;

use engine_core::{Availability, SlotRegistration};
use types::{SlotId, SlotViewKind, StepId};

use crate::data::RulesData;
use crate::mechanics::{
    describe_selection, incomplete, sel_text, Dnd5eState, SLOT_DESCRIPTION, SLOT_NAME, STEP_DETAILS,
};

pub fn registrations(data: &Arc<RulesData>) -> Vec<SlotRegistration<Dnd5eState>> {
    let d1 = data.clone();
    let d2 = data.clone();
    vec![
        SlotRegistration::<Dnd5eState> {
            id: SlotId::new(SLOT_NAME),
            step: StepId::new(STEP_DETAILS),
            label: "Name".into(),
            required: true,
            presentation_hint: None,
            kind: Box::new(|_| SlotViewKind::Text { multiline: false }),
            unlock: Box::new(|_| Availability::Open),
            dependents: vec![],
            options: Box::new(|_| vec![]),
            apply: Box::new(|state, decision| {
                state.name = Some(sel_text(&decision.selection)?.trim().to_string());
                Ok(())
            }),
            validate: Box::new(|state, _| {
                if state.name.as_deref().unwrap_or("").is_empty() {
                    vec![incomplete(
                        SLOT_NAME,
                        STEP_DETAILS,
                        "Details",
                        "Give your character a name",
                        "character creation",
                    )]
                } else {
                    vec![]
                }
            }),
            meters: Box::new(|_, _| vec![]),
            describe: Box::new(move |sel| describe_selection(&d1, sel)),
        },
        SlotRegistration::<Dnd5eState> {
            id: SlotId::new(SLOT_DESCRIPTION),
            step: StepId::new(STEP_DETAILS),
            label: "Appearance & notes".into(),
            required: false,
            presentation_hint: None,
            kind: Box::new(|_| SlotViewKind::Text { multiline: true }),
            unlock: Box::new(|_| Availability::Open),
            dependents: vec![],
            options: Box::new(|_| vec![]),
            apply: Box::new(|state, decision| {
                state.description = Some(sel_text(&decision.selection)?.to_string());
                Ok(())
            }),
            validate: Box::new(|_, _| vec![]),
            meters: Box::new(|_, _| vec![]),
            describe: Box::new(move |sel| describe_selection(&d2, sel)),
        },
    ]
}
