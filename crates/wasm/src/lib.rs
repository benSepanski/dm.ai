//! The browser copy of the engine: one serde-tagged request enum in, one
//! response enum out, with tsify-generated TypeScript declarations welded
//! into the wasm-bindgen `.d.ts`. The UI imports only the thin TS façade
//! over this module (`ui/src/engine`).
#![forbid(unsafe_code)]

use std::sync::{Arc, OnceLock};

use ruleset_pf2e::Pf2eEngine;
use tsify::{Ts, Tsify};
use types::{EngineRequest, EngineResponse};
use wasm_bindgen::prelude::*;

// The same rules-data files the server embeds — one commit, one data set,
// two runtimes.
const RULES_MANIFEST: &str = include_str!("../../../rules-data/manifest.json");
const RULES_ANCESTRIES: &str = include_str!("../../../rules-data/ancestries.json");
const RULES_HERITAGES: &str = include_str!("../../../rules-data/heritages.json");
const RULES_ANCESTRY_FEATS: &str = include_str!("../../../rules-data/ancestry-feats.json");
const RULES_BACKGROUNDS: &str = include_str!("../../../rules-data/backgrounds.json");
const RULES_CLASSES: &str = include_str!("../../../rules-data/classes.json");
const RULES_CLASS_FEATS: &str = include_str!("../../../rules-data/class-feats.json");
const RULES_GENERAL_FEATS: &str = include_str!("../../../rules-data/general-feats.json");
const RULES_SKILLS: &str = include_str!("../../../rules-data/skills.json");
const RULES_EQUIPMENT: &str = include_str!("../../../rules-data/equipment.json");
const RULES_SPELLS: &str = include_str!("../../../rules-data/spells.json");

fn engine() -> &'static Pf2eEngine {
    static ENGINE: OnceLock<Pf2eEngine> = OnceLock::new();
    ENGINE.get_or_init(|| {
        let data = ruleset_pf2e::RulesData::parse(&ruleset_pf2e::RulesDataFiles {
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
        })
        .expect("embedded rules data parses (asserted at build by checks)");
        ruleset_pf2e::engine(Arc::new(data))
    })
}

/// Surfaces Rust panic messages to the browser console so a dead engine is
/// loud, never a silently inert widget.
#[wasm_bindgen(start)]
pub fn start() {
    console_error_panic_hook::set_once();
}

/// The narrow boundary: every engine interaction is one request in, one
/// response out. Deserialization failures surface as catchable JS errors.
#[wasm_bindgen]
pub fn engine_request(request: Ts<EngineRequest>) -> Result<Ts<EngineResponse>, JsError> {
    let request: EngineRequest = request.to_rust()?;
    let response = handle(request);
    Ok(response.into_ts()?)
}

fn handle(request: EngineRequest) -> EngineResponse {
    match request {
        EngineRequest::Project { log, prep } => match engine().project(&log, &prep) {
            Ok(projection) => EngineResponse::Projection { projection },
            Err(e) => EngineResponse::Error {
                message: e.to_string(),
            },
        },
        EngineRequest::Preview {
            log,
            candidate,
            prep,
        } => match engine().preview(&log, &candidate, &prep) {
            Ok(projection) => EngineResponse::Projection { projection },
            Err(e) => EngineResponse::Error {
                message: e.to_string(),
            },
        },
        EngineRequest::PreviewPrep { log, prep } => match engine().project(&log, &prep) {
            Ok(projection) => EngineResponse::Projection { projection },
            Err(e) => EngineResponse::Error {
                message: e.to_string(),
            },
        },
        EngineRequest::ClearPreview { log, slot, prep } => {
            match engine().clear_preview(&log, &prep, &slot) {
                Ok(preview) => EngineResponse::ClearPreview { preview },
                Err(e) => EngineResponse::Error {
                    message: e.to_string(),
                },
            }
        }
    }
}

/// The HTTP wire types aren't referenced by the engine boundary, but the UI
/// needs their TypeScript declarations from the same generated `.d.ts`.
/// This carrier keeps them alive through code generation; it is never
/// instantiated.
#[derive(Tsify, serde::Serialize, serde::Deserialize)]
pub struct WireTypeExports {
    pub roster: types::RosterView,
    pub character: types::CharacterView,
    pub create_request: types::CreateCharacterRequest,
    pub confirm_request: types::ConfirmRequest,
    pub confirm_outcome: types::ConfirmOutcome,
    pub clear_request: types::ClearRequest,
    pub clear_outcome: types::ClearOutcome,
    pub step_request: types::StepRequest,
    pub finalize_request: types::FinalizeRequest,
    pub finalize_outcome: types::FinalizeOutcome,
    pub api_error: types::ApiError,
    pub version_action_request: types::VersionActionRequest,
    pub version_resolution_outcome: types::VersionResolutionOutcome,
    pub version_flagged_error: types::VersionFlaggedError,
    pub quick_build_request: types::QuickBuildRequest,
    pub quick_build_result: types::QuickBuildResult,
    pub fill_remaining_request: types::FillRemainingRequest,
    pub fill_remaining_outcome: types::FillRemainingOutcome,
    pub prep_save_request: types::PrepSaveRequest,
    pub prep_save_outcome: types::PrepSaveOutcome,
}

#[wasm_bindgen]
pub fn __wire_type_exports(value: Ts<WireTypeExports>) -> Ts<WireTypeExports> {
    value
}
