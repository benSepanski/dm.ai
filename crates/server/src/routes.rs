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
use engine_core::{
    AppendOutcome, EngineError, EngineOps, Ruleset, Sampler, SlotSuggestion, SuggestionContext,
};
use tokio::sync::Mutex;
use types::{
    AbandonLevelOutcome, AbandonLevelRequest, ApiError, CampaignView, CharacterId, CharacterView,
    ChecklistEntry, ChecklistSeverity, ClassOption, ClearOutcome, ClearRequest, CloneRequest,
    CloneResult, ConfirmOutcome, ConfirmRequest, CreateCharacterRequest, Decision, DecisionId,
    DecisionInput, DecisionSource, DeclareCampaignRequest, DraftView, FillRemainingOutcome,
    FillRemainingRequest, FinalizeOutcome, FinalizeRequest, GameOption, LevelUpOutcome,
    LevelUpRequest, LevelUpView, QuickBuildRequest, QuickBuildResult, RandomMintRequest,
    ReplayOutcome, RosterCharacterState, RosterEntry, RosterProblem, RosterView, Selection, SlotId,
    StepId, StepRequest, VersionActionRequest, VersionFlaggedError, VersionResolutionOutcome,
    VersionStatus,
};

use crate::clock;
use crate::persistence::{DocState, KeepOldMarker, Loaded, Store, StoreError, VersionEvent};
use crate::version::{repair_replay, sheet_diffs, status_for, KnownVersions};

pub(crate) struct App {
    /// Every shipped ruleset; the campaign's declaration selects one.
    pub rulesets: Vec<Arc<dyn Ruleset>>,
    /// Per-ruleset known-version sets, keyed by system id.
    pub known: BTreeMap<String, KnownVersions>,
    pub store: Mutex<Store>,
    /// The random-name pools file (app data, not rules content). Read at
    /// mint time so editing it is a data change, not a rebuild; a
    /// malformed file fails the mint, never the server.
    pub name_pools: PathBuf,
}

/// The ruleset a campaign plays, resolved per request under the store
/// lock: the declared system's ruleset and its known-version set.
pub(crate) struct Ctx<'a> {
    pub rs: &'a dyn Ruleset,
    pub known: &'a KnownVersions,
    pub name_pools: &'a std::path::Path,
}

impl App {
    pub fn ruleset_for(&self, system: &str) -> Option<&Arc<dyn Ruleset>> {
        self.rulesets.iter().find(|r| r.system() == system)
    }

    /// Resolve the campaign's ruleset; an undeclared campaign refuses
    /// every character route, typed.
    pub fn ctx(&self, store: &Store) -> Result<Ctx<'_>, Failure> {
        let system = store.system().ok_or_else(|| {
            Failure::Unprocessable(
                "this campaign has not chosen its game yet — declare it first".into(),
            )
        })?;
        let rs = self.ruleset_for(system).ok_or_else(|| {
            Failure::Unprocessable(format!(
                "this campaign is declared for '{system}', which this build does not ship"
            ))
        })?;
        let known = self
            .known
            .get(system)
            .ok_or_else(|| Failure::Internal(format!("no known-version set for '{system}'")))?;
        Ok(Ctx {
            rs: rs.as_ref(),
            known,
            name_pools: &self.name_pools,
        })
    }

    /// Every shipped ruleset's license paragraphs — attribution follows
    /// the binary, never the open campaign.
    pub fn license_lines(&self) -> Vec<String> {
        self.rulesets
            .iter()
            .flat_map(|r| r.license_lines())
            .collect()
    }
}

pub(crate) type SharedApp = Arc<App>;

