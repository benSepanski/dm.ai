import { create } from "zustand";
import { persist } from "zustand/middleware";

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
  messages: ChatMessage[];
  isLoading: boolean;
  combat: ActiveCombat | null;
  currentLocation: LocationData | null;
  characters: CharacterData[];
  proposals: ProposalData[];
  tokenPositions: Record<string, TokenPosition>;

  setSession: (sessionId: string, worldId: string) => void;
  clearSession: () => void;
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
// session. Everything else is re-hydrated from the API on load.
export const useGameStore = create<GameState>()(
  persist(
    (set) => ({
      ...initialState,
      setSession: (sessionId, worldId) => set({ sessionId, worldId }),
      clearSession: () => set({ ...initialState }),
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
      partialize: (s) => ({
        sessionId: s.sessionId,
        worldId: s.worldId,
        tokenPositions: s.tokenPositions,
      }),
    }
  )
);
