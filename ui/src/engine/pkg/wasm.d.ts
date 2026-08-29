/* tslint:disable */
/* eslint-disable */
/**
 * 409 body when a wizard write is refused because the draft pins a
 * rules-data version that is not current and unresolved.
 */
export interface VersionFlaggedError {
    message: string;
    status: VersionStatus;
}

/**
 * A character (draft or finalized); also its filename stem in the data dir.
 */
export type CharacterId = string;

/**
 * A confirmed choice as recorded in the log.
 */
export interface Decision {
    id: DecisionId;
    slot: SlotId;
    selection: Selection;
    source: DecisionSource;
    /**
     * Position in the log when confirmed. Redundant with log order by
     * construction; stored so a hand-inspected file reads chronologically.
     */
    order: number;
}

/**
 * A draft mid-wizard, as the server owns it.
 */
export interface DraftView {
    id: CharacterId;
    /**
     * Bumps on every accepted mutation; confirms carry the version they
     * were made against and stale ones are rejected.
     */
    version: number;
    /**
     * Server-side step cursor: where resume lands.
     */
    current_step: StepId;
    projection: ProjectionView;
    /**
     * The rules-data version this draft is built against.
     */
    rules_version: string;
    /**
     * Where that pin stands against the shipped data (always `Current`
     * here: a draft with an unresolved older pin arrives as
     * `CharacterView::FlaggedDraft` instead, never with a projection).
     */
    version_status: VersionStatus;
}

/**
 * A not-yet-ordered decision as submitted by a client.
 */
export interface DecisionInput {
    id: DecisionId;
    slot: SlotId;
    selection: Selection;
    source: DecisionSource;
}

/**
 * A render-ready gauge attached to a slot — always present, not only on
 * violation ("Spent 5 gp, 8 sp of 15 gp", "2 of 4 chosen").
 */
export interface MeterView {
    label: string;
    /**
     * Render-ready current value.
     */
    current: string;
    /**
     * Render-ready bound, when one exists.
     */
    limit: string | undefined;
    state: MeterState;
}

/**
 * A required slot the suggestion planner could not fill, with the reason —
 * the "cannot complete" half of a quick-build/fill response. The same
 * slots also appear on the ordinary checklist.
 */
export interface UnresolvedSuggestion {
    slot: SlotId;
    label: string;
    reason: string;
}

/**
 * A ruleset-defined choice slot, e.g. `pf2e.ancestry` or `pf2e.boosts.free`.
 */
export type SlotId = string;

/**
 * A single character as fetched by ID.
 */
export type CharacterView = ({ state: "draft" } & DraftView) | { state: "finalized"; id: CharacterId; sheet: SheetView; version_status: VersionStatus; version: number; prep?: ScopedProjection; prep_broken?: boolean } | { state: "flagged_draft"; id: CharacterId; name: string; sheet: SheetView; version: number; status: VersionStatus };

/**
 * A stable rules-data record ID, e.g. `ancestry.dwarf`.
 */
export type OptionId = string;

/**
 * A wizard step grouping slots, e.g. `ancestry` or `equipment`.
 */
export type StepId = string;

/**
 * Client-minted per confirm; a replayed ID appends nothing (idempotency).
 */
export type DecisionId = string;

/**
 * Everything the engine can say about a draft from its log alone.
 * The server wraps this with persistence metadata (id, version, cursor).
 */
export interface ProjectionView {
    steps: StepView[];
    checklist: ChecklistEntry[];
    sheet: SheetView;
    /**
     * True iff the checklist is empty — nothing incomplete, nothing illegal.
     */
    can_finalize: boolean;
}

/**
 * Fill only the open required slots of an existing draft with suggestions.
 * Carries the draft version like every wizard write; `request_id` makes the
 * expansion idempotent under retry.
 */
export interface FillRemainingRequest {
    request_id: string;
    version: number;
}

/**
 * How a slot collects its selection. Presentation-mechanical only — the
 * meaning of the options is the ruleset's business.
 */
export type SlotViewKind = { kind: "single" } | { kind: "multi"; count: number } | { kind: "list" } | { kind: "text"; multiline: boolean };

/**
 * One pick in a scoped section. No decision ID and no order: the section
 * is replaced as a whole, so idempotency and history live at the save
 * layer, not per choice.
 */
export interface ScopedChoice {
    slot: SlotId;
    selection: Selection;
}

/**
 * One sheet value that would change under current data, old → new.
 */
export interface SheetDiff {
    section: string;
    label: string;
    /**
     * The stored value ("(absent)" when the entry did not exist).
     */
    old: string;
    /**
     * The value current data derives ("(absent)" when it no longer exists).
     */
    new: string;
}

