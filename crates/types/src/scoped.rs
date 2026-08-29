//! Scoped choices: selections bound to slots outside the permanent decision
//! log — replaceable wholesale, validated against the folded build state,
//! never replayed. The preparation section is the first scope; Epoch 8's
//! daily flows reuse these shapes.

use serde::{Deserialize, Serialize};

use crate::{ChecklistEntry, Selection, SlotId, SlotView};

/// One pick in a scoped section. No decision ID and no order: the section
/// is replaced as a whole, so idempotency and history live at the save
/// layer, not per choice.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
pub struct ScopedChoice {
    pub slot: SlotId,
    pub selection: Selection,
}

/// The engine's verdict on a scoped choice set: the scoped slots rendered
/// exactly like wizard slots, plus the checklist entries the set produces.
/// Total by design — a hand-edited section (unknown slot, malformed pick,
/// choices on a class with no such slots) comes back as Illegal entries,
/// never as an error that blocks loading.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
pub struct ScopedProjection {
    pub slots: Vec<SlotView>,
    pub checklist: Vec<ChecklistEntry>,
}
