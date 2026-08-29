//! The engine: six operations over a ruleset's slot registrations —
//! slot-graph resolution, log append/replay, validation into the checklist,
//! the fold traversal, the draft lifecycle, and scoped-choice validation
//! (choice sets that live beside the log, replaceable wholesale, validated
//! against the folded base — the preparation section's machinery).

use std::collections::BTreeSet;

use types::{
    ChecklistEntry, ChecklistSeverity, ClearPreview, ClearedDecision, Decision, DecisionId,
    DecisionInput, DecisionSource, MeterState, MeterView, OptionId, ProjectionView, ScopedChoice,
    ScopedProjection, Selection, SheetSection, SheetView, SlotId, SlotStatus, SlotView,
    SlotViewKind, StepId, StepStatus, StepView, UnresolvedSuggestion,
};

use crate::{Availability, SlotRegistration};

/// Derive the materialized sheet from folded state.
pub type SheetFn<S> = Box<dyn Fn(&S) -> SheetView + Send + Sync>;
/// Derive the scoped display sections from folded state + choices.
pub type ScopedSheetFn<S> = Box<dyn Fn(&S, &[ScopedChoice]) -> Vec<SheetSection> + Send + Sync>;
/// Construct a fresh (empty) folded state.
pub type NewStateFn<S> = Box<dyn Fn() -> S + Send + Sync>;

/// Internal: the scoped half of a projection — the state after applying
/// scoped choices, the rendered scoped slot views, and their checklist.
type ScopedViews<S> = (S, Vec<(StepId, SlotView)>, Vec<ChecklistEntry>);

/// A ruleset assembled into a runnable engine. `S` is the ruleset's folded
/// state; the engine orchestrates, the registrations know the game.
pub struct Engine<S> {
    steps: Vec<(StepId, String)>,
    slots: Vec<SlotRegistration<S>>,
    /// Scoped slots: registered like wizard slots (same unlock/options/
    /// apply/validate contract) but their selections are a replaceable
    /// choice set beside the log, never decisions in it. They render into
    /// steps like any slot, flagged `scoped` so clients switch save paths.
    scoped: Vec<SlotRegistration<S>>,
    new_state: NewStateFn<S>,
    sheet: SheetFn<S>,
    /// Render-ready sheet sections derived from the scoped choice set —
    /// appended to *displayed* sheets only, never to the materialized
    /// sheet (`Engine::sheet` stays a pure function of the log).
    scoped_sheet: ScopedSheetFn<S>,
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

/// One slot's suggested content, supplied by the caller (a ruleset reads it
/// from its content records; engine-core sees only option IDs and text —
/// no game vocabulary).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SlotSuggestion {
    /// Ordered candidates: the planner takes the first legal one for a
    /// single-pick slot, or the first legal `count` for a multi-pick slot
    /// (`count` is state-dependent, read from the slot's kind at plan time).
    Candidates(Vec<OptionId>),
    /// Free text for a text slot.
    Text(String),
}

/// Result of expanding suggestions over a draft log: the extended log (the
/// legal prefix — an inapplicable suggestion is skipped and reported, never
/// rolled back), what was appended, and which required slots remain open
/// with the reason each one could not be filled.
#[derive(Debug, Clone)]
pub struct SuggestionPlan {
    pub log: Vec<Decision>,
    pub appended: Vec<Decision>,
    pub unresolved: Vec<UnresolvedSuggestion>,
}

impl<S> Engine<S> {
    /// Assemble an engine with no scoped slots (the common test shape).
    pub fn new(
        steps: Vec<(StepId, String)>,
        slots: Vec<SlotRegistration<S>>,
        new_state: NewStateFn<S>,
        sheet: SheetFn<S>,
    ) -> Self {
        Self::with_scoped(
            steps,
            slots,
            Vec::new(),
            new_state,
            sheet,
            Box::new(|_, _| Vec::new()),
        )
    }

