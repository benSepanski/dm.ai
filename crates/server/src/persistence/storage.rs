//! Storage documents — the shapes serialized to disk. Private to the
//! persistence module: route handlers build responses from view types in
//! `types`, never from these (wire is not storage; enforced by visibility
//! and spot-checked by checks/crate_layering.rs).

use serde::{Deserialize, Serialize};
use types::{Decision, SheetDiff, SheetView, StepId};

/// Current schema, stamped on every write. v2 = v1 plus the `suggested`
/// decision source (quick build); structurally identical otherwise.
pub(crate) const SCHEMA_VERSION: u32 = 2;
/// Oldest schema this binary still reads. v1 files are accepted on load,
/// never rewritten by loading, and upgraded on their next ordinary write.
pub(crate) const MIN_SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub(crate) struct CharacterDoc {
    /// Always first field so a human reading the file sees it immediately.
    pub(crate) schema_version: u32,
    pub(crate) id: String,
    /// The rules-data version the decision log was built against.
    pub(crate) rules_version: String,
    pub(crate) state: DocState,
    /// Server-side wizard cursor (resume lands here).
    pub(crate) current_step: StepId,
    /// Bumps on every accepted mutation; stale confirms are rejected.
    pub(crate) draft_version: u64,
    /// The materialized sheet — the load path. `verify` replays the log
    /// and reports divergence, but never rewrites this.
    pub(crate) sheet: SheetView,
    /// The ordered decision log — the source of truth under replay.
    pub(crate) log: Vec<Decision>,
    /// Explicit version-resolution actions, oldest first. Written only by
    /// the version routes (re-pin / accept / keep-old / resolve-errors) —
    /// never by loading. Absent entirely on files that never resolved.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub(crate) version_history: Vec<VersionEvent>,
    /// Standing keep-old decision: the character stays on its stored
    /// derivation, un-flagged, until the shipped data version differs from
    /// `evaluated_against` again. Cleared by a later re-pin or accept.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub(crate) keep_old: Option<KeepOldMarker>,
}

/// One recorded version-resolution action.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub(crate) struct VersionEvent {
    /// "re_pin" | "accept" | "keep_old" | "resolve_replay_error".
    pub(crate) action: String,
    /// The rules-data version the file pinned before the action.
    pub(crate) from: String,
    /// The version it pins after (for keep-old: unchanged, equals `from`).
    pub(crate) to: String,
    pub(crate) at_millis: u64,
    /// Human-readable note, e.g. "identical replay".
    pub(crate) note: String,
    /// For accept: every sheet value the action superseded, old → new —
    /// nothing the table saw is lost.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub(crate) superseded_values: Vec<SheetDiff>,
    /// For resolve-replay-error on a draft: the decisions the cascade
    /// cleared (slot and selection preserved verbatim).
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub(crate) cleared_decisions: Vec<Decision>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub(crate) struct KeepOldMarker {
    /// The old version the character stays pinned to.
    pub(crate) pinned: String,
    /// The shipped version the decision was evaluated against; when the
    /// shipped version moves past this, the flag returns.
    pub(crate) evaluated_against: String,
    pub(crate) at_millis: u64,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub(crate) enum DocState {
    Draft,
    Finalized,
}

/// Parse outcome for one file on disk.
#[derive(Debug)]
pub(crate) enum ParsedDoc {
    /// Boxed: the doc dwarfs the other variants (clippy large_enum_variant).
    Ok(Box<CharacterDoc>),
    /// JSON parsed but the schema version is newer than this binary knows.
    NewerSchema { version: u32 },
    /// Unparseable or schema-invalid.
    Corrupt { message: String },
}

pub(crate) fn parse_doc(text: &str) -> ParsedDoc {
    // Peek the version first so a newer-schema file is distinguishable
    // from corruption.
    let value: serde_json::Value = match serde_json::from_str(text) {
        Ok(v) => v,
        Err(e) => {
            return ParsedDoc::Corrupt {
                message: format!("not valid JSON: {e}"),
            }
        }
    };
    let version = value
        .get("schema_version")
        .and_then(|v| v.as_u64())
        .unwrap_or(0) as u32;
    if version > SCHEMA_VERSION {
        return ParsedDoc::NewerSchema { version };
    }
    match serde_json::from_value::<CharacterDoc>(value) {
        Ok(doc) if (MIN_SCHEMA_VERSION..=SCHEMA_VERSION).contains(&doc.schema_version) => {
            ParsedDoc::Ok(Box::new(doc))
        }
        Ok(doc) => ParsedDoc::Corrupt {
            message: format!("unsupported schema version {}", doc.schema_version),
        },
        Err(e) => ParsedDoc::Corrupt {
            message: format!("schema-invalid: {e}"),
        },
    }
}
