import { create } from "zustand";

interface ChatMessage {
  id: string;
  role: "dm" | "ai" | "system";
  content: string;
  timestamp: string;
}

interface GameState {
  sessionId: string | null;
  worldId: string | null;
  messages: ChatMessage[];
  isLoading: boolean;

  setSession: (sessionId: string, worldId: string) => void;
  addMessage: (msg: ChatMessage) => void;
  setMessages: (msgs: ChatMessage[]) => void;
  setLoading: (loading: boolean) => void;
  reset: () => void;
}

export const useGameStore = create<GameState>((set) => ({
  sessionId: null,
  worldId: null,
  messages: [],
  isLoading: false,

  setSession: (sessionId, worldId) => set({ sessionId, worldId }),
  addMessage: (msg) =>
    set((state) => ({ messages: [...state.messages, msg] })),
  setMessages: (msgs) => set({ messages: msgs }),
  setLoading: (loading) => set({ isLoading: loading }),
  reset: () =>
    set({ sessionId: null, worldId: null, messages: [], isLoading: false }),
}));
