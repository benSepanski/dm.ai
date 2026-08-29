//! HTTP routes. The server is the authority: every write re-validates and
//! re-derives natively; responses are view types from `types`, never
//! storage documents.

use std::sync::Arc;

use axum::extract::{Path as AxumPath, State};
use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use axum::routing::{get, post};
use axum::{Json, Router};
use engine_core::{AppendOutcome, EngineError};
use ruleset_pf2e::Pf2eEngine;
use tokio::sync::Mutex;
use types::{
    ApiError, CharacterId, CharacterView, ChecklistEntry, ChecklistSeverity, ClearOutcome,
    ClearRequest, ConfirmOutcome, ConfirmRequest, CreateCharacterRequest, DraftView,
    FinalizeOutcome, FinalizeRequest, ReplayOutcome, RosterCharacterState, RosterEntry,
    RosterProblem, RosterView, Selection, SlotId, StepId, StepRequest, VersionActionRequest,
    VersionFlaggedError, VersionResolutionOutcome, VersionStatus,
};

use crate::clock;
use crate::persistence::{DocState, KeepOldMarker, Loaded, Store, StoreError, VersionEvent};
use crate::version::{repair_replay, status_for, KnownVersions};

pub(crate) struct App {
    pub engine: Pf2eEngine,
    pub store: Mutex<Store>,
    pub rules_version: String,
    pub known: KnownVersions,
    pub license_notice: String,
}

pub(crate) type SharedApp = Arc<App>;

pub(crate) fn router(app: SharedApp) -> Router {
    Router::new()
        .route("/api/roster", get(roster))
        .route("/api/characters", post(create_character))
        .route(
            "/api/characters/{id}",
            get(get_character).delete(delete_character),
        )
        .route("/api/characters/{id}/confirm", post(confirm))
        .route("/api/characters/{id}/amend", post(amend))
        .route("/api/characters/{id}/clear", post(clear))
        .route("/api/characters/{id}/step", post(set_step))
        .route("/api/characters/{id}/finalize", post(finalize))
        .route("/api/characters/{id}/version/repin", post(version_repin))
        .route("/api/characters/{id}/version/accept", post(version_accept))
        .route(
            "/api/characters/{id}/version/keep-old",
            post(version_keep_old),
        )
        .route(
            "/api/characters/{id}/version/resolve-errors",
            post(version_resolve_errors),
        )
        .with_state(app)
}

enum Failure {
    NotFound(String),
    Unprocessable(String),
    Internal(String),
    /// A wizard write on a draft whose rules-data pin is not current and
    /// unresolved: refused with the flag attached (409). Boxed to keep the
    /// error variant small (clippy result_large_err).
    VersionFlagged(Box<VersionStatus>),
}

impl From<StoreError> for Failure {
    fn from(e: StoreError) -> Self {
        match e {
            StoreError::NotFound(id) => Failure::NotFound(format!("character '{id}' not found")),
            other => Failure::Internal(other.to_string()),
        }
    }
}

impl IntoResponse for Failure {
    fn into_response(self) -> Response {
        let (status, message) = match self {
            Failure::NotFound(m) => (StatusCode::NOT_FOUND, m),
            Failure::Unprocessable(m) => (StatusCode::UNPROCESSABLE_ENTITY, m),
            Failure::Internal(m) => (StatusCode::INTERNAL_SERVER_ERROR, m),
            Failure::VersionFlagged(flag) => {
                return (
                    StatusCode::CONFLICT,
                    Json(VersionFlaggedError {
                        message: "this draft was built against an older rules-data version — \
                                  resolve the version flag before continuing the wizard"
                            .into(),
                        status: *flag,
                    }),
                )
                    .into_response();
            }
        };
        (status, Json(ApiError { message })).into_response()
    }
}

fn step_index(engine: &Pf2eEngine, step: &StepId) -> usize {
    engine
        .steps()
        .iter()
        .position(|(id, _)| id == step)
        .unwrap_or(0)
}

