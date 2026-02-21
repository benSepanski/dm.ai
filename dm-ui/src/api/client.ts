const BASE_URL = "/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  // Worlds
  createWorld: (data: Record<string, unknown>) =>
    request("/worlds/", { method: "POST", body: JSON.stringify(data) }),
  getWorld: (id: string) => request(`/worlds/${id}`),

  // Sessions
  createSession: (data: Record<string, unknown>) =>
    request("/sessions/", { method: "POST", body: JSON.stringify(data) }),
  getSession: (id: string) => request(`/sessions/${id}`),
  chat: (sessionId: string, message: string) =>
    request<{ response: string; proposal?: Record<string, unknown> | null }>(
      `/sessions/${sessionId}/chat`,
      { method: "POST", body: JSON.stringify({ message }) },
    ),
  endSession: (id: string) =>
    request(`/sessions/${id}/end`, { method: "PUT" }),

  // Characters
  createCharacter: (data: Record<string, unknown>) =>
    request("/characters/", { method: "POST", body: JSON.stringify(data) }),
  getCharacter: (id: string) => request(`/characters/${id}`),

  // Locations
  createLocation: (data: Record<string, unknown>) =>
    request("/locations/", { method: "POST", body: JSON.stringify(data) }),
  getLocation: (id: string) => request(`/locations/${id}`),

  // Combat
  startCombat: (sessionId: string) =>
    request(`/sessions/${sessionId}/combat`, { method: "POST" }),
  getCombat: (sessionId: string) =>
    request(`/sessions/${sessionId}/combat`),
  submitAction: (sessionId: string, action: Record<string, unknown>) =>
    request(`/sessions/${sessionId}/combat/action`, {
      method: "POST",
      body: JSON.stringify(action),
    }),
  endCombat: (sessionId: string) =>
    request(`/sessions/${sessionId}/combat/end`, { method: "PUT" }),

  // Proposals
  acceptProposal: (id: string, data?: Record<string, unknown>) =>
    request(`/ai/proposals/${id}/accept`, {
      method: "POST",
      body: JSON.stringify(data ?? {}),
    }),
  rejectProposal: (id: string, data?: Record<string, unknown>) =>
    request(`/ai/proposals/${id}/reject`, {
      method: "POST",
      body: JSON.stringify(data ?? {}),
    }),
};
