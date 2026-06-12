const BASE_URL = "/api";

// ---- Request/Response types ----

export interface CreateWorldRequest {
  name: string;
  setting_description?: string;
}

export interface CreateSessionRequest {
  world_id: string;
  name: string;
}

export interface ChatResponse {
  response: string;
  proposals: ProposalResponse[];
}

export type ProposalStatus = "pending" | "accepted" | "rejected" | "modified";

export interface ProposalResponse {
  id: string;
  session_id: string | null;
  world_id: string;
  type: string;
  content: Record<string, unknown> | null;
  status: ProposalStatus;
  dm_notes: string | null;
  created_at: string;
}

export interface SessionResponse {
  id: string;
  world_id: string;
  name: string;
  rule_engine_version: string;
  player_character_ids: string[] | null;
  current_location_id: string | null;
  session_summary: string | null;
  started_at: string;
  ended_at: string | null;
}

export interface ChatMessageResponse {
  id: string;
  session_id: string;
  role: "dm" | "ai" | "system";
  content: string;
  timestamp: string;
}

export interface CharacterResponse {
  id: string;
  world_id: string;
  type: string;
  name: string;
  race: string | null;
  char_class: string | null;
  level: number;
  alignment: string | null;
  stats: Record<string, unknown> | null;
  hp_current: number | null;
  hp_max: number | null;
  ac: number | null;
  speed: number | null;
}

// ---- Character creation (engine-backed) ----

export type AbilityName =
  | "strength"
  | "dexterity"
  | "constitution"
  | "intelligence"
  | "wisdom"
  | "charisma";

export type AbilityScores = Record<AbilityName, number>;

export interface ClassOption {
  character_class: string;
  hit_die: number;
  primary_abilities: AbilityName[];
  saving_throw_proficiencies: AbilityName[];
  armor_training: string[];
  weapon_category_training: string[];
  skill_choices: string[];
  num_skill_choices: number;
  spellcasting: boolean;
}

export interface SpeciesTrait {
  name: string;
  description: string;
}

export interface SpeciesOption {
  species: string;
  creature_type: string;
  size_options: string[];
  speed: number;
  darkvision_ft: number;
  traits: SpeciesTrait[];
  damage_resistances: string[];
  description: string;
}

export interface BackgroundOption {
  background: string;
  ability_scores: AbilityName[];
  skill_proficiencies: string[];
  tool_proficiency: string;
  origin_feat: string;
  equipment: string[];
  description: string;
}

export interface ArmorOption {
  name: string;
  armor_type: string;
  base_ac: number;
  dex_bonus: boolean;
  dex_cap: number | null;
  stealth_disadvantage: boolean;
}

export interface SkillOption {
  skill: string;
  governing_ability: AbilityName;
}

export interface CreationOptions {
  classes: ClassOption[];
  species: SpeciesOption[];
  backgrounds: BackgroundOption[];
  armor: ArmorOption[];
  skills: SkillOption[];
  languages: string[];
  alignments: string[];
  standard_array: number[];
  point_buy_budget: number;
  point_buy_costs: Record<string, number>;
}

export interface CharacterBuildRequest {
  world_id: string;
  name: string;
  character_class: string;
  species: string;
  background: string;
  ability_scores: AbilityScores;
  skill_choices: string[];
  background_ability_allocation: Partial<Record<AbilityName, number>> | null;
  languages: string[] | null;
  armor_name: string | null;
  shield: boolean;
  alignment: string | null;
}

export interface CharacterBuildResponse {
  character: CharacterResponse;
  warnings: string[];
}

export interface LocationResponse {
  id: string;
  world_id: string;
  type: string;
  name: string;
  description: string | null;
}

export interface AcceptProposalRequest {
  dm_notes?: string;
  modifications?: Record<string, unknown>;
}

export interface RejectProposalRequest {
  dm_notes?: string;
}

// Entry in initiative_order — one per combatant, sorted by initiative desc.
export interface InitiativeEntry {
  character_id: string;
  name: string;
  initiative: number;
}

// Entry in combatants — CharacterSheet.to_dict() shape from the rule engine.
// Indices align 1:1 with initiative_order after initiative is rolled.
export interface CombatantState {
  id: string;
  name: string;
  hp_current: number;
  hp_max: number;
  ac: number;
  speed: number;
  level: number;
  conditions: string[];
  condition_durations: Record<string, number>;
}

export interface CombatStateResponse {
  id: string;
  session_id: string;
  location_id: string | null;
  round_number: number;
  current_turn_index: number;
  initiative_order: InitiativeEntry[] | null;
  combatants: CombatantState[] | null;
  combat_log: Record<string, unknown>[] | null;
  started_at: string;
  ended_at: string | null;
}

