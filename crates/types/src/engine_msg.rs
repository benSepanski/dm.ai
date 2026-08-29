//! The narrow WASM boundary: one request enum in, one response enum out.
//! The browser engine is stateless — every request carries the full log.

use serde::{Deserialize, Serialize};

use crate::{ClearPreview, Decision, DecisionInput, ProjectionView, ScopedChoice, SlotId};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
#[serde(tag = "request", rename_all = "snake_case")]
pub enum EngineRequest {
    /// Project the wizard (steps, options, checklist, sheet) from a log,
    /// with any scoped preparation choices folded into the view.
    Project {
        log: Vec<Decision>,
        #[serde(default)]
        prep: Vec<ScopedChoice>,
    },
    /// Project what the wizard would look like if `candidate` were
    /// confirmed — the live preview while a selection is still tentative.
    Preview {
        log: Vec<Decision>,
        candidate: DecisionInput,
        #[serde(default)]
        prep: Vec<ScopedChoice>,
    },
    /// Project with a tentative scoped choice set replacing the current
    /// one — the prep picker's live preview.
    PreviewPrep {
        log: Vec<Decision>,
        prep: Vec<ScopedChoice>,
    },
    /// What would changing this confirmed slot clear? Scoped choices ride
    /// along so dependents across the scope boundary appear in the preview.
    ClearPreview {
        log: Vec<Decision>,
        slot: SlotId,
        #[serde(default)]
        prep: Vec<ScopedChoice>,
    },
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
