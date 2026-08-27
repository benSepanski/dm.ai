//! The four free attribute boosts ("finish attribute boosts"). Not a kind
//! module — free boosts belong to character creation itself.

use std::sync::Arc;

use engine_core::{Availability, SlotRegistration};
use types::{SlotId, SlotViewKind, StepId};

use crate::data::RulesData;
use crate::mechanics::{
    attribute_options, describe_selection, illegal, incomplete, sel_attributes, Pf2eState,
    SLOT_FREE_BOOSTS,
};

const STEP: &str = crate::mechanics::STEP_BOOSTS;
const COUNT: usize = 4;

pub fn registrations(data: &Arc<RulesData>) -> Vec<SlotRegistration<Pf2eState>> {
    let d_desc = data.clone();
    vec![SlotRegistration::<Pf2eState> {
        id: SlotId::new(SLOT_FREE_BOOSTS),
        step: StepId::new(STEP),
        label: "Free attribute boosts".into(),
        required: true,
        presentation_hint: Some("attribute-boosts".into()),
        kind: Box::new(|_| SlotViewKind::Multi {
            count: COUNT as u32,
        }),
        unlock: Box::new(|_| Availability::Open),
        dependents: vec![],
        options: Box::new(|_| attribute_options(|_| None)),
        apply: Box::new(|state, decision| {
            let attrs = sel_attributes(&decision.selection)?;
            state.boost_batches.insert("free".into(), attrs);
            Ok(())
        }),
        validate: Box::new(|state, decision| {
            let batch = state.boost_batches.get("free").cloned().unwrap_or_default();
            let mut out = Vec::new();
            if decision.is_none() || batch.len() < COUNT {
                out.push(incomplete(
                    SLOT_FREE_BOOSTS,
                    STEP,
                    "Attribute boosts",
                    &format!("{} free boost(s) left", COUNT - batch.len().min(COUNT)),
                    "character creation",
                ));
            }
            let mut sorted = batch.clone();
            sorted.sort();
            let mut deduped = sorted.clone();
            deduped.dedup();
            if sorted.len() != deduped.len() {
                out.push(illegal(
                    SLOT_FREE_BOOSTS,
                    STEP,
                    "Attribute boosts",
                    "Boosts gained at the same time must go to different attributes",
                    "Player Core pg. 19",
                ));
            }
            out
        }),
        describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
    }]
}
