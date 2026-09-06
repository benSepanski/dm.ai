//! Equipment kind: the class's starting-equipment choice — one of its
//! published packages or the coin alternative, all data on the class
//! record. The background's own offer is the background kind's slot.

use std::sync::Arc;

use engine_core::{ApplyError, Availability, SlotRegistration};
use types::{OptionId, OptionView, SlotId, SlotViewKind, StepId};

use crate::data::RulesData;
use crate::mechanics::{
    describe_selection, incomplete, sel_single, Dnd5eState, SLOT_EQUIPMENT_PACKAGE, STEP_EQUIPMENT,
};

pub fn registrations(data: &Arc<RulesData>) -> Vec<SlotRegistration<Dnd5eState>> {
    let d = data.clone();
    let d_apply = data.clone();
    let d_val = data.clone();
    let d_desc = data.clone();
    vec![SlotRegistration::<Dnd5eState> {
        id: SlotId::new(SLOT_EQUIPMENT_PACKAGE),
        step: StepId::new(STEP_EQUIPMENT),
        label: "Class starting equipment".into(),
        required: true,
        presentation_hint: None,
        kind: Box::new(|_| SlotViewKind::Single),
        unlock: Box::new(|state| match state.class {
            Some(_) => Availability::Open,
            None => Availability::Locked {
                reason: "choose a class first — starting equipment is class-specific".into(),
            },
        }),
        dependents: vec![],
        options: Box::new(move |state| {
            let Some(c) = state.class.as_ref().and_then(|id| d.class(id)) else {
                return vec![];
            };
            let mut out = Vec::new();
            for p in &c.equipment_packages {
                let items: Vec<String> = p
                    .items
                    .iter()
                    .map(|line| {
                        let name = d.item_name(&line.item).unwrap_or_default();
                        if line.count > 1 {
                            format!("{} {name}", line.count)
                        } else {
                            name
                        }
                    })
                    .collect();
                out.push(OptionView {
                    id: OptionId::new(&p.id),
                    label: format!("Package {}", p.label),
                    summary: format!("{}, and {} GP", items.join(", "), p.gold),
                    details: vec![],
                    available: true,
                    unavailable_reason: None,
                    group: None,
                    badge: None,
                });
            }
            out.push(OptionView {
                id: OptionId::new(&c.gold_alternative.id),
                label: format!("Option {}", c.gold_alternative.label),
                summary: format!("{} GP to buy equipment yourself", c.gold_alternative.gold),
                details: vec![],
                available: true,
                unavailable_reason: None,
                group: None,
                badge: None,
            });
            out
        }),
        apply: Box::new(move |state, decision| {
            let id = sel_single(&decision.selection)?;
            let Some(c) = state.class.as_ref().and_then(|id| d_apply.class(id)) else {
                return Err(ApplyError::new(
                    "choose a class before its starting equipment",
                ));
            };
            let known = c.equipment_packages.iter().any(|p| p.id == id.as_str())
                || c.gold_alternative.id == id.as_str();
            if !known {
                return Err(ApplyError::new(format!(
                    "'{id}' is not one of the {}'s starting-equipment options",
                    c.name
                )));
            }
            state.equipment_package = Some(id.as_str().to_string());
            Ok(())
        }),
        validate: Box::new(move |state, decision| {
            let Some(c) = state.class.as_ref().and_then(|id| d_val.class(id)) else {
                return vec![];
            };
            if decision.is_none() || state.equipment_package.is_none() {
                vec![incomplete(
                    SLOT_EQUIPMENT_PACKAGE,
                    STEP_EQUIPMENT,
                    "Starting Equipment",
                    "Choose a starting-equipment package or the coin alternative",
                    &format!("from {}", c.name),
                )]
            } else {
                vec![]
            }
        }),
        meters: Box::new(|_, _| vec![]),
        describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
    }]
}