fn draft_view(app: &App, loaded: &Loaded) -> Result<DraftView, Failure> {
    let projection = app
        .engine
        .project(&loaded.log)
        .map_err(|e| Failure::Internal(format!("stored log does not replay: {e}")))?;
    Ok(DraftView {
        id: loaded.id.clone(),
        version: loaded.draft_version,
        current_step: loaded.current_step.clone(),
        projection,
        rules_version: loaded.rules_version.clone(),
        // Only current drafts are projected; flagged drafts arrive as
        // CharacterView::FlaggedDraft instead.
        version_status: VersionStatus::Current,
    })
}

/// The full character view, version flag included. A draft with an
/// unresolved non-current pin gets no projection (that would replay the old
/// log against new data outside the resolution flow) — its stored sheet and
/// flag arrive as `FlaggedDraft`.
fn character_view(app: &App, loaded: &Loaded) -> Result<CharacterView, Failure> {
    let status = status_for(&app.engine, &app.known, loaded);
    Ok(match loaded.state {
        DocState::Finalized => CharacterView::Finalized {
            id: loaded.id.clone(),
            sheet: loaded.sheet.clone(),
            version_status: status,
            version: loaded.draft_version,
        },
        DocState::Draft if status == VersionStatus::Current => {
            CharacterView::Draft(draft_view(app, loaded)?)
        }
        DocState::Draft => CharacterView::FlaggedDraft {
            id: loaded.id.clone(),
            name: display_name(loaded),
            sheet: loaded.sheet.clone(),
            version: loaded.draft_version,
            status,
        },
    })
}

/// Reject wizard writes on a draft whose pin is not current: continuing
/// would replay (and extend) an old log against new data. Resolution is the
/// only path forward; the refusal carries the flag.
fn guard_wizard_write(app: &App, loaded: &Loaded) -> Result<(), Failure> {
    if loaded.state == DocState::Draft && loaded.rules_version != app.rules_version {
        return Err(Failure::VersionFlagged(Box::new(status_for(
            &app.engine,
            &app.known,
            loaded,
        ))));
    }
    Ok(())
}

fn resume_label(app: &App, loaded: &Loaded) -> String {
    let steps = app.engine.steps();
    let index = step_index(&app.engine, &loaded.current_step);
    let title = steps
        .get(index)
        .map(|(_, t)| t.as_str())
        .unwrap_or("Concept");
    format!("step {} of {} — {}", index + 1, steps.len(), title)
}

fn summary_line(loaded: &Loaded) -> String {
    loaded.sheet.summary.first().cloned().unwrap_or_default()
}

fn display_name(loaded: &Loaded) -> String {
    if loaded.sheet.name.trim().is_empty() {
        "Unnamed adventurer".to_string()
    } else {
        loaded.sheet.name.clone()
    }
}

async fn roster(State(app): State<SharedApp>) -> Result<Json<RosterView>, Failure> {
    let store = app.store.lock().await;
    let load = store.load_all()?;
    let mut entries: Vec<RosterEntry> = load
        .characters
        .iter()
        .map(|c| RosterEntry {
            id: c.id.clone(),
            name: display_name(c),
            summary: summary_line(c),
            state: match c.state {
                DocState::Draft => RosterCharacterState::Draft {
                    resume_label: resume_label(&app, c),
                },
                DocState::Finalized => RosterCharacterState::Finalized,
            },
            version: status_for(&app.engine, &app.known, c),
        })
        .collect();
    entries.sort_by(|a, b| a.id.cmp(&b.id));
    Ok(Json(RosterView {
        entries,
        problems: load
            .problems
            .into_iter()
            .map(|(file, message)| RosterProblem { file, message })
            .collect(),
        license_notice: app.license_notice.clone(),
    }))
}

