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
    FinalizeOutcome, FinalizeRequest, RosterCharacterState, RosterEntry, RosterProblem, RosterView,
    Selection, SlotId, StepId, StepRequest,
};

use crate::persistence::{DocState, Loaded, Store, StoreError};

pub(crate) struct App {
    pub engine: Pf2eEngine,
    pub store: Mutex<Store>,
    pub rules_version: String,
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
        .with_state(app)
}

enum Failure {
    NotFound(String),
    Unprocessable(String),
    Internal(String),
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
    })
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
    Ok(Json(match loaded.state {
        DocState::Draft => CharacterView::Draft(draft_view(&app, &loaded)?),
        DocState::Finalized => CharacterView::Finalized {
            id: loaded.id.clone(),
            sheet: loaded.sheet.clone(),
        },
    }))
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
    if request.version != loaded.draft_version {
        return Ok(Json(FinalizeOutcome::Conflict {
            current: draft_view(&app, &loaded)?,
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
