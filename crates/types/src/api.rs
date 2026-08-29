//! HTTP wire types. Every response the server sends is one of these view
//! types — never a storage document (wire is not storage).

use serde::{Deserialize, Serialize};

use crate::{
    CharacterId, ChecklistEntry, ClearPreview, DecisionInput, ProjectionView, ScopedChoice,
    ScopedProjection, SheetView, SlotId, StepId, VersionStatus,
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
        /// The display sheet: the materialized build sheet plus any scoped
        /// sections (prepared spells) the projection layer appends. The
        /// stored sheet on disk never contains the scoped sections.
        sheet: SheetView,
        /// Version flag for the sheet view; resolution actions hang off it.
        version_status: VersionStatus,
        /// Carried so resolution requests can pass the write version.
        version: u64,
        /// The scoped preparation section, rendered for the sheet view's
        /// "change prepared spells" editor. `None` when the character's
        /// class has no scoped slots (no affordance is shown), or when the
        /// stored section could not be parsed (see `prep_broken`).
        #[serde(default, skip_serializing_if = "Option::is_none")]
        prep: Option<ScopedProjection>,
        /// True when the stored preparation section is structurally
        /// unparseable: the character still loads, the sheet renders, and
        /// the editor offers wholesale replacement.
        #[serde(default)]
        prep_broken: bool,
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

// ---- Scoped preparation saves (chargen-wizard) ----

/// The lifecycle state a scoped save expects to act on. A stale UI holding
/// the wrong lifecycle (a draft tab after finalize, or vice versa) is
/// rejected with the current state, never coerced.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
#[serde(rename_all = "snake_case")]
pub enum LifecycleState {
    Draft,
    Finalized,
}

/// Replace a character's scoped preparation section wholesale. Carries the
/// character's write version like every mutation; `request_id` makes the
/// save idempotent under retry (a crash between save and ack returns the
/// saved result and changes nothing).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
pub struct PrepSaveRequest {
    pub request_id: String,
    pub version: u64,
    pub expected_state: LifecycleState,
    pub choices: Vec<ScopedChoice>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
#[serde(tag = "outcome", rename_all = "snake_case")]
pub enum PrepSaveOutcome {
    /// Saved durably (or already saved under the same request ID).
    Saved { character: Box<CharacterView> },
    /// Stale version or lifecycle mismatch — reload from `character`.
    Conflict { character: Box<CharacterView> },
    /// The choice set is illegal; nothing was written.
    Rejected {
        reasons: Vec<ChecklistEntry>,
        character: Box<CharacterView>,
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
