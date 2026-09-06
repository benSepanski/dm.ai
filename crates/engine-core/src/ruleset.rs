//! The ruleset boundary as a contract, not a type: one object-safe surface
//! the server, the WASM bundle, and the checks talk to, so two rulesets can
//! stand behind one runtime selector. Log in, views out — no game
//! vocabulary here (slots, levels, versions, pools; never classes or
//! scores).
//!
//! `EngineOps` is the engine half (one blanket implementation over
//! `Engine<S>`); `Ruleset` adds the escape hatches a ruleset answers from
//! its own data (which slot is the name, what level a log is at, which
//! slot advances it, what a mint may write into a required text slot).

use std::collections::BTreeMap;

use types::{
    ClearPreview, ClearedDecision, Decision, DecisionId, DecisionInput, DecisionSource, OptionId,
    ProjectionView, SheetView, SlotId, StepId,
};

use crate::{
    AppendOutcome, Engine, EngineError, SlotSuggestion, SuggestionContext, SuggestionPlan,
};

/// The engine operations the routes and the browser call, state-erased.
pub trait EngineOps: Send + Sync {
    /// Replay the log and discard the state: "does this log fold?".
    fn folds(&self, log: &[Decision]) -> Result<(), EngineError>;
    fn sheet(&self, log: &[Decision]) -> Result<SheetView, EngineError>;
    fn project(&self, log: &[Decision]) -> Result<ProjectionView, EngineError>;
    fn preview(
        &self,
        log: &[Decision],
        candidate: &DecisionInput,
    ) -> Result<ProjectionView, EngineError>;
    fn append(&self, log: &[Decision], input: DecisionInput) -> Result<AppendOutcome, EngineError>;
    fn amend(&self, log: &[Decision], input: DecisionInput) -> Result<AppendOutcome, EngineError>;
    fn clear_preview(&self, log: &[Decision], slot: &SlotId) -> Result<ClearPreview, EngineError>;
    fn clear(&self, log: &[Decision], slot: &SlotId) -> Result<Vec<Decision>, EngineError>;
    fn expand_suggestions(
        &self,
        log: &[Decision],
        suggest: &mut dyn FnMut(&SuggestionContext) -> Option<SlotSuggestion>,
        mint_id: &dyn Fn(&SlotId) -> DecisionId,
        source: DecisionSource,
    ) -> Result<SuggestionPlan, EngineError>;
    fn unresolved_suggestions(
        &self,
        log: &[Decision],
        suggest: &mut dyn FnMut(&SuggestionContext) -> Option<SlotSuggestion>,
        source: DecisionSource,
    ) -> Result<Vec<types::UnresolvedSuggestion>, EngineError>;
    fn live_steps(&self, log: &[Decision]) -> Result<Vec<(StepId, String)>, EngineError>;
    fn describe_decision(&self, decision: &Decision) -> Option<ClearedDecision>;
}

impl<S: Send + Sync + 'static> EngineOps for Engine<S> {
    fn folds(&self, log: &[Decision]) -> Result<(), EngineError> {
        self.fold(log).map(|_| ())
    }
    fn sheet(&self, log: &[Decision]) -> Result<SheetView, EngineError> {
        Engine::sheet(self, log)
    }
    fn project(&self, log: &[Decision]) -> Result<ProjectionView, EngineError> {
        Engine::project(self, log)
    }
    fn preview(
        &self,
        log: &[Decision],
        candidate: &DecisionInput,
    ) -> Result<ProjectionView, EngineError> {
        Engine::preview(self, log, candidate)
    }
    fn append(&self, log: &[Decision], input: DecisionInput) -> Result<AppendOutcome, EngineError> {
        Engine::append(self, log, input)
    }
    fn amend(&self, log: &[Decision], input: DecisionInput) -> Result<AppendOutcome, EngineError> {
        Engine::amend(self, log, input)
    }
    fn clear_preview(&self, log: &[Decision], slot: &SlotId) -> Result<ClearPreview, EngineError> {
        Engine::clear_preview(self, log, slot)
    }
    fn clear(&self, log: &[Decision], slot: &SlotId) -> Result<Vec<Decision>, EngineError> {
        Engine::clear(self, log, slot)
    }
    fn expand_suggestions(
        &self,
        log: &[Decision],
        suggest: &mut dyn FnMut(&SuggestionContext) -> Option<SlotSuggestion>,
        mint_id: &dyn Fn(&SlotId) -> DecisionId,
        source: DecisionSource,
    ) -> Result<SuggestionPlan, EngineError> {
        Engine::expand_suggestions(self, log, suggest, mint_id, source)
    }
    fn unresolved_suggestions(
        &self,
        log: &[Decision],
        suggest: &mut dyn FnMut(&SuggestionContext) -> Option<SlotSuggestion>,
        source: DecisionSource,
    ) -> Result<Vec<types::UnresolvedSuggestion>, EngineError> {
        Engine::unresolved_suggestions(self, log, suggest, source)
    }
    fn live_steps(&self, log: &[Decision]) -> Result<Vec<(StepId, String)>, EngineError> {
        Engine::live_steps(self, log)
    }
    fn describe_decision(&self, decision: &Decision) -> Option<ClearedDecision> {
        Engine::describe_decision(self, decision)
    }
}

/// A suggested build: class record ID → (slot → suggestion), the planner's
/// shape, translated from content once per ruleset.
pub type SuggestedBuild = (String, BTreeMap<SlotId, SlotSuggestion>);

/// One game system, assembled: its engine plus the handful of questions
/// the server and browser must ask a ruleset that the engine cannot
/// answer on its own. Every method is a pure function of the ruleset's
/// embedded data and the log it is handed.
pub trait Ruleset: Send + Sync {
    /// The system id — the campaign declaration's value, the rules-data
    /// directory name, and the prefix of every rules version ("pf2e").
    fn system(&self) -> &str;
    /// Render-ready game name ("Pathfinder 2e").
    fn system_name(&self) -> &str;
    /// The shipped manifest version — what new characters pin.
    fn rules_version(&self) -> &str;
    /// Prior shipped versions this one supersedes, oldest first.
    fn supersedes(&self) -> &[String];
    /// The shipped-versions lineage document, verbatim (its key set is the
    /// server's older-known input).
    fn shipped_versions_json(&self) -> &str;
    /// License and attribution paragraphs the app must display.
    fn license_lines(&self) -> Vec<String>;

    fn engine(&self) -> &dyn EngineOps;

    /// The free-text slot that names the character.
    fn name_slot(&self) -> SlotId;
    /// The slot whose options are the shipped classes.
    fn class_slot(&self) -> SlotId;
    /// The character level a log folds to.
    fn level_of(&self, log: &[Decision]) -> Result<u32, EngineError>;
    /// The level a finalized log can advance to next, if any.
    fn next_level(&self, log: &[Decision]) -> Result<Option<u32>, EngineError>;
    /// The advance slot for a level and its one option.
    fn advance_slot(&self, level: u32) -> SlotId;
    fn advance_option(&self, level: u32) -> OptionId;
    fn is_advance_slot(&self, slot: &SlotId) -> bool;
    /// Every published suggested build (empty when the rules publish none).
    fn suggested_builds(&self) -> &[SuggestedBuild];
    /// Candidate texts a random mint may write into a required text slot
    /// (own-authored app vocabulary, never rules content); empty means the
    /// slot must stay open.
    fn text_fill_candidates(&self, slot: &SlotId) -> Vec<String>;
    /// The record id a random mint keys its name pool on (the ancestry or
    /// species chosen in the log), if any.
    fn name_pool_key(&self, log: &[Decision]) -> Option<String>;
}