async fn create_character(
    State(app): State<SharedApp>,
    Json(request): Json<CreateCharacterRequest>,
) -> Result<Json<DraftView>, Failure> {
    let store = app.store.lock().await;
    let id = store.mint_character_id();
    let mut log = Vec::new();
    if let Some(name) = request.name.filter(|n| !n.trim().is_empty()) {
        // A working name arrives as a normal decision on the name slot.
        let input = types::DecisionInput {
            id: types::DecisionId::new(format!("{id}-initial-name")),
            slot: SlotId::new("pf2e.details.name"),
            selection: Selection::Text(name),
            source: types::DecisionSource::Player,
        };
        if let Ok(AppendOutcome::Appended(new_log)) = app.engine.append(&log, input) {
            log = new_log;
        }
    }
    let sheet = app
        .engine
        .sheet(&log)
        .map_err(|e| Failure::Internal(e.to_string()))?;
    let loaded = Loaded {
        id: id.clone(),
        state: DocState::Draft,
        current_step: app.engine.steps()[0].0.clone(),
        draft_version: 1,
        sheet,
        log,
        rules_version: app.rules_version.clone(),
        version_history: Vec::new(),
        keep_old: None,
    };
    store.save(&loaded)?;
    Ok(Json(draft_view(&app, &loaded)?))
}

async fn get_character(
    State(app): State<SharedApp>,
    AxumPath(id): AxumPath<String>,
) -> Result<Json<CharacterView>, Failure> {
    let store = app.store.lock().await;
    let loaded = store.load(&CharacterId::new(id))?;
    Ok(Json(character_view(&app, &loaded)?))
}

async fn delete_character(
    State(app): State<SharedApp>,
    AxumPath(id): AxumPath<String>,
) -> Result<StatusCode, Failure> {
    let store = app.store.lock().await;
    store.delete(&CharacterId::new(id))?;
    Ok(StatusCode::NO_CONTENT)
}

fn engine_error_entry(step: StepId, slot: SlotId, message: String) -> ChecklistEntry {
    ChecklistEntry {
        severity: ChecklistSeverity::Illegal,
        slot,
        step,
        rule: "Server validation".into(),
        message,
        source: "server".into(),
    }
}

async fn confirm(
    State(app): State<SharedApp>,
    AxumPath(id): AxumPath<String>,
    Json(request): Json<ConfirmRequest>,
) -> Result<Json<ConfirmOutcome>, Failure> {
    let store = app.store.lock().await;
    let mut loaded = store.load(&CharacterId::new(id))?;
    if loaded.state == DocState::Finalized {
        return Err(Failure::Unprocessable(
            "character is finalized — build decisions are locked".into(),
        ));
    }
    guard_wizard_write(&app, &loaded)?;
    // Idempotency first: a retry after a crash between save and ack carries
    // the version it was originally made against, which is stale by now —
    // but its decision ID is already in the log, so it's a success, not a
    // conflict, and appends nothing.
    if loaded.log.iter().any(|d| d.id == request.decision.id) {
        return Ok(Json(ConfirmOutcome::Confirmed {
            draft: draft_view(&app, &loaded)?,
        }));
    }
    if request.version != loaded.draft_version {
        return Ok(Json(ConfirmOutcome::Conflict {
            current: draft_view(&app, &loaded)?,
        }));
    }
    let slot = request.decision.slot.clone();
    match app.engine.append(&loaded.log, request.decision) {
        Ok(AppendOutcome::AlreadyPresent) => {
            // Idempotent retry: already durable, acknowledge again.
            Ok(Json(ConfirmOutcome::Confirmed {
                draft: draft_view(&app, &loaded)?,
            }))
        }
        Ok(AppendOutcome::Appended(new_log)) => {
            loaded.log = new_log;
            loaded.sheet = app
                .engine
                .sheet(&loaded.log)
                .map_err(|e| Failure::Internal(e.to_string()))?;
            loaded.draft_version += 1;
            store.save(&loaded)?;
            Ok(Json(ConfirmOutcome::Confirmed {
                draft: draft_view(&app, &loaded)?,
            }))
        }
        Err(e) => {
            let step = app
                .engine
                .steps()
                .iter()
                .map(|(id, _)| id.clone())
                .next()
                .unwrap_or_else(|| StepId::new("concept"));
            let entry = match &e {
                EngineError::UnknownSlot { .. }
                | EngineError::InvalidDecision { .. }
                | EngineError::NothingToClear { .. } => {
                    engine_error_entry(step, slot, e.to_string())
                }
            };
            Ok(Json(ConfirmOutcome::Rejected {
                reasons: vec![entry],
                draft: draft_view(&app, &loaded)?,
            }))
        }
    }
}

