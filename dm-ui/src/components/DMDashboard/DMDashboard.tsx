import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import { api } from "../../api/client";
import { mapCharacterResponse, mapCombatResponse } from "../../api/mappers";
import { useSessionWebSocket } from "../../api/ws";
import { useGameStore } from "../../store/gameStore";
import CharacterCard from "../CharacterCard/CharacterCard";
import CombatTracker from "../CombatTracker/CombatTracker";
import LocationPanel from "../LocationPanel/LocationPanel";
import BattleMap from "../BattleMap/BattleMap";
import GameSettingsModal from "../GameSettings/GameSettingsModal";
import ProposalCard from "../ProposalCard/ProposalCard";
import DMUnlock from "./DMUnlock";

const ROLE_COLORS: Record<string, string> = {
  dm: "#16213e",
  ai: "#1a1a2e",
  system: "#1c1c1c",
};

const ROLE_LABELS: Record<string, string> = {
  dm: "DM",
  ai: "AI",
  system: "SYSTEM",
};

export default function DMDashboard() {
  const { sessionId: routeSessionId } = useParams<{ sessionId: string }>();
  const {
    sessionId,
    worldId,
    messages,
    isLoading,
    addMessage,
    setLoading,
    proposals,
    addProposal,
    setSession,
    clearSession,
    setMessages,
    setCharacters,
    setCombat,
    setLocation,
    moveToken,
    dmToken,
    isDM,
    setIsDM,
  } = useGameStore();
  const [input, setInput] = useState("");
  const [showMap, setShowMap] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [linkCopied, setLinkCopied] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  // Load (or re-load) all session state from the server. Runs on mount and
  // URL change, and again after a WebSocket reconnect to catch up on events
  // missed while the socket was down (laptop sleep, server restart).
  const hydrateSession = useCallback(async () => {
    if (!routeSessionId) return;
    try {
      const session = await api.getSession(routeSessionId);
      const [msgs, chars, combat, location] = await Promise.all([
        api.getSessionMessages(routeSessionId),
        api.listWorldCharacters(session.world_id).catch(() => []),
        api
          .getCombat(routeSessionId)
          .then(mapCombatResponse)
          .catch(() => null),
        session.current_location_id
          ? api.getLocation(session.current_location_id).catch(() => null)
          : Promise.resolve(null),
      ]);
      setSession(session.id, session.world_id);
      setMessages(
        msgs.map((m) => ({ id: m.id, role: m.role, content: m.content, timestamp: m.timestamp }))
      );
      setCharacters(chars.map(mapCharacterResponse));
      setCombat(combat);
      setLocation(
        location
          ? {
              id: location.id,
              name: location.name,
              type: location.type,
              description: location.description,
            }
          : null
      );
    } catch {
      // The session no longer exists (e.g. the database was reset) — forget
      // it and return to the new-session screen.
      clearSession();
      navigate("/", { replace: true });
    }
  }, [
    routeSessionId,
    setSession,
    setMessages,
    setCharacters,
    setCombat,
    setLocation,
    clearSession,
    navigate,
  ]);

  useEffect(() => {
    void hydrateSession();
  }, [hydrateSession]);

  // Verify the stored DM token against the server. The server is the only
  // authority on roles — a stale or wrong token quietly degrades to player.
  useEffect(() => {
    let cancelled = false;
    if (!dmToken) {
      setIsDM(false);
      return;
    }
    api
      .getRole()
      .then((r) => {
        if (!cancelled) setIsDM(r.role === "dm");
      })
      .catch(() => {
        if (!cancelled) setIsDM(false);
      });
    return () => {
      cancelled = true;
    };
  }, [dmToken, setIsDM]);

  // Real-time updates from the server via WebSocket; re-hydrate on reconnect.
  const sendWsEvent = useSessionWebSocket(sessionId, hydrateSession);

  // Load any existing proposals for this session (DM only — the endpoint
  // rejects players, who never see proposals).
  useEffect(() => {
    if (!sessionId || !isDM) return;
    api
      .listSessionProposals(sessionId)
      .then((list) => list.forEach(addProposal))
      .catch(console.error);
  }, [sessionId, isDM, addProposal]);

  // Auto-scroll when messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  const sendMessage = useCallback(async () => {
    if (!sessionId || !input.trim() || isLoading) return;
    const text = input.trim();
    setInput("");
    setLoading(true);

    try {
      // The DM echo and AI reply both arrive via the WebSocket broadcast
      // (with server-assigned ids, deduped in the store) so every connected
      // client renders the same conversation. The HTTP response only needs
      // to surface the proposals immediately.
      const res = await api.chat(sessionId, text);
      res.proposals.forEach(addProposal);
    } catch (err) {
      addMessage({
        id: crypto.randomUUID(),
        role: "system",
        content: `Error: ${err instanceof Error ? err.message : "Unknown error"}`,
        timestamp: new Date().toISOString(),
      });
    } finally {
      setLoading(false);
    }
  }, [sessionId, input, isLoading, addMessage, setLoading, addProposal]);

  const handleTokenMove = useCallback(
    (tokenId: string, x: number, y: number) => {
      moveToken(tokenId, x, y);
      sendWsEvent({ type: "map_token_move", token_id: tokenId, x, y });
    },
    [moveToken, sendWsEvent]
  );

  const copyInviteLink = useCallback(() => {
    const url = window.location.href;
    if (navigator.clipboard) {
      navigator.clipboard
        .writeText(url)
        .then(() => {
          setLinkCopied(true);
          window.setTimeout(() => setLinkCopied(false), 1500);
        })
        .catch(() => window.prompt("Copy this link:", url));
    } else {
      // Clipboard API needs a secure context; plain-HTTP LAN pages fall back.
      window.prompt("Copy this link:", url);
    }
  }, []);

  const startNewSession = useCallback(() => {
    clearSession();
    navigate("/", { replace: true });
  }, [clearSession, navigate]);

  // Wrap up the session: the server generates and stores an AI summary
  // (used for "previously on…" context in future sessions), then this
  // browser detaches. The session itself stays in the database.
  const [ending, setEnding] = useState(false);
  const [showEndConfirm, setShowEndConfirm] = useState(false);

  const confirmEndSession = useCallback(async () => {
    if (!sessionId || ending) return;
    setShowEndConfirm(false);
    setEnding(true);
    try {
      await api.endSession(sessionId);
      clearSession();
      navigate("/", { replace: true });
    } catch (err) {
      addMessage({
        id: crypto.randomUUID(),
        role: "system",
        content: `Error ending session: ${err instanceof Error ? err.message : "Unknown error"}`,
        timestamp: new Date().toISOString(),
      });
    } finally {
      setEnding(false);
    }
  }, [sessionId, ending, clearSession, navigate, addMessage]);

  if (!sessionId) {
    return (
      <div
        style={{
          height: "100vh",
          background: "#0d0d1a",
          color: "#888",
          fontFamily: "sans-serif",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        Loading session…
      </div>
    );
  }

  const pendingProposals = proposals.filter((p) => p.status === "pending");
  const resolvedProposals = proposals.filter((p) => p.status !== "pending");

  return (
    <div
      style={{
        display: "flex",
        height: "100vh",
        fontFamily: "sans-serif",
        background: "#0d0d1a",
        color: "#fff",
      }}
    >
      {/* Left sidebar */}
      <aside
        style={{
          width: 280,
          borderRight: "1px solid #333",
          padding: 16,
          overflow: "auto",
          display: "flex",
          flexDirection: "column",
          gap: 16,
        }}
      >
        <h2 style={{ margin: 0, fontSize: 18, color: "#e0d7ff" }}>dm.ai</h2>
        <LocationPanel />
        <CharacterCard />
      </aside>

      {/* Main area */}
      <main style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        {/* Map toggle bar */}
        <div
          style={{
            padding: "6px 12px",
            borderBottom: "1px solid #333",
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          <button
            onClick={() => setShowMap((v) => !v)}
            style={{
              padding: "4px 10px",
              background: showMap ? "#7c6af7" : "#333",
              color: "#fff",
              border: "none",
              borderRadius: 4,
              cursor: "pointer",
              fontSize: 12,
            }}
          >
            {showMap ? "Hide Map" : "Show Map"}
          </button>
          <span
            style={{
              fontSize: 11,
              padding: "2px 8px",
              borderRadius: 10,
              background: isDM ? "#7c6af733" : "#2e2e2e",
              color: isDM ? "#7c6af7" : "#888",
            }}
          >
            {isDM ? "DM" : "Player"}
          </span>
          <div style={{ flex: 1 }} />
          {!isDM && <DMUnlock />}
          {/* Game settings edit AI models and storage — DM only (the API
              rejects non-DM config reads/writes too). */}
          {isDM && worldId && (
            <button
              onClick={() => setShowSettings(true)}
              title="Per-game settings: AI models, context budget, and storage locations"
              style={{
                padding: "4px 10px",
                background: "#333",
                color: "#fff",
                border: "none",
                borderRadius: 4,
                cursor: "pointer",
                fontSize: 12,
              }}
            >
              Game Settings
            </button>
          )}
          {/* Players build their own PCs — creation stays open to everyone. */}
          <button
            onClick={() => worldId && navigate(`/world/${worldId}/create-character`)}
            disabled={!worldId}
            title="Build a level-1 player character with the 2024 PHB rules"
            style={{
              padding: "4px 10px",
              background: "#333",
              color: "#fff",
              border: "none",
              borderRadius: 4,
              cursor: worldId ? "pointer" : "not-allowed",
              fontSize: 12,
            }}
          >
            Create Character
          </button>
          <button
            onClick={copyInviteLink}
            title="Share this link with players on your network so they can watch the session"
            style={{
              padding: "4px 10px",
              background: linkCopied ? "#2e7d32" : "#333",
              color: "#fff",
              border: "none",
              borderRadius: 4,
              cursor: "pointer",
              fontSize: 12,
            }}
          >
            {linkCopied ? "Copied!" : "Copy Invite Link"}
          </button>
          {isDM && (
            <>
              <button
                onClick={() => setShowEndConfirm(true)}
                disabled={ending}
                title="End the session for everyone — saves an AI summary the next session will recall"
                style={{
                  padding: "4px 10px",
                  background: ending ? "#444" : "#8e2f2f",
                  color: "#fff",
                  border: "none",
                  borderRadius: 4,
                  cursor: ending ? "not-allowed" : "pointer",
                  fontSize: 12,
                }}
              >
                {ending ? "Ending…" : "End Session"}
              </button>
              <button
                onClick={startNewSession}
                title="Leave this session and start a new one (this session stays saved on the server)"
                style={{
                  padding: "4px 10px",
                  background: "#333",
                  color: "#fff",
                  border: "none",
                  borderRadius: 4,
                  cursor: "pointer",
                  fontSize: 12,
                }}
              >
                New Session
              </button>
            </>
          )}
        </div>

        {/* Battle map (collapsible) */}
        {showMap && (
          <div
            style={{
              borderBottom: "1px solid #333",
              padding: 12,
              overflow: "auto",
              background: "#111",
            }}
          >
            <BattleMap onTokenMove={handleTokenMove} />
          </div>
        )}

        {/* Chat messages */}
        <div style={{ flex: 1, overflow: "auto", padding: 16 }}>
          {messages.length === 0 && (
            <p style={{ color: "#555", fontSize: 13, textAlign: "center", marginTop: 32 }}>
              Session started. Describe what happens…
            </p>
          )}
          {messages.map((m) => (
            <div
              key={m.id}
              style={{
                marginBottom: 12,
                padding: 10,
                borderRadius: 6,
                background: ROLE_COLORS[m.role] ?? "#1a1a1a",
                borderLeft: m.role === "system" ? "3px solid #666" : "none",
              }}
            >
              <div
                style={{
                  fontSize: 11,
                  color: "#888",
                  marginBottom: 4,
                  textTransform: "uppercase",
                }}
              >
                {ROLE_LABELS[m.role] ?? m.role}
                <span style={{ marginLeft: 8, fontWeight: "normal" }}>
                  {new Date(m.timestamp).toLocaleTimeString()}
                </span>
              </div>
              <div style={{ margin: 0, lineHeight: 1.6, fontSize: 14 }}>
                <ReactMarkdown
                  components={{
                    p: ({ children }) => <p style={{ margin: "0 0 8px" }}>{children}</p>,
                    blockquote: ({ children }) => (
                      <blockquote
                        style={{
                          borderLeft: "3px solid #555",
                          margin: "8px 0",
                          paddingLeft: 10,
                          color: "#ccc",
                          fontStyle: "italic",
                        }}
                      >
                        {children}
                      </blockquote>
                    ),
                    hr: () => <hr style={{ border: "none", borderTop: "1px solid #444", margin: "8px 0" }} />,
                    h1: ({ children }) => <h1 style={{ fontSize: 16, margin: "8px 0 4px", color: "#e0d7ff" }}>{children}</h1>,
                    h2: ({ children }) => <h2 style={{ fontSize: 15, margin: "8px 0 4px", color: "#e0d7ff" }}>{children}</h2>,
                    h3: ({ children }) => <h3 style={{ fontSize: 14, margin: "8px 0 4px", color: "#e0d7ff" }}>{children}</h3>,
                    ul: ({ children }) => <ul style={{ margin: "4px 0", paddingLeft: 20 }}>{children}</ul>,
                    ol: ({ children }) => <ol style={{ margin: "4px 0", paddingLeft: 20 }}>{children}</ol>,
                    strong: ({ children }) => <strong style={{ color: "#f0eaff" }}>{children}</strong>,
                  }}
                >
                  {m.content}
                </ReactMarkdown>
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        {/* Input bar — only the DM narrates; players watch the story unfold */}
        {!isDM && (
          <div
            style={{
              padding: "10px 12px",
              borderTop: "1px solid #333",
              color: "#666",
              fontSize: 12,
              textAlign: "center",
            }}
          >
            You're watching as a player — the DM drives the story.
          </div>
        )}
        {isDM && (
        <div
          style={{
            display: "flex",
            padding: 12,
            borderTop: "1px solid #333",
            gap: 8,
          }}
        >
          <input
            style={{
              flex: 1,
              padding: "8px 12px",
              borderRadius: 4,
              border: "1px solid #555",
              background: "#111",
              color: "#fff",
              fontSize: 14,
            }}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage()}
            placeholder="Describe what happens…"
            disabled={!sessionId || isLoading}
          />
          <button
            style={{
              padding: "8px 16px",
              background: isLoading ? "#444" : "#7c6af7",
              color: "#fff",
              border: "none",
              borderRadius: 4,
              cursor: isLoading ? "not-allowed" : "pointer",
              fontWeight: "bold",
            }}
            onClick={sendMessage}
            disabled={!sessionId || isLoading}
          >
            {isLoading ? "…" : "Send"}
          </button>
        </div>
        )}
      </main>

      {/* Right panel */}
      <aside
        style={{
          width: 300,
          borderLeft: "1px solid #333",
          padding: 16,
          overflow: "auto",
          display: "flex",
          flexDirection: "column",
          gap: 16,
        }}
      >
        <CombatTracker />

        {/* Proposals panel — DM eyes only: unreviewed AI content */}
        {isDM && proposals.length > 0 && (
          <section>
            <h3
              style={{
                margin: "0 0 8px",
                fontSize: 14,
                color: "#ccc",
                textTransform: "uppercase",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              Proposals
              {pendingProposals.length > 0 && (
                <span
                  style={{
                    fontSize: 11,
                    padding: "2px 6px",
                    borderRadius: 10,
                    background: "#7c6af733",
                    color: "#7c6af7",
                  }}
                >
                  {pendingProposals.length} pending
                </span>
              )}
            </h3>
            {/* Pending proposals first */}
            {pendingProposals.map((p) => (
              <ProposalCard key={p.id} proposal={p} />
            ))}
            {/* Resolved proposals (collapsed appearance) */}
            {resolvedProposals.map((p) => (
              <ProposalCard key={p.id} proposal={p} />
            ))}
          </section>
        )}
      </aside>

      {showSettings && worldId && (
        <GameSettingsModal worldId={worldId} onClose={() => setShowSettings(false)} />
      )}

      {showEndConfirm && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.7)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
          }}
        >
          <div
            style={{
              background: "#1a1a2e",
              border: "1px solid #444",
              borderRadius: 8,
              padding: 24,
              maxWidth: 360,
              width: "90%",
            }}
          >
            <h3 style={{ margin: "0 0 12px", color: "#e0d7ff", fontSize: 16 }}>End Session?</h3>
            <p style={{ color: "#aaa", fontSize: 14, margin: "0 0 20px", lineHeight: 1.5 }}>
              This will end the session for everyone. An AI summary will be saved so the next
              session can pick up where you left off.
            </p>
            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
              <button
                onClick={() => setShowEndConfirm(false)}
                style={{
                  padding: "6px 16px",
                  background: "#333",
                  color: "#ccc",
                  border: "1px solid #555",
                  borderRadius: 4,
                  cursor: "pointer",
                  fontSize: 13,
                }}
              >
                Cancel
              </button>
              <button
                onClick={() => void confirmEndSession()}
                style={{
                  padding: "6px 16px",
                  background: "#8e2f2f",
                  color: "#fff",
                  border: "none",
                  borderRadius: 4,
                  cursor: "pointer",
                  fontSize: 13,
                  fontWeight: "bold",
                }}
              >
                End Session
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
