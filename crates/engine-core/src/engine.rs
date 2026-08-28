//! The engine: five operations over a ruleset's slot registrations —
//! slot-graph resolution, log append/replay, validation into the checklist,
//! the fold traversal, and the draft lifecycle.

use std::collections::BTreeSet;

use types::{
    ChecklistEntry, ChecklistSeverity, ClearPreview, ClearedDecision, Decision, DecisionInput,
    MeterState, MeterView, ProjectionView, Selection, SheetView, SlotId, SlotStatus, SlotView,
    SlotViewKind, StepId, StepStatus, StepView,
};

use crate::{Availability, SlotRegistration};

/// A ruleset assembled into a runnable engine. `S` is the ruleset's folded
/// state; the engine orchestrates, the registrations know the game.
pub struct Engine<S> {
    steps: Vec<(StepId, String)>,
    slots: Vec<SlotRegistration<S>>,
    new_state: Box<dyn Fn() -> S + Send + Sync>,
    sheet: Box<dyn Fn(&S) -> SheetView + Send + Sync>,
}

/// Replay of a log failed at a specific decision.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum EngineError {
    #[error("decision {index} targets unknown slot '{slot}'")]
    UnknownSlot { index: usize, slot: SlotId },
    #[error("decision {index} on slot '{slot}' is invalid: {message}")]
    InvalidDecision {
        index: usize,
        slot: SlotId,
        message: String,
    },
    #[error("slot '{slot}' has no confirmed decision to clear")]
    NothingToClear { slot: SlotId },
}

/// Outcome of appending one decision to a draft log.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AppendOutcome {
    /// The log grew by one decision.
    Appended(Vec<Decision>),
    /// The decision ID was already present — the log is unchanged and this
    /// is success (an idempotent retry), not an error.
    AlreadyPresent,
}

impl<S> Engine<S> {
    /// Assemble an engine. Panics on duplicate slot IDs, an unknown step in
    /// a slot, or an unknown slot in a dependents list — these are ruleset
    /// authoring bugs, caught by the ruleset's own construction test.
    pub fn new(
        steps: Vec<(StepId, String)>,
        slots: Vec<SlotRegistration<S>>,
        new_state: Box<dyn Fn() -> S + Send + Sync>,
        sheet: Box<dyn Fn(&S) -> SheetView + Send + Sync>,
    ) -> Self {
        let mut seen = BTreeSet::new();
        for slot in &slots {
            assert!(
                seen.insert(slot.id.clone()),
                "duplicate slot registration: {}",
                slot.id
            );
            assert!(
                steps.iter().any(|(id, _)| *id == slot.step),
                "slot {} names unknown step {}",
                slot.id,
                slot.step
            );
        }
        for slot in &slots {
            for dep in &slot.dependents {
                assert!(
                    seen.contains(dep),
                    "slot {} lists unknown dependent {}",
                    slot.id,
                    dep
                );
            }
        }
        Self {
            steps,
            slots,
            new_state,
            sheet,
        }
    }

    fn registration(&self, slot: &SlotId) -> Option<&SlotRegistration<S>> {
        self.slots.iter().find(|s| s.id == *slot)
    }

    /// The fold: replay a log into ruleset state. Pure — same log, same
    /// registrations, same state, every time.
    pub fn fold(&self, log: &[Decision]) -> Result<S, EngineError> {
        let mut state = (self.new_state)();
        for (index, decision) in log.iter().enumerate() {
            let reg =
                self.registration(&decision.slot)
                    .ok_or_else(|| EngineError::UnknownSlot {
                        index,
                        slot: decision.slot.clone(),
                    })?;
            (reg.apply)(&mut state, decision).map_err(|e| EngineError::InvalidDecision {
                index,
                slot: decision.slot.clone(),
                message: e.message,
            })?;
        }
        Ok(state)
    }

    /// Derive the sheet for a log (the materialized-sheet source of truth).
    pub fn sheet(&self, log: &[Decision]) -> Result<SheetView, EngineError> {
        Ok((self.sheet)(&self.fold(log)?))
    }