/// Replace a slot's decision atomically (cascade + append in one durable
/// write). Same request/outcome shapes and idempotency rules as confirm.
async fn amend(
    State(app): State<SharedApp>,
    AxumPath(id): AxumPath<String>,
    Json(request): Json<ConfirmRequest>,
) -> Result<Json<ConfirmOutcome>, Failure> {
    let store = app.store.lock().await;
    let mut loaded = store.load(&CharacterId::new(id))?;
    if loaded.state == DocState::Finalized {
        return Err(Failure::Unprocessable(
            "character is finalized — build decisions are locked".into(),
        ));
    }
    guard_wizard_write(&app, &loaded)?;
    if loaded.log.iter().any(|d| d.id == request.decision.id) {
        return Ok(Json(ConfirmOutcome::Confirmed {
            draft: draft_view(&app, &loaded)?,
        }));
    }
    if request.version != loaded.draft_version {
        return Ok(Json(ConfirmOutcome::Conflict {
            current: draft_view(&app, &loaded)?,
        }));
    }
    let slot = request.decision.slot.clone();
    match app.engine.amend(&loaded.log, request.decision) {
        Ok(AppendOutcome::AlreadyPresent) => Ok(Json(ConfirmOutcome::Confirmed {
            draft: draft_view(&app, &loaded)?,
        })),
        Ok(AppendOutcome::Appended(new_log)) => {
            loaded.log = new_log;
            loaded.sheet = app
                .engine
                .sheet(&loaded.log)
                .map_err(|e| Failure::Internal(e.to_string()))?;
            loaded.draft_version += 1;
            store.save(&loaded)?;
            Ok(Json(ConfirmOutcome::Confirmed {
                draft: draft_view(&app, &loaded)?,
            }))
        }
        Err(e) => {
            let step = app
                .engine
                .steps()
                .first()
                .map(|(id, _)| id.clone())
                .unwrap_or_else(|| StepId::new("concept"));
            Ok(Json(ConfirmOutcome::Rejected {
                reasons: vec![engine_error_entry(step, slot, e.to_string())],
                draft: draft_view(&app, &loaded)?,
            }))
        }
    }
}

async fn clear(
    State(app): State<SharedApp>,
    AxumPath(id): AxumPath<String>,
    Json(request): Json<ClearRequest>,
) -> Result<Json<ClearOutcome>, Failure> {
    let store = app.store.lock().await;
    let mut loaded = store.load(&CharacterId::new(id))?;
    if loaded.state == DocState::Finalized {
        return Err(Failure::Unprocessable(
            "character is finalized — build decisions are locked".into(),
        ));
    }
    guard_wizard_write(&app, &loaded)?;
    if request.version != loaded.draft_version {
        return Ok(Json(ClearOutcome::Conflict {
            current: draft_view(&app, &loaded)?,
        }));
    }
    let preview = app
        .engine
        .clear_preview(&loaded.log, &request.slot)
        .map_err(|e| Failure::Unprocessable(e.to_string()))?;
    let new_log = app
        .engine
        .clear(&loaded.log, &request.slot)
        .map_err(|e| Failure::Unprocessable(e.to_string()))?;
    loaded.log = new_log;
    loaded.sheet = app
        .engine
        .sheet(&loaded.log)
        .map_err(|e| Failure::Internal(e.to_string()))?;
    loaded.draft_version += 1;
    store.save(&loaded)?;
    Ok(Json(ClearOutcome::Cleared {
        draft: draft_view(&app, &loaded)?,
        preview,
    }))
}

