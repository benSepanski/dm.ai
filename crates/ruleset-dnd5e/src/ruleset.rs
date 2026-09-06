//! The 5.5e ruleset behind the engine-core `Ruleset` contract, plus the
//! embedded rules data every runtime (server, browser, checks) shares —
//! one commit, one data set. The escape hatches answered here are the
//! only 5.5e facts the server ever learns; everything else is a slot.

use std::sync::{Arc, OnceLock};

use engine_core::{EngineError, EngineOps, Ruleset, SuggestedBuild};
use types::{Decision, OptionId, Selection, SlotId};

use crate::data::{RulesData, RulesDataFiles};
use crate::mechanics::{self, Dnd5eState};
use crate::Dnd5eEngine;

pub struct Dnd5eRuleset {
    data: Arc<RulesData>,
    engine: Dnd5eEngine,
    shipped_versions_json: String,
}

impl Dnd5eRuleset {
    /// Assemble over parsed data plus the shipped-versions lineage text.
    pub fn new(data: Arc<RulesData>, shipped_versions_json: String) -> Self {
        let engine = crate::engine(data.clone());
        Self {
            data,
            engine,
            shipped_versions_json,
        }
    }

    /// The concrete engine, for callers inside the workspace's checks that
    /// drive 5.5e directly.
    pub fn concrete(&self) -> &Dnd5eEngine {
        &self.engine
    }

    pub fn data(&self) -> &Arc<RulesData> {
        &self.data
    }

    fn state(&self, log: &[Decision]) -> Result<Dnd5eState, EngineError> {
        self.engine.fold(log)
    }
}

impl Ruleset for Dnd5eRuleset {
    fn system(&self) -> &str {
        &self.data.manifest.system
    }
    fn system_name(&self) -> &str {
        "D&D 5.5e"
    }
    fn rules_version(&self) -> &str {
        &self.data.manifest.version
    }
    fn supersedes(&self) -> &[String] {
        &self.data.manifest.supersedes
    }
    fn shipped_versions_json(&self) -> &str {
        &self.shipped_versions_json
    }
    fn license_lines(&self) -> Vec<String> {
        let n = &self.data.manifest.license_notice;
        vec![n.attribution.clone(), n.license.clone()]
    }
    fn engine(&self) -> &dyn EngineOps {
        &self.engine
    }
    fn name_slot(&self) -> SlotId {
        SlotId::new(mechanics::SLOT_NAME)
    }
    fn class_slot(&self) -> SlotId {
        SlotId::new(mechanics::SLOT_CLASS)
    }
    fn level_of(&self, log: &[Decision]) -> Result<u32, EngineError> {
        Ok(self.state(log)?.level())
    }
    fn next_level(&self, log: &[Decision]) -> Result<Option<u32>, EngineError> {
        let state = self.state(log)?;
        Ok(crate::next_level(&self.data, &state))
    }
    fn advance_slot(&self, level: u32) -> SlotId {
        SlotId::new(mechanics::slot_level_advance(level))
    }
    fn advance_option(&self, level: u32) -> OptionId {
        crate::advancement::advance_option_id(level)
    }
    fn is_advance_slot(&self, slot: &SlotId) -> bool {
        mechanics::advance_level_of(slot.as_str()).is_some()
    }
    /// The SRD publishes no suggested build.
    fn suggested_builds(&self) -> &[SuggestedBuild] {
        &[]
    }
    /// No required free-text slot exists besides the name (the
    /// description is optional), so a mint never writes text here.
    fn text_fill_candidates(&self, _slot: &SlotId) -> Vec<String> {
        Vec::new()
    }
    /// A random mint assigns the standard array (spec req 8): the method
    /// slot is pinned to the first array-kind method record.
    fn mint_pin(&self, slot: &SlotId) -> Option<OptionId> {
        if slot.as_str() != mechanics::SLOT_SCORES_METHOD {
            return None;
        }
        self.data
            .scores
            .methods
            .iter()
            .find(|m| !m.is_point_buy())
            .map(|m| OptionId::new(&m.id))
    }
    fn name_pool_key(&self, log: &[Decision]) -> Option<String> {
        log.iter()
            .rev()
            .find(|d| d.slot.as_str() == mechanics::SLOT_SPECIES)
            .and_then(|d| match &d.selection {
                Selection::Option(id) => Some(id.as_str().to_string()),
                _ => None,
            })
    }
}

// The shipped rules data, embedded at compile time: the same files every
// runtime sees. A corrupt file is a build-time refusal (the checks parse
// it; the first `embedded()` call would panic otherwise).
const RULES_MANIFEST: &str = include_str!("../../../rules-data/dnd5e/manifest.json");
const RULES_SKILLS: &str = include_str!("../../../rules-data/dnd5e/skills.json");
const RULES_SCORES: &str = include_str!("../../../rules-data/dnd5e/scores.json");
const RULES_SPECIES: &str = include_str!("../../../rules-data/dnd5e/species.json");
const RULES_BACKGROUNDS: &str = include_str!("../../../rules-data/dnd5e/backgrounds.json");
const RULES_FEATS: &str = include_str!("../../../rules-data/dnd5e/feats.json");
const RULES_CLASSES: &str = include_str!("../../../rules-data/dnd5e/classes.json");
const RULES_SUBCLASSES: &str = include_str!("../../../rules-data/dnd5e/subclasses.json");
const RULES_EQUIPMENT: &str = include_str!("../../../rules-data/dnd5e/equipment.json");
const RULES_SHIPPED_VERSIONS: &str =
    include_str!("../../../rules-data/dnd5e/shipped-versions.json");

/// The embedded files as the parser takes them.
pub fn embedded_files() -> RulesDataFiles<'static> {
    RulesDataFiles {
        manifest: RULES_MANIFEST,
        skills: RULES_SKILLS,
        scores: RULES_SCORES,
        species: RULES_SPECIES,
        backgrounds: RULES_BACKGROUNDS,
        feats: RULES_FEATS,
        classes: RULES_CLASSES,
        subclasses: RULES_SUBCLASSES,
        equipment: RULES_EQUIPMENT,
    }
}

/// Parse the embedded data (each runtime does this once).
pub fn embedded_data() -> Result<RulesData, crate::DataError> {
    RulesData::parse(&embedded_files())
}

/// The shipped 5.5e ruleset over its embedded data, assembled once per
/// process.
pub fn embedded() -> Arc<Dnd5eRuleset> {
    static RULESET: OnceLock<Arc<Dnd5eRuleset>> = OnceLock::new();
    RULESET
        .get_or_init(|| {
            let data =
                embedded_data().expect("embedded 5.5e rules data parses (asserted by checks)");
            Arc::new(Dnd5eRuleset::new(
                Arc::new(data),
                RULES_SHIPPED_VERSIONS.to_string(),
            ))
        })
        .clone()
}