    /// Project the full wizard view from a log.
    pub fn project(&self, log: &[Decision]) -> Result<ProjectionView, EngineError> {
        let state = self.fold(log)?;
        let mut checklist: Vec<ChecklistEntry> = Vec::new();
        let mut slot_views: Vec<(StepId, SlotView)> = Vec::new();

        for reg in &self.slots {
            let availability = (reg.unlock)(&state);
            if availability == Availability::Hidden {
                continue;
            }
            let decision = log.iter().rev().find(|d| d.slot == reg.id);
            let entries = (reg.validate)(&state, decision);

            let locked_reason = match &availability {
                Availability::Locked { reason } => Some(reason.clone()),
                _ => None,
            };
            // The engine's verdict, delivered pre-joined: the UI renders
            // status, it never re-derives it from decisions or entries.
            let status = if locked_reason.is_some() {
                SlotStatus::Locked
            } else if entries
                .iter()
                .any(|e| e.severity == ChecklistSeverity::Illegal)
            {
                SlotStatus::Illegal
            } else if decision.is_none() {
                SlotStatus::Empty
            } else if entries
                .iter()
                .any(|e| e.severity == ChecklistSeverity::Incomplete)
            {
                SlotStatus::Partial
            } else {
                SlotStatus::Complete
            };
            checklist.extend(entries);

            let kind = (reg.kind)(&state);
            let mut meters = Vec::new();
            // Auto count meter for every open Multi slot — the engine knows
            // both numbers, so no ruleset should hand-roll these.
            if locked_reason.is_none() {
                if let SlotViewKind::Multi { count } = kind {
                    let picked = match decision.map(|d| &d.selection) {
                        Some(Selection::Options(ids)) => ids.len(),
                        Some(_) => 1,
                        None => 0,
                    };
                    meters.push(MeterView {
                        label: "Chosen".to_string(),
                        current: picked.to_string(),
                        limit: Some(count.to_string()),
                        state: match (picked as u64).cmp(&u64::from(count)) {
                            std::cmp::Ordering::Less => MeterState::Short,
                            std::cmp::Ordering::Equal => MeterState::Ok,
                            std::cmp::Ordering::Greater => MeterState::Exceeded,
                        },
                    });
                }
                meters.extend((reg.meters)(&state, decision));
            }

            let options = if locked_reason.is_none() {
                (reg.options)(&state)
            } else {
                Vec::new()
            };
            slot_views.push((
                reg.step.clone(),
                SlotView {
                    id: reg.id.clone(),
                    label: reg.label.clone(),
                    kind,
                    presentation_hint: reg.presentation_hint.clone(),
                    locked_reason,
                    required: reg.required,
                    status,
                    meters,
                    decision: decision.cloned(),
                    options,
                },
            ));
        }

        let steps = self
            .steps
            .iter()
            .map(|(id, title)| {
                let slots: Vec<SlotView> = slot_views
                    .iter()
                    .filter(|(step, _)| step == id)
                    .map(|(_, v)| v.clone())
                    .collect();
                // A pure fold over slot statuses: any Illegal wins; any
                // required actionable gap shows Incomplete; required slots
                // that exist but are locked mean Waiting — "nothing to do
                // yet" is not "done".
                let status = if slots.iter().any(|s| s.status == SlotStatus::Illegal) {
                    StepStatus::Illegal
                } else if slots.iter().any(|s| {
                    s.required && matches!(s.status, SlotStatus::Empty | SlotStatus::Partial)
                }) {
                    StepStatus::Incomplete
                } else if slots
                    .iter()
                    .any(|s| s.required && s.status == SlotStatus::Locked)
                {
                    StepStatus::Waiting
                } else {
                    StepStatus::Complete
                };
                StepView {
                    id: id.clone(),
                    title: title.clone(),
                    status,
                    slots,
                }
            })
            .collect();

        let sheet = (self.sheet)(&state);
        let can_finalize = checklist.is_empty();
        Ok(ProjectionView {
            steps,
            checklist,
            sheet,
            can_finalize,
        })
    }

    /// Project the wizard as if `candidate` were confirmed — replacing any
    /// existing decision in its slot. The live-preview path; nothing is
    /// recorded.
    pub fn preview(
        &self,
        log: &[Decision],
        candidate: &DecisionInput,
    ) -> Result<ProjectionView, EngineError> {
        let mut hypothetical: Vec<Decision> = log
            .iter()
            .filter(|d| d.slot != candidate.slot)
            .cloned()
            .collect();
        let order = hypothetical.len() as u32;
        hypothetical.push(candidate.clone().into_decision(order));
        self.project(&hypothetical)
    }

