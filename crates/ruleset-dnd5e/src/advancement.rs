//! Advancement kind: the level-advance slots. Advancing to a level is a
//! decision in the log — its presence is what makes a character that
//! level (the fold counts advances; nothing stores a level). Each advance
//! slot lives in a step that is never live, so the start-level route can
//! append it while no card ever renders it. Applying an advance grants
//! the class's fixed features for that level, from data; the choice slot
//! a level opens (the subclass) is registered by the class kind.

use std::sync::Arc;

use engine_core::{ApplyError, Availability, SlotRegistration};
use types::{OptionId, OptionView, SlotId, SlotViewKind, StepId};

use crate::data::RulesData;
use crate::mechanics::{sel_single, slot_level_advance, step_level_advance, Dnd5eState};

/// The one option an advance slot offers.
pub fn advance_option_id(level: u32) -> OptionId {
    OptionId::new(format!("advance.{level}"))
}

pub fn registrations(data: &Arc<RulesData>) -> Vec<SlotRegistration<Dnd5eState>> {
    let mut regs = Vec::new();
    for level in 2..=data.max_advancement_level() {
        let d_unlock = data.clone();
        let d_apply = data.clone();
        regs.push(SlotRegistration::<Dnd5eState> {
            id: SlotId::new(slot_level_advance(level)),
            step: StepId::new(step_level_advance(level)),
            label: format!("Advance to level {level}"),
            // Never on the checklist: a character is complete at every
            // level; advancing is an act, not a gap.
            required: false,
            presentation_hint: None,
            kind: Box::new(|_| SlotViewKind::Single),
            unlock: Box::new(move |state| {
                let cap = state
                    .class
                    .as_ref()
                    .and_then(|id| d_unlock.class(id))
                    .map(|c| c.level_cap())
                    .unwrap_or(1);
                if state.level() + 1 == level && level <= cap {
                    Availability::Open
                } else {
                    Availability::Hidden
                }
            }),
            dependents: vec![],
            options: Box::new(move |_| {
                vec![OptionView {
                    id: advance_option_id(level),
                    label: format!("Level {level}"),
                    summary: format!("Advance to level {level}"),
                    details: vec![],
                    available: true,
                    unavailable_reason: None,
                    group: None,
                    badge: None,
                }]
            }),
            apply: Box::new(move |state, decision| {
                let id = sel_single(&decision.selection)?;
                if *id != advance_option_id(level) {
                    return Err(ApplyError::new(format!("unknown advance option '{id}'")));
                }
                // Advances are strictly sequential: one per level, in
                // order — two advances in one tail cannot fold.
                if state.level() + 1 != level {
                    return Err(ApplyError::new(format!(
                        "cannot advance to level {level} from level {}",
                        state.level()
                    )));
                }
                let class = state
                    .class
                    .as_ref()
                    .and_then(|id| d_apply.class(id))
                    .ok_or_else(|| ApplyError::new("choose a class before advancing"))?;
                let adv = class.advancement_at(level).ok_or_else(|| {
                    ApplyError::new(format!(
                        "{} has no level {level} in this rules data",
                        class.name
                    ))
                })?;
                state.level_advances += 1;
                for feature in &adv.features {
                    state.granted_features.push((level, feature.id.clone()));
                }
                Ok(())
            }),
            validate: Box::new(|_, _| vec![]),
            meters: Box::new(|_, _| vec![]),
            describe: Box::new(move |_| format!("advanced to level {level}")),
        });
    }
    regs
}
