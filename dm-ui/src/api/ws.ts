import { useEffect, useRef } from "react";
import { type CombatStateResponse } from "./client";
import { useGameStore } from "../store/gameStore";

const WS_BASE = "/ws";

// Shape of server-push events received over the WebSocket.
type WsEvent =
  | { type: "chat_message"; session_id: string; role: "dm" | "ai" | "system"; content: string }
  | { type: "combat_update"; session_id: string; combat: CombatStateResponse }
  | { type: "proposal_ready"; session_id: string; proposal_id: string; proposal_type: string; status?: string }
  | { type: "entity_update"; session_id: string; entity_type: string; entity_id: string };

function mapCombatFromWs(combat: CombatStateResponse) {
  const order = combat.initiative_order ?? [];
  const data = combat.combatants ?? [];
  return {
    id: combat.id,
    round_number: combat.round_number,
    current_turn_index: combat.current_turn_index,
    combatants: order.map((entry, i) => ({
      char_id: entry.character_id,
      name: entry.name,
      hp_current: data[i]?.hp_current ?? 0,
      hp_max: data[i]?.hp_max ?? 0,
      ac: data[i]?.ac ?? 10,
      initiative: entry.initiative,
      is_current_turn: i === combat.current_turn_index,
    })),
  };
}

export function useSessionWebSocket(sessionId: string | null): void {
  const { addMessage, setCombat } = useGameStore();
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!sessionId) return;

    const ws = new WebSocket(`${WS_BASE}/sessions/${sessionId}`);
    wsRef.current = ws;

    ws.onmessage = (evt) => {
      let event: WsEvent;
      try {
        event = JSON.parse(evt.data) as WsEvent;
      } catch {
        return;
      }

      if (event.type === "chat_message" && event.role === "ai") {
        addMessage({
          id: crypto.randomUUID(),
          role: "ai",
          content: event.content,
          timestamp: new Date().toISOString(),
        });
      } else if (event.type === "combat_update") {
        setCombat(mapCombatFromWs(event.combat));
      }
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [sessionId, addMessage, setCombat]);
}