/**
 * One-tap quick build: create a draft and fill every required slot from
 * the class's suggested build. `request_id` is client-generated and makes
 * the request idempotent: a retry after a crash between save and ack
 * returns the already-saved draft and appends nothing.
 */
export interface QuickBuildRequest {
    request_id: string;
    /**
     * Optional working name; seeds the name slot as a player decision (the
     * planner never overwrites it).
     */
    name: string | undefined;
}

/**
 * Outcome of a confirm. `Conflict` carries the current draft so a stale
 * tab can reload; `Rejected` is the server refusing an illegal confirm.
 */
export type ConfirmOutcome = { outcome: "confirmed"; draft: DraftView } | { outcome: "conflict"; current: DraftView } | { outcome: "rejected"; reasons: ChecklistEntry[]; draft: DraftView };

/**
 * Outcome of a version-resolution route.
 */
export type VersionResolutionOutcome = { outcome: "resolved"; character: CharacterView } | { outcome: "conflict"; character: CharacterView } | { outcome: "refused"; message: string; status: VersionStatus };

/**
 * Replace a character's scoped preparation section wholesale. Carries the
 * character's write version like every mutation; `request_id` makes the
 * save idempotent under retry (a crash between save and ack returns the
 * saved result and changes nothing).
 */
export interface PrepSaveRequest {
    request_id: string;
    version: number;
    expected_state: LifecycleState;
    choices: ScopedChoice[];
}

/**
 * Request body for the version-resolution routes (re-pin / accept /
 * keep-old / resolve-errors). Carries the draft version like every write.
 */
export interface VersionActionRequest {
    version: number;
}

/**
 * The HTTP wire types aren't referenced by the engine boundary, but the UI
 * needs their TypeScript declarations from the same generated `.d.ts`.
 * This carrier keeps them alive through code generation; it is never
 * instantiated.
 */
export interface WireTypeExports {
    roster: RosterView;
    character: CharacterView;
    create_request: CreateCharacterRequest;
    confirm_request: ConfirmRequest;
    confirm_outcome: ConfirmOutcome;
    clear_request: ClearRequest;
    clear_outcome: ClearOutcome;
    step_request: StepRequest;
    finalize_request: FinalizeRequest;
    finalize_outcome: FinalizeOutcome;
    api_error: ApiError;
    version_action_request: VersionActionRequest;
    version_resolution_outcome: VersionResolutionOutcome;
    version_flagged_error: VersionFlaggedError;
    quick_build_request: QuickBuildRequest;
    quick_build_result: QuickBuildResult;
    fill_remaining_request: FillRemainingRequest;
    fill_remaining_outcome: FillRemainingOutcome;
    prep_save_request: PrepSaveRequest;
    prep_save_outcome: PrepSaveOutcome;
}

/**
 * The engine's verdict on a scoped choice set: the scoped slots rendered
 * exactly like wizard slots, plus the checklist entries the set produces.
 * Total by design — a hand-edited section (unknown slot, malformed pick,
 * choices on a class with no such slots) comes back as Illegal entries,
 * never as an error that blocks loading.
 */
export interface ScopedProjection {
    slots: SlotView[];
    checklist: ChecklistEntry[];
}

/**
 * The engine's verdict on one slot — delivered pre-joined so the UI never
 * infers state from weaker signals (decision presence, entry absence).
 */
export type SlotStatus = "locked" | "empty" | "partial" | "complete" | "illegal";

/**
 * The lifecycle state a scoped save expects to act on. A stale UI holding
 * the wrong lifecycle (a draft tab after finalize, or vice versa) is
 * rejected with the current state, never coerced.
 */
export type LifecycleState = "draft" | "finalized";

/**
 * The quick-build response: a normal draft view (review state, NOT
 * finalized) plus any slots the suggested build could not fill.
 */
export interface QuickBuildResult {
    draft: DraftView;
    unresolved: UnresolvedSuggestion[];
}

/**
 * The result of replaying an older-known character's log against current
 * rules data.
 */
export type ReplayOutcome = { kind: "identical" } | { kind: "divergent"; differences: SheetDiff[] } | { kind: "replay_error"; message: string; failing_decision: DecisionId; slot: SlotId; would_reopen?: ClearedDecision[] };

/**
 * Uniform error body for everything that is not a typed outcome.
 */
export interface ApiError {
    message: string;
}

/**
 * What changing (or clearing) a confirmed slot would take with it.
 */
