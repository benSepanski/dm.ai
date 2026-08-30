//! HTTP routes. The server is the authority: every write re-validates and
//! re-derives natively; responses are view types from `types`, never
//! storage documents.

use std::collections::BTreeMap;
use std::path::PathBuf;
use std::sync::Arc;

use axum::extract::{Path as AxumPath, State};
use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use axum::routing::{get, post};
use axum::{Json, Router};
use engine_core::{AppendOutcome, EngineError, Sampler, SlotSuggestion, SuggestionContext};
use ruleset_pf2e::Pf2eEngine;
use tokio::sync::Mutex;
use types::{
    ApiError, CharacterId, CharacterView, ChecklistEntry, ChecklistSeverity, ClassOption,
    ClearOutcome, ClearRequest, CloneRequest, CloneResult, ConfirmOutcome, ConfirmRequest,
    CreateCharacterRequest, Decision, DecisionId, DecisionInput, DecisionSource, DraftView,
    FillRemainingOutcome, FillRemainingRequest, FinalizeOutcome, FinalizeRequest,
    QuickBuildRequest, QuickBuildResult, RandomMintRequest, ReplayOutcome, RosterCharacterState,
    RosterEntry, RosterProblem, RosterView, Selection, SlotId, StepId, StepRequest,
    VersionActionRequest, VersionFlaggedError, VersionResolutionOutcome, VersionStatus,
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
    /// Per-class suggested builds (class record ID → slot → suggestion),
    /// resolved from the class records' suggested_build blocks at startup.
    pub suggested: Vec<(String, BTreeMap<SlotId, SlotSuggestion>)>,
    /// The random-name pools file (app data, not rules content). Read at
    /// mint time so editing it is a data change, not a rebuild; a
    /// malformed file fails the mint, never the server.
    pub name_pools: PathBuf,
}

pub(crate) type SharedApp = Arc<App>;

pub(crate) fn router(app: SharedApp) -> Router {
    Router::new()
        .route("/api/roster", get(roster))
        .route("/api/characters", post(create_character))
        .route("/api/characters/quick-build", post(quick_build))
        .route("/api/characters/random-mint", post(random_mint))
        .route("/api/characters/clone", post(clone_character))
        .route("/api/characters/{id}/fill-remaining", post(fill_remaining))
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
        classes: class_catalog(&app)?,
    }))
}

/// The shipped classes, for the random-mint picker: the class slot's
/// available options against an empty log (a projection query — the
/// engine stays the only authority on what is offered).
fn class_catalog(app: &App) -> Result<Vec<ClassOption>, Failure> {
    let projection = app
        .engine
        .project(&[])
        .map_err(|e| Failure::Internal(e.to_string()))?;
    Ok(projection
        .steps
        .iter()
        .flat_map(|s| s.slots.iter())
        .filter(|slot| slot.id.as_str() == ruleset_pf2e::CLASS_SLOT_ID)
        .flat_map(|slot| slot.options.iter())
        .filter(|o| o.available)
        .map(|o| ClassOption {
            id: o.id.as_str().to_string(),
            name: o.label.clone(),
        })
        .collect())
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

// ---- Quick-build routes (spec req 7) ----
//
// The planner runs server-side over the same engine (the WASM engine
// previews, the server decides); each route is one engine transaction and
// one temp-file → fsync → rename write. Both are wizard writes for every
// guard, including the version flag.

/// Character IDs minted by quick-build derive from the client's request ID,
/// so the file's existence IS the durable idempotency marker: a re-tap
/// after a crash between save and ack loads the same file, returns the
/// saved result, and appends nothing.
const QUICK_BUILD_ID_PREFIX: &str = "c-qb-";

/// Request IDs become filename stems and decision-ID prefixes; keep them to
/// a safe shape (client generates UUIDs).
fn valid_request_id(id: &str) -> bool {
    !id.is_empty()
        && id.len() <= 64
        && id
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || c == '-' || c == '_')
}