export interface CombatActionRequest {
  actor_id: string;
  action_type: string;
  target_id?: string;
}

export type AIProvider = "anthropic" | "claude_cli";

// Per-game overrides; null means "inherit the deployment default".
export interface GameConfigOverrides {
  ai_provider: AIProvider | null;
  orchestrator_model: string | null;
  generation_model: string | null;
  context_token_limit: number | null;
  context_preserve_last_n: number | null;
  database_url: string | null;
  redis_url: string | null;
}

// Fully resolved settings the engine actually uses (overrides + defaults).
export interface EffectiveGameConfig {
  ai_provider: string;
  orchestrator_model: string;
  generation_model: string;
  context_token_limit: number;
  context_preserve_last_n: number;
  database_url: string;
  redis_url: string;
}

export interface GameConfigResponse {
  world_id: string;
  overrides: GameConfigOverrides;
  effective: EffectiveGameConfig;
}

// ---- HTTP helper ----

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const { headers: extraHeaders, ...rest } = options ?? {};
  const res = await fetch(`${BASE_URL}${path}`, {
    ...rest,
    headers: { "Content-Type": "application/json", ...(extraHeaders as Record<string, string>) },
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(body || `API ${res.status}: ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

// ---- API client ----

export const api = {
  // Worlds
  createWorld: (data: CreateWorldRequest) =>
    request<{ id: string }>("/worlds/", { method: "POST", body: JSON.stringify(data) }),
  getGameConfig: (worldId: string) =>
    request<GameConfigResponse>(`/worlds/${worldId}/config`),
  updateGameConfig: (worldId: string, overrides: GameConfigOverrides) =>
    request<GameConfigResponse>(`/worlds/${worldId}/config`, {
      method: "PUT",
      body: JSON.stringify(overrides),
    }),

  // Sessions
  createSession: (data: CreateSessionRequest) =>
    request<{ id: string }>("/sessions/", { method: "POST", body: JSON.stringify(data) }),
  getSession: (sessionId: string) =>
    request<SessionResponse>(`/sessions/${sessionId}`),
  getSessionMessages: (sessionId: string) =>
    request<ChatMessageResponse[]>(`/sessions/${sessionId}/messages`),
  chat: (sessionId: string, message: string) =>
    request<ChatResponse>(
      `/sessions/${sessionId}/chat`,
      { method: "POST", body: JSON.stringify({ message }) },
    ),

  // Combat
  startCombat: (sessionId: string) =>
    request<CombatStateResponse>(`/sessions/${sessionId}/combat`, { method: "POST" }),
  getCombat: (sessionId: string) =>
    request<CombatStateResponse>(`/sessions/${sessionId}/combat`),
  submitAction: (sessionId: string, action: CombatActionRequest) =>
    request<CombatStateResponse>(`/sessions/${sessionId}/combat/action`, {
      method: "POST",
      body: JSON.stringify(action),
    }),
  nextTurn: (sessionId: string) =>
    request<CombatStateResponse>(`/sessions/${sessionId}/combat/next-turn`, { method: "POST" }),
  endCombat: (sessionId: string) =>
    request<CombatStateResponse>(`/sessions/${sessionId}/combat/end`, { method: "PUT" }),

  // Proposals
  getProposal: (proposalId: string) =>
    request<ProposalResponse>(`/ai/proposals/${proposalId}`),
  listSessionProposals: (sessionId: string) =>
    request<ProposalResponse[]>(`/ai/sessions/${sessionId}/proposals`),
  acceptProposal: (proposalId: string, opts: AcceptProposalRequest = {}) =>
    request<ProposalResponse>(`/ai/proposals/${proposalId}/accept`, {
      method: "POST",
      body: JSON.stringify(opts),
    }),
  rejectProposal: (proposalId: string, opts: RejectProposalRequest = {}) =>
    request<ProposalResponse>(`/ai/proposals/${proposalId}/reject`, {
      method: "POST",
      body: JSON.stringify(opts),
    }),

  // Characters
  listWorldCharacters: (worldId: string) =>
    request<CharacterResponse[]>(`/characters/world/${worldId}`),
  getCharacter: (charId: string) =>
    request<CharacterResponse>(`/characters/${charId}`),

  // Character creation (engine-backed)
  getCreationOptions: () =>
    request<CreationOptions>("/characters/creation/options"),
  buildCharacter: (data: CharacterBuildRequest) =>
    request<CharacterBuildResponse>("/characters/creation/build", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Locations
  getLocation: (locId: string) =>
    request<LocationResponse>(`/locations/${locId}`),
};
