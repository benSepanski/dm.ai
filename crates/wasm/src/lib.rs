//! The browser copy of the engine: one serde-tagged request enum in, one
//! response enum out, with tsify-generated TypeScript declarations welded
//! into the wasm-bindgen `.d.ts`. The UI imports only the thin TS façade
//! over this module (`ui/src/engine`).
#![forbid(unsafe_code)]

use std::sync::Arc;

use engine_core::Ruleset;
use tsify::{Ts, Tsify};
use types::{EngineRequest, EngineResponse};
use wasm_bindgen::prelude::*;

/// Every shipped ruleset, the same embedded data the server holds. Adding
/// a game is one arm here (and one in the server) — no registry.
fn ruleset_for(system: &str) -> Option<Arc<dyn Ruleset>> {
    match system {
        "pf2e" => Some(ruleset_pf2e::embedded()),
        "dnd5e" => Some(ruleset_dnd5e::embedded()),
        _ => None,
    }
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
pub fn engine_request(
    system: &str,
    request: Ts<EngineRequest>,
) -> Result<Ts<EngineResponse>, JsError> {
    let request: EngineRequest = request.to_rust()?;
    let response = match ruleset_for(system) {
        Some(rs) => handle(rs.engine(), request),
        None => EngineResponse::Error {
            message: format!("unknown game system '{system}'"),
        },
    };
    Ok(response.into_ts()?)
}

fn handle(engine: &dyn engine_core::EngineOps, request: EngineRequest) -> EngineResponse {
    match request {
        EngineRequest::Project { log } => match engine.project(&log) {
            Ok(projection) => EngineResponse::Projection { projection },
            Err(e) => EngineResponse::Error {
                message: e.to_string(),
            },
        },
        EngineRequest::Preview { log, candidate } => match engine.preview(&log, &candidate) {
            Ok(projection) => EngineResponse::Projection { projection },
            Err(e) => EngineResponse::Error {
                message: e.to_string(),
            },
        },
        EngineRequest::ClearPreview { log, slot } => match engine.clear_preview(&log, &slot) {
            Ok(preview) => EngineResponse::ClearPreview { preview },
            Err(e) => EngineResponse::Error {
                message: e.to_string(),
            },
        },
    }
}

/// The HTTP wire types aren't referenced by the engine boundary, but the UI
/// needs their TypeScript declarations from the same generated `.d.ts`.
/// This carrier keeps them alive through code generation; it is never
/// instantiated.
#[derive(Tsify, serde::Serialize, serde::Deserialize)]
pub struct WireTypeExports {
    pub roster: types::RosterView,
    pub campaign: types::CampaignView,
    pub declare_campaign_request: types::DeclareCampaignRequest,
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
}

#[wasm_bindgen]
pub fn __wire_type_exports(value: Ts<WireTypeExports>) -> Ts<WireTypeExports> {
    value
}
