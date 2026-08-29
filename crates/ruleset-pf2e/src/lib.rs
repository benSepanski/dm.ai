//! Pathfinder 2e ruleset: slot definitions, option catalogs, validators,
//! and sheet derivation. Rules-data records are passed in as strings —
//! this crate never touches the filesystem.
//!
//! Layering inside the crate (enforced by checks/crate_layering.rs):
//! kind modules (ancestry, background, class, feats, skills, equipment)
//! never import each other; kinds -> mechanics -> engine-core.
#![forbid(unsafe_code)]

mod ancestry;
mod background;
mod boosts;
mod class;
mod data;
mod details;
mod equipment;
mod feats;
mod mechanics;
mod skills;
#[cfg(test)]
mod tests;

use std::sync::Arc;

use engine_core::Engine;
use types::StepId;

pub use data::{DataError, RulesData, RulesDataFiles};
pub use mechanics::Pf2eState;

pub type Pf2eEngine = Engine<Pf2eState>;

/// Assemble the PF2e engine over a parsed rules-data set.
pub fn engine(data: Arc<RulesData>) -> Pf2eEngine {
    let steps = vec![
        (StepId::new(mechanics::STEP_CONCEPT), "Concept".to_string()),
        (
            StepId::new(mechanics::STEP_ANCESTRY),
            "Ancestry".to_string(),
        ),
        (
            StepId::new(mechanics::STEP_BACKGROUND),
            "Background".to_string(),
        ),
        (StepId::new(mechanics::STEP_CLASS), "Class".to_string()),
        (
            StepId::new(mechanics::STEP_BOOSTS),
            "Attribute Boosts".to_string(),
        ),
        (
            StepId::new(mechanics::STEP_EQUIPMENT),
            "Equipment".to_string(),
        ),
        (StepId::new(mechanics::STEP_DETAILS), "Details".to_string()),
    ];

    let mut registrations = Vec::new();
    registrations.extend(details::registrations(&data));
    registrations.extend(ancestry::registrations(&data));
    registrations.extend(background::registrations(&data));
    registrations.extend(class::registrations(&data));
    registrations.extend(feats::registrations(&data));
    registrations.extend(skills::registrations(&data));
    registrations.extend(boosts::registrations(&data));
    registrations.extend(equipment::registrations(&data));

    let d_sheet = data.clone();
    Engine::new(
        steps,
        registrations,
        Box::new(Pf2eState::default),
        Box::new(move |state| mechanics::derive_sheet(state, &d_sheet)),
    )
}

/// The manifest version string ("pf2e-pc.0.1.0") — what characters pin.
pub fn rules_version(data: &RulesData) -> &str {
    &data.manifest.version
}
