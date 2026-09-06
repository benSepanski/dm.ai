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
    /// Shipped classes, for the random-mint class picker.
    #[serde(default)]
    pub classes: Vec<ClassOption>,
    /// The class the quick-build control would build, when this campaign's
    /// game publishes a suggested build; absent when the rules publish
    /// none (the roster then shows no quick-build control).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub quick_build: Option<ClassOption>,
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
    /// Finalized with a level-up in progress; the finalized sheet stays
    /// authoritative until the level is finalized. Label render-ready,
    /// e.g. "level 2 — step 1 of 1".
    Leveling {
        resume_label: String,
    },
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

/// The campaign as a whole: which game it plays (or that it has not chosen
/// one), the games this build ships to choose from, and every shipped
/// license paragraph — attribution follows the binary, never the open
/// campaign. Fetched first by the UI; the only view that names a system.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
pub struct CampaignView {
    /// The game this campaign plays, when resolved (declared, or inferred
    /// for a pre-declaration directory that holds characters).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub system: Option<String>,
    /// Render-ready name of that game.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub system_name: Option<String>,
    /// True when the game was inferred rather than declared (the app never
    /// writes a declaration into such a campaign).
    pub inferred: bool,
    /// Whether the game may still be chosen or changed: only while the
    /// campaign holds no character.
    pub can_declare: bool,
    /// Why no game could be resolved, naming the fix; absent otherwise.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub problem: Option<String>,
    /// The games this build ships, for the choose-game screen.
    pub games: Vec<GameOption>,
    /// Every shipped ruleset's license paragraphs, in display order.
    pub license_lines: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
pub struct GameOption {
    pub id: String,
    pub name: String,
}

/// Declare (or, while the campaign is empty, change) the campaign's game.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
pub struct DeclareCampaignRequest {
    pub system: String,
}
