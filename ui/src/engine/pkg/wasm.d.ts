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
    /**
     * Present while this draft is a pending level on a finalized
     * character: what the level grants, the finalize deltas, and the
     * choices an abandon would discard. Absent on creation drafts.
     */
    level_up?: LevelUpView;
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
export type CharacterView = ({ state: "draft" } & DraftView) | { state: "finalized"; id: CharacterId; sheet: SheetView; version_status: VersionStatus; version: number; next_level?: number } | { state: "leveling"; id: CharacterId; sheet: SheetView; draft: DraftView } | { state: "flagged_draft"; id: CharacterId; name: string; sheet: SheetView; version: number; status: VersionStatus };

/**
 * A stable rules-data record ID, e.g. `ancestry.dwarf`.
 */
export type OptionId = string;

/**
 * A successful clone: the new character's roster identity. The client
 * refreshes the roster or opens the character by ID.
 */
export interface CloneResult {
    id: CharacterId;
    name: string;
    /**
     * True when the clone is finalized (source was finalized).
     */
    finalized: boolean;
}

/**
 * A wizard step grouping slots, e.g. `ancestry` or `equipment`.
 */
export type StepId = string;

/**
 * Abandon the pending level: the tail is discarded (atomically), the
 * finalized state stands untouched.
 */
export interface AbandonLevelRequest {
    version: number;
}

/**
 * Client-minted per confirm; a replayed ID appends nothing (idempotency).
 */
export type DecisionId = string;

/**
 * Declare (or, while the campaign is empty, change) the campaign's game.
 * `replaces` is the game the client believes is currently declared:
 * absent from the choose-game screen (the client believes none), so a
 * racing second answer meets an existing declaration and is refused;
 * present for a deliberate change while the campaign is still empty.
 */
export interface DeclareCampaignRequest {
    system: string;
    replaces?: string;
}

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
    /**
     * Render-ready explanation of the new value — the sheet entry's own
     * detail line ("7 expert + 2 Con"), when the sheet carries one. So a
     * reader of a diff (a level-up's gains, a version review) sees why a
     * number moved, not only that it did.
     */
    why?: string;
}

/**
 * One shipped class, as the random-mint picker offers it.
 */