/// The suggested build that applies to this log: the chosen class's block
/// when the log names a class, else the first class shipping one.
fn suggestion_map<'a>(
    app: &'a App,
    log: &[Decision],
) -> Option<&'a BTreeMap<SlotId, SlotSuggestion>> {
    let chosen_class = log
        .iter()
        .rev()
        .find(|d| d.slot.as_str() == ruleset_pf2e::CLASS_SLOT_ID)
        .and_then(|d| match &d.selection {
            Selection::Option(id) => Some(id.as_str().to_string()),
            _ => None,
        });
    match chosen_class {
        Some(class_id) => app
            .suggested
            .iter()
            .find(|(id, _)| *id == class_id)
            .map(|(_, map)| map),
        None => app.suggested.first().map(|(_, map)| map),
    }
}

/// Deterministic decision IDs for one expansion: `{request_id}.{slot}` —
/// hand-inspectable, and a replayed request re-mints the same IDs so the
/// engine's decision-ID idempotency also covers partial retries.
fn suggestion_decision_id(request_id: &str, slot: &SlotId) -> DecisionId {
    DecisionId::new(format!("{request_id}.{slot}"))
}

async fn quick_build(
    State(app): State<SharedApp>,
    Json(request): Json<QuickBuildRequest>,
) -> Result<Json<QuickBuildResult>, Failure> {
    if !valid_request_id(&request.request_id) {
        return Err(Failure::Unprocessable(
            "quick-build needs a request_id of 1-64 letters, digits, '-' or '_' \
             (it makes the request safely retryable)"
                .into(),
        ));
    }
    let store = app.store.lock().await;
    let id = CharacterId::new(format!("{QUICK_BUILD_ID_PREFIX}{}", request.request_id));
    let suggest_owned;
    // Replay: the file already exists — return the saved result, append
    // nothing (crash-between-save-and-ack contract).
    if let Ok(loaded) = store.load(&id) {
        if loaded.state == DocState::Finalized {
            return Err(Failure::Unprocessable(
                "this quick-build request was already completed and finalized".into(),
            ));
        }
        guard_wizard_write(&app, &loaded)?;
        let Some(suggest) = suggestion_map(&app, &loaded.log) else {
            return Err(Failure::Unprocessable(
                "no shipped class carries a suggested build".into(),
            ));
        };
        let unresolved = app
            .engine
            .unresolved_suggestions(
                &loaded.log,
                &mut |ctx: &SuggestionContext| suggest.get(ctx.slot).cloned(),
                DecisionSource::Suggested,
            )
            .map_err(|e| Failure::Internal(e.to_string()))?;
        return Ok(Json(QuickBuildResult {
            draft: draft_view(&app, &loaded)?,
            unresolved,
        }));
    }
    // Fresh build: seed the optional name as a player decision (the planner
    // never overwrites it), expand, and write exactly once.
    let mut log = Vec::new();
    if let Some(name) = request.name.as_ref().filter(|n| !n.trim().is_empty()) {
        let input = DecisionInput {
            id: DecisionId::new(format!("{}.initial-name", request.request_id)),
            slot: SlotId::new("pf2e.details.name"),
            selection: Selection::Text(name.clone()),
            source: DecisionSource::Player,
        };
        if let Ok(AppendOutcome::Appended(new_log)) = app.engine.append(&log, input) {
            log = new_log;
        }
    }
    {
        let Some(suggest) = suggestion_map(&app, &log) else {
            return Err(Failure::Unprocessable(
                "no shipped class carries a suggested build".into(),
            ));
        };
        suggest_owned = suggest.clone();
    }
    let request_id = request.request_id.clone();
    let plan = app
        .engine
        .expand_suggestions(
            &log,
            &mut |ctx: &SuggestionContext| suggest_owned.get(ctx.slot).cloned(),
            &|slot| suggestion_decision_id(&request_id, slot),
            DecisionSource::Suggested,
        )
        .map_err(|e| Failure::Internal(e.to_string()))?;
    let sheet = app
        .engine
        .sheet(&plan.log)
        .map_err(|e| Failure::Internal(e.to_string()))?;
    let loaded = Loaded {
        id,
        state: DocState::Draft,
        // Review state: resume lands on the final step, where the player
        // confirms the name and finalizes.
        current_step: app
            .engine
            .steps()
            .last()
            .map(|(id, _)| id.clone())
            .unwrap_or_else(|| StepId::new("concept")),
        draft_version: 1,
        sheet,
        log: plan.log,
        rules_version: app.rules_version.clone(),
        version_history: Vec::new(),
        keep_old: None,
    };
    store.save(&loaded)?;
    Ok(Json(QuickBuildResult {
        draft: draft_view(&app, &loaded)?,
        unresolved: plan.unresolved,
    }))
}

