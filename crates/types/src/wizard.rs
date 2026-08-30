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
    /// Every required slot in the step is resolved and legal.
    Complete,
    /// Actionable work remains (the badge case — never blocking).
    Incomplete,
    /// Nothing to do yet: required slots exist but are locked behind
    /// choices made elsewhere ("nothing to do yet" is not "done").
    Waiting,
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
    /// An open-ended list of options; repeats allowed (a shopping list).
    List,
    /// Free text.
    Text { multiline: bool },
}

/// The engine's verdict on one slot — delivered pre-joined so the UI never
/// infers state from weaker signals (decision presence, entry absence).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
#[serde(rename_all = "snake_case")]
pub enum SlotStatus {
    /// Not selectable yet; `locked_reason` explains why.
    Locked,
    /// Open with nothing confirmed.
    Empty,
    /// Confirmed but unfinished (fewer picks than required) — the editor
    /// stays open and confirming again amends.
    Partial,
    /// Resolved and legal.
    Complete,
    /// A confirmed state here breaks a rule (checklist explains).
    Illegal,
}

/// A render-ready gauge attached to a slot — always present, not only on
/// violation ("Spent 5 gp, 8 sp of 15 gp", "2 of 4 chosen").
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
pub struct MeterView {
    pub label: String,
    /// Render-ready current value.
    pub current: String,
    /// Render-ready bound, when one exists.
    pub limit: Option<String>,
    pub state: MeterState,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
#[serde(rename_all = "snake_case")]
pub enum MeterState {
    Ok,
    /// Unfinished (under the required count).
    Short,
    /// Over a hard bound.
    Exceeded,
}

impl MeterView {
    /// Progress toward a minimum (e.g. a curriculum's "at least N"): more
    /// than enough is fine and invisible, so the displayed count clamps at
    /// the target — "3 of 2" is unrepresentable.
    pub fn requirement(label: impl Into<String>, have: usize, need: usize) -> Self {
        MeterView {
            label: label.into(),
            current: have.min(need).to_string(),
            limit: Some(need.to_string()),
            state: if have >= need {
                MeterState::Ok
            } else {
                MeterState::Short
            },
        }
    }

    /// An exact-fill count (e.g. a picker's "choose N"): both directions
    /// are violations, so the true count always shows, with Exceeded past
    /// the target.
    pub fn exact(label: impl Into<String>, have: usize, need: usize) -> Self {
        MeterView {
            label: label.into(),
            current: have.to_string(),
            limit: Some(need.to_string()),
            state: match have.cmp(&need) {
                std::cmp::Ordering::Less => MeterState::Short,
                std::cmp::Ordering::Equal => MeterState::Ok,
                std::cmp::Ordering::Greater => MeterState::Exceeded,
            },
        }
    }

    /// A spend against a cap (e.g. starting wealth): the headline is what
    /// remains (negative once overspent — never clamped), and any
    /// overspend is Exceeded. `render` formats amounts for display.
    pub fn budget(
        label: impl Into<String>,
        spent: i64,
        cap: i64,
        render: impl Fn(i64) -> String,
    ) -> Self {
        MeterView {
            label: label.into(),
            current: render(cap - spent),
            limit: Some(render(cap)),
            state: if spent > cap {
                MeterState::Exceeded
            } else {
                MeterState::Ok
            },
        }
    }
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
    /// The engine's verdict on this slot; the UI renders it, never infers it.
    pub status: SlotStatus,
    /// Always-on gauges (counts, budgets), live under previews.
    pub meters: Vec<MeterView>,
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
    /// Render-ready group heading. Consecutive options sharing a group are
    /// rendered under one labeled header ("School of Battle Magic
    /// curriculum"); `None` options fall in the unlabeled remainder.
    #[serde(default)]
    pub group: Option<String>,
    /// Short render-ready badge shown as a chip next to the name
    /// ("Curriculum"); survives filtering, unlike position or grouping.
    #[serde(default)]
    pub badge: Option<String>,
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

#[cfg(test)]
mod meter_tests {
    use super::*;

    /// A requirement meter never displays past its target — over-
    /// satisfaction is fine and invisible.
    #[test]
    fn requirement_clamps_and_flips_state_at_the_threshold() {
        for (have, need, current, state) in [
            (0, 2, "0", MeterState::Short),
            (1, 2, "1", MeterState::Short),
            (2, 2, "2", MeterState::Ok),
            (3, 2, "2", MeterState::Ok), // the "3 of 2" bug, unrepresentable
            (7, 2, "2", MeterState::Ok),
        ] {
            let m = MeterView::requirement("Curriculum", have, need);
            assert_eq!(
                (m.current.as_str(), m.state),
                (current, state),
                "{have} of {need}"
            );
            assert_eq!(m.limit.as_deref(), Some("2"));
        }
    }

    /// An exact meter shows the true count in both directions and flags
    /// overfill as Exceeded — never clamped.
    #[test]
    fn exact_shows_true_count_and_flags_both_directions() {
        for (have, need, state) in [
            (0, 3, MeterState::Short),
            (3, 3, MeterState::Ok),
            (5, 3, MeterState::Exceeded),
        ] {
            let m = MeterView::exact("Chosen", have, need);
            assert_eq!(m.current, have.to_string());
            assert_eq!(m.state, state, "{have} of {need}");
        }
    }

    /// A budget meter headlines what remains (negative once overspent,
    /// never clamped) and flags overspend as Exceeded.
    #[test]
    fn budget_shows_remaining_and_flags_overspend() {
        let render = |v: i64| format!("{v} cp");
        let ok = MeterView::budget("Remaining", 900, 1500, render);
        assert_eq!((ok.current.as_str(), ok.state), ("600 cp", MeterState::Ok));
        let edge = MeterView::budget("Remaining", 1500, 1500, render);
        assert_eq!(
            (edge.current.as_str(), edge.state),
            ("0 cp", MeterState::Ok)
        );
        let over = MeterView::budget("Remaining", 1700, 1500, render);
        assert_eq!(
            (over.current.as_str(), over.state),
            ("-200 cp", MeterState::Exceeded)
        );
    }
}
