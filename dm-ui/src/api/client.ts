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
  proposal?: Record<string, unknown> | null;
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

  // Sessions
  createSession: (data: CreateSessionRequest) =>
    request<{ id: string }>("/sessions/", { method: "POST", body: JSON.stringify(data) }),
  chat: (sessionId: string, message: string) =>
    request<ChatResponse>(
      `/sessions/${sessionId}/chat`,
      { method: "POST", body: JSON.stringify({ message }) },
    ),

  // Combat
  startCombat: (sessionId: string) =>
    request<CombatStateResponse>(`/sessions/${sessionId}/combat`, { method: "POST" }),
  submitAction: (sessionId: string, action: CombatActionRequest) =>
    request<CombatStateResponse>(`/sessions/${sessionId}/combat/action`, {
      method: "POST",
      body: JSON.stringify(action),
    }),
  nextTurn: (sessionId: string) =>
    request<CombatStateResponse>(`/sessions/${sessionId}/combat/next-turn`, { method: "POST" }),
  endCombat: (sessionId: string) =>
    request<CombatStateResponse>(`/sessions/${sessionId}/combat/end`, { method: "PUT" }),
};
