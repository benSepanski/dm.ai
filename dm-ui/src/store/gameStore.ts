import { create } from "zustand";
import { createJSONStorage, persist, type StateStorage } from "zustand/middleware";

// dmToken/isDM are security-sensitive and must never leak between browser
// tabs on the same origin (e.g. via "Copy Invite Link" into a second tab) —
// they live in sessionStorage, which is per-tab. Everything else persisted
// (sessionId, worldId, tokenPositions) is fine to share across tabs/refreshes
// and stays in localStorage. Zustand's persist middleware only accepts one
// storage, so this adapter splits the single serialized blob's top-level keys
// across the two backing stores on write/read/remove.
const SESSION_STORAGE_KEYS = new Set(["dmToken", "isDM"]);

const splitStorage: StateStorage = {
  getItem: (name) => {
    const localRaw = window.localStorage.getItem(name);
    const sessionRaw = window.sessionStorage.getItem(name);
    if (localRaw === null && sessionRaw === null) return null;

    const localParsed = localRaw ? JSON.parse(localRaw) : { state: {} };
    const sessionParsed = sessionRaw ? JSON.parse(sessionRaw) : { state: {} };
    // Session-only keys (dmToken/isDM) must come exclusively from
    // sessionStorage: a stale value left in localStorage (e.g. by a
    // pre-upgrade build that persisted them there) must never leak into a
    // tab whose sessionStorage doesn't have it, or DM authority would leak
    // across tabs — the exact bug this split storage exists to prevent.
    const localState = { ...localParsed.state };
    for (const key of SESSION_STORAGE_KEYS) {
      delete localState[key];
    }
    return JSON.stringify({
      ...localParsed,
      state: { ...localState, ...sessionParsed.state },
    });
  },
  setItem: (name, value) => {
    const parsed = JSON.parse(value) as { state: Record<string, unknown>; version?: number };
    const localState: Record<string, unknown> = {};
    const sessionState: Record<string, unknown> = {};
    for (const [key, val] of Object.entries(parsed.state)) {
      (SESSION_STORAGE_KEYS.has(key) ? sessionState : localState)[key] = val;
    }
    window.localStorage.setItem(name, JSON.stringify({ ...parsed, state: localState }));
    window.sessionStorage.setItem(name, JSON.stringify({ ...parsed, state: sessionState }));
  },
  removeItem: (name) => {
    window.localStorage.removeItem(name);
    window.sessionStorage.removeItem(name);
  },
};

// ---- Domain types ----

export interface ChatMessage {
  id: string;
  role: "dm" | "ai" | "system";
  content: string;
  timestamp: string;
}

export interface Combatant {
  char_id: string;
  name: string;
  hp_current: number;
  hp_max: number;
  ac: number;
  initiative: number;
  is_current_turn: boolean;
}

export interface ActiveCombat {
  id: string;
  round_number: number;
  current_turn_index: number;
  combatants: Combatant[];
}

export interface LocationData {
  id: string;
  name: string;
  type: string;
  description: string | null;
}

export interface CharacterData {
  id: string;
  // CharacterType enum value from the backend: "PC" | "NPC" | "MONSTER".
  type: string;
  name: string;
  char_class: string | null;
  race: string | null;
  level: number;
  hp_current: number | null;
  hp_max: number | null;
  ac: number | null;
  stats: Record<string, unknown> | null;
}

// Grid cell coordinates of a battle-map token, keyed by character id.
export interface TokenPosition {
  x: number;
  y: number;
}

export interface ProposalData {
  id: string;
  session_id: string | null;
  world_id: string;
  type: string;
  content: Record<string, unknown> | null;
  status: "pending" | "accepted" | "rejected" | "modified";
  dm_notes: string | null;
  created_at: string;
}

// ---- Store shape ----

interface GameState {
  sessionId: string | null;
  worldId: string | null;
  // DM token entered by this browser (null = player). isDM flips to true
  // only after the server confirms the token via GET /api/auth/role.
  dmToken: string | null;
  isDM: boolean;
  messages: ChatMessage[];
  isLoading: boolean;
  combat: ActiveCombat | null;
  currentLocation: LocationData | null;
  characters: CharacterData[];
  proposals: ProposalData[];
  tokenPositions: Record<string, TokenPosition>;

