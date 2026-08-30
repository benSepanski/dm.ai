//! The decision log: every confirmed choice, with provenance.

use serde::{Deserialize, Serialize};

use crate::{DecisionId, OptionId, SlotId};

/// What was chosen in a slot.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
#[serde(tag = "kind", content = "value", rename_all = "snake_case")]
pub enum Selection {
    /// One option from the slot's catalog.
    Option(OptionId),
    /// Several options from the catalog; order is the player's pick order.
    Options(Vec<OptionId>),
    /// Free text (name, appearance, backstory).
    Text(String),
}

/// Who (or what) made a decision. DM exceptions and auto-mode arrive in
/// later epochs as new variants.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
#[serde(rename_all = "snake_case")]
pub enum DecisionSource {
    Player,
    /// Filled in by the quick-build planner from the class's suggested
    /// build. Inert for derivation; editing the slot later records the
    /// player as the new source. (Storage schema v2.)
    Suggested,
    /// Sampled by the random-mint planner from the slot's legal options.
    /// Inert for derivation, like `Suggested`. (Storage schema v3.)
    Random,
    /// The re-minted name decision of a cloned character — the one
    /// decision a clone does not share verbatim with its source.
    /// (Storage schema v3.)
    Clone,
}

/// A confirmed choice as recorded in the log.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
pub struct Decision {
    pub id: DecisionId,
    pub slot: SlotId,
    pub selection: Selection,
    pub source: DecisionSource,
    /// Position in the log when confirmed. Redundant with log order by
    /// construction; stored so a hand-inspected file reads chronologically.
    pub order: u32,
}

/// A not-yet-ordered decision as submitted by a client.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
pub struct DecisionInput {
    pub id: DecisionId,
    pub slot: SlotId,
    pub selection: Selection,
    pub source: DecisionSource,
}

impl DecisionInput {
    pub fn into_decision(self, order: u32) -> Decision {
        Decision {
            id: self.id,
            slot: self.slot,
            selection: self.selection,
            source: self.source,
            order,
        }
    }
}