export interface ClearPreview {
    /**
     * The slot being changed.
     */
    slot: SlotId;
    /**
     * Dependent decisions that would be cleared, in log order — shown
     * verbatim in the confirmation prompt.
     */
    cleared: ClearedDecision[];
}

/**
 * What was chosen in a slot.
 */
export type Selection = { kind: "option"; value: OptionId } | { kind: "options"; value: OptionId[] } | { kind: "text"; value: string };

/**
 * Where a character's pinned rules-data version stands relative to the
 * version this build ships. Computed fresh on every load.
 */
export type VersionStatus = { status: "current" } | { status: "older_known"; pinned: string; current: string; outcome: ReplayOutcome } | { status: "kept_old"; pinned: string; evaluated_against: string } | { status: "unknown"; pinned: string; current: string };

/**
 * Who (or what) made a decision. DM exceptions and auto-mode arrive in
 * later epochs as new variants.
 */
export type DecisionSource = "player" | "suggested";

export interface ChecklistEntry {
    severity: ChecklistSeverity;
    /**
     * The offending slot; clicking the entry jumps here.
     */
    slot: SlotId;
    /**
     * The step that slot lives in.
     */
    step: StepId;
    /**
     * The rule's name, e.g. "Attribute boosts".
     */
    rule: string;
    /**
     * Human explanation, e.g. "boosts in this group must go to different
     * attributes".
     */
    message: string;
    /**
     * Where the obligation came from, e.g. "from Background: Field Medic".
     */
    source: string;
}

export interface ClearRequest {
    slot: SlotId;
    version: number;
}

export interface ClearedDecision {
    slot: SlotId;
    slot_label: string;
    /**
     * Render-ready description of what was chosen there.
     */
    selection_label: string;
    selection: Selection;
}

export interface ConfirmRequest {
    decision: DecisionInput;
    /**
     * The draft version this confirm was made against.
     */
    version: number;
}

export interface CreateCharacterRequest {
    /**
     * Optional working name; the details step confirms the real one.
     */
    name: string | undefined;
}

export interface FinalizeRequest {
    version: number;
}

export interface OptionView {
    id: OptionId;
    label: string;
    /**
     * One-line render-ready summary ("Hit Points 10 · Speed 20 feet · …").
     */
    summary: string;
    /**
     * Render-ready detail bullets.
     */
    details: string[];
    /**
     * False when a prerequisite fails; the option shows greyed out.
     */
    available: boolean;
    /**
     * Why it is unavailable, e.g. "requires a spellcasting class feature".
     */
    unavailable_reason: string | undefined;
}

export interface RosterEntry {
    id: CharacterId;
    name: string;
    /**
     * Identity line, e.g. "Dwarf Fighter 1".
     */
    summary: string;
    state: RosterCharacterState;
    /**
     * Rules-data version flag — computed at load, never written by it.
     */
    version: VersionStatus;
}

export interface RosterProblem {
    /**
     * The affected file name (not a full path).
     */
    file: string;
    /**
     * What happened, e.g. "could not be read — quarantined".
     */
    message: string;
}

export interface RosterView {
    entries: RosterEntry[];
    /**
     * Files that could not be loaded (quarantined or unreadable) — always
     * reported, never blocking the rest of the roster.
     */
    problems: RosterProblem[];
    /**
     * The ORC attribution notice, displayed in the app.
     */
    license_notice: string;
}

export interface SheetEntry {
    label: string;
    /**
     * Render-ready value, e.g. "18" or "+7" or "2 Bulk, 3 L".
     */
    value: string;
    /**
     * Optional provenance/breakdown, e.g. "10 + 2 Dex + 4 scale mail + 2 trained".
     */
    detail: string | undefined;
}

export interface SheetSection {
    title: string;
    entries: SheetEntry[];
}

export interface SheetView {
    name: string;
    /**
     * Identity line(s), e.g. "Dwarf (Rock Dwarf) Fighter 1".
     */
    summary: string[];
    sections: SheetSection[];
}