async fn fill_remaining(
    State(app): State<SharedApp>,
    AxumPath(id): AxumPath<String>,
    Json(request): Json<FillRemainingRequest>,
) -> Result<Json<FillRemainingOutcome>, Failure> {
    if !valid_request_id(&request.request_id) {
        return Err(Failure::Unprocessable(
            "fill-remaining needs a request_id of 1-64 letters, digits, '-' or '_' \
             (it makes the request safely retryable)"
                .into(),
        ));
    }
    let store = app.store.lock().await;
    let mut loaded = store.load(&CharacterId::new(id))?;
    if loaded.state == DocState::Finalized {
        return Err(Failure::Unprocessable(
            "character is finalized — build decisions are locked".into(),
        ));
    }
    guard_wizard_write(&app, &loaded)?;
    let Some(suggest) = suggestion_map(&app, &loaded.log).cloned() else {
        return Err(Failure::Unprocessable(
            "the chosen class carries no suggested build".into(),
        ));
    };
    let mut suggest_fn = |ctx: &SuggestionContext| suggest.get(ctx.slot).cloned();
    // Idempotency first (like confirm): a decision minted by this request
    // ID already in the log means the expansion committed — return the
    // saved state, append nothing, even under a now-stale version.
    let marker = format!("{}.", request.request_id);
    if loaded
        .log
        .iter()
        .any(|d| d.id.as_str().starts_with(&marker))
    {
        let unresolved = app
            .engine
            .unresolved_suggestions(&loaded.log, &mut suggest_fn, DecisionSource::Suggested)
            .map_err(|e| Failure::Internal(e.to_string()))?;
        return Ok(Json(FillRemainingOutcome::Filled {
            draft: draft_view(&app, &loaded)?,
            unresolved,
        }));
    }
    if request.version != loaded.draft_version {
        return Ok(Json(FillRemainingOutcome::Conflict {
            current: draft_view(&app, &loaded)?,
        }));
    }
    let request_id = request.request_id.clone();
    let plan = app
        .engine
        .expand_suggestions(
            &loaded.log,
            &mut suggest_fn,
            &|slot| suggestion_decision_id(&request_id, slot),
            DecisionSource::Suggested,
        )
        .map_err(|e| Failure::Internal(e.to_string()))?;
    if !plan.appended.is_empty() {
        loaded.log = plan.log;
        loaded.sheet = app
            .engine
            .sheet(&loaded.log)
            .map_err(|e| Failure::Internal(e.to_string()))?;
        loaded.draft_version += 1;
        store.save(&loaded)?;
    }
    Ok(Json(FillRemainingOutcome::Filled {
        draft: draft_view(&app, &loaded)?,
        unresolved: plan.unresolved,
    }))
}

// ---- Random mint & clone (roster-ergonomics spec reqs 1-5) ----
//
// Both follow the quick-build shape: the character ID derives from the
// client request ID under a per-route prefix, so the file's existence is
// the durable idempotency marker; each is one engine transaction and one
// crash-safe write; any failure writes nothing.

