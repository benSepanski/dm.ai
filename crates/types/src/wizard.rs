//! The wizard as the engine projects it: steps built from slot metadata,
//! options with availability and explanations, and the dependent-clear
//! preview. The UI renders these; it never derives them.

use serde::{Deserialize, Serialize};

use crate::{ChecklistEntry, Decision, OptionId, Selection, SheetView, SlotId, StepId};

/// Everything the engine can say about a draft from its log alone.
/// The server wraps this with persistence metadata (id, version, cursor).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
pub struct ProjectionView {
    pub steps: Vec<StepView>,
    pub checklist: Vec<ChecklistEntry>,
    pub sheet: SheetView,
    /// True iff the checklist is empty — nothing incomplete, nothing illegal.
    pub can_finalize: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
#[serde(rename_all = "snake_case")]
pub enum StepStatus {
    /// Every slot in the step is resolved and legal.
    Complete,
    /// Unresolved slots remain (the badge case — never blocking).
    Incomplete,
    /// A confirmed choice in this step is illegal.
    Illegal,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
pub struct StepView {
    pub id: StepId,
    pub title: String,
    pub status: StepStatus,
    pub slots: Vec<SlotView>,
}

/// How a slot collects its selection. Presentation-mechanical only — the
/// meaning of the options is the ruleset's business.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum SlotViewKind {
    /// Pick exactly one option.
    Single,
    /// Pick `count` distinct options.
    Multi { count: u32 },
    /// Free text.
    Text { multiline: bool },
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
pub struct SlotView {
    pub id: SlotId,
    pub label: String,
    pub kind: SlotViewKind,
    /// Free-form rendering hint (e.g. `attribute-boosts`); the UI may use it
    /// to pick a nicer widget, never to compute values.
    pub presentation_hint: Option<String>,
    /// Present when the slot is currently locked (e.g. heritage before an
    /// ancestry exists), with the reason to show.
    pub locked_reason: Option<String>,
    /// Whether resolving this slot is required to finalize.
    pub required: bool,
    /// The confirmed decision currently occupying this slot, if any.
    pub decision: Option<Decision>,
    /// The catalog as of the current log (empty for text slots).
    pub options: Vec<OptionView>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
pub struct OptionView {
    pub id: OptionId,
    pub label: String,
    /// One-line render-ready summary ("Hit Points 10 · Speed 20 feet · …").
    pub summary: String,
    /// Render-ready detail bullets.
    pub details: Vec<String>,
    /// False when a prerequisite fails; the option shows greyed out.
    pub available: bool,
    /// Why it is unavailable, e.g. "requires a spellcasting class feature".
    pub unavailable_reason: Option<String>,
}

/// What changing (or clearing) a confirmed slot would take with it.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
pub struct ClearPreview {
    /// The slot being changed.
    pub slot: SlotId,
    /// Dependent decisions that would be cleared, in log order — shown
    /// verbatim in the confirmation prompt.
    pub cleared: Vec<ClearedDecision>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
pub struct ClearedDecision {
    pub slot: SlotId,
    pub slot_label: String,
    /// Render-ready description of what was chosen there.
    pub selection_label: String,
    pub selection: Selection,
}