async fn set_step(
    State(app): State<SharedApp>,
    AxumPath(id): AxumPath<String>,
    Json(request): Json<StepRequest>,
) -> Result<Json<DraftView>, Failure> {
    let store = app.store.lock().await;
    let mut loaded = store.load(&CharacterId::new(id))?;
    if loaded.state == DocState::Finalized {
        return Err(Failure::Unprocessable("character is finalized".into()));
    }
    guard_wizard_write(&app, &loaded)?;
    // The step cursor is navigation, not a decision: last write wins and no
    // version bump (a stale-tab navigation shouldn't invalidate confirms).
    if !app.engine.steps().iter().any(|(s, _)| *s == request.step) {
        return Err(Failure::Unprocessable(format!(
            "unknown step '{}'",
            request.step
        )));
    }
    loaded.current_step = request.step;
    store.save(&loaded)?;
    Ok(Json(draft_view(&app, &loaded)?))
}

async fn finalize(
    State(app): State<SharedApp>,
    AxumPath(id): AxumPath<String>,
    Json(request): Json<FinalizeRequest>,
) -> Result<Json<FinalizeOutcome>, Failure> {
    let store = app.store.lock().await;
    let mut loaded = store.load(&CharacterId::new(id))?;
    if loaded.state == DocState::Finalized {
        return Ok(Json(FinalizeOutcome::Finalized {
            sheet: loaded.sheet.clone(),
        }));
    }
    guard_wizard_write(&app, &loaded)?;
    if request.version != loaded.draft_version {
        return Ok(Json(FinalizeOutcome::Conflict {
            current: Box::new(draft_view(&app, &loaded)?),
        }));
    }
    let projection = app
        .engine
        .project(&loaded.log)
        .map_err(|e| Failure::Internal(e.to_string()))?;
    if !projection.can_finalize {
        return Ok(Json(FinalizeOutcome::Blocked {
            reasons: projection.checklist,
        }));
    }
    loaded.state = DocState::Finalized;
    loaded.sheet = projection.sheet;
    loaded.draft_version += 1;
    store.save(&loaded)?;
    Ok(Json(FinalizeOutcome::Finalized {
        sheet: loaded.sheet.clone(),
    }))
}

// ---- Version-resolution routes ----
//
// The only paths that change a file's rules-data pin. Each loads, checks the
// submitted version (stale tabs hit the same conflict machinery as
// confirms), recomputes the status fresh, and either refuses (typed, nothing
// written) or writes exactly once through temp-file → fsync → rename.

fn refused(message: impl Into<String>, status: VersionStatus) -> VersionResolutionOutcome {
    VersionResolutionOutcome::Refused {
        message: message.into(),
        status,
    }
}

fn resolution_event(action: &str, from: &str, to: &str, note: impl Into<String>) -> VersionEvent {
    VersionEvent {
        action: action.to_string(),
        from: from.to_string(),
        to: to.to_string(),
        at_millis: clock::now_millis(),
        note: note.into(),
        superseded_values: Vec::new(),
        cleared_decisions: Vec::new(),
    }
}

