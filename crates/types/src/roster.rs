//! The character roster and its problem reports.

use serde::{Deserialize, Serialize};

use crate::{CharacterId, VersionStatus};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
pub struct RosterView {
    pub entries: Vec<RosterEntry>,
    /// Files that could not be loaded (quarantined or unreadable) — always
    /// reported, never blocking the rest of the roster.
    pub problems: Vec<RosterProblem>,
    /// The ORC attribution notice, displayed in the app.
    pub license_notice: String,
    /// Shipped classes, for the random-mint class picker.
    #[serde(default)]
    pub classes: Vec<ClassOption>,
}

/// One shipped class, as the random-mint picker offers it.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
pub struct ClassOption {
    /// The class record ID (a class-slot option ID).
    pub id: String,
    pub name: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
#[serde(tag = "state", rename_all = "snake_case")]
pub enum RosterCharacterState {
    /// Mid-wizard; the label is render-ready, e.g. "step 4 of 7 — Class".
    Draft {
        resume_label: String,
    },
    Finalized,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
pub struct RosterEntry {
    pub id: CharacterId,
    pub name: String,
    /// Identity line, e.g. "Dwarf Fighter 1".
    pub summary: String,
    pub state: RosterCharacterState,
    /// Rules-data version flag — computed at load, never written by it.
    pub version: VersionStatus,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
pub struct RosterProblem {
    /// The affected file name (not a full path).
    pub file: String,
    /// What happened, e.g. "could not be read — quarantined".
    pub message: String,
}