  setSession: (sessionId: string, worldId: string) => void;
  clearSession: () => void;
  setDmToken: (token: string | null) => void;
  setIsDM: (isDM: boolean) => void;
  addMessage: (msg: ChatMessage) => void;
  setMessages: (messages: ChatMessage[]) => void;
  moveToken: (tokenId: string, x: number, y: number) => void;
  setLoading: (loading: boolean) => void;
  setCombat: (combat: ActiveCombat | null) => void;
  setLocation: (location: LocationData | null) => void;
  setCharacters: (characters: CharacterData[]) => void;
  upsertCharacter: (char: CharacterData) => void;
  addProposal: (proposal: ProposalData) => void;
  updateProposal: (proposalId: string, updates: Partial<ProposalData>) => void;
}

const initialState = {
  sessionId: null,
  worldId: null,
  dmToken: null as string | null,
  isDM: false,
  messages: [] as ChatMessage[],
  isLoading: false,
  combat: null,
  currentLocation: null,
  characters: [] as CharacterData[],
  proposals: [] as ProposalData[],
  tokenPositions: {} as Record<string, TokenPosition>,
};

// sessionId / worldId / tokenPositions are persisted to localStorage so a
// page refresh (or closing the laptop between game days) resumes the same
// session. dmToken / isDM are persisted to sessionStorage instead (see
// splitStorage above) so DM authority stays scoped to the tab it was entered
// in. Everything else is re-hydrated from the API on load.
export const useGameStore = create<GameState>()(
  persist(
    (set) => ({
      ...initialState,
      setSession: (sessionId, worldId) => set({ sessionId, worldId }),
      // Leaving a session keeps the DM credentials — the DM shouldn't have
      // to re-enter the token to start next week's session.
      clearSession: () =>
        set((s) => ({ ...initialState, dmToken: s.dmToken, isDM: s.isDM })),
      setDmToken: (dmToken) => set({ dmToken }),
      setIsDM: (isDM) => set({ isDM }),
      // Dedupes by id: the same message can arrive via hydration (GET
      // /messages) and the WebSocket broadcast — server-assigned ids match.
      addMessage: (msg) =>
        set((s) =>
          s.messages.some((m) => m.id === msg.id) ? s : { messages: [...s.messages, msg] }
        ),
      setMessages: (messages) => set({ messages }),
      moveToken: (tokenId, x, y) =>
        set((s) => ({ tokenPositions: { ...s.tokenPositions, [tokenId]: { x, y } } })),
      setLoading: (loading) => set({ isLoading: loading }),
      setCombat: (combat) => set({ combat }),
      setLocation: (location) => set({ currentLocation: location }),
      setCharacters: (characters) => set({ characters }),
      upsertCharacter: (char) =>
        set((s) => {
          const idx = s.characters.findIndex((c) => c.id === char.id);
          if (idx >= 0) {
            const updated = [...s.characters];
            updated[idx] = char;
            return { characters: updated };
          }
          return { characters: [...s.characters, char] };
        }),
      addProposal: (proposal) =>
        set((s) => {
          const idx = s.proposals.findIndex((p) => p.id === proposal.id);
          if (idx >= 0) {
            const updated = [...s.proposals];
            updated[idx] = proposal;
            return { proposals: updated };
          }
          return { proposals: [...s.proposals, proposal] };
        }),
      updateProposal: (proposalId, updates) =>
        set((s) => ({
          proposals: s.proposals.map((p) => (p.id === proposalId ? { ...p, ...updates } : p)),
        })),
    }),
    {
      name: "dmai-game",
      storage: createJSONStorage(() => splitStorage),
      partialize: (s) => ({
        sessionId: s.sessionId,
        worldId: s.worldId,
        dmToken: s.dmToken,
        isDM: s.isDM,
        tokenPositions: s.tokenPositions,
      }),
    }
  )
);