/// Re-pin an older-known character whose replay is identical. The one
/// version action with no visible sheet change; still explicit, still
/// recorded in the file.
async fn version_repin(
    State(app): State<SharedApp>,
    AxumPath(id): AxumPath<String>,
    Json(request): Json<VersionActionRequest>,
) -> Result<Json<VersionResolutionOutcome>, Failure> {
    let store = app.store.lock().await;
    let mut loaded = store.load(&CharacterId::new(id))?;
    if request.version != loaded.draft_version {
        return Ok(Json(VersionResolutionOutcome::Conflict {
            character: Box::new(character_view(&app, &loaded)?),
        }));
    }
    let status = status_for(&app.engine, &app.known, &loaded);
    match &status {
        VersionStatus::OlderKnown {
            pinned,
            outcome: ReplayOutcome::Identical,
            ..
        } => {
            let from = pinned.clone();
            loaded.rules_version = app.rules_version.clone();
            loaded.keep_old = None;
            loaded.version_history.push(resolution_event(
                "re_pin",
                &from,
                &app.rules_version,
                "identical replay",
            ));
            loaded.draft_version += 1;
            store.save(&loaded)?;
            Ok(Json(VersionResolutionOutcome::Resolved {
                character: Box::new(character_view(&app, &loaded)?),
            }))
        }
        VersionStatus::OlderKnown { .. } => Ok(Json(refused(
            "re-pin applies only when the replay is identical — review the flagged differences and accept, or keep the old derivation",
            status,
        ))),
        _ => Ok(Json(refused(
            "nothing to re-pin: the character is not on an older known rules-data version",
            status,
        ))),
    }
}

/// Accept a divergent replay: re-pin, store the new sheet, and record every
/// superseded value in the file — nothing the table saw is lost. For a
/// draft this is the resolve action; decisions now illegal stay in the log
/// and reopen through the checklist's existing Illegal machinery.
async fn version_accept(
    State(app): State<SharedApp>,
    AxumPath(id): AxumPath<String>,
    Json(request): Json<VersionActionRequest>,
) -> Result<Json<VersionResolutionOutcome>, Failure> {
    let store = app.store.lock().await;
    let mut loaded = store.load(&CharacterId::new(id))?;
    if request.version != loaded.draft_version {
        return Ok(Json(VersionResolutionOutcome::Conflict {
            character: Box::new(character_view(&app, &loaded)?),
        }));
    }
    let status = status_for(&app.engine, &app.known, &loaded);
    match &status {
        VersionStatus::OlderKnown {
            pinned,
            outcome: ReplayOutcome::Divergent { differences },
            ..
        } => {
            let from = pinned.clone();
            let replayed = app
                .engine
                .sheet(&loaded.log)
                .map_err(|e| Failure::Internal(e.to_string()))?;
            let mut event = resolution_event(
                "accept",
                &from,
                &app.rules_version,
                "accepted divergent replay; superseded values recorded",
            );
            event.superseded_values = differences.clone();
            loaded.sheet = replayed;
            loaded.rules_version = app.rules_version.clone();
            loaded.keep_old = None;
            loaded.version_history.push(event);
            loaded.draft_version += 1;
            store.save(&loaded)?;
            Ok(Json(VersionResolutionOutcome::Resolved {
                character: Box::new(character_view(&app, &loaded)?),
            }))
        }
        VersionStatus::OlderKnown {
            outcome: ReplayOutcome::Identical,
            ..
        } => Ok(Json(refused(
            "the replay is identical — use re-pin, there is nothing to accept",
            status,
        ))),
        VersionStatus::OlderKnown {
            outcome:
                ReplayOutcome::ReplayError {
                    failing_decision,
                    slot,
                    ..
                },
            ..
        } => {
            let message = format!(
                "accept unavailable: the log does not replay against current data — decision '{failing_decision}' on slot '{slot}' fails. Keep the old derivation, or (for a draft) resolve to reopen the failing choices"
            );
            Ok(Json(refused(message, status)))
        }
        _ => Ok(Json(refused(
            "nothing to accept: the character is not on an older known rules-data version",
            status,
        ))),
    }
}