    /// Assemble an engine. Panics on duplicate slot IDs (across wizard and
    /// scoped slots), an unknown step in a slot, or an unknown slot in a
    /// dependents list — these are ruleset authoring bugs, caught by the
    /// ruleset's own construction test. Dependents may cross the scope
    /// boundary: a wizard slot may list a scoped slot as a dependent (its
    /// scoped choices clear when the wizard slot changes).
    pub fn with_scoped(
        steps: Vec<(StepId, String)>,
        slots: Vec<SlotRegistration<S>>,
        scoped: Vec<SlotRegistration<S>>,
        new_state: NewStateFn<S>,
        sheet: SheetFn<S>,
        scoped_sheet: ScopedSheetFn<S>,
    ) -> Self {
        let mut seen = BTreeSet::new();
        for slot in slots.iter().chain(scoped.iter()) {
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
        for slot in slots.iter().chain(scoped.iter()) {
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
            scoped,
            new_state,
            sheet,
            scoped_sheet,
        }
    }

    fn registration(&self, slot: &SlotId) -> Option<&SlotRegistration<S>> {
        self.slots.iter().find(|s| s.id == *slot)
    }

    fn scoped_registration(&self, slot: &SlotId) -> Option<&SlotRegistration<S>> {
        self.scoped.iter().find(|s| s.id == *slot)
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

    /// One slot's view and checklist entries — the single driver behind
    /// wizard slots and scoped slots alike (one validation driver,
    /// observable: native, verify, and WASM all route through here).
    fn slot_view(
        &self,
        reg: &SlotRegistration<S>,
        state: &S,
        decision: Option<&Decision>,
        scoped: bool,
    ) -> Option<(SlotView, Vec<ChecklistEntry>)> {
        let availability = (reg.unlock)(state);
        if availability == Availability::Hidden {
            return None;
        }
        let entries = (reg.validate)(state, decision);

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

        let kind = (reg.kind)(state);
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
            meters.extend((reg.meters)(state, decision));
        }

        let options = if locked_reason.is_none() {
            (reg.options)(state)
        } else {
            Vec::new()
        };
        Some((
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
                scoped,
            },
            entries,
        ))
    }

    /// Scoped choices carried as synthetic decisions so the one slot driver
    /// serves both scopes; the id/order are display plumbing, never stored.
    fn scoped_decision(choice: &ScopedChoice, index: usize) -> Decision {
        Decision {
            id: DecisionId::new(format!("scoped.{}", choice.slot)),
            slot: choice.slot.clone(),
            selection: choice.selection.clone(),
            source: DecisionSource::Player,
            order: index as u32,
        }
    }

    /// Fold a scoped choice set onto the base state. Total: structural
    /// problems (unknown slot, duplicate, unavailable slot, rejected
    /// apply) come back as Illegal entries — a hand-edited section is
    /// reported, never a crash or a load failure.
    fn apply_scoped(&self, state: &mut S, choices: &[ScopedChoice]) -> Vec<ChecklistEntry> {
        let mut problems = Vec::new();
        let mut seen: BTreeSet<&SlotId> = BTreeSet::new();
        let scoped_step = |slot: &SlotId| {
            self.scoped_registration(slot)
                .map(|r| r.step.clone())
                .unwrap_or_else(|| StepId::new("scoped"))
        };
        let illegal = |slot: &SlotId, step: StepId, message: String| ChecklistEntry {
            severity: ChecklistSeverity::Illegal,
            slot: slot.clone(),
            step,
            rule: "Scoped section".into(),
            message,
            source: "scoped section".into(),
        };
        for (index, choice) in choices.iter().enumerate() {
            if !seen.insert(&choice.slot) {
                problems.push(illegal(
                    &choice.slot,
                    scoped_step(&choice.slot),
                    format!("two entries for slot '{}' — keep one", choice.slot),
                ));
                continue;
            }
            let Some(reg) = self.scoped_registration(&choice.slot) else {
                problems.push(illegal(
                    &choice.slot,
                    StepId::new("scoped"),
                    format!("unknown scoped slot '{}'", choice.slot),
                ));
                continue;
            };
            match (reg.unlock)(state) {
                Availability::Open => {}
                Availability::Locked { reason } => {
                    problems.push(illegal(
                        &choice.slot,
                        reg.step.clone(),
                        format!("this choice is not available: {reason}"),
                    ));
                    continue;
                }
                Availability::Hidden => {
                    problems.push(illegal(
                        &choice.slot,
                        reg.step.clone(),
                        "this choice does not exist for this character".into(),
                    ));
                    continue;
                }
            }
            let decision = Self::scoped_decision(choice, index);
            if let Err(e) = (reg.apply)(state, &decision) {
                problems.push(illegal(&choice.slot, reg.step.clone(), e.message));
            }
        }
        problems
    }

