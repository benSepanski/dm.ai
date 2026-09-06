//! Rules-data version status — computed at load, never stored. A character
//! or draft pins the rules-data version its log was built against; when the
//! shipped data moves on, the server replays the log against current data
//! and reports the outcome here. Resolution (re-pin / accept / keep-old) is
//! always an explicit route, never a side effect of loading.

use serde::{Deserialize, Serialize};

use crate::{ClearedDecision, DecisionId, SlotId};

/// Where a character's pinned rules-data version stands relative to the
/// version this build ships. Computed fresh on every load.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
#[serde(tag = "status", rename_all = "snake_case")]
pub enum VersionStatus {
    /// The pin equals the shipped manifest version — nothing to resolve.
    Current,
    /// The pin is an older version this build knows (listed in the
    /// manifest's supersedes chain with a recorded ID set), so the log was
    /// replayed against current data; `outcome` says how that went.
    OlderKnown {
        pinned: String,
        current: String,
        outcome: ReplayOutcome,
    },
    /// Ben chose to keep the old derivation, recorded in the file. Not
    /// re-flagged until the shipped data version changes again.
    KeptOld {
        pinned: String,
        /// The shipped version the keep-old decision was evaluated against.
        evaluated_against: String,
    },
    /// The pin is no version this build knows — replay impossible; the
    /// materialized sheet still loads read-only.
    Unknown { pinned: String, current: String },
}

/// The result of replaying an older-known character's log against current
/// rules data.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum ReplayOutcome {
    /// The replayed sheet equals the stored sheet — eligible for a quiet
    /// re-pin (still only via the explicit route).
    Identical,
    /// The replayed sheet differs; every differing value listed old → new.
    /// The stored sheet is untouched until an explicit accept.
    Divergent { differences: Vec<SheetDiff> },
    /// The log no longer replays — a decision is invalid under current
    /// data. Accept is unavailable; the failing decision is named.
    ReplayError {
        message: String,
        failing_decision: DecisionId,
        slot: SlotId,
        /// For drafts: what resolving would clear and reopen (the failing
        /// decision and everything the cascade takes with it). Empty for
        /// finalized characters.
        #[serde(default)]
        would_reopen: Vec<ClearedDecision>,
    },
}

/// One sheet value that would change under current data, old → new.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
pub struct SheetDiff {
    pub section: String,
    pub label: String,
    /// The stored value ("(absent)" when the entry did not exist).
    pub old: String,
    /// The value current data derives ("(absent)" when it no longer exists).
    pub new: String,
    /// Render-ready explanation of the new value — the sheet entry's own
    /// detail line ("7 expert + 2 Con"), when the sheet carries one. So a
    /// reader of a diff (a level-up's gains, a version review) sees why a
    /// number moved, not only that it did.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub why: Option<String>,
}

/// Request body for the version-resolution routes (re-pin / accept /
/// keep-old / resolve-errors). Carries the draft version like every write.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
pub struct VersionActionRequest {
    pub version: u64,
}

/// Outcome of a version-resolution route.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
#[serde(tag = "outcome", rename_all = "snake_case")]
pub enum VersionResolutionOutcome {
    /// The file was rewritten once (temp-file → fsync → rename); the fresh
    /// view reflects the new pin.
    Resolved {
        character: Box<crate::CharacterView>,
    },
    /// The submitted version is stale — reload from `character`.
    Conflict {
        character: Box<crate::CharacterView>,
    },
    /// Typed refusal: the action does not apply to the character's current
    /// status (e.g. accept on a replay-error names the failing decision).
    /// Nothing was written.
    Refused {
        message: String,
        status: VersionStatus,
    },
}

/// 409 body when a wizard write is refused because the draft pins a
/// rules-data version that is not current and unresolved.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
pub struct VersionFlaggedError {
    pub message: String,
    pub status: VersionStatus,
}