const RANDOM_MINT_ID_PREFIX: &str = "c-rn-";
const CLONE_ID_PREFIX: &str = "c-cl-";

/// Free-text lore topics for slots that ask the player to name a Lore
/// skill. Own-authored app vocabulary, not rules content.
const LORE_TOPICS: &[&str] = &[
    "Farming Lore",
    "Fishing Lore",
    "Milling Lore",
    "Tanning Lore",
    "Caravan Lore",
    "Brewing Lore",
    "Stonework Lore",
    "Herbalism Lore",
];

/// The name-pools document (`app-data/name-pools.json`).
#[derive(serde::Deserialize)]
struct NamePools {
    default: Vec<String>,
    #[serde(default)]
    pools: BTreeMap<String, Vec<String>>,
}

/// Read and parse the pools file at mint time. A malformed (or missing)
/// file is a typed mint failure naming the file — never a crash, and the
/// mint writes nothing.
fn load_name_pools(app: &App) -> Result<NamePools, Failure> {
    let path = &app.name_pools;
    let text = std::fs::read_to_string(path).map_err(|e| {
        Failure::Unprocessable(format!(
            "the name-pools file '{}' could not be read ({e}) — random minting \
             needs it; nothing was created",
            path.display()
        ))
    })?;
    serde_json::from_str(&text).map_err(|e| {
        Failure::Unprocessable(format!(
            "the name-pools file '{}' is malformed ({e}) — fix it and mint \
             again; nothing was created",
            path.display()
        ))
    })
}

impl NamePools {
    /// The pool for an ancestry record ID; a missing or empty pool falls
    /// back to the default pool (which the data lint keeps non-empty).
    fn for_ancestry(&self, ancestry: Option<&str>) -> &[String] {
        ancestry
            .and_then(|a| self.pools.get(a))
            .filter(|p| !p.is_empty())
            .map_or(&self.default[..], |p| &p[..])
    }
}

/// The ancestry record ID chosen in a log, if any.
fn chosen_ancestry(log: &[Decision]) -> Option<String> {
    log.iter()
        .rev()
        .find(|d| d.slot.as_str() == ruleset_pf2e::ANCESTRY_SLOT_ID)
        .and_then(|d| match &d.selection {
            Selection::Option(id) => Some(id.as_str().to_string()),
            _ => None,
        })
}

