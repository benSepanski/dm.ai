//! The PF2e ruleset behind the engine-core `Ruleset` contract, plus the
//! embedded rules data every runtime (server, browser, checks) shares —
//! one commit, one data set. The escape hatches answered here are the
//! only PF2e facts the server ever learns; everything else is a slot.

use std::sync::{Arc, OnceLock};

use engine_core::{EngineError, EngineOps, Ruleset, SuggestedBuild};
use types::{Decision, OptionId, Selection, SlotId};

use crate::data::{RulesData, RulesDataFiles};
use crate::mechanics::{self, Pf2eState};
use crate::Pf2eEngine;

/// Free-text lore topics a random mint may write into a slot that asks the
/// player to name a Lore skill. Own-authored app vocabulary, not rules
/// content.
const LORE_TOPICS: &[&str] = &[
    "Farming Lore",
    "Fishing Lore",
    "Milling Lore",
    "Tanning Lore",
    "Caravan Lore",
    "Brewing Lore",
    "Stonework Lore",
    "Herbalism Lore",
];

pub struct Pf2eRuleset {
    data: Arc<RulesData>,
    engine: Pf2eEngine,
    suggested: Vec<SuggestedBuild>,
    shipped_versions_json: String,
}

impl Pf2eRuleset {
    /// Assemble over parsed data plus the shipped-versions lineage text.
    pub fn new(data: Arc<RulesData>, shipped_versions_json: String) -> Self {
        let suggested = crate::suggested_builds(&data);
        let engine = crate::engine(data.clone());
        Self {
            data,
            engine,
            suggested,
            shipped_versions_json,
        }
    }

    /// The concrete engine, for callers inside the workspace's checks that
    /// drive PF2e directly.
    pub fn concrete(&self) -> &Pf2eEngine {
        &self.engine
    }

    pub fn data(&self) -> &Arc<RulesData> {
        &self.data
    }

    fn state(&self, log: &[Decision]) -> Result<Pf2eState, EngineError> {
        self.engine.fold(log)
    }
}

impl Ruleset for Pf2eRuleset {
    fn system(&self) -> &str {
        &self.data.manifest.system
    }
    fn system_name(&self) -> &str {
        "Pathfinder 2e"
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
        vec![
            n.orc_notice.clone(),
            n.attribution.clone(),
            n.reserved.clone(),
        ]
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
        Ok(self.state(log)?.level() as u32)
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
    fn suggested_builds(&self) -> &[SuggestedBuild] {
        &self.suggested
    }
    fn text_fill_candidates(&self, slot: &SlotId) -> Vec<String> {
        if slot.as_str() == mechanics::SLOT_NAME {
            return Vec::new();
        }
        LORE_TOPICS.iter().map(|t| (*t).to_string()).collect()
    }
    fn name_pool_key(&self, log: &[Decision]) -> Option<String> {
        log.iter()
            .rev()
            .find(|d| d.slot.as_str() == mechanics::SLOT_ANCESTRY)
            .and_then(|d| match &d.selection {
                Selection::Option(id) => Some(id.as_str().to_string()),
                _ => None,
            })
    }
}

// The shipped rules data, embedded at compile time: the same files every
// runtime sees. A corrupt file is a build-time refusal (the checks parse
// it; the first `embedded()` call would panic otherwise).
const RULES_MANIFEST: &str = include_str!("../../../rules-data/pf2e/manifest.json");
const RULES_ANCESTRIES: &str = include_str!("../../../rules-data/pf2e/ancestries.json");
const RULES_HERITAGES: &str = include_str!("../../../rules-data/pf2e/heritages.json");
const RULES_ANCESTRY_FEATS: &str = include_str!("../../../rules-data/pf2e/ancestry-feats.json");
const RULES_BACKGROUNDS: &str = include_str!("../../../rules-data/pf2e/backgrounds.json");
const RULES_CLASSES: &str = include_str!("../../../rules-data/pf2e/classes.json");
const RULES_CLASS_FEATS: &str = include_str!("../../../rules-data/pf2e/class-feats.json");
const RULES_GENERAL_FEATS: &str = include_str!("../../../rules-data/pf2e/general-feats.json");
const RULES_SKILLS: &str = include_str!("../../../rules-data/pf2e/skills.json");
const RULES_EQUIPMENT: &str = include_str!("../../../rules-data/pf2e/equipment.json");
const RULES_SPELLS: &str = include_str!("../../../rules-data/pf2e/spells.json");
const RULES_SHIPPED_VERSIONS: &str = include_str!("../../../rules-data/pf2e/shipped-versions.json");

/// The embedded files as the parser takes them.
pub fn embedded_files() -> RulesDataFiles<'static> {
    RulesDataFiles {
        manifest: RULES_MANIFEST,
        ancestries: RULES_ANCESTRIES,
        heritages: RULES_HERITAGES,
        ancestry_feats: RULES_ANCESTRY_FEATS,
        backgrounds: RULES_BACKGROUNDS,
        classes: RULES_CLASSES,
        class_feats: RULES_CLASS_FEATS,
        general_feats: RULES_GENERAL_FEATS,
        skills: RULES_SKILLS,
        equipment: RULES_EQUIPMENT,
        spells: RULES_SPELLS,
    }
}

/// Parse the embedded data (each runtime does this once).
pub fn embedded_data() -> Result<RulesData, crate::DataError> {
    RulesData::parse(&embedded_files())
}

/// The shipped PF2e ruleset over its embedded data, assembled once per
/// process.
pub fn embedded() -> Arc<Pf2eRuleset> {
    static RULESET: OnceLock<Arc<Pf2eRuleset>> = OnceLock::new();
    RULESET
        .get_or_init(|| {
            let data =
                embedded_data().expect("embedded PF2e rules data parses (asserted by checks)");
            Arc::new(Pf2eRuleset::new(
                Arc::new(data),
                RULES_SHIPPED_VERSIONS.to_string(),
            ))
        })
        .clone()
}
