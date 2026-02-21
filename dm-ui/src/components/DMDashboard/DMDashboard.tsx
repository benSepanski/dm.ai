import { useCallback, useRef, useState } from "react";
import { api } from "../../api/client";
import { useGameStore } from "../../store/gameStore";
import CharacterCard from "../CharacterCard/CharacterCard";
import CombatTracker from "../CombatTracker/CombatTracker";
import LocationPanel from "../LocationPanel/LocationPanel";

export default function DMDashboard() {
  const { sessionId, messages, isLoading, addMessage, setLoading } =
    useGameStore();
  const [input, setInput] = useState("");
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

  return (
    <div style={{ display: "flex", height: "100vh", fontFamily: "sans-serif" }}>
      {/* Sidebar */}
      <aside style={{ width: 280, borderRight: "1px solid #333", padding: 16, overflow: "auto" }}>
        <h2>dm.ai</h2>
        <LocationPanel />
        <CharacterCard />
      </aside>

      {/* Main chat area */}
      <main style={{ flex: 1, display: "flex", flexDirection: "column" }}>
        <div style={{ flex: 1, overflow: "auto", padding: 16 }}>
          {messages.map((m) => (
            <div
              key={m.id}
              style={{
                marginBottom: 12,
                padding: 8,
                borderRadius: 6,
                background: m.role === "ai" ? "#1a1a2e" : "#16213e",
              }}
            >
              <strong>{m.role.toUpperCase()}</strong>
              <p style={{ margin: "4px 0 0" }}>{m.content}</p>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        <div style={{ display: "flex", padding: 12, borderTop: "1px solid #333" }}>
          <input
            style={{ flex: 1, padding: 8, borderRadius: 4, border: "1px solid #555" }}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && sendMessage()}
            placeholder={sessionId ? "Describe what happens..." : "Start a session first"}
            disabled={!sessionId || isLoading}
          />
          <button
            style={{ marginLeft: 8, padding: "8px 16px" }}
            onClick={sendMessage}
            disabled={!sessionId || isLoading}
          >
            {isLoading ? "..." : "Send"}
          </button>
        </div>
      </main>

      {/* Right panel */}
      <aside style={{ width: 300, borderLeft: "1px solid #333", padding: 16, overflow: "auto" }}>
        <CombatTracker />
      </aside>
    </div>
  );
}
