//! Pathfinder 2e ruleset: slot definitions, option catalogs, validators,
//! and sheet derivation. Rules-data records are passed in as strings —
//! this crate never touches the filesystem.
//!
//! Layering inside the crate (enforced by checks/crate_layering.rs):
//! kind modules (ancestry, background, class, feats, skills, equipment)
//! never import each other; kinds -> mechanics -> engine-core.
#![forbid(unsafe_code)]

mod advancement;
mod ancestry;
mod background;
mod boosts;
mod class;
mod data;
mod details;
mod equipment;
mod feats;
mod mechanics;
mod ruleset;
mod skills;
mod spells;
#[cfg(test)]
mod tests;

use std::sync::Arc;

use engine_core::{Engine, StepRegistration};
use types::StepId;

pub use data::{DataError, RulesData, RulesDataFiles};
pub use mechanics::Pf2eState;
pub use ruleset::{embedded, embedded_data, embedded_files, Pf2eRuleset};

pub type Pf2eEngine = Engine<Pf2eState>;

/// Assemble the PF2e engine over a parsed rules-data set.
pub fn engine(data: Arc<RulesData>) -> Pf2eEngine {
    // Creation steps are live while the character is level 1 — the
    // creation dialog. Each further level has a rendered step (live while
    // that level is the character's current one) and a never-live step
    // holding its advance slot.
    let creation = |id: &str, title: &str| StepRegistration::<Pf2eState> {
        id: StepId::new(id),
        title: title.to_string(),
        live: Box::new(|state| state.level() == 1),
    };
    let mut steps = vec![
        creation(mechanics::STEP_CONCEPT, "Concept"),
        creation(mechanics::STEP_ANCESTRY, "Ancestry"),
        creation(mechanics::STEP_BACKGROUND, "Background"),
        creation(mechanics::STEP_CLASS, "Class"),
        creation(mechanics::STEP_BOOSTS, "Attribute Boosts"),
        creation(mechanics::STEP_EQUIPMENT, "Equipment"),
        creation(mechanics::STEP_DETAILS, "Details"),
    ];
    for level in 2..=data.max_advancement_level() {
        steps.push(StepRegistration::<Pf2eState> {
            id: StepId::new(mechanics::step_level_advance(level)),
            title: format!("Advance to level {level}"),
            live: Box::new(|_| false),
        });
        steps.push(StepRegistration::<Pf2eState> {
            id: StepId::new(mechanics::step_level(level)),
            title: format!("Level {level}"),
            live: Box::new(move |state| state.level() as u32 == level),
        });
    }

    let mut registrations = Vec::new();
    registrations.extend(advancement::registrations(&data));
    registrations.extend(details::registrations(&data));
    registrations.extend(ancestry::registrations(&data));
    registrations.extend(background::registrations(&data));
    registrations.extend(class::registrations(&data));
    registrations.extend(spells::registrations(&data));
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

pub use mechanics::SLOT_ANCESTRY as ANCESTRY_SLOT_ID;
pub use mechanics::{advance_level_of, level_grants, slot_level_advance, step_level, LevelGrants};

/// The level a finalized log's class can advance to next, if any: one past
/// the log's level while that is within the class's shipped cap.
pub fn next_level(data: &RulesData, state: &Pf2eState) -> Option<u32> {
    let cap = data.class(state.class.as_ref()?)?.level_cap();
    let next = state.level() as u32 + 1;
    (next <= cap).then_some(next)
}
/// The class-selection slot ID — lets the server steer fill-remaining to
/// the chosen class's suggested build without hardcoding game vocabulary.
pub use mechanics::SLOT_CLASS as CLASS_SLOT_ID;
pub use mechanics::SLOT_NAME as NAME_SLOT_ID;

/// Every class's suggested build, resolved into the planner's shape:
/// (class record ID, slot → suggestion). The planner interprets the class
/// record's ordered-candidate block directly (architecture: no per-slot
/// suggest hook); this is the one translation from content to the
/// engine-core vocabulary.
pub fn suggested_builds(
    data: &RulesData,
) -> Vec<(
    String,
    std::collections::BTreeMap<types::SlotId, engine_core::SlotSuggestion>,
)> {
    data.classes
        .iter()
        .filter_map(|class| {
            let block = class.suggested_build.as_ref()?;
            let map = block
                .entries
                .iter()
                .map(|entry| {
                    let suggestion = match &entry.text {
                        Some(text) => engine_core::SlotSuggestion::Text(text.clone()),
                        None => engine_core::SlotSuggestion::Candidates(
                            entry.candidates.iter().map(types::OptionId::new).collect(),
                        ),
                    };
                    (types::SlotId::new(&entry.slot), suggestion)
                })
                .collect();
            Some((class.id.clone(), map))
        })
        .collect()
}