    /// Append a decision to a draft log — the confirm path. Validates
    /// structurally (fold must accept it); duplicate decision IDs are
    /// idempotent successes; a slot with an existing decision rejects (the
    /// client clears first, so "change" is always clear-then-confirm).
    pub fn append(
        &self,
        log: &[Decision],
        input: DecisionInput,
    ) -> Result<AppendOutcome, EngineError> {
        if log.iter().any(|d| d.id == input.id) {
            return Ok(AppendOutcome::AlreadyPresent);
        }
        if let Some(existing) = log.iter().find(|d| d.slot == input.slot) {
            return Err(EngineError::InvalidDecision {
                index: log.len(),
                slot: input.slot.clone(),
                message: format!(
                    "slot already holds decision {} — clear it before confirming a new choice",
                    existing.id
                ),
            });
        }
        let reg = self
            .registration(&input.slot)
            .ok_or_else(|| EngineError::UnknownSlot {
                index: log.len(),
                slot: input.slot.clone(),
            })?;
        // The slot must be open under the current state.
        let state = self.fold(log)?;
        match (reg.unlock)(&state) {
            Availability::Open => {}
            Availability::Locked { reason } => {
                return Err(EngineError::InvalidDecision {
                    index: log.len(),
                    slot: input.slot.clone(),
                    message: format!("slot is locked: {reason}"),
                });
            }
            Availability::Hidden => {
                return Err(EngineError::InvalidDecision {
                    index: log.len(),
                    slot: input.slot.clone(),
                    message: "slot does not exist under the current state".into(),
                });
            }
        }
        let mut new_log = log.to_vec();
        let order = new_log.len() as u32;
        new_log.push(input.into_decision(order));
        // Structural validation is the fold accepting the new log.
        self.fold(&new_log)?;
        Ok(AppendOutcome::Appended(new_log))
    }

    /// Replace a slot's decision atomically: cascade-clear the old decision
    /// (same dependents rule as `clear`), then append the new one — a single
    /// engine step, one durable write at the persistence layer. Idempotent
    /// under decision-ID replay; on an unoccupied slot it behaves as append.
    pub fn amend(
        &self,
        log: &[Decision],
        input: DecisionInput,
    ) -> Result<AppendOutcome, EngineError> {
        if log.iter().any(|d| d.id == input.id) {
            return Ok(AppendOutcome::AlreadyPresent);
        }
        let base = if log.iter().any(|d| d.slot == input.slot) {
            self.clear(log, &input.slot)?
        } else {
            log.to_vec()
        };
        self.append(&base, input)
    }

    /// What clearing `slot` would take with it (the confirmation prompt).
    pub fn clear_preview(
        &self,
        log: &[Decision],
        slot: &SlotId,
    ) -> Result<ClearPreview, EngineError> {
        if !log.iter().any(|d| d.slot == *slot) {
            return Err(EngineError::NothingToClear { slot: slot.clone() });
        }
        let doomed = self.transitive_dependents(slot);
        let cleared = log
            .iter()
            .filter(|d| doomed.contains(&d.slot))
            .map(|d| {
                let reg = self
                    .registration(&d.slot)
                    .expect("logged slot is registered");
                ClearedDecision {
                    slot: d.slot.clone(),
                    slot_label: reg.label.clone(),
                    selection_label: (reg.describe)(&d.selection),
                    selection: d.selection.clone(),
                }
            })
            .collect();
        Ok(ClearPreview {
            slot: slot.clone(),
            cleared,
        })
    }

    /// Clear `slot` and its transitive dependents, renumbering the survivors'
    /// order to match their positions (the log stays dense and chronological).
    pub fn clear(&self, log: &[Decision], slot: &SlotId) -> Result<Vec<Decision>, EngineError> {
        if !log.iter().any(|d| d.slot == *slot) {
            return Err(EngineError::NothingToClear { slot: slot.clone() });
        }
        let doomed = self.transitive_dependents(slot);
        let new_log: Vec<Decision> = log
            .iter()
            .filter(|d| !doomed.contains(&d.slot))
            .cloned()
            .enumerate()
            .map(|(i, mut d)| {
                d.order = i as u32;
                d
            })
            .collect();
        // The surviving log must still fold (clearing never corrupts).
        self.fold(&new_log)?;
        Ok(new_log)
    }

    /// The slot plus everything reachable through `dependents` edges.
    fn transitive_dependents(&self, slot: &SlotId) -> BTreeSet<SlotId> {
        let mut doomed: BTreeSet<SlotId> = BTreeSet::new();
        let mut stack = vec![slot.clone()];
        while let Some(current) = stack.pop() {
            if !doomed.insert(current.clone()) {
                continue;
            }
            if let Some(reg) = self.registration(&current) {
                stack.extend(reg.dependents.iter().cloned());
            }
        }
        doomed
    }

    pub fn steps(&self) -> &[(StepId, String)] {
        &self.steps
    }
}
