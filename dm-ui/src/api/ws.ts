import { useEffect, useRef } from "react";
import { api, type CombatStateResponse } from "./client";
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
  const { addMessage, setCombat, addProposal, updateProposal, upsertCharacter, setLocation } =
    useGameStore();
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
      } else if (event.type === "proposal_ready") {
        const status = event.status;
        if (!status || status === "pending") {
          // Fetch full proposal data and add to store.
          api.getProposal(event.proposal_id).then(addProposal).catch(console.error);
        } else {
          // Proposal was accepted or rejected — update existing store entry.
          updateProposal(event.proposal_id, {
            status: status as "accepted" | "rejected" | "modified",
          });
        }
      } else if (event.type === "entity_update") {
        if (event.entity_type === "character") {
          api
            .getCharacter(event.entity_id)
            .then((char) =>
              upsertCharacter({
                id: char.id,
                name: char.name,
                char_class: char.char_class,
                race: char.race,
                level: char.level,
                hp_current: char.hp_current,
                hp_max: char.hp_max,
                ac: char.ac,
                stats: char.stats,
              })
            )
            .catch(console.error);
        } else if (event.entity_type === "location") {
          api
            .getLocation(event.entity_id)
            .then((loc) =>
              setLocation({
                id: loc.id,
                name: loc.name,
                type: loc.type,
                description: loc.description,
              })
            )
            .catch(console.error);
        }
      }
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [sessionId, addMessage, setCombat, addProposal, updateProposal, upsertCharacter, setLocation]);
}
