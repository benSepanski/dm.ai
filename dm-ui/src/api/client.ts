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

export interface CombatStateResponse {
  id: string;
  round_number: number;
  current_turn_index: number;
  combatants: Array<{
    char_id: string;
    name: string;
    hp_current: number;
    hp_max: number;
    ac: number;
    initiative: number;
    is_current_turn: boolean;
  }> | null;
}

export interface CombatActionRequest {
  action_type: string;
  actor_id?: string;
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
  endCombat: (sessionId: string) =>
    request<CombatStateResponse>(`/sessions/${sessionId}/combat/end`, { method: "PUT" }),
};
