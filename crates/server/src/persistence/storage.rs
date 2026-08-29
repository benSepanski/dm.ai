//! Storage documents — the shapes serialized to disk. Private to the
//! persistence module: route handlers build responses from view types in
//! `types`, never from these (wire is not storage; enforced by visibility
//! and spot-checked by checks/crate_layering.rs).

use serde::{Deserialize, Serialize};
use types::{Decision, SheetView, StepId};

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
    Ok(CharacterDoc),
    /// JSON parsed but the schema version is newer than this binary knows.
    NewerSchema {
        version: u32,
    },
    /// Unparseable or schema-invalid.
    Corrupt {
        message: String,
    },
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
            ParsedDoc::Ok(doc)
        }
        Ok(doc) => ParsedDoc::Corrupt {
            message: format!("unsupported schema version {}", doc.schema_version),
        },
        Err(e) => ParsedDoc::Corrupt {
            message: format!("schema-invalid: {e}"),
        },
    }
}
