//! The live validation checklist: every entry names its rule, distinguishes
//! incomplete from illegal, and points at the slot to fix.

use serde::{Deserialize, Serialize};

use crate::{SlotId, StepId};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
#[serde(rename_all = "snake_case")]
pub enum ChecklistSeverity {
    /// Something is still to do ("1 skill choice left").
    Incomplete,
    /// A confirmed state breaks a rule; finalize is impossible until fixed.
    Illegal,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
pub struct ChecklistEntry {
    pub severity: ChecklistSeverity,
    /// The offending slot; clicking the entry jumps here.
    pub slot: SlotId,
    /// The step that slot lives in.
    pub step: StepId,
    /// The rule's name, e.g. "Attribute boosts".
    pub rule: String,
    /// Human explanation, e.g. "boosts in this group must go to different
    /// attributes".
    pub message: String,
    /// Where the obligation came from, e.g. "from Background: Field Medic".
    pub source: String,
}
