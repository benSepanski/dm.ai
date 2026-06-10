import { useCallback, useEffect, useRef } from "react";
import { api, type CombatStateResponse } from "./client";
import { mapCharacterResponse, mapCombatResponse } from "./mappers";
import { useGameStore } from "../store/gameStore";

// The WS route lives under the API router (/api/ws/...), so it shares the
// /api dev-server proxy with the REST endpoints.
const WS_BASE = "/api/ws";

const RECONNECT_DELAY_MS = 2000;

// Client→client event relayed verbatim by the backend peer relay
// (see dm-api ws.py): one browser drags a token, all others apply the move.
export interface MapTokenMoveEvent {
  type: "map_token_move";
  token_id: string;
  x: number;
  y: number;
}

// Shape of events received over the WebSocket (server-push + peer relay).
type WsEvent =
  | {
      type: "chat_message";
      session_id: string;
      message_id?: string;
      role: "dm" | "ai" | "system";
      content: string;
    }
  | { type: "combat_update"; session_id: string; combat: CombatStateResponse }
  | { type: "proposal_ready"; session_id: string; proposal_id: string; proposal_type: string; status?: string }
  | { type: "entity_update"; session_id: string; entity_type: string; entity_id: string }
  | (MapTokenMoveEvent & { session_id: string });

export type SendWsEvent = (event: MapTokenMoveEvent) => void;

export function useSessionWebSocket(
  sessionId: string | null,
  onReconnect?: () => void
): SendWsEvent {
  const {
    addMessage,
    setCombat,
    addProposal,
    updateProposal,
    upsertCharacter,
    setLocation,
    moveToken,
  } = useGameStore();
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!sessionId) return;

    let disposed = false;
    let retryTimer: number | undefined;
    let hadConnected = false;

    const handleEvent = (evt: MessageEvent) => {
      let event: WsEvent;
      try {
        event = JSON.parse(evt.data as string) as WsEvent;
      } catch {
        return;
      }

      if (event.type === "chat_message" && (event.role === "dm" || event.role === "ai")) {
        addMessage({
          id: event.message_id ?? crypto.randomUUID(),
          role: event.role,
          content: event.content,
          timestamp: new Date().toISOString(),
        });
      } else if (event.type === "combat_update") {
        setCombat(mapCombatResponse(event.combat));
      } else if (event.type === "map_token_move") {
        moveToken(event.token_id, event.x, event.y);
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
            .then((char) => upsertCharacter(mapCharacterResponse(char)))
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

    // Connect with auto-reconnect: laptop sleep or a server restart drops the
    // socket; on re-open the caller's onReconnect re-hydrates missed state.
    const connect = () => {
      const ws = new WebSocket(`${WS_BASE}/sessions/${sessionId}`);
      wsRef.current = ws;
      ws.onmessage = handleEvent;
      ws.onopen = () => {
        if (hadConnected) onReconnect?.();
        hadConnected = true;
      };
      ws.onclose = () => {
        if (wsRef.current === ws) wsRef.current = null;
        if (!disposed) retryTimer = window.setTimeout(connect, RECONNECT_DELAY_MS);
      };
    };
    connect();

    return () => {
      disposed = true;
      if (retryTimer !== undefined) window.clearTimeout(retryTimer);
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [
    sessionId,
    onReconnect,
    addMessage,
    setCombat,
    addProposal,
    updateProposal,
    upsertCharacter,
    setLocation,
    moveToken,
  ]);

  return useCallback((event: MapTokenMoveEvent) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(event));
    }
  }, []);
}
