//! HTTP wire types. Every response the server sends is one of these view
//! types — never a storage document (wire is not storage).

use serde::{Deserialize, Serialize};

use crate::{
    CharacterId, ChecklistEntry, ClearPreview, DecisionInput, ProjectionView, SheetView, SlotId,
    StepId, VersionStatus,
};

/// A draft mid-wizard, as the server owns it.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
pub struct DraftView {
    pub id: CharacterId,
    /// Bumps on every accepted mutation; confirms carry the version they
    /// were made against and stale ones are rejected.
    pub version: u64,
    /// Server-side step cursor: where resume lands.
    pub current_step: StepId,
    pub projection: ProjectionView,
    /// The rules-data version this draft is built against.
    pub rules_version: String,
    /// Where that pin stands against the shipped data (always `Current`
    /// here: a draft with an unresolved older pin arrives as
    /// `CharacterView::FlaggedDraft` instead, never with a projection).
    pub version_status: VersionStatus,
}

/// A single character as fetched by ID.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
#[serde(tag = "state", rename_all = "snake_case")]
pub enum CharacterView {
    Draft(DraftView),
    Finalized {
        id: CharacterId,
        sheet: SheetView,
        /// Version flag for the sheet view; resolution actions hang off it.
        version_status: VersionStatus,
        /// Carried so resolution requests can pass the write version.
        version: u64,
    },
    /// A draft whose pin is not current and unresolved: the wizard is
    /// blocked behind resolution, and no projection is computed (that would
    /// replay the old log against new data outside the resolution flow).
    /// The stored sheet is shown read-only beside the flag.
    FlaggedDraft {
        id: CharacterId,
        name: String,
        sheet: SheetView,
        /// Draft version, for the resolution request.
        version: u64,
        status: VersionStatus,
    },
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
pub struct CreateCharacterRequest {
    /// Optional working name; the details step confirms the real one.
    pub name: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
pub struct ConfirmRequest {
    pub decision: DecisionInput,
    /// The draft version this confirm was made against.
    pub version: u64,
}

/// Outcome of a confirm. `Conflict` carries the current draft so a stale
/// tab can reload; `Rejected` is the server refusing an illegal confirm.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
#[serde(tag = "outcome", rename_all = "snake_case")]
pub enum ConfirmOutcome {
    /// Saved durably (or already present under the same decision ID).
    Confirmed { draft: DraftView },
    /// The submitted version is stale — reload from `current`.
    Conflict { current: DraftView },
    /// The decision is illegal or malformed; nothing was appended.
    Rejected {
        reasons: Vec<ChecklistEntry>,
        draft: DraftView,
    },
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
pub struct ClearRequest {
    pub slot: SlotId,
    pub version: u64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
#[serde(tag = "outcome", rename_all = "snake_case")]
pub enum ClearOutcome {
    Cleared {
        draft: DraftView,
        preview: ClearPreview,
    },
    Conflict {
        current: DraftView,
    },
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
pub struct StepRequest {
    pub step: StepId,
    pub version: u64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
pub struct FinalizeRequest {
    pub version: u64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
#[serde(tag = "outcome", rename_all = "snake_case")]
pub enum FinalizeOutcome {
    Finalized {
        sheet: SheetView,
    },
    /// The checklist is non-empty; every gap is listed.
    Blocked {
        reasons: Vec<ChecklistEntry>,
    },
    Conflict {
        /// Boxed: `DraftView` dwarfs the other variants (clippy
        /// large_enum_variant); serde/tsify treat the box as transparent.
        current: Box<DraftView>,
    },
}

/// Uniform error body for everything that is not a typed outcome.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
pub struct ApiError {
    pub message: String,
}