    /// The scoped half of a projection: fold the log, apply the choice
    /// set, and render every scoped slot through the one slot driver.
    /// Returns the mutated state so callers can reuse it.
    fn scoped_views(
        &self,
        log: &[Decision],
        prep: &[ScopedChoice],
    ) -> Result<ScopedViews<S>, EngineError> {
        let mut state = self.fold(log)?;
        let mut checklist = self.apply_scoped(&mut state, prep);
        let mut views = Vec::new();
        for reg in &self.scoped {
            let decision = prep
                .iter()
                .enumerate()
                .rev()
                .find(|(_, c)| c.slot == reg.id)
                .map(|(i, c)| Self::scoped_decision(c, i));
            if let Some((view, entries)) = self.slot_view(reg, &state, decision.as_ref(), true) {
                checklist.extend(entries);
                views.push((reg.step.clone(), view));
            }
        }
        Ok((state, views, checklist))
    }

    /// Operation six, standalone: validate a scoped choice set against the
    /// folded base — the verify pass and the finalized sheet view's prep
    /// editor both call this. Total over the choice set (illegal or
    /// hand-mangled picks come back as entries); errors only when the log
    /// itself does not fold.
    pub fn scoped_projection(
        &self,
        log: &[Decision],
        prep: &[ScopedChoice],
    ) -> Result<ScopedProjection, EngineError> {
        let (_, views, checklist) = self.scoped_views(log, prep)?;
        Ok(ScopedProjection {
            slots: views.into_iter().map(|(_, v)| v).collect(),
            checklist,
        })
    }

    /// Whether any scoped slot exists (is not Hidden) for this log — drives
    /// whether a client offers the scoped editor at all.
    pub fn has_scoped_slots(&self, log: &[Decision]) -> Result<bool, EngineError> {
        let state = self.fold(log)?;
        Ok(self
            .scoped
            .iter()
            .any(|reg| (reg.unlock)(&state) != Availability::Hidden))
    }

    /// The scoped sheet sections alone — for callers whose base sheet is
    /// the *stored* materialized sheet (the load path), never a refold.
    pub fn scoped_sections(
        &self,
        log: &[Decision],
        prep: &[ScopedChoice],
    ) -> Result<Vec<SheetSection>, EngineError> {
        let (state, _, _) = self.scoped_views(log, prep)?;
        Ok((self.scoped_sheet)(&state, prep))
    }

    /// The displayed sheet: the materialized sheet plus the scoped
    /// sections. The stored sheet is `Engine::sheet` — this never feeds
    /// persistence.
    pub fn display_sheet(
        &self,
        log: &[Decision],
        prep: &[ScopedChoice],
    ) -> Result<SheetView, EngineError> {
        let (state, _, _) = self.scoped_views(log, prep)?;
        let mut sheet = (self.sheet)(&state);
        sheet.sections.extend((self.scoped_sheet)(&state, prep));
        Ok(sheet)
    }