async fn random_mint(
    State(app): State<SharedApp>,
    Json(request): Json<RandomMintRequest>,
) -> Result<Json<QuickBuildResult>, Failure> {
    if !valid_request_id(&request.request_id) {
        return Err(Failure::Unprocessable(
            "random-mint needs a request_id of 1-64 letters, digits, '-' or '_' \
             (it makes the request safely retryable)"
                .into(),
        ));
    }
    let store = app.store.lock().await;
    let id = CharacterId::new(format!("{RANDOM_MINT_ID_PREFIX}{}", request.request_id));
    // Replay: the file already exists — return the saved result, append
    // nothing (crash-between-save-and-ack contract; a changed class or
    // name in the retried request is ignored — first write wins).
    if let Ok(loaded) = store.load(&id) {
        if loaded.state == DocState::Finalized {
            return Err(Failure::Unprocessable(
                "this random-mint request was already completed and finalized".into(),
            ));
        }
        guard_wizard_write(&app, &loaded)?;
        return Ok(Json(QuickBuildResult {
            draft: draft_view(&app, &loaded)?,
            unresolved: Vec::new(),
        }));
    }
    // Everything that can refuse does so before any write: pools first
    // (spec: a malformed pool file fails the mint, nothing written).
    let pools = load_name_pools(&app)?;
    // The request ID is the entropy: same request, same character —
    // deterministic, reproducible, replay-safe.
    let mut sampler = Sampler::from_key(&request.request_id);
    let catalog = class_catalog(&app)?;
    let (class_id, class_source) = match &request.class_id {
        Some(wanted) => {
            if !catalog.iter().any(|c| c.id == *wanted) {
                return Err(Failure::Unprocessable(format!(
                    "unknown class '{wanted}' — the shipped classes are: {}",
                    catalog
                        .iter()
                        .map(|c| c.id.as_str())
                        .collect::<Vec<_>>()
                        .join(", ")
                )));
            }
            // The player picked the class; the provenance says so.
            (wanted.clone(), DecisionSource::Player)
        }
        None => match sampler.pick(&catalog) {
            Some(class) => (class.id.clone(), DecisionSource::Random),
            None => {
                return Err(Failure::Internal(
                    "no classes are shipped — cannot mint".into(),
                ))
            }
        },
    };
    let mut log = Vec::new();
    // A typed name is a player decision the generator never overwrites —
    // same contract as quick build.
    if let Some(name) = request.name.as_ref().filter(|n| !n.trim().is_empty()) {
        let input = DecisionInput {
            id: DecisionId::new(format!("{}.initial-name", request.request_id)),
            slot: SlotId::new(ruleset_pf2e::NAME_SLOT_ID),
            selection: Selection::Text(name.clone()),
            source: DecisionSource::Player,
        };
        if let Ok(AppendOutcome::Appended(new_log)) = app.engine.append(&log, input) {
            log = new_log;
        }
    }
    let class_input = DecisionInput {
        id: DecisionId::new(format!("{}.class-pick", request.request_id)),
        slot: SlotId::new(ruleset_pf2e::CLASS_SLOT_ID),
        selection: Selection::Option(types::OptionId::new(class_id)),
        source: class_source,
    };
    match app.engine.append(&log, class_input) {
        Ok(AppendOutcome::Appended(new_log)) => log = new_log,
        Ok(AppendOutcome::AlreadyPresent) => {}
        Err(e) => {
            return Err(Failure::Internal(format!(
                "the class decision did not apply: {e}"
            )))
        }
    }
    // The random suggestion source: every option slot gets a fresh shuffle
    // of its LEGAL options (the mint path's legality filter — the Sampler
    // itself filters nothing); required free-text slots get a sampled lore
    // topic; the name slot is left for the pool step below, where the
    // sampled ancestry is known.
    let request_id = request.request_id.clone();
    let plan = {
        let sampler = &mut sampler;
        let mut random_source = |ctx: &SuggestionContext| -> Option<SlotSuggestion> {
            if ctx.slot.as_str() == ruleset_pf2e::NAME_SLOT_ID {
                return None;
            }
            match ctx.kind {
                types::SlotViewKind::Text { .. } => {
                    let topic = sampler.pick(LORE_TOPICS)?;
                    Some(SlotSuggestion::Text((*topic).to_string()))
                }
                _ => {
                    let legal: Vec<types::OptionId> = ctx
                        .options
                        .iter()
                        .filter(|o| o.available)
                        .map(|o| o.id.clone())
                        .collect();
                    if legal.is_empty() {
                        return None;
                    }
                    Some(SlotSuggestion::Candidates(sampler.shuffled(&legal)))
                }
            }
        };
        let mut plan = app
            .engine
            .expand_suggestions(
                &log,
                &mut random_source,
                &|slot| suggestion_decision_id(&request_id, slot),
                DecisionSource::Random,
            )
            .map_err(|e| Failure::Internal(e.to_string()))?;
        // Two situations leave a flagged slot behind: a sampled pick can
        // grow a later count (boosting Intelligence raises the language
        // and trained-skill counts) after those slots were filled, and a
        // set-level validator can flag a confirmed selection (the
        // Wizard's curriculum floor judges at the checklist, not at
        // append). The planner never overwrites, so re-open OUR OWN
        // generated decisions that got flagged and resample them at the
        // settled counts. Bounded; player decisions are never touched.
        for _ in 0..8 {
            let projection = app
                .engine
                .project(&plan.log)
                .map_err(|e| Failure::Internal(e.to_string()))?;
            let incomplete: Vec<SlotId> = projection
                .checklist
                .iter()
                .map(|e| e.slot.clone())
                .filter(|slot| {
                    plan.log
                        .iter()
                        .any(|d| d.slot == *slot && d.source == DecisionSource::Random)
                })
                .collect();
            if incomplete.is_empty() {
                break;
            }
            let mut cleared = plan.log.clone();
            for slot in &incomplete {
                if let Ok(new_log) = app.engine.clear(&cleared, slot) {
                    cleared = new_log;
                }
            }
            plan = app
                .engine
                .expand_suggestions(
                    &cleared,
                    &mut random_source,
                    &|slot| suggestion_decision_id(&request_id, slot),
                    DecisionSource::Random,
                )
                .map_err(|e| Failure::Internal(e.to_string()))?;
        }
        plan
    };
    log = plan.log;
    // Name the character from the sampled ancestry's pool (typed names
    // already occupy the slot and stand).
    if !log
        .iter()
        .any(|d| d.slot.as_str() == ruleset_pf2e::NAME_SLOT_ID)
    {
        let ancestry = chosen_ancestry(&log);
        let pool = pools.for_ancestry(ancestry.as_deref());
        let Some(name) = sampler.pick(pool) else {
            return Err(Failure::Unprocessable(format!(
                "the name-pools file '{}' has an empty default pool — random \
                 minting needs at least one name; nothing was created",
                app.name_pools.display()
            )));
        };
        let input = DecisionInput {
            id: DecisionId::new(format!("{}.random-name", request.request_id)),
            slot: SlotId::new(ruleset_pf2e::NAME_SLOT_ID),
            selection: Selection::Text(name.clone()),
            source: DecisionSource::Random,
        };
        match app.engine.append(&log, input) {
            Ok(AppendOutcome::Appended(new_log)) => log = new_log,
            Ok(AppendOutcome::AlreadyPresent) => {}
            Err(e) => {
                return Err(Failure::Internal(format!(
                    "the sampled name did not apply: {e}"
                )))
            }
        }
    }
    let sheet = app
        .engine
        .sheet(&log)
        .map_err(|e| Failure::Internal(e.to_string()))?;
    // Unresolved is expected empty over shipped data; recomputed here so
    // future data reports honestly (same surface as quick build).
    let unresolved = app
        .engine
        .unresolved_suggestions(
            &log,
            &mut |_ctx: &SuggestionContext| None,
            DecisionSource::Random,
        )
        .map_err(|e| Failure::Internal(e.to_string()))?
        .into_iter()
        .map(|mut u| {
            u.reason = "the random mint could not fill this slot — finish it in the wizard".into();
            u
        })
        .collect();
    let loaded = Loaded {
        id,
        state: DocState::Draft,
        // Review state: resume lands on the final step, like quick build.
        current_step: app
            .engine
            .steps()
            .last()
            .map(|(id, _)| id.clone())
            .unwrap_or_else(|| StepId::new("concept")),
        draft_version: 1,
        sheet,
        log,
        rules_version: app.rules_version.clone(),
        version_history: Vec::new(),
        keep_old: None,
    };
    store.save(&loaded)?;
    Ok(Json(QuickBuildResult {
        draft: draft_view(&app, &loaded)?,
        unresolved,
    }))
}

