//! D&D 5.5e (SRD 5.2.1) ruleset: slot definitions, option catalogs,
//! validators, and sheet derivation. Rules-data records are passed in as
//! strings — this crate never touches the filesystem.
//!
//! Layering inside the crate (enforced by checks/crate_layering.rs):
//! kind modules (class, background, species, scores, feats, equipment,
//! details, advancement) never import each other; kinds -> mechanics ->
//! engine-core.
#![forbid(unsafe_code)]

mod advancement;
mod background;
mod class;
mod data;
mod details;
mod equipment;
mod feats;
mod mechanics;
mod ruleset;
mod scores;
mod species;
#[cfg(test)]
mod tests;

use std::sync::Arc;

use engine_core::{Engine, StepRegistration};
use types::StepId;

pub use data::{DataError, RulesData, RulesDataFiles};
pub use mechanics::Dnd5eState;
pub use ruleset::{embedded, embedded_data, embedded_files, Dnd5eRuleset};

pub type Dnd5eEngine = Engine<Dnd5eState>;

/// Assemble the 5.5e engine over a parsed rules-data set.
pub fn engine(data: Arc<RulesData>) -> Dnd5eEngine {
    // Creation steps follow the published sequence and are live while the
    // character is level 1 — the creation dialog. Each further level has
    // a rendered step (live while that level is the character's current
    // one; empty when the level grants no choice) and a never-live step
    // holding its advance slot.
    let creation = |id: &str, title: &str| StepRegistration::<Dnd5eState> {
        id: StepId::new(id),
        title: title.to_string(),
        live: Box::new(|state| state.level() == 1),
    };
    let mut steps = vec![
        creation(mechanics::STEP_CLASS, "Class"),
        creation(mechanics::STEP_ORIGIN, "Origin"),
        creation(mechanics::STEP_SCORES, "Ability Scores"),
        creation(mechanics::STEP_CLASS_CHOICES, "Class Choices"),
        creation(mechanics::STEP_EQUIPMENT, "Equipment"),
        creation(mechanics::STEP_DETAILS, "Details"),
    ];
    for level in 2..=data.max_advancement_level() {
        steps.push(StepRegistration::<Dnd5eState> {
            id: StepId::new(mechanics::step_level_advance(level)),
            title: format!("Advance to level {level}"),
            live: Box::new(|_| false),
        });
        steps.push(StepRegistration::<Dnd5eState> {
            id: StepId::new(mechanics::step_level(level)),
            title: format!("Level {level}"),
            live: Box::new(move |state| state.level() == level),
        });
    }

    let mut registrations = Vec::new();
    registrations.extend(advancement::registrations(&data));
    registrations.extend(details::registrations(&data));
    registrations.extend(class::registrations(&data));
    registrations.extend(background::registrations(&data));
    registrations.extend(species::registrations(&data));
    registrations.extend(scores::registrations(&data));
    registrations.extend(feats::registrations(&data));
    registrations.extend(equipment::registrations(&data));

    let d_sheet = data.clone();
    Engine::new(
        steps,
        registrations,
        Box::new(Dnd5eState::default),
        Box::new(move |state| mechanics::derive_sheet(state, &d_sheet)),
    )
}

/// The manifest version string ("dnd5e-srd.0.1.0") — what characters pin.
pub fn rules_version(data: &RulesData) -> &str {
    &data.manifest.version
}

/// The level a finalized log's class can advance to next, if any: one past
/// the log's level while that is within the class's shipped cap.
pub fn next_level(data: &RulesData, state: &Dnd5eState) -> Option<u32> {
    let cap = data.class(state.class.as_ref()?)?.level_cap();
    let next = state.level() + 1;
    (next <= cap).then_some(next)
}

pub use mechanics::SLOT_CLASS as CLASS_SLOT_ID;
pub use mechanics::SLOT_NAME as NAME_SLOT_ID;
pub use mechanics::SLOT_SPECIES as SPECIES_SLOT_ID;
pub use mechanics::{advance_level_of, slot_level_advance, slot_level_subclass, step_level};
