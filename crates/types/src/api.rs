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

// ---- Quick build (spec req 7) ----

/// A required slot the suggestion planner could not fill, with the reason —
/// the "cannot complete" half of a quick-build/fill response. The same
/// slots also appear on the ordinary checklist.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
pub struct UnresolvedSuggestion {
    pub slot: SlotId,
    pub label: String,
    pub reason: String,
}

/// One-tap quick build: create a draft and fill every required slot from
/// the class's suggested build. `request_id` is client-generated and makes
/// the request idempotent: a retry after a crash between save and ack
/// returns the already-saved draft and appends nothing.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
pub struct QuickBuildRequest {
    pub request_id: String,
    /// Optional working name; seeds the name slot as a player decision (the
    /// planner never overwrites it).
    pub name: Option<String>,
}

/// The quick-build response: a normal draft view (review state, NOT
/// finalized) plus any slots the suggested build could not fill.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
pub struct QuickBuildResult {
    pub draft: DraftView,
    pub unresolved: Vec<UnresolvedSuggestion>,
}

/// Fill only the open required slots of an existing draft with suggestions.
/// Carries the draft version like every wizard write; `request_id` makes the
/// expansion idempotent under retry.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
pub struct FillRemainingRequest {
    pub request_id: String,
    pub version: u64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
#[serde(tag = "outcome", rename_all = "snake_case")]
pub enum FillRemainingOutcome {
    /// The legal prefix was appended and saved (possibly nothing, when
    /// every slot was already confirmed); `unresolved` names what remains.
    Filled {
        draft: DraftView,
        unresolved: Vec<UnresolvedSuggestion>,
    },
    /// The submitted version is stale — reload from `current`.
    Conflict { current: DraftView },
}

// ---- Random mint & clone (roster-ergonomics spec reqs 1-5) ----

/// One-tap random character: create a draft and fill every required slot
/// with random legal picks (never the published suggested build).
/// `request_id` is client-generated and doubles as the entropy source —
/// the same request always mints the same character, so a retry after a
/// crash returns the already-saved draft and appends nothing.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
pub struct RandomMintRequest {
    pub request_id: String,
    /// Class record ID to mint, or `None` for "any" (sampled uniformly
    /// over shipped classes). A chosen class is recorded as a player
    /// decision; a sampled one as a random decision.
    pub class_id: Option<String>,
    /// Optional player-typed name; recorded as a player decision and
    /// never overwritten by the generator.
    pub name: Option<String>,
}

/// The clone request: duplicate `source_id` as a new character whose only
/// log difference is the name decision (clone provenance, this `name`).
/// `request_id` follows the quick-build idempotency scheme; a retried
/// request returns the already-created character and ignores a changed
/// `name` (first write wins).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
pub struct CloneRequest {
    pub request_id: String,
    pub source_id: CharacterId,
    pub name: String,
}

/// A successful clone: the new character's roster identity. The client
/// refreshes the roster or opens the character by ID.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
pub struct CloneResult {
    pub id: CharacterId,
    pub name: String,
    /// True when the clone is finalized (source was finalized).
    pub finalized: bool,
}