async fn clone_character(
    State(app): State<SharedApp>,
    Json(request): Json<CloneRequest>,
) -> Result<Json<CloneResult>, Failure> {
    if !valid_request_id(&request.request_id) {
        return Err(Failure::Unprocessable(
            "clone needs a request_id of 1-64 letters, digits, '-' or '_' \
             (it makes the request safely retryable)"
                .into(),
        ));
    }
    let new_name = request.name.trim().to_string();
    if new_name.is_empty() || new_name.len() > 200 {
        return Err(Failure::Unprocessable(
            "the clone needs a name (1-200 characters)".into(),
        ));
    }
    let store = app.store.lock().await;
    let id = CharacterId::new(format!("{CLONE_ID_PREFIX}{}", request.request_id));
    // Replay: already created — return it, ignore the retried parameters
    // (first write wins).
    if let Ok(existing) = store.load(&id) {
        return Ok(Json(CloneResult {
            id: existing.id.clone(),
            name: display_name(&existing),
            finalized: existing.state == DocState::Finalized,
        }));
    }
    // A trashed source is NotFound; a quarantined one refuses typed —
    // either way nothing is written.
    let source = match store.load(&request.source_id) {
        Ok(source) => source,
        Err(StoreError::Storage(message)) => {
            return Err(Failure::Unprocessable(format!(
                "'{}' cannot be cloned — its file is quarantined ({message}); \
                 nothing was created",
                request.source_id
            )))
        }
        Err(e) => return Err(e.into()),
    };
    let status = status_for(&app.engine, &app.known, &source);
    if let VersionStatus::Unknown { pinned, .. } = &status {
        return Err(Failure::Unprocessable(format!(
            "'{}' is pinned to rules-data version '{pinned}', which this \
             server does not know — it cannot be replayed, so it cannot be \
             cloned; nothing was created",
            display_name(&source)
        )));
    }
    // A current-pin source must replay to its stored sheet — clones are
    // born verify-clean, and a tampered source refuses instead of
    // propagating. (An older-known pin cannot be replayed under today's
    // data; its stored sheet is copied verbatim and the established
    // version flag meets the clone on first open, exactly as it would the
    // source.)
    let current_pin = source.rules_version == app.rules_version;
    if current_pin {
        let replayed = app
            .engine
            .sheet(&source.log)
            .map_err(|e| Failure::Unprocessable(format!(
                "'{}' does not replay cleanly ({e}) — run `verify`; nothing \
                 was created",
                display_name(&source)
            )))?;
        if replayed != source.sheet {
            return Err(Failure::Unprocessable(format!(
                "'{}' diverges from its decision log — run `verify` and \
                 resolve it before cloning; nothing was created",
                display_name(&source)
            )));
        }
    }
    // The clone's log: the source's, verbatim, except the name decision —
    // re-minted with clone provenance and the clone-time name (appended
    // when the source never named itself).
    let name_decision_at = source
        .log
        .iter()
        .rposition(|d| d.slot.as_str() == ruleset_pf2e::NAME_SLOT_ID);
    let mut log = source.log.clone();
    let minted = |order: u32| Decision {
        id: DecisionId::new(format!("{}.clone-name", request.request_id)),
        slot: SlotId::new(ruleset_pf2e::NAME_SLOT_ID),
        selection: Selection::Text(new_name.clone()),
        source: DecisionSource::Clone,
        order,
    };
    match name_decision_at {
        Some(at) => log[at] = minted(log[at].order),
        None => {
            let order = log.len() as u32;
            log.push(minted(order));
        }
    }
    // The sheet: re-derived by replay for a current pin; for an
    // older-known pin, the stored sheet with the one field the changed
    // decision projects (the name) updated.
    let sheet = if current_pin {
        app.engine
            .sheet(&log)
            .map_err(|e| Failure::Internal(format!("the cloned log does not replay: {e}")))?
    } else {
        let mut sheet = source.sheet.clone();
        sheet.name = new_name.clone();
        sheet
    };
    let loaded = Loaded {
        id,
        state: source.state,
        current_step: source.current_step.clone(),
        draft_version: source.draft_version,
        sheet,
        log,
        rules_version: source.rules_version.clone(),
        version_history: source.version_history.clone(),
        keep_old: source.keep_old.clone(),
    };
    store.save(&loaded)?;
    Ok(Json(CloneResult {
        id: loaded.id.clone(),
        name: display_name(&loaded),
        finalized: loaded.state == DocState::Finalized,
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
