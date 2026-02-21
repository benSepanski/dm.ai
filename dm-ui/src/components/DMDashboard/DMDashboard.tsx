import { useCallback, useRef, useState } from "react";
import { api } from "../../api/client";
import { useGameStore } from "../../store/gameStore";
import CharacterCard from "../CharacterCard/CharacterCard";
import CombatTracker from "../CombatTracker/CombatTracker";
import LocationPanel from "../LocationPanel/LocationPanel";
import BattleMap from "../BattleMap/BattleMap";
import NewSessionForm from "./NewSessionForm";

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
  const { sessionId, messages, isLoading, addMessage, setLoading } =
    useGameStore();
  const [input, setInput] = useState("");
  const [showMap, setShowMap] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const sendMessage = useCallback(async () => {
    if (!sessionId || !input.trim()) return;
    const text = input.trim();
    setInput("");
    setLoading(true);

    addMessage({
      id: crypto.randomUUID(),
      role: "dm",
      content: text,
      timestamp: new Date().toISOString(),
    });

    try {
      const res = await api.chat(sessionId, text);
      addMessage({
        id: crypto.randomUUID(),
        role: "ai",
        content: res.response,
        timestamp: new Date().toISOString(),
      });
    } catch (err) {
      addMessage({
        id: crypto.randomUUID(),
        role: "system",
        content: `Error: ${err instanceof Error ? err.message : "Unknown error"}`,
        timestamp: new Date().toISOString(),
      });
    } finally {
      setLoading(false);
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [sessionId, input, addMessage, setLoading]);

  if (!sessionId) {
    return (
      <div
        style={{
          height: "100vh",
          background: "#0d0d1a",
          color: "#fff",
          fontFamily: "sans-serif",
        }}
      >
        <NewSessionForm />
      </div>
    );
  }

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
            <BattleMap />
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
              <p style={{ margin: 0, lineHeight: 1.6, fontSize: 14 }}>{m.content}</p>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        {/* Input bar */}
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
            placeholder={
              sessionId ? "Describe what happens…" : "Start a session first"
            }
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
      </main>

      {/* Right panel */}
      <aside
        style={{
          width: 300,
          borderLeft: "1px solid #333",
          padding: 16,
          overflow: "auto",
        }}
      >
        <CombatTracker />
      </aside>
    </div>
  );
}