/// Keep the old derivation, recorded in the file: the character stays on
/// its stored sheet, un-flagged, until the shipped data version changes
/// again. Finalized characters only — a draft must resolve to continue.
async fn version_keep_old(
    State(app): State<SharedApp>,
    AxumPath(id): AxumPath<String>,
    Json(request): Json<VersionActionRequest>,
) -> Result<Json<VersionResolutionOutcome>, Failure> {
    let store = app.store.lock().await;
    let mut loaded = store.load(&CharacterId::new(id))?;
    if request.version != loaded.draft_version {
        return Ok(Json(VersionResolutionOutcome::Conflict {
            character: Box::new(character_view(&app, &loaded)?),
        }));
    }
    let status = status_for(&app.engine, &app.known, &loaded);
    match &status {
        VersionStatus::OlderKnown {
            pinned, outcome, ..
        } => {
            if loaded.state != DocState::Finalized {
                return Ok(Json(refused(
                    "keep-old applies to finalized characters; a draft cannot continue against mismatched data — resolve it instead",
                    status,
                )));
            }
            let from = pinned.clone();
            let note = match outcome {
                ReplayOutcome::Identical => "kept old derivation (replay was identical)",
                ReplayOutcome::Divergent { .. } => "kept old derivation over a divergent replay",
                ReplayOutcome::ReplayError { .. } => {
                    "kept old derivation (log does not replay against current data)"
                }
            };
            loaded.keep_old = Some(KeepOldMarker {
                pinned: from.clone(),
                evaluated_against: app.rules_version.clone(),
                at_millis: clock::now_millis(),
            });
            loaded
                .version_history
                .push(resolution_event("keep_old", &from, &from, note));
            loaded.draft_version += 1;
            store.save(&loaded)?;
            Ok(Json(VersionResolutionOutcome::Resolved {
                character: Box::new(character_view(&app, &loaded)?),
            }))
        }
        _ => Ok(Json(refused(
            "nothing to keep: the character is not on an older known rules-data version",
            status,
        ))),
    }
}

/// Resolve a draft whose log no longer replays: clear the failing decision
/// and everything the existing cascade takes with it (repeating until the
/// log folds), re-pin, and record the cleared decisions verbatim. The
/// reopened slots land on the checklist like any cleared slot; the client
/// shows `would_reopen` from the flag as the confirmation before calling.
async fn version_resolve_errors(
    State(app): State<SharedApp>,
    AxumPath(id): AxumPath<String>,
    Json(request): Json<VersionActionRequest>,
) -> Result<Json<VersionResolutionOutcome>, Failure> {
    let store = app.store.lock().await;
    let mut loaded = store.load(&CharacterId::new(id))?;
    if request.version != loaded.draft_version {
        return Ok(Json(VersionResolutionOutcome::Conflict {
            character: Box::new(character_view(&app, &loaded)?),
        }));
    }
    let status = status_for(&app.engine, &app.known, &loaded);
    match &status {
        VersionStatus::OlderKnown {
            pinned,
            outcome: ReplayOutcome::ReplayError { .. },
            ..
        } if loaded.state == DocState::Draft => {
            let from = pinned.clone();
            let repair = repair_replay(&app.engine, &loaded.log);
            let sheet = app
                .engine
                .sheet(&repair.log)
                .map_err(|e| Failure::Internal(format!("repaired log must fold: {e}")))?;
            let mut event = resolution_event(
                "resolve_replay_error",
                &from,
                &app.rules_version,
                format!(
                    "log no longer replayed; {} decision(s) cleared and reopened",
                    repair.cleared_decisions.len()
                ),
            );
            event.cleared_decisions = repair.cleared_decisions;
            loaded.log = repair.log;
            loaded.sheet = sheet;
            loaded.rules_version = app.rules_version.clone();
            loaded.keep_old = None;
            loaded.version_history.push(event);
            loaded.draft_version += 1;
            store.save(&loaded)?;
            Ok(Json(VersionResolutionOutcome::Resolved {
                character: Box::new(character_view(&app, &loaded)?),
            }))
        }
        _ => Ok(Json(refused(
            "resolve-errors applies only to a draft on an older known version whose log fails to replay",
            status,
        ))),
    }
}
