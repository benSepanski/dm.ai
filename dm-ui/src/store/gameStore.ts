import { create } from "zustand";

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
  stats: Record<string, number> | null;
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

  setSession: (sessionId: string, worldId: string) => void;
  addMessage: (msg: ChatMessage) => void;
  setMessages: (msgs: ChatMessage[]) => void;
  setLoading: (loading: boolean) => void;
  setCombat: (combat: ActiveCombat | null) => void;
  setLocation: (location: LocationData | null) => void;
  setCharacters: (characters: CharacterData[]) => void;
  reset: () => void;
}

const initialState = {
  sessionId: null,
  worldId: null,
  messages: [],
  isLoading: false,
  combat: null,
  currentLocation: null,
  characters: [],
};

export const useGameStore = create<GameState>((set) => ({
  ...initialState,
  setSession: (sessionId, worldId) => set({ sessionId, worldId }),
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  setMessages: (msgs) => set({ messages: msgs }),
  setLoading: (loading) => set({ isLoading: loading }),
  setCombat: (combat) => set({ combat }),
  setLocation: (location) => set({ currentLocation: location }),
  setCharacters: (characters) => set({ characters }),
  reset: () => set(initialState),
}));
