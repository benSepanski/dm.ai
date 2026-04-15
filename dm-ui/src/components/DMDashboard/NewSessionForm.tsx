import { useState } from "react";
import { api } from "../../api/client";
import { useGameStore } from "../../store/gameStore";

export default function NewSessionForm() {
  const [worldName, setWorldName] = useState("My World");
  const [sessionName, setSessionName] = useState("Session 1");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { setSession } = useGameStore();

  const handleStart = async () => {
    setLoading(true);
    setError(null);
    try {
      const world = await api.createWorld({ name: worldName });
      const session = await api.createSession({
        world_id: world.id,
        name: sessionName,
      });
      setSession(session.id, world.id);
    } catch (err) {
      console.error("Failed to start session:", err);
      setError(err instanceof Error ? err.message : "Failed to start session");
    } finally {
      setLoading(false);
    }
  };

  const isDisabled = loading || !worldName.trim() || !sessionName.trim();

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        height: "100%",
        padding: 32,
      }}
    >
      <div
        style={{
          background: "#1a1a2e",
          borderRadius: 8,
          padding: 32,
          width: "100%",
          maxWidth: 420,
          boxShadow: "0 4px 24px rgba(0,0,0,0.4)",
        }}
      >
        <h2
          style={{
            margin: "0 0 24px",
            fontSize: 22,
            color: "#e0d7ff",
            textAlign: "center",
          }}
        >
          dm.ai — New Session
        </h2>

        <label style={{ display: "block", marginBottom: 16 }}>
          <span style={{ fontSize: 12, color: "#aaa", display: "block", marginBottom: 4 }}>
            World Name
          </span>
          <input
            value={worldName}
            onChange={(e) => setWorldName(e.target.value)}
            disabled={loading}
            style={{
              width: "100%",
              padding: "8px 10px",
              borderRadius: 4,
              border: "1px solid #444",
              background: "#111",
              color: "#fff",
              fontSize: 14,
              boxSizing: "border-box",
            }}
          />
        </label>

        <label style={{ display: "block", marginBottom: 24 }}>
          <span style={{ fontSize: 12, color: "#aaa", display: "block", marginBottom: 4 }}>
            Session Name
          </span>
          <input
            value={sessionName}
            onChange={(e) => setSessionName(e.target.value)}
            disabled={loading}
            style={{
              width: "100%",
              padding: "8px 10px",
              borderRadius: 4,
              border: "1px solid #444",
              background: "#111",
              color: "#fff",
              fontSize: 14,
              boxSizing: "border-box",
            }}
          />
        </label>

        {error && (
          <p
            style={{
              color: "#f44336",
              fontSize: 13,
              margin: "0 0 16px",
              background: "#2a1010",
              padding: "8px 10px",
              borderRadius: 4,
            }}
          >
            {error}
          </p>
        )}

        <button
          onClick={handleStart}
          disabled={isDisabled}
          style={{
            width: "100%",
            padding: "10px 0",
            background: isDisabled ? "#444" : "#7c6af7",
            color: "#fff",
            border: "none",
            borderRadius: 4,
            fontSize: 15,
            cursor: isDisabled ? "not-allowed" : "pointer",
            fontWeight: "bold",
          }}
        >
          {loading ? "Starting…" : "Start Session"}
        </button>
      </div>
    </div>
  );
}