export interface ClassOption {
    /**
     * The class record ID (a class-slot option ID).
     */
    id: string;
    name: string;
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
 * One-tap random character: create a draft and fill every required slot
 * with random legal picks (never the published suggested build).
 * `request_id` is client-generated and doubles as the entropy source —
 * the same request always mints the same character, so a retry after a
 * crash returns the already-saved draft and appends nothing.
 */
export interface RandomMintRequest {
    request_id: string;
    /**
     * Class record ID to mint, or `None` for "any" (sampled uniformly
     * over shipped classes). A chosen class is recorded as a player
     * decision; a sampled one as a random decision.
     */
    class_id: string | undefined;
    /**
     * Optional player-typed name; recorded as a player decision and
     * never overwritten by the generator.
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
 * Request body for the version-resolution routes (re-pin / accept /
 * keep-old / resolve-errors). Carries the draft version like every write.
 */
export interface VersionActionRequest {
    version: number;
}

/**
 * Start (or resume) a level-up; carries the write version like every
 * wizard write. Idempotent: a character already leveling returns its
 * pending level.
 */
export interface LevelUpRequest {
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
    campaign: CampaignView;
    declare_campaign_request: DeclareCampaignRequest;
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
}

/**
 * The campaign as a whole: which game it plays (or that it has not chosen
 * one), the games this build ships to choose from, and every shipped
 * license paragraph — attribution follows the binary, never the open
 * campaign. Fetched first by the UI; the only view that names a system.
 */
export interface CampaignView {
    /**
     * The game this campaign plays, when resolved (declared, or inferred
     * for a pre-declaration directory that holds characters).
     */
    system?: string;
    /**
     * Render-ready name of that game.
     */
    system_name?: string;
    /**
     * True when the game was inferred rather than declared (the app never
     * writes a declaration into such a campaign).
     */
    inferred: boolean;
    /**
     * Whether the game may still be chosen or changed: only while the
     * campaign holds no character.
     */
    can_declare: boolean;
    /**
     * Why no game could be resolved, naming the fix; absent otherwise.
     */
    problem?: string;
    /**
     * The games this build ships, for the choose-game screen.
     */
    games: GameOption[];
    /**
     * Every shipped ruleset's license paragraphs, in display order.
     */
    license_lines: string[];
}

/**
 * The clone request: duplicate `source_id` as a new character whose only
 * log difference is the name decision (clone provenance, this `name`).
 * `request_id` follows the quick-build idempotency scheme; a retried
 * request returns the already-created character and ignores a changed
 * `name` (first write wins).
 */
export interface CloneRequest {
    request_id: string;
    source_id: CharacterId;
    name: string;
}

/**
 * The engine's verdict on one slot — delivered pre-joined so the UI never
 * infers state from weaker signals (decision presence, entry absence).
 */
export type SlotStatus = "locked" | "empty" | "partial" | "complete" | "illegal";

/**
 * The pending level's derived companions (spec req 4): every value here
 * comes from the sheet diff between folds — nothing is hand-authored.
 */
export interface LevelUpView {
    /**
     * The level being gained.
     */
    level: number;
    /**
     * "At level N you gain…": the finalized sheet vs the sheet folded
     * through the advance decision alone (before any choice).
     */
    gains: SheetDiff[];
    /**
     * Before/after for the values the level changed so far: the
     * finalized sheet vs the sheet folded through the whole tail.
     */
    deltas: SheetDiff[];
    /**
     * The tail's decisions, described — what abandon discards (the
     * clear-confirmation shape, so the existing dialog renders it).
     */
    pending: ClearedDecision[];
}

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
export type DecisionSource = "player" | "suggested" | "random" | "clone";

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

export interface GameOption {
    id: string;
    name: string;
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
    /**
     * Render-ready group heading. Consecutive options sharing a group are
     * rendered under one labeled header ("School of Battle Magic
     * curriculum"); `None` options fall in the unlabeled remainder.
     */
    group?: string | undefined;
    /**
     * Short render-ready badge shown as a chip next to the name
     * ("Curriculum"); survives filtering, unlike position or grouping.
     */
    badge?: string | undefined;
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
     * Shipped classes, for the random-mint class picker.
     */
    classes?: ClassOption[];
    /**
     * The class the quick-build control would build, when this campaign's
     * game publishes a suggested build; absent when the rules publish
     * none (the roster then shows no quick-build control).
     */
    quick_build?: ClassOption;
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

export type AbandonLevelOutcome = { outcome: "abandoned"; character: CharacterView } | { outcome: "conflict"; character: CharacterView };

export type ChecklistSeverity = "incomplete" | "illegal";

export type ClearOutcome = { outcome: "cleared"; draft: DraftView; preview: ClearPreview } | { outcome: "conflict"; current: DraftView };

export type EngineRequest = { request: "project"; log: Decision[] } | { request: "preview"; log: Decision[]; candidate: DecisionInput } | { request: "clear_preview"; log: Decision[]; slot: SlotId };

export type EngineResponse = { response: "projection"; projection: ProjectionView } | { response: "clear_preview"; preview: ClearPreview } | { response: "error"; message: string };

export type FillRemainingOutcome = { outcome: "filled"; draft: DraftView; unresolved: UnresolvedSuggestion[] } | { outcome: "conflict"; current: DraftView };

export type FinalizeOutcome = { outcome: "finalized"; sheet: SheetView } | { outcome: "blocked"; reasons: ChecklistEntry[] } | { outcome: "conflict"; current: DraftView };

export type LevelUpOutcome = { outcome: "started"; draft: DraftView } | { outcome: "conflict"; character: CharacterView };

export type MeterState = "ok" | "short" | "exceeded";

export type RosterCharacterState = { state: "draft"; resume_label: string } | { state: "finalized" } | { state: "leveling"; resume_label: string };

export type StepStatus = "complete" | "incomplete" | "waiting" | "illegal";


export function __wire_type_exports(value: WireTypeExports): WireTypeExports;

/**
 * The narrow boundary: every engine interaction is one request in, one
 * response out. Deserialization failures surface as catchable JS errors.
 */
export function engine_request(system: string, request: EngineRequest): EngineResponse;

/**
 * Surfaces Rust panic messages to the browser console so a dead engine is
 * loud, never a silently inert widget.
 */
export function start(): void;

export type InitInput = RequestInfo | URL | Response | BufferSource | WebAssembly.Module;

export interface InitOutput {
    readonly memory: WebAssembly.Memory;
    readonly __wire_type_exports: (a: any) => any;
    readonly engine_request: (a: number, b: number, c: any) => [number, number, number];
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