    /// Project the full wizard view from a log plus its scoped choice set.
    /// Scoped slots render into their steps like any slot, flagged
    /// `scoped`; their entries join the checklist, so finalize blocks on
    /// illegal or incomplete preparation exactly as on build gaps.
    pub fn project(
        &self,
        log: &[Decision],
        prep: &[ScopedChoice],
    ) -> Result<ProjectionView, EngineError> {
        let (state, scoped_views, mut checklist) = self.scoped_views(log, prep)?;
        let mut slot_views: Vec<(StepId, SlotView)> = Vec::new();

        for reg in &self.slots {
            let decision = log.iter().rev().find(|d| d.slot == reg.id);
            if let Some((view, entries)) = self.slot_view(reg, &state, decision, false) {
                checklist.extend(entries);
                slot_views.push((reg.step.clone(), view));
            }
        }
        slot_views.extend(scoped_views);

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

        // The projection's sheet is the *displayed* sheet: materialized
        // values plus scoped sections. The materialized sheet on disk stays
        // `Engine::sheet(log)` — a pure function of the log.
        let mut sheet = (self.sheet)(&state);
        sheet.sections.extend((self.scoped_sheet)(&state, prep));
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
        prep: &[ScopedChoice],
    ) -> Result<ProjectionView, EngineError> {
        let mut hypothetical: Vec<Decision> = log
            .iter()
            .filter(|d| d.slot != candidate.slot)
            .cloned()
            .collect();
        let order = hypothetical.len() as u32;
        hypothetical.push(candidate.clone().into_decision(order));
        self.project(&hypothetical, prep)
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
    /// Returns the surviving scoped choices beside the outcome — dependents
    /// across the scope boundary clear in the same step.
    pub fn amend(
        &self,
        log: &[Decision],
        prep: &[ScopedChoice],
        input: DecisionInput,
    ) -> Result<(AppendOutcome, Vec<ScopedChoice>), EngineError> {
        if log.iter().any(|d| d.id == input.id) {
            return Ok((AppendOutcome::AlreadyPresent, prep.to_vec()));
        }
        let (base, surviving) = if log.iter().any(|d| d.slot == input.slot) {
            self.clear(log, prep, &input.slot)?
        } else {
            (log.to_vec(), prep.to_vec())
        };
        Ok((self.append(&base, input)?, surviving))
    }

    /// What clearing `slot` would take with it (the confirmation prompt) —
    /// log decisions and scoped choices alike, in that order.
    pub fn clear_preview(
        &self,
        log: &[Decision],
        prep: &[ScopedChoice],
        slot: &SlotId,
    ) -> Result<ClearPreview, EngineError> {
        if !log.iter().any(|d| d.slot == *slot) {
            return Err(EngineError::NothingToClear { slot: slot.clone() });
        }
        let doomed = self.transitive_dependents(slot);
        let mut cleared: Vec<ClearedDecision> = log
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
        cleared.extend(
            prep.iter()
                .filter(|c| doomed.contains(&c.slot))
                .filter_map(|c| {
                    let reg = self.scoped_registration(&c.slot)?;
                    Some(ClearedDecision {
                        slot: c.slot.clone(),
                        slot_label: reg.label.clone(),
                        selection_label: (reg.describe)(&c.selection),
                        selection: c.selection.clone(),
                    })
                }),
        );
        Ok(ClearPreview {
            slot: slot.clone(),
            cleared,
        })
    }

    /// Clear `slot` and its transitive dependents — reaching across the
    /// scope boundary: dependent scoped choices clear in the same step, so
    /// the caller persists log and scoped section in one durable write.
    /// Survivors' order is renumbered (the log stays dense and
    /// chronological).
    pub fn clear(
        &self,
        log: &[Decision],
        prep: &[ScopedChoice],
        slot: &SlotId,
    ) -> Result<(Vec<Decision>, Vec<ScopedChoice>), EngineError> {
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
        let surviving_prep: Vec<ScopedChoice> = prep
            .iter()
            .filter(|c| !doomed.contains(&c.slot))
            .cloned()
            .collect();
        Ok((new_log, surviving_prep))
    }

    // ---- The suggestion planner (quick build / fill-remaining) ----

    /// Expand suggestions over a draft log: walk the open required slots in
    /// registration (unlock/dependency) order against the folded state,
    /// resolve each slot's suggestion, append through the normal validated
    /// `append` path with the given provenance `source`, refold, and repeat
    /// until no open required slot has an applicable suggestion. Never
    /// overwrites an existing decision; deterministic (registration order ×
    /// candidate order, no randomness). A suggestion that cannot apply is
    /// skipped and reported in `unresolved` — the legal prefix is kept,
    /// never rolled back.
    pub fn expand_suggestions(
        &self,
        log: &[Decision],
        suggest: &dyn Fn(&SlotId) -> Option<SlotSuggestion>,
        mint_id: &dyn Fn(&SlotId) -> DecisionId,
        source: DecisionSource,
    ) -> Result<SuggestionPlan, EngineError> {
        let mut log = log.to_vec();
        let mut appended = Vec::new();
        loop {
            let state = self.fold(&log)?;
            let mut progressed = false;
            for reg in &self.slots {
                if !reg.required || log.iter().any(|d| d.slot == reg.id) {
                    continue;
                }
                if (reg.unlock)(&state) != Availability::Open {
                    continue;
                }
                let Some(suggestion) = suggest(&reg.id) else {
                    continue;
                };
                let Ok(selection) = self.suggested_selection(reg, &state, &suggestion) else {
                    continue;
                };
                let input = DecisionInput {
                    id: mint_id(&reg.id),
                    slot: reg.id.clone(),
                    selection,
                    source,
                };
                if let Ok(AppendOutcome::Appended(new_log)) = self.append(&log, input) {
                    appended.push(
                        new_log
                            .last()
                            .cloned()
                            .expect("append grew the log by one decision"),
                    );
                    log = new_log;
                    progressed = true;
                    // Refold before the next slot: counts, catalogs, and
                    // unlocks may all have changed under this decision.
                    break;
                }
            }
            if !progressed {
                break;
            }
        }
        let unresolved = self.unresolved_suggestions(&log, suggest, source)?;
        Ok(SuggestionPlan {
            log,
            appended,
            unresolved,
        })
    }

    /// The open required slots of `log` that the suggestions do not fill,
    /// each with the reason (no entry, no legal candidate, or the engine's
    /// structural refusal). After `expand_suggestions` this is exactly the
    /// cannot-complete remainder; standalone (the idempotent-replay path) a
    /// fillable slot reports that a fresh fill would apply it.
    pub fn unresolved_suggestions(
        &self,
        log: &[Decision],
        suggest: &dyn Fn(&SlotId) -> Option<SlotSuggestion>,
        source: DecisionSource,
    ) -> Result<Vec<UnresolvedSuggestion>, EngineError> {
        let state = self.fold(log)?;
        let mut out = Vec::new();
        for reg in &self.slots {
            if !reg.required || log.iter().any(|d| d.slot == reg.id) {
                continue;
            }
            if (reg.unlock)(&state) != Availability::Open {
                continue;
            }
            let reason = match suggest(&reg.id) {
                None => "the suggested build has no entry for this slot".to_string(),
                Some(suggestion) => match self.suggested_selection(reg, &state, &suggestion) {
                    Err(reason) => reason,
                    Ok(selection) => {
                        // The selection resolves — probe the append (dry, on
                        // a throwaway ID) so the reason is the engine's own
                        // refusal, or an honest "not applied by this run".
                        let probe = DecisionInput {
                            id: DecisionId::new(format!("__suggestion-probe.{}", reg.id)),
                            slot: reg.id.clone(),
                            selection,
                            source,
                        };
                        match self.append(log, probe) {
                            Err(e) => e.to_string(),
                            Ok(_) => "a legal suggestion exists for this slot — \
                                      fill remaining again to apply it"
                                .to_string(),
                        }
                    }
                },
            };
            out.push(UnresolvedSuggestion {
                slot: reg.id.clone(),
                label: reg.label.clone(),
                reason,
            });
        }
        Ok(out)
    }

    /// Resolve one slot's suggestion into a concrete selection against the
    /// folded state, or say why none applies. Candidates are filtered to
    /// currently-available options, deduplicated, in the authored order.
    fn suggested_selection(
        &self,
        reg: &SlotRegistration<S>,
        state: &S,
        suggestion: &SlotSuggestion,
    ) -> Result<Selection, String> {
        let kind = (reg.kind)(state);
        match (&kind, suggestion) {
            (SlotViewKind::Text { .. }, SlotSuggestion::Text(t)) => Ok(Selection::Text(t.clone())),
            (SlotViewKind::Text { .. }, SlotSuggestion::Candidates(_)) => {
                Err("the suggestion lists options but this slot takes text".to_string())
            }
            (_, SlotSuggestion::Text(_)) => {
                Err("the suggestion is text but this slot takes options".to_string())
            }
            (_, SlotSuggestion::Candidates(candidates)) => {
                let options = (reg.options)(state);
                let mut legal: Vec<OptionId> = Vec::new();
                for candidate in candidates {
                    if legal.contains(candidate) {
                        continue;
                    }
                    if options.iter().any(|o| o.available && o.id == *candidate) {
                        legal.push(candidate.clone());
                    }
                }
                match kind {
                    SlotViewKind::Single => legal
                        .first()
                        .cloned()
                        .map(Selection::Option)
                        .ok_or_else(|| {
                            "no suggested option is currently legal for this slot".to_string()
                        }),
                    SlotViewKind::Multi { count } => {
                        let take: Vec<OptionId> = legal.into_iter().take(count as usize).collect();
                        if take.len() < count as usize {
                            Err(format!(
                                "only {} of the {count} needed suggestion(s) are currently legal",
                                take.len()
                            ))
                        } else {
                            Ok(Selection::Options(take))
                        }
                    }
                    SlotViewKind::List => Ok(Selection::Options(legal)),
                    SlotViewKind::Text { .. } => unreachable!("matched above"),
                }
            }
        }
    }

    /// The slot plus everything reachable through `dependents` edges — one
    /// graph spanning wizard and scoped slots (the existing clearing
    /// machinery's reach extends across the scope boundary; there is no
    /// second dependency tracker).
    fn transitive_dependents(&self, slot: &SlotId) -> BTreeSet<SlotId> {
        let mut doomed: BTreeSet<SlotId> = BTreeSet::new();
        let mut stack = vec![slot.clone()];
        while let Some(current) = stack.pop() {
            if !doomed.insert(current.clone()) {
                continue;
            }
            if let Some(reg) = self
                .registration(&current)
                .or_else(|| self.scoped_registration(&current))
            {
                stack.extend(reg.dependents.iter().cloned());
            }
        }
        doomed
    }

    pub fn steps(&self) -> &[(StepId, String)] {
        &self.steps
    }
}
