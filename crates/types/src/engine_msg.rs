//! The narrow WASM boundary: one request enum in, one response enum out.
//! The browser engine is stateless — every request carries the full log.

use serde::{Deserialize, Serialize};

use crate::{ClearPreview, Decision, DecisionInput, ProjectionView, SlotId};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
#[serde(tag = "request", rename_all = "snake_case")]
pub enum EngineRequest {
    /// Project the wizard (steps, options, checklist, sheet) from a log.
    Project { log: Vec<Decision> },
    /// Project what the wizard would look like if `candidate` were
    /// confirmed — the live preview while a selection is still tentative.
    Preview {
        log: Vec<Decision>,
        candidate: DecisionInput,
    },
    /// What would changing this confirmed slot clear?
    ClearPreview { log: Vec<Decision>, slot: SlotId },
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
#[serde(tag = "response", rename_all = "snake_case")]
pub enum EngineResponse {
    Projection {
        projection: ProjectionView,
    },
    ClearPreview {
        preview: ClearPreview,
    },
    /// The request could not be processed (malformed log, unknown slot).
    Error {
        message: String,
    },
}
