//! The engine: five operations over a ruleset's slot registrations —
//! slot-graph resolution, log append/replay, validation into the checklist,
//! the fold traversal, and the draft lifecycle.

use std::collections::BTreeSet;

use types::{
    ChecklistEntry, ChecklistSeverity, ClearPreview, ClearedDecision, Decision, DecisionId,
    DecisionInput, DecisionSource, MeterView, OptionId, ProjectionView, Selection, SheetView,
    SlotId, SlotStatus, SlotView, SlotViewKind, StepId, StepStatus, StepView, UnresolvedSuggestion,
};

use crate::{Availability, SlotRegistration, StepRegistration};

/// A ruleset assembled into a runnable engine. `S` is the ruleset's folded
/// state; the engine orchestrates, the registrations know the game.
pub struct Engine<S> {
    steps: Vec<StepRegistration<S>>,
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

/// What a suggestion source sees when asked about one open slot: the
/// slot's identity plus its current kind and option views against the
/// folded state. A published-build source keys on `slot` alone; a
/// sampling source shuffles `options` (choosing its own legality filter —
/// `available`-only for a mint, everything for a fuzz driver).
pub struct SuggestionContext<'a> {
    pub slot: &'a SlotId,
    pub label: &'a str,
    pub kind: SlotViewKind,
    pub options: &'a [types::OptionView],
}

/// A suggestion that resolves but is refused by `append` (a set-level
/// constraint, say) is re-asked from the source up to this many times per
/// slot per pass — a sampling source yields a fresh shuffle each ask; a
/// deterministic source repeats itself and the loop stops early on the
/// first repeat.
const RESAMPLE_LIMIT: u32 = 64;

impl<S> Engine<S> {
    /// Assemble an engine. Panics on duplicate slot IDs, an unknown step in
    /// a slot, or an unknown slot in a dependents list — these are ruleset
    /// authoring bugs, caught by the ruleset's own construction test.
    pub fn new(
        steps: Vec<StepRegistration<S>>,
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
                steps.iter().any(|st| st.id == slot.step),
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
        // Step liveness: only live steps render, and a dead step's slots
        // are neither rendered nor validated (they stay appendable — that
        // is what lets a ruleset keep a slot open to a route without ever
        // showing it as a card).
        let live: Vec<&StepRegistration<S>> =
            self.steps.iter().filter(|st| (st.live)(&state)).collect();

        for reg in &self.slots {
            if !live.iter().any(|st| st.id == reg.step) {
                continue;
            }
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
                    meters.push(MeterView::exact("Chosen", picked, count as usize));
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

        let steps = live
            .iter()
            .map(|st| {
                let (id, title) = (&st.id, &st.title);
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

    // ---- The suggestion planner (quick build / fill-remaining) ----

    /// Expand suggestions over a draft log: walk the open required slots in
    /// registration (unlock/dependency) order against the folded state,
    /// ask the source for each slot (handing it the slot's kind and option
    /// views — a sampling source shuffles them, a published-build source
    /// ignores them), append through the normal validated `append` path
    /// with the given provenance `source`, refold, and repeat until no open
    /// required slot has an applicable suggestion. A refused suggestion is
    /// re-asked up to `RESAMPLE_LIMIT` times (stopping early when the
    /// source repeats itself — the deterministic-source case). Never
    /// overwrites an existing decision; deterministic given the source
    /// (registration order × whatever the source returns — the engine
    /// itself has no randomness). A suggestion that cannot apply is skipped
    /// and reported in `unresolved` — the legal prefix is kept, never
    /// rolled back.
    pub fn expand_suggestions(
        &self,
        log: &[Decision],
        suggest: &mut dyn FnMut(&SuggestionContext) -> Option<SlotSuggestion>,
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
                let options = (reg.options)(&state);
                let ctx = SuggestionContext {
                    slot: &reg.id,
                    label: &reg.label,
                    kind: (reg.kind)(&state),
                    options: &options,
                };
                let mut last_tried: Option<SlotSuggestion> = None;
                for _ in 0..RESAMPLE_LIMIT {
                    let Some(suggestion) = suggest(&ctx) else {
                        break;
                    };
                    // A source that repeats itself is deterministic —
                    // retrying the identical suggestion cannot succeed.
                    if last_tried.as_ref() == Some(&suggestion) {
                        break;
                    }
                    let Ok(selection) = self.suggested_selection(reg, &state, &suggestion) else {
                        last_tried = Some(suggestion);
                        continue;
                    };
                    last_tried = Some(suggestion);
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
                        break;
                    }
                }
                if progressed {
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
        suggest: &mut dyn FnMut(&SuggestionContext) -> Option<SlotSuggestion>,
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
            let options = (reg.options)(&state);
            let ctx = SuggestionContext {
                slot: &reg.id,
                label: &reg.label,
                kind: (reg.kind)(&state),
                options: &options,
            };
            let reason = match suggest(&ctx) {
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

    /// The steps live under a log's folded state, in registration order —
    /// the only step list a client ever sees (resume labels, cursors, and
    /// the projection all index this).
    pub fn live_steps(&self, log: &[Decision]) -> Result<Vec<(StepId, String)>, EngineError> {
        let state = self.fold(log)?;
        Ok(self
            .steps
            .iter()
            .filter(|st| (st.live)(&state))
            .map(|st| (st.id.clone(), st.title.clone()))
            .collect())
    }

    /// Render-ready description of one logged decision (slot label +
    /// selection label), the shape the clear-confirmation prompt uses.
    pub fn describe_decision(&self, decision: &Decision) -> Option<ClearedDecision> {
        let reg = self.registration(&decision.slot)?;
        Some(ClearedDecision {
            slot: decision.slot.clone(),
            slot_label: reg.label.clone(),
            selection_label: (reg.describe)(&decision.selection),
            selection: decision.selection.clone(),
        })
    }
}
