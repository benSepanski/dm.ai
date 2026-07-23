import { useGameStore } from "../store/gameStore";

const BASE_URL = "/api";

// ---- Request/Response types ----

export type ClientRole = "dm" | "player";

export interface RoleResponse {
  role: ClientRole;
}

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

// A single spell-slot level's capacity. Mirrors dm_api.db.models.character.SpellSlotRead.
export interface SpellSlot {
  slot_level: number;
  maximum: number;
  remaining: number;
  is_pact: boolean;
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
  // Flat list of item-name strings (e.g. "Spear", "Chain Mail", "Shield").
  // Names that match the weapon registry (see CreationOptions.weapon_mastery_options)
  // are offered as Attack weapon choices in the combat tracker (PT-29).
  equipment: string[] | null;
  // Derived server-side (CharacterRead._derive_spellcasting_fields) from the
  // engine's known_spells/prepared_spells/spells column — offered as Cast
  // Spell choices in the combat tracker (PT-28). null means none known, or
  // hidden because this is an NPC/monster viewed by a player.
  known_spells: string[] | null;
  spell_slots: SpellSlot[] | null;
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

export interface WeaponMasteryOption {
  name: string;
  category: string;
  mastery_property: string;
  is_melee: boolean;
  properties: string[];
}

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
  weapon_mastery_count: number;
  cantrips_known: number;
  prepared_spells_known: number;
}

export interface SpeciesTraitChoice {
  skill_options: string[];
  lineage_options: string[];
}

export interface SpeciesTrait {
  name: string;
  description: string;
  choice: SpeciesTraitChoice | null;
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

export interface SpellOption {
  name: string;
  level: number;
  school: string;
  classes: string[];
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
  weapon_mastery_options: WeaponMasteryOption[];
  spells: SpellOption[];
}

export interface CharacterBuildRequest {
  world_id: string;
  // Set when building from inside a live session so the server can broadcast a
  // roster update to other connected clients (players see the new PC live).
  session_id?: string;
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
  weapon_masteries?: string[] | null;
  species_trait_choices?: Record<string, string> | null;
  starting_cantrips?: string[] | null;
  starting_spells?: string[] | null;
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

export interface CreateLocationRequest {
  world_id: string;
  type: string;
  name: string;
  description?: string;
  lore?: string;
  history?: string;
}

export interface CreateCharacterRequest {
  world_id: string;
  type: "NPC" | "MONSTER";
  name: string;
  race?: string;
  char_class?: string;
  level?: number;
  hp_max?: number;
  hp_current?: number;
  ac?: number;
  personality_traits?: string;
}

export interface SessionUpdateRequest {
  current_location_id?: string | null;
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
  combat_log: (Record<string, unknown> & { flavor_text?: string })[] | null;
  started_at: string;
  ended_at: string | null;
}

export interface StartCombatRequest {
  character_ids: string[];
}

export interface CharacterPatchRequest {
  hp_max?: number;
  hp_current?: number;
  ac?: number;
  name?: string;
}

// Mirrors dm_api.db.models.combat.AttackDetailsRequest. Only weapon_name is
// sent by the UI — when it matches the weapon registry, the server derives
// damage dice/type/ability/mastery from the registry and the actor's
// training rather than trusting client-supplied combat numbers.
export interface AttackDetailsRequest {
  weapon_name: string;
}

export interface CombatActionRequest {
  actor_id: string;
  action_type: string;
  target_id?: string;
  attack_details?: AttackDetailsRequest;
}

// Mirrors dm_api.db.models.combat.CastSpellRequest. slot_level omitted lets
// the engine default to the spell's own level (no upcast).
export interface CastSpellRequest {
  actor_id: string;
  spell_name: string;
  target_ids: string[];
  slot_level?: number;
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

// DM authentication: the token (if this browser has one) rides on every
// request. The server decides the role per request — no token means the
// caller is treated as a player and gets the redacted views.
function authHeaders(): Record<string, string> {
  const token = useGameStore.getState().dmToken;
  return token ? { "X-DM-Token": token } : {};
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const { headers: extraHeaders, ...rest } = options ?? {};
  const res = await fetch(`${BASE_URL}${path}`, {
    ...rest,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(extraHeaders as Record<string, string>),
    },
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(body || `API ${res.status}: ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

// ---- API client ----

export const api = {
  // Auth
  getRole: () => request<RoleResponse>("/auth/role"),

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
  endSession: (sessionId: string) =>
    request<SessionResponse>(`/sessions/${sessionId}/end`, { method: "PUT" }),

  // Combat
  startCombat: (sessionId: string, characterIds: string[]) =>
    request<CombatStateResponse>(`/sessions/${sessionId}/combat`, {
      method: "POST",
      body: JSON.stringify({ character_ids: characterIds } satisfies StartCombatRequest),
    }),
  getCombat: (sessionId: string) =>
    request<CombatStateResponse>(`/sessions/${sessionId}/combat`),
  submitAction: (sessionId: string, action: CombatActionRequest) =>
    request<CombatStateResponse>(`/sessions/${sessionId}/combat/action`, {
      method: "POST",
      body: JSON.stringify(action),
    }),
  castSpell: (sessionId: string, payload: CastSpellRequest) =>
    request<CombatStateResponse>(`/sessions/${sessionId}/combat/cast-spell`, {
      method: "POST",
      body: JSON.stringify(payload),
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

  // Sessions (mutable fields)
  patchSession: (sessionId: string, data: SessionUpdateRequest) =>
    request<SessionResponse>(`/sessions/${sessionId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  // Characters
  listWorldCharacters: (worldId: string) =>
    request<CharacterResponse[]>(`/characters/world/${worldId}`),
  getCharacter: (charId: string) =>
    request<CharacterResponse>(`/characters/${charId}`),
  patchCharacter: (charId: string, data: CharacterPatchRequest) =>
    request<CharacterResponse>(`/characters/${charId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  createCharacter: (data: CreateCharacterRequest, sessionId?: string) =>
    request<CharacterResponse>(
      `/characters/${sessionId ? `?session_id=${sessionId}` : ""}`,
      { method: "POST", body: JSON.stringify(data) },
    ),

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
  listWorldLocations: (worldId: string) =>
    request<LocationResponse[]>(`/worlds/${worldId}/locations`),
  createLocation: (data: CreateLocationRequest) =>
    request<LocationResponse>("/locations/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};