export interface SlotView {
    id: SlotId;
    label: string;
    kind: SlotViewKind;
    /**
     * Free-form rendering hint (e.g. `attribute-boosts`); the UI may use it
     * to pick a nicer widget, never to compute values.
     */
    presentation_hint: string | undefined;
    /**
     * Present when the slot is currently locked (e.g. heritage before an
     * ancestry exists), with the reason to show.
     */
    locked_reason: string | undefined;
    /**
     * Whether resolving this slot is required to finalize.
     */
    required: boolean;
    /**
     * The engine's verdict on this slot; the UI renders it, never infers it.
     */
    status: SlotStatus;
    /**
     * Always-on gauges (counts, budgets), live under previews.
     */
    meters: MeterView[];
    /**
     * The confirmed decision currently occupying this slot, if any.
     */
    decision: Decision | undefined;
    /**
     * The catalog as of the current log (empty for text slots).
     */
    options: OptionView[];
    /**
     * True for a slot in a scoped section (preparation): its selection is
     * saved through the scoped-save route as part of a wholesale
     * replacement, never confirmed into the decision log. The UI switches
     * the save path on this flag and nothing else.
     */
    scoped?: boolean;
}

export interface StepRequest {
    step: StepId;
    version: number;
}

export interface StepView {
    id: StepId;
    title: string;
    status: StepStatus;
    slots: SlotView[];
}

export type ChecklistSeverity = "incomplete" | "illegal";

export type ClearOutcome = { outcome: "cleared"; draft: DraftView; preview: ClearPreview } | { outcome: "conflict"; current: DraftView };

export type EngineRequest = { request: "project"; log: Decision[]; prep?: ScopedChoice[] } | { request: "preview"; log: Decision[]; candidate: DecisionInput; prep?: ScopedChoice[] } | { request: "preview_prep"; log: Decision[]; prep: ScopedChoice[] } | { request: "clear_preview"; log: Decision[]; slot: SlotId; prep?: ScopedChoice[] };

export type EngineResponse = { response: "projection"; projection: ProjectionView } | { response: "clear_preview"; preview: ClearPreview } | { response: "error"; message: string };

export type FillRemainingOutcome = { outcome: "filled"; draft: DraftView; unresolved: UnresolvedSuggestion[] } | { outcome: "conflict"; current: DraftView };

export type FinalizeOutcome = { outcome: "finalized"; sheet: SheetView } | { outcome: "blocked"; reasons: ChecklistEntry[] } | { outcome: "conflict"; current: DraftView };

export type MeterState = "ok" | "short" | "exceeded";

export type PrepSaveOutcome = { outcome: "saved"; character: CharacterView } | { outcome: "conflict"; character: CharacterView } | { outcome: "rejected"; reasons: ChecklistEntry[]; character: CharacterView };

export type RosterCharacterState = { state: "draft"; resume_label: string } | { state: "finalized" };

export type StepStatus = "complete" | "incomplete" | "waiting" | "illegal";


export function __wire_type_exports(value: WireTypeExports): WireTypeExports;

/**
 * The narrow boundary: every engine interaction is one request in, one
 * response out. Deserialization failures surface as catchable JS errors.
 */
export function engine_request(request: EngineRequest): EngineResponse;

/**
 * Surfaces Rust panic messages to the browser console so a dead engine is
 * loud, never a silently inert widget.
 */
export function start(): void;

export type InitInput = RequestInfo | URL | Response | BufferSource | WebAssembly.Module;

export interface InitOutput {
    readonly memory: WebAssembly.Memory;
    readonly __wire_type_exports: (a: any) => any;
    readonly engine_request: (a: any) => [number, number, number];
    readonly start: () => void;
    readonly __wbindgen_malloc: (a: number, b: number) => number;
    readonly __wbindgen_realloc: (a: number, b: number, c: number, d: number) => number;
    readonly __wbindgen_exn_store: (a: number) => void;
    readonly __externref_table_alloc: () => number;
    readonly __wbindgen_externrefs: WebAssembly.Table;
    readonly __wbindgen_free: (a: number, b: number, c: number) => void;
    readonly __externref_table_dealloc: (a: number) => void;
    readonly __wbindgen_start: () => void;
}

export type SyncInitInput = BufferSource | WebAssembly.Module;

/**
 * Instantiates the given `module`, which can either be bytes or
 * a precompiled `WebAssembly.Module`.
 *
 * @param {{ module: SyncInitInput }} module - Passing `SyncInitInput` directly is deprecated.
 *
 * @returns {InitOutput}
 */
export function initSync(module: { module: SyncInitInput } | SyncInitInput): InitOutput;

/**
 * If `module_or_path` is {RequestInfo} or {URL}, makes a request and
 * for everything else, calls `WebAssembly.instantiate` directly.
 *
 * @param {{ module_or_path: InitInput | Promise<InitInput> }} module_or_path - Passing `InitInput` directly is deprecated.
 *
 * @returns {Promise<InitOutput>}
 */
export default function __wbg_init (module_or_path?: { module_or_path: InitInput | Promise<InitInput> } | InitInput | Promise<InitInput>): Promise<InitOutput>;