pub(crate) fn router(app: SharedApp) -> Router {
    Router::new()
        .route("/api/campaign", get(campaign).post(declare_campaign))
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
        .route("/api/characters/{id}/level-up", post(level_up))
        .route("/api/characters/{id}/level-up/abandon", post(abandon_level))
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

pub(crate) enum Failure {
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
            StoreError::Refused(message) => Failure::Unprocessable(message),
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

/// The steps live for a log (creation steps while creating, the pending
/// level's step while leveling) — the only step list any client sees.
fn live_steps(engine: &dyn EngineOps, log: &[Decision]) -> Vec<(StepId, String)> {
    engine.live_steps(log).unwrap_or_default()
}

fn first_live_step(engine: &dyn EngineOps, log: &[Decision]) -> StepId {
    live_steps(engine, log)
        .first()
        .map(|(id, _)| id.clone())
        .unwrap_or_else(|| StepId::new("concept"))
}

fn step_index(engine: &dyn EngineOps, log: &[Decision], step: &StepId) -> usize {
    live_steps(engine, log)
        .iter()
        .position(|(id, _)| id == step)
        .unwrap_or(0)
}

fn draft_view(cx: &Ctx, loaded: &Loaded) -> Result<DraftView, Failure> {
    let projection = cx
        .rs
        .engine()
        .project(&loaded.log)
        .map_err(|e| Failure::Internal(format!("stored log does not replay: {e}")))?;
    let level_up = if loaded.has_pending_tail() {
        Some(level_up_view(cx, loaded)?)
    } else {
        None
    };
    Ok(DraftView {
        id: loaded.id.clone(),
        version: loaded.draft_version,
        current_step: loaded.current_step.clone(),
        projection,
        rules_version: loaded.rules_version.clone(),
        // Only current drafts are projected; flagged drafts arrive as
        // CharacterView::FlaggedDraft instead.
        version_status: VersionStatus::Current,
        level_up,
    })
}

/// The pending level's derived companions (spec req 4): gains are the
/// finalized sheet vs the fold through the advance decision alone; deltas
/// are the finalized sheet vs the fold through the whole tail; pending is
/// the tail described for the abandon dialog. Nothing hand-authored.
fn level_up_view(cx: &Ctx, loaded: &Loaded) -> Result<LevelUpView, Failure> {
    let prefix = loaded.finalized_prefix();
    let tail = loaded.pending_tail();
    let level = cx
        .rs
        .level_of(&loaded.log)
        .map_err(|e| Failure::Internal(e.to_string()))?;
    let advanced: Vec<Decision> = prefix.iter().chain(tail.iter().take(1)).cloned().collect();
    let advance_sheet = cx
        .rs
        .engine()
        .sheet(&advanced)
        .map_err(|e| Failure::Internal(e.to_string()))?;
    let full_sheet = cx
        .rs
        .engine()
        .sheet(&loaded.log)
        .map_err(|e| Failure::Internal(e.to_string()))?;
    Ok(LevelUpView {
        level,
        gains: sheet_diffs(&loaded.sheet, &advance_sheet),
        deltas: sheet_diffs(&loaded.sheet, &full_sheet),
        pending: tail
            .iter()
            .filter_map(|d| cx.rs.engine().describe_decision(d))
            .collect(),
    })
}

/// The level a finalized character can advance to, when its pin is
/// current and the class's advancement table has more (the cap is data).
fn next_level_for(cx: &Ctx, loaded: &Loaded, status: &VersionStatus) -> Option<u32> {
    if *status != VersionStatus::Current || loaded.state != DocState::Finalized {
        return None;
    }
    cx.rs.next_level(loaded.finalized_prefix()).ok()?
}

/// The full character view, version flag included. A draft with an
/// unresolved non-current pin gets no projection (that would replay the old
/// log against new data outside the resolution flow) — its stored sheet and
/// flag arrive as `FlaggedDraft`.
fn character_view(cx: &Ctx, loaded: &Loaded) -> Result<CharacterView, Failure> {
    let status = status_for(cx.rs.engine(), cx.known, loaded);
    Ok(match loaded.state {
        // A pending level rides beside the still-authoritative sheet; the
        // pin is current by construction (the level started under it and
        // a flagged character cannot resume until resolved).
        DocState::Finalized if loaded.has_pending_tail() && status == VersionStatus::Current => {
            CharacterView::Leveling {
                id: loaded.id.clone(),
                sheet: loaded.sheet.clone(),
                draft: draft_view(cx, loaded)?,
            }
        }
        DocState::Finalized => CharacterView::Finalized {
            id: loaded.id.clone(),
            sheet: loaded.sheet.clone(),
            next_level: next_level_for(cx, loaded, &status),
            version_status: status,
            version: loaded.draft_version,
        },
        DocState::Draft if status == VersionStatus::Current => {
            CharacterView::Draft(draft_view(cx, loaded)?)
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
fn guard_wizard_write(cx: &Ctx, loaded: &Loaded) -> Result<(), Failure> {
    if (loaded.state == DocState::Draft || loaded.has_pending_tail())
        && loaded.rules_version != cx.rs.rules_version()
    {
        return Err(Failure::VersionFlagged(Box::new(status_for(
            cx.rs.engine(),
            cx.known,
            loaded,
        ))));
    }
    Ok(())
}

/// Every wizard write lands on a creation draft or a pending level; a
/// finalized character with no pending level refuses, typed — and this
/// refusal precedes every idempotency shortcut, so a retried tail confirm
/// after the level finalized can never answer "confirmed".
fn guard_wizard_target(loaded: &Loaded) -> Result<(), Failure> {
    if loaded.state == DocState::Finalized && !loaded.has_pending_tail() {
        return Err(Failure::Unprocessable(
            "character is finalized — build decisions are locked (start a level-up to make \
             new ones)"
                .into(),
        ));
    }
    Ok(())
}

/// Nothing below the finalized marker ever moves: a write naming a
/// decision in the finalized prefix (directly, or through a cascade)
/// refuses, typed. The prefix invariant is asserted by `verify`; this is
/// the guard.
fn guard_below_marker(
    loaded: &Loaded,
    slots: impl IntoIterator<Item = SlotId>,
) -> Result<(), Failure> {
    for slot in slots {
        if let Some(index) = loaded.log.iter().position(|d| d.slot == slot) {
            if index < loaded.finalized_through {
                return Err(Failure::Unprocessable(format!(
                    "'{slot}' is part of the finalized character — level-up choices can't \
                     change it (editing finalized choices is a later feature)"
                )));
            }
        }
    }
    Ok(())
}

/// After a wizard write: a creation draft's stored sheet tracks its whole
/// log; a finalized character's stored sheet reflects ONLY its finalized
/// prefix — a confirm into a pending level never touches it (the prefix
/// invariant; only finalize-pending moves the sheet, with the marker).
fn refresh_draft_sheet(cx: &Ctx, loaded: &mut Loaded) -> Result<(), Failure> {
    if loaded.state == DocState::Draft {
        loaded.sheet = cx
            .rs
            .engine()
            .sheet(&loaded.log)
            .map_err(|e| Failure::Internal(e.to_string()))?;
    }
    Ok(())
}

fn resume_label(cx: &Ctx, loaded: &Loaded) -> String {
    let steps = live_steps(cx.rs.engine(), &loaded.log);
    let index = step_index(cx.rs.engine(), &loaded.log, &loaded.current_step);
    let title = steps
        .get(index)
        .map(|(_, t)| t.as_str())
        .unwrap_or("Concept");
    if loaded.has_pending_tail() {
        let level = cx.rs.level_of(&loaded.log).unwrap_or(0);
        format!(
            "level {level} — step {} of {} — {}",
            index + 1,
            steps.len(),
            title
        )
    } else {
        format!("step {} of {} — {}", index + 1, steps.len(), title)
    }
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

/// The campaign view: which game, whether it can still be chosen, the
/// games to choose from, every shipped license paragraph.
fn campaign_view(app: &App, store: &Store) -> CampaignView {
    let status = store.campaign_status();
    let system_name = status
        .system
        .as_deref()
        .and_then(|s| app.ruleset_for(s))
        .map(|r| r.system_name().to_string());
    CampaignView {
        system: status.system,
        system_name,
        inferred: status.inferred,
        can_declare: store.is_empty(),
        problem: status.problem,
        games: app
            .rulesets
            .iter()
            .map(|r| GameOption {
                id: r.system().to_string(),
                name: r.system_name().to_string(),
            })
            .collect(),
        license_lines: app.license_lines(),
    }
}

async fn campaign(State(app): State<SharedApp>) -> Result<Json<CampaignView>, Failure> {
    let store = app.store.lock().await;
    Ok(Json(campaign_view(&app, &store)))
}

/// Declare (or, while the campaign is empty, change) the game. Refusals
/// are typed and write nothing; a racing second declaration loses to the
/// first (create-exclusive) and is told to reload.
async fn declare_campaign(
    State(app): State<SharedApp>,
    Json(request): Json<DeclareCampaignRequest>,
) -> Result<Json<CampaignView>, Failure> {
    let mut store = app.store.lock().await;
    store.declare(&request.system)?;
    Ok(Json(campaign_view(&app, &store)))
}

async fn roster(State(app): State<SharedApp>) -> Result<Json<RosterView>, Failure> {
    let store = app.store.lock().await;
    let load = store.load_all()?;
    let problems: Vec<RosterProblem> = load
        .problems
        .into_iter()
        .map(|(file, message)| RosterProblem { file, message })
        .collect();
    // An undeclared (or unresolvable) campaign serves the roster shell:
    // no entries, the problems, no class catalog — the campaign view
    // carries the reason and the choose-game options.
    let Ok(cx) = app.ctx(&store) else {
        return Ok(Json(RosterView {
            entries: Vec::new(),
            problems,
            classes: Vec::new(),
            quick_build: None,
        }));
    };
    let cx = &cx;
    let mut entries: Vec<RosterEntry> = load
        .characters
        .iter()
        .map(|c| RosterEntry {
            id: c.id.clone(),
            name: display_name(c),
            summary: summary_line(c),
            state: match c.state {
                DocState::Draft => RosterCharacterState::Draft {
                    resume_label: resume_label(cx, c),
                },
                DocState::Finalized if c.has_pending_tail() => RosterCharacterState::Leveling {
                    resume_label: resume_label(cx, c),
                },
                DocState::Finalized => RosterCharacterState::Finalized,
            },
            version: status_for(cx.rs.engine(), cx.known, c),
        })
        .collect();
    entries.sort_by(|a, b| a.id.cmp(&b.id));
    Ok(Json(RosterView {
        entries,
        problems,
        classes: class_catalog(cx)?,
        quick_build: quick_build_class(cx)?,
    }))
}

/// The class quick build would make: the first shipped class carrying a
/// suggested build (the same choice the quick-build route makes for a log
/// that names no class), as the catalog offers it.
fn quick_build_class(cx: &Ctx) -> Result<Option<ClassOption>, Failure> {
    let Some((class_id, _)) = cx.rs.suggested_builds().first() else {
        return Ok(None);
    };
    Ok(class_catalog(cx)?.into_iter().find(|c| c.id == *class_id))
}

/// The shipped classes, for the random-mint picker: the class slot's
/// available options against an empty log (a projection query — the
/// engine stays the only authority on what is offered).
fn class_catalog(cx: &Ctx) -> Result<Vec<ClassOption>, Failure> {
    let projection = cx
        .rs
        .engine()
        .project(&[])
        .map_err(|e| Failure::Internal(e.to_string()))?;
    Ok(projection
        .steps
        .iter()
        .flat_map(|s| s.slots.iter())
        .filter(|slot| slot.id == cx.rs.class_slot())
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
    let cx = &app.ctx(&store)?;
    let id = store.mint_character_id();
    let mut log = Vec::new();
    if let Some(name) = request.name.filter(|n| !n.trim().is_empty()) {
        // A working name arrives as a normal decision on the name slot.
        let input = types::DecisionInput {
            id: types::DecisionId::new(format!("{id}-initial-name")),
            slot: cx.rs.name_slot(),
            selection: Selection::Text(name),
            source: types::DecisionSource::Player,
        };
        if let Ok(AppendOutcome::Appended(new_log)) = cx.rs.engine().append(&log, input) {
            log = new_log;
        }
    }
    let sheet = cx
        .rs
        .engine()
        .sheet(&log)
        .map_err(|e| Failure::Internal(e.to_string()))?;
    let loaded = Loaded {
        id: id.clone(),
        system: cx.rs.system().to_string(),
        state: DocState::Draft,
        current_step: first_live_step(cx.rs.engine(), &log),
        draft_version: 1,
        sheet,
        log,
        finalized_through: 0,
        rules_version: cx.rs.rules_version().to_string(),
        version_history: Vec::new(),
        keep_old: None,
    };
    store.save(&loaded)?;
    Ok(Json(draft_view(cx, &loaded)?))
}

async fn get_character(
    State(app): State<SharedApp>,
    AxumPath(id): AxumPath<String>,
) -> Result<Json<CharacterView>, Failure> {
    let store = app.store.lock().await;
    let cx = &app.ctx(&store)?;
    let loaded = store.load(&CharacterId::new(id))?;
    Ok(Json(character_view(cx, &loaded)?))
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
    let cx = &app.ctx(&store)?;
    let mut loaded = store.load(&CharacterId::new(id))?;
    guard_wizard_target(&loaded)?;
    guard_wizard_write(cx, &loaded)?;
    // A level advance enters the log only through the level-up route.
    if cx.rs.is_advance_slot(&request.decision.slot) {
        return Err(Failure::Unprocessable(
            "level advances start through Level up, not as a confirmed choice".into(),
        ));
    }
    guard_below_marker(&loaded, [request.decision.slot.clone()])?;
    // Idempotency first: a retry after a crash between save and ack carries
    // the version it was originally made against, which is stale by now —
    // but its decision ID is already in the log, so it's a success, not a
    // conflict, and appends nothing.
    if loaded.log.iter().any(|d| d.id == request.decision.id) {
        return Ok(Json(ConfirmOutcome::Confirmed {
            draft: draft_view(cx, &loaded)?,
        }));
    }
    if request.version != loaded.draft_version {
        return Ok(Json(ConfirmOutcome::Conflict {
            current: draft_view(cx, &loaded)?,
        }));
    }
    let slot = request.decision.slot.clone();
    match cx.rs.engine().append(&loaded.log, request.decision) {
        Ok(AppendOutcome::AlreadyPresent) => {
            // Idempotent retry: already durable, acknowledge again.
            Ok(Json(ConfirmOutcome::Confirmed {
                draft: draft_view(cx, &loaded)?,
            }))
        }
        Ok(AppendOutcome::Appended(new_log)) => {
            loaded.log = new_log;
            refresh_draft_sheet(cx, &mut loaded)?;
            loaded.draft_version += 1;
            store.save(&loaded)?;
            Ok(Json(ConfirmOutcome::Confirmed {
                draft: draft_view(cx, &loaded)?,
            }))
        }
        Err(e) => {
            let step = first_live_step(cx.rs.engine(), &loaded.log);
            let entry = match &e {
                EngineError::UnknownSlot { .. }
                | EngineError::InvalidDecision { .. }
                | EngineError::NothingToClear { .. } => {
                    engine_error_entry(step, slot, e.to_string())
                }
            };
            Ok(Json(ConfirmOutcome::Rejected {
                reasons: vec![entry],
                draft: draft_view(cx, &loaded)?,
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
    let cx = &app.ctx(&store)?;
    let mut loaded = store.load(&CharacterId::new(id))?;
    guard_wizard_target(&loaded)?;
    guard_wizard_write(cx, &loaded)?;
    if cx.rs.is_advance_slot(&request.decision.slot) {
        return Err(Failure::Unprocessable(
            "level advances start through Level up, not as a confirmed choice".into(),
        ));
    }
    // An amend cascades like a clear: the slot and everything it drags
    // along must sit above the marker.
    let doomed: Vec<SlotId> = cx
        .rs
        .engine()
        .clear_preview(&loaded.log, &request.decision.slot)
        .map(|p| p.cleared.into_iter().map(|c| c.slot).collect())
        .unwrap_or_default();
    guard_below_marker(
        &loaded,
        std::iter::once(request.decision.slot.clone()).chain(doomed),
    )?;
    if loaded.log.iter().any(|d| d.id == request.decision.id) {
        return Ok(Json(ConfirmOutcome::Confirmed {
            draft: draft_view(cx, &loaded)?,
        }));
    }
    if request.version != loaded.draft_version {
        return Ok(Json(ConfirmOutcome::Conflict {
            current: draft_view(cx, &loaded)?,
        }));
    }
    let slot = request.decision.slot.clone();
    match cx.rs.engine().amend(&loaded.log, request.decision) {
        Ok(AppendOutcome::AlreadyPresent) => Ok(Json(ConfirmOutcome::Confirmed {
            draft: draft_view(cx, &loaded)?,
        })),
        Ok(AppendOutcome::Appended(new_log)) => {
            loaded.log = new_log;
            refresh_draft_sheet(cx, &mut loaded)?;
            loaded.draft_version += 1;
            store.save(&loaded)?;
            Ok(Json(ConfirmOutcome::Confirmed {
                draft: draft_view(cx, &loaded)?,
            }))
        }
        Err(e) => {
            let step = first_live_step(cx.rs.engine(), &loaded.log);
            Ok(Json(ConfirmOutcome::Rejected {
                reasons: vec![engine_error_entry(step, slot, e.to_string())],
                draft: draft_view(cx, &loaded)?,
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
    let cx = &app.ctx(&store)?;
    let mut loaded = store.load(&CharacterId::new(id))?;
    guard_wizard_target(&loaded)?;
    guard_wizard_write(cx, &loaded)?;
    if cx.rs.is_advance_slot(&request.slot) {
        return Err(Failure::Unprocessable(
            "a pending level is discarded through Abandon level, not by clearing".into(),
        ));
    }
    if request.version != loaded.draft_version {
        return Ok(Json(ClearOutcome::Conflict {
            current: draft_view(cx, &loaded)?,
        }));
    }
    let preview = cx
        .rs
        .engine()
        .clear_preview(&loaded.log, &request.slot)
        .map_err(|e| Failure::Unprocessable(e.to_string()))?;
    guard_below_marker(
        &loaded,
        std::iter::once(request.slot.clone()).chain(preview.cleared.iter().map(|c| c.slot.clone())),
    )?;
    let new_log = cx
        .rs
        .engine()
        .clear(&loaded.log, &request.slot)
        .map_err(|e| Failure::Unprocessable(e.to_string()))?;
    loaded.log = new_log;
    refresh_draft_sheet(cx, &mut loaded)?;
    loaded.draft_version += 1;
    store.save(&loaded)?;
    Ok(Json(ClearOutcome::Cleared {
        draft: draft_view(cx, &loaded)?,
        preview,
    }))
}

async fn set_step(
    State(app): State<SharedApp>,
    AxumPath(id): AxumPath<String>,
    Json(request): Json<StepRequest>,
) -> Result<Json<DraftView>, Failure> {
    let store = app.store.lock().await;
    let cx = &app.ctx(&store)?;
    let mut loaded = store.load(&CharacterId::new(id))?;
    guard_wizard_target(&loaded)?;
    guard_wizard_write(cx, &loaded)?;
    // The step cursor is navigation, not a decision: last write wins and no
    // version bump (a stale-tab navigation shouldn't invalidate confirms).
    if !live_steps(cx.rs.engine(), &loaded.log)
        .iter()
        .any(|(s, _)| *s == request.step)
    {
        return Err(Failure::Unprocessable(format!(
            "unknown step '{}'",
            request.step
        )));
    }
    loaded.current_step = request.step;
    store.save(&loaded)?;
    Ok(Json(draft_view(cx, &loaded)?))
}

async fn finalize(
    State(app): State<SharedApp>,
    AxumPath(id): AxumPath<String>,
    Json(request): Json<FinalizeRequest>,
) -> Result<Json<FinalizeOutcome>, Failure> {
    let store = app.store.lock().await;
    let cx = &app.ctx(&store)?;
    let mut loaded = store.load(&CharacterId::new(id))?;
    // "Finalize what is pending": nothing pending on a finalized character
    // is an idempotent no-op returning the current sheet (the retry after
    // a crash between a level finalize's save and its ack lands here).
    if loaded.state == DocState::Finalized && !loaded.has_pending_tail() {
        return Ok(Json(FinalizeOutcome::Finalized {
            sheet: loaded.sheet.clone(),
        }));
    }
    guard_wizard_write(cx, &loaded)?;
    if request.version != loaded.draft_version {
        return Ok(Json(FinalizeOutcome::Conflict {
            current: Box::new(draft_view(cx, &loaded)?),
        }));
    }
    let projection = cx
        .rs
        .engine()
        .project(&loaded.log)
        .map_err(|e| Failure::Internal(e.to_string()))?;
    if !projection.can_finalize {
        return Ok(Json(FinalizeOutcome::Blocked {
            reasons: projection.checklist,
        }));
    }
    // One atomic transition: marker and sheet move together, in one write.
    loaded.state = DocState::Finalized;
    loaded.sheet = projection.sheet;
    loaded.finalized_through = loaded.log.len();
    loaded.draft_version += 1;
    store.save(&loaded)?;
    Ok(Json(FinalizeOutcome::Finalized {
        sheet: loaded.sheet.clone(),
    }))
}

// ---- Level-up routes (level-up spec reqs 1-2) ----
//
// A pending level is the log's un-finalized tail behind the document's
// finalized marker: start appends the level's advance decision (the tail's
// head), the wizard routes append its choices, finalize moves the marker,
// abandon truncates to it. Each transition is one crash-safe write.

async fn level_up(
    State(app): State<SharedApp>,
    AxumPath(id): AxumPath<String>,
    Json(request): Json<LevelUpRequest>,
) -> Result<Json<LevelUpOutcome>, Failure> {
    let store = app.store.lock().await;
    let cx = &app.ctx(&store)?;
    let mut loaded = store.load(&CharacterId::new(id))?;
    if loaded.state == DocState::Draft {
        return Err(Failure::Unprocessable(
            "finish creating this character before leveling it up".into(),
        ));
    }
    // Idempotent: a character already leveling returns its pending level —
    // a second tab, a retry, never a second advance.
    if loaded.has_pending_tail() {
        guard_wizard_write(cx, &loaded)?;
        return Ok(Json(LevelUpOutcome::Started {
            draft: Box::new(draft_view(cx, &loaded)?),
        }));
    }
    let status = status_for(cx.rs.engine(), cx.known, &loaded);
    if status != VersionStatus::Current {
        // Kept-old or otherwise non-current: the log cannot be extended
        // under today's data; resolve the flag first (kept-old characters
        // never level).
        return Err(Failure::VersionFlagged(Box::new(status)));
    }
    if request.version != loaded.draft_version {
        return Ok(Json(LevelUpOutcome::Conflict {
            character: Box::new(character_view(cx, &loaded)?),
        }));
    }
    let current_level = cx
        .rs
        .level_of(&loaded.log)
        .map_err(|e| Failure::Internal(e.to_string()))?;
    let Some(level) = cx
        .rs
        .next_level(&loaded.log)
        .map_err(|e| Failure::Internal(e.to_string()))?
    else {
        return Err(Failure::Unprocessable(format!(
            "level {current_level} is as far as this rules data goes — higher levels are coming"
        )));
    };
    let input = DecisionInput {
        id: DecisionId::new(format!("level-{level}-advance")),
        slot: cx.rs.advance_slot(level),
        selection: Selection::Option(cx.rs.advance_option(level)),
        source: DecisionSource::Player,
    };
    match cx.rs.engine().append(&loaded.log, input) {
        Ok(AppendOutcome::Appended(new_log)) => loaded.log = new_log,
        Ok(AppendOutcome::AlreadyPresent) => {}
        Err(e) => {
            return Err(Failure::Unprocessable(format!(
                "cannot start level {level}: {e}"
            )))
        }
    }
    // The stored sheet stays the finalized one; only the tail grew.
    loaded.current_step = first_live_step(cx.rs.engine(), &loaded.log);
    loaded.draft_version += 1;
    store.save(&loaded)?;
    Ok(Json(LevelUpOutcome::Started {
        draft: Box::new(draft_view(cx, &loaded)?),
    }))
}

async fn abandon_level(
    State(app): State<SharedApp>,
    AxumPath(id): AxumPath<String>,
    Json(request): Json<AbandonLevelRequest>,
) -> Result<Json<AbandonLevelOutcome>, Failure> {
    let store = app.store.lock().await;
    let cx = &app.ctx(&store)?;
    let mut loaded = store.load(&CharacterId::new(id))?;
    if !loaded.has_pending_tail() {
        return Err(Failure::Unprocessable(
            "no level-up is in progress on this character".into(),
        ));
    }
    // Abandon is always permitted — the exit from a tail whose replay no
    // longer works — so no version-flag guard here.
    if request.version != loaded.draft_version {
        return Ok(Json(AbandonLevelOutcome::Conflict {
            character: Box::new(character_view(cx, &loaded)?),
        }));
    }
    // Truncate to the marker: the finalized prefix and sheet are untouched
    // by construction; the version counter stays monotonic so a tab stale
    // from this attempt can never land in the next.
    loaded.log.truncate(loaded.finalized_through);
    loaded.current_step = first_live_step(cx.rs.engine(), &loaded.log);
    loaded.draft_version += 1;
    store.save(&loaded)?;
    Ok(Json(AbandonLevelOutcome::Abandoned {
        character: Box::new(character_view(cx, &loaded)?),
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
    cx: &'a Ctx<'a>,
    log: &[Decision],
) -> Option<&'a BTreeMap<SlotId, SlotSuggestion>> {
    let chosen_class = log
        .iter()
        .rev()
        .find(|d| d.slot == cx.rs.class_slot())
        .and_then(|d| match &d.selection {
            Selection::Option(id) => Some(id.as_str().to_string()),
            _ => None,
        });
    match chosen_class {
        Some(class_id) => cx
            .rs
            .suggested_builds()
            .iter()
            .find(|(id, _)| *id == class_id)
            .map(|(_, map)| map),
        None => cx.rs.suggested_builds().first().map(|(_, map)| map),
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
    let cx = &app.ctx(&store)?;
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
        guard_wizard_write(cx, &loaded)?;
        let Some(suggest) = suggestion_map(cx, &loaded.log) else {
            return Err(Failure::Unprocessable(
                "no shipped class carries a suggested build".into(),
            ));
        };
        let unresolved = cx
            .rs
            .engine()
            .unresolved_suggestions(
                &loaded.log,
                &mut |ctx: &SuggestionContext| suggest.get(ctx.slot).cloned(),
                DecisionSource::Suggested,
            )
            .map_err(|e| Failure::Internal(e.to_string()))?;
        return Ok(Json(QuickBuildResult {
            draft: draft_view(cx, &loaded)?,
            unresolved,
        }));
    }
    // Fresh build: seed the optional name as a player decision (the planner
    // never overwrites it), expand, and write exactly once.
    let mut log = Vec::new();
    if let Some(name) = request.name.as_ref().filter(|n| !n.trim().is_empty()) {
        let input = DecisionInput {
            id: DecisionId::new(format!("{}.initial-name", request.request_id)),
            slot: cx.rs.name_slot(),
            selection: Selection::Text(name.clone()),
            source: DecisionSource::Player,
        };
        if let Ok(AppendOutcome::Appended(new_log)) = cx.rs.engine().append(&log, input) {
            log = new_log;
        }
    }
    {
        let Some(suggest) = suggestion_map(cx, &log) else {
            return Err(Failure::Unprocessable(
                "no shipped class carries a suggested build".into(),
            ));
        };
        suggest_owned = suggest.clone();
    }
    let request_id = request.request_id.clone();
    let plan = cx
        .rs
        .engine()
        .expand_suggestions(
            &log,
            &mut |ctx: &SuggestionContext| suggest_owned.get(ctx.slot).cloned(),
            &|slot| suggestion_decision_id(&request_id, slot),
            DecisionSource::Suggested,
        )
        .map_err(|e| Failure::Internal(e.to_string()))?;
    let sheet = cx
        .rs
        .engine()
        .sheet(&plan.log)
        .map_err(|e| Failure::Internal(e.to_string()))?;
    let loaded = Loaded {
        id,
        system: cx.rs.system().to_string(),
        state: DocState::Draft,
        // Review state: resume lands on the final step, where the player
        // confirms the name and finalizes.
        current_step: live_steps(cx.rs.engine(), &plan.log)
            .last()
            .map(|(id, _)| id.clone())
            .unwrap_or_else(|| StepId::new("concept")),
        draft_version: 1,
        sheet,
        log: plan.log,
        finalized_through: 0,
        rules_version: cx.rs.rules_version().to_string(),
        version_history: Vec::new(),
        keep_old: None,
    };
    store.save(&loaded)?;
    Ok(Json(QuickBuildResult {
        draft: draft_view(cx, &loaded)?,
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
    let cx = &app.ctx(&store)?;
    let mut loaded = store.load(&CharacterId::new(id))?;
    guard_wizard_target(&loaded)?;
    if loaded.has_pending_tail() {
        return Err(Failure::Unprocessable(
            "suggested builds cover character creation only — level-up choices are yours to make"
                .into(),
        ));
    }
    guard_wizard_write(cx, &loaded)?;
    let Some(suggest) = suggestion_map(cx, &loaded.log).cloned() else {
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
        let unresolved = cx
            .rs
            .engine()
            .unresolved_suggestions(&loaded.log, &mut suggest_fn, DecisionSource::Suggested)
            .map_err(|e| Failure::Internal(e.to_string()))?;
        return Ok(Json(FillRemainingOutcome::Filled {
            draft: draft_view(cx, &loaded)?,
            unresolved,
        }));
    }
    if request.version != loaded.draft_version {
        return Ok(Json(FillRemainingOutcome::Conflict {
            current: draft_view(cx, &loaded)?,
        }));
    }
    let request_id = request.request_id.clone();
    let plan = cx
        .rs
        .engine()
        .expand_suggestions(
            &loaded.log,
            &mut suggest_fn,
            &|slot| suggestion_decision_id(&request_id, slot),
            DecisionSource::Suggested,
        )
        .map_err(|e| Failure::Internal(e.to_string()))?;
    if !plan.appended.is_empty() {
        loaded.log = plan.log;
        refresh_draft_sheet(cx, &mut loaded)?;
        loaded.draft_version += 1;
        store.save(&loaded)?;
    }
    Ok(Json(FillRemainingOutcome::Filled {
        draft: draft_view(cx, &loaded)?,
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

/// A random candidate order over a slot's legal options. Ungrouped
/// options are simply shuffled. Grouped options (a pick per group, as the
/// `one-per-group` presentation renders them) come one per group first —
/// groups in random order, each group's pick random among its options
/// whose label no earlier pick used, so distinct groups take distinct
/// values where the catalog allows — then the rest, shuffled. Labels are
/// data; the server knows nothing about what a group is.
fn grouped_shuffle(sampler: &mut Sampler, legal: &[&types::OptionView]) -> Vec<types::OptionId> {
    if legal.iter().all(|o| o.group.is_none()) {
        let ids: Vec<types::OptionId> = legal.iter().map(|o| o.id.clone()).collect();
        return sampler.shuffled(&ids);
    }
    let mut groups: Vec<String> = Vec::new();
    for o in legal {
        let g = o.group.clone().unwrap_or_default();
        if !groups.contains(&g) {
            groups.push(g);
        }
    }
    let groups = sampler.shuffled(&groups);
    let mut head: Vec<types::OptionId> = Vec::new();
    let mut used_labels: Vec<&str> = Vec::new();
    for group in &groups {
        let members: Vec<&types::OptionView> = legal
            .iter()
            .copied()
            .filter(|o| o.group.as_deref().unwrap_or_default() == group)
            .collect();
        let order = sampler.shuffled(&members);
        let pick = order
            .iter()
            .find(|o| !used_labels.contains(&o.label.as_str()))
            .or_else(|| order.first());
        if let Some(pick) = pick {
            used_labels.push(&pick.label);
            head.push(pick.id.clone());
        }
    }
    let rest: Vec<types::OptionId> = legal
        .iter()
        .map(|o| o.id.clone())
        .filter(|id| !head.contains(id))
        .collect();
    head.extend(sampler.shuffled(&rest));
    head
}

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
fn load_name_pools(cx: &Ctx) -> Result<NamePools, Failure> {
    let path = cx.name_pools;
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
    fn for_key(&self, key: Option<&str>) -> &[String] {
        key.and_then(|a| self.pools.get(a))
            .filter(|p| !p.is_empty())
            .map_or(&self.default[..], |p| &p[..])
    }
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
    let cx = &app.ctx(&store)?;
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
        guard_wizard_write(cx, &loaded)?;
        return Ok(Json(QuickBuildResult {
            draft: draft_view(cx, &loaded)?,
            unresolved: Vec::new(),
        }));
    }
    // Everything that can refuse does so before any write: pools first
    // (spec: a malformed pool file fails the mint, nothing written).
    let pools = load_name_pools(cx)?;
    // The request ID is the entropy: same request, same character —
    // deterministic, reproducible, replay-safe.
    let mut sampler = Sampler::from_key(&request.request_id);
    let catalog = class_catalog(cx)?;
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
            slot: cx.rs.name_slot(),
            selection: Selection::Text(name.clone()),
            source: DecisionSource::Player,
        };
        if let Ok(AppendOutcome::Appended(new_log)) = cx.rs.engine().append(&log, input) {
            log = new_log;
        }
    }
    let class_input = DecisionInput {
        id: DecisionId::new(format!("{}.class-pick", request.request_id)),
        slot: cx.rs.class_slot(),
        selection: Selection::Option(types::OptionId::new(class_id)),
        source: class_source,
    };
    match cx.rs.engine().append(&log, class_input) {
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
            if *ctx.slot == cx.rs.name_slot() {
                return None;
            }
            match ctx.kind {
                types::SlotViewKind::Text { .. } => {
                    let candidates = cx.rs.text_fill_candidates(ctx.slot);
                    let topic = sampler.pick(&candidates)?;
                    Some(SlotSuggestion::Text(topic.clone()))
                }
                _ => {
                    // A pinned pick (a generation method the mint never
                    // varies) goes first; the ruleset says which.
                    if let Some(pinned) = cx.rs.mint_pin(ctx.slot) {
                        if ctx.options.iter().any(|o| o.available && o.id == pinned) {
                            return Some(SlotSuggestion::Candidates(vec![pinned]));
                        }
                    }
                    let legal: Vec<&types::OptionView> =
                        ctx.options.iter().filter(|o| o.available).collect();
                    if legal.is_empty() {
                        return None;
                    }
                    Some(SlotSuggestion::Candidates(grouped_shuffle(sampler, &legal)))
                }
            }
        };
        let mut plan = cx
            .rs
            .engine()
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
            let projection = cx
                .rs
                .engine()
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
                if let Ok(new_log) = cx.rs.engine().clear(&cleared, slot) {
                    cleared = new_log;
                }
            }
            plan = cx
                .rs
                .engine()
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
    if !log.iter().any(|d| d.slot == cx.rs.name_slot()) {
        let key = cx.rs.name_pool_key(&log);
        let pool = pools.for_key(key.as_deref());
        let Some(name) = sampler.pick(pool) else {
            return Err(Failure::Unprocessable(format!(
                "the name-pools file '{}' has an empty default pool — random \
                 minting needs at least one name; nothing was created",
                cx.name_pools.display()
            )));
        };
        let input = DecisionInput {
            id: DecisionId::new(format!("{}.random-name", request.request_id)),
            slot: cx.rs.name_slot(),
            selection: Selection::Text(name.clone()),
            source: DecisionSource::Random,
        };
        match cx.rs.engine().append(&log, input) {
            Ok(AppendOutcome::Appended(new_log)) => log = new_log,
            Ok(AppendOutcome::AlreadyPresent) => {}
            Err(e) => {
                return Err(Failure::Internal(format!(
                    "the sampled name did not apply: {e}"
                )))
            }
        }
    }
    let sheet = cx
        .rs
        .engine()
        .sheet(&log)
        .map_err(|e| Failure::Internal(e.to_string()))?;
    // Unresolved is expected empty over shipped data; recomputed here so
    // future data reports honestly (same surface as quick build).
    let unresolved = cx
        .rs
        .engine()
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
        system: cx.rs.system().to_string(),
        state: DocState::Draft,
        // Review state: resume lands on the final step, like quick build.
        current_step: live_steps(cx.rs.engine(), &log)
            .last()
            .map(|(id, _)| id.clone())
            .unwrap_or_else(|| StepId::new("concept")),
        draft_version: 1,
        sheet,
        log,
        finalized_through: 0,
        rules_version: cx.rs.rules_version().to_string(),
        version_history: Vec::new(),
        keep_old: None,
    };
    store.save(&loaded)?;
    Ok(Json(QuickBuildResult {
        draft: draft_view(cx, &loaded)?,
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
    let cx = &app.ctx(&store)?;
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
    let status = status_for(cx.rs.engine(), cx.known, &source);
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
    let current_pin = source.rules_version == cx.rs.rules_version();
    // What the stored sheet reflects: the whole log for a creation draft,
    // the finalized prefix for a finalized character (a pending tail is
    // never part of the stored sheet).
    let reflected: &[Decision] = source.finalized_prefix();
    if current_pin {
        let replayed = cx.rs.engine().sheet(reflected).map_err(|e| {
            Failure::Unprocessable(format!(
                "'{}' does not replay cleanly ({e}) — run `verify`; nothing \
                 was created",
                display_name(&source)
            ))
        })?;
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
    let name_decision_at = source.log.iter().rposition(|d| d.slot == cx.rs.name_slot());
    let mut log = source.log.clone();
    let minted = |order: u32| Decision {
        id: DecisionId::new(format!("{}.clone-name", request.request_id)),
        slot: cx.rs.name_slot(),
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
        // The clone's sheet is the fold of what its stored sheet reflects
        // (the pending tail, if any, is copied along but stays pending);
        // the whole log is folded once for cleanliness.
        cx.rs
            .engine()
            .folds(&log)
            .map_err(|e| Failure::Internal(format!("the cloned log does not replay: {e}")))?;
        let reflected_len = if source.state == DocState::Draft {
            log.len()
        } else {
            source.finalized_through.min(log.len())
        };
        cx.rs
            .engine()
            .sheet(&log[..reflected_len])
            .map_err(|e| Failure::Internal(format!("the cloned log does not replay: {e}")))?
    } else {
        let mut sheet = source.sheet.clone();
        sheet.name = new_name.clone();
        sheet
    };
    let loaded = Loaded {
        id,
        system: source.system.clone(),
        state: source.state,
        current_step: source.current_step.clone(),
        draft_version: source.draft_version,
        sheet,
        log,
        finalized_through: source.finalized_through,
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
    let cx = &app.ctx(&store)?;
    let mut loaded = store.load(&CharacterId::new(id))?;
    if request.version != loaded.draft_version {
        return Ok(Json(VersionResolutionOutcome::Conflict {
            character: Box::new(character_view(cx, &loaded)?),
        }));
    }
    let status = status_for(cx.rs.engine(), cx.known, &loaded);
    match &status {
        VersionStatus::OlderKnown {
            pinned,
            outcome: ReplayOutcome::Identical,
            ..
        } => {
            let from = pinned.clone();
            loaded.rules_version = cx.rs.rules_version().to_string();
            loaded.keep_old = None;
            loaded.version_history.push(resolution_event(
                "re_pin",
                &from,
                cx.rs.rules_version(),
                "identical replay",
            ));
            loaded.draft_version += 1;
            store.save(&loaded)?;
            Ok(Json(VersionResolutionOutcome::Resolved {
                character: Box::new(character_view(cx, &loaded)?),
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
    let cx = &app.ctx(&store)?;
    let mut loaded = store.load(&CharacterId::new(id))?;
    if request.version != loaded.draft_version {
        return Ok(Json(VersionResolutionOutcome::Conflict {
            character: Box::new(character_view(cx, &loaded)?),
        }));
    }
    let status = status_for(cx.rs.engine(), cx.known, &loaded);
    match &status {
        VersionStatus::OlderKnown {
            pinned,
            outcome: ReplayOutcome::Divergent { differences },
            ..
        } => {
            let from = pinned.clone();
            let replayed = cx
                .rs
                .engine()
                .sheet(loaded.finalized_prefix())
                .map_err(|e| Failure::Internal(e.to_string()))?;
            let mut event = resolution_event(
                "accept",
                &from,
                cx.rs.rules_version(),
                "accepted divergent replay; superseded values recorded",
            );
            event.superseded_values = differences.clone();
            loaded.sheet = replayed;
            loaded.rules_version = cx.rs.rules_version().to_string();
            loaded.keep_old = None;
            loaded.version_history.push(event);
            loaded.draft_version += 1;
            store.save(&loaded)?;
            Ok(Json(VersionResolutionOutcome::Resolved {
                character: Box::new(character_view(cx, &loaded)?),
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
    let cx = &app.ctx(&store)?;
    let mut loaded = store.load(&CharacterId::new(id))?;
    if request.version != loaded.draft_version {
        return Ok(Json(VersionResolutionOutcome::Conflict {
            character: Box::new(character_view(cx, &loaded)?),
        }));
    }
    let status = status_for(cx.rs.engine(), cx.known, &loaded);
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
                evaluated_against: cx.rs.rules_version().to_string(),
                at_millis: clock::now_millis(),
            });
            loaded
                .version_history
                .push(resolution_event("keep_old", &from, &from, note));
            loaded.draft_version += 1;
            store.save(&loaded)?;
            Ok(Json(VersionResolutionOutcome::Resolved {
                character: Box::new(character_view(cx, &loaded)?),
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
    let cx = &app.ctx(&store)?;
    let mut loaded = store.load(&CharacterId::new(id))?;
    if request.version != loaded.draft_version {
        return Ok(Json(VersionResolutionOutcome::Conflict {
            character: Box::new(character_view(cx, &loaded)?),
        }));
    }
    let status = status_for(cx.rs.engine(), cx.known, &loaded);
    match &status {
        VersionStatus::OlderKnown {
            pinned,
            outcome: ReplayOutcome::ReplayError { .. },
            ..
        } if loaded.state == DocState::Draft => {
            let from = pinned.clone();
            let repair = repair_replay(cx.rs.engine(), &loaded.log);
            let sheet = cx
                .rs
                .engine()
                .sheet(&repair.log)
                .map_err(|e| Failure::Internal(format!("repaired log must fold: {e}")))?;
            let mut event = resolution_event(
                "resolve_replay_error",
                &from,
                cx.rs.rules_version(),
                format!(
                    "log no longer replayed; {} decision(s) cleared and reopened",
                    repair.cleared_decisions.len()
                ),
            );
            event.cleared_decisions = repair.cleared_decisions;
            loaded.log = repair.log;
            loaded.sheet = sheet;
            loaded.rules_version = cx.rs.rules_version().to_string();
            loaded.keep_old = None;
            loaded.version_history.push(event);
            loaded.draft_version += 1;
            store.save(&loaded)?;
            Ok(Json(VersionResolutionOutcome::Resolved {
                character: Box::new(character_view(cx, &loaded)?),
            }))
        }
        _ => Ok(Json(refused(
            "resolve-errors applies only to a draft on an older known version whose log fails to replay",
            status,
        ))),
    }
}
