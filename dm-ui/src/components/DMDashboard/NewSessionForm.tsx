import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../../api/client";
import { mapCharacterResponse } from "../../api/mappers";
import { useGameStore } from "../../store/gameStore";

export default function NewSessionForm() {
  const { setSession, setCharacters, setDmToken, setIsDM, dmToken } = useGameStore();
  const [worldName, setWorldName] = useState("My World");
  const [sessionName, setSessionName] = useState("Session 1");
  // Creating a world/session is a DM action — the server wants the DM token
  // (set DM_TOKEN in .env, or copy the generated one from the API logs).
  const [token, setToken] = useState(dmToken ?? "");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const handleStart = async () => {
    setLoading(true);
    setError(null);
    // Store the token first so the API client sends it on the calls below.
    setDmToken(token.trim() || null);
    try {
      const world = await api.createWorld({ name: worldName });
      // The DM-gated call succeeded, so this browser is the DM.
      setIsDM(true);
      const session = await api.createSession({
        world_id: world.id,
        name: sessionName,
      });
      // Seed the store with any characters that already exist in the world.
      const chars = await api.listWorldCharacters(world.id).catch(() => []);
      setCharacters(chars.map(mapCharacterResponse));
      setSession(session.id, world.id);
      navigate(`/session/${session.id}`, { replace: true });
    } catch (err) {
      console.error("Failed to start session:", err);
      const message = err instanceof Error ? err.message : "Failed to start session";
      setError(
        message.includes("DM token required")
          ? "Invalid DM token — check DM_TOKEN in .env or the API startup logs."
          : message
      );
    } finally {
      setLoading(false);
    }
  };

  const isDisabled = loading || !worldName.trim() || !sessionName.trim() || !token.trim();

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

        <label style={{ display: "block", marginBottom: 16 }}>
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

        <label style={{ display: "block", marginBottom: 24 }}>
          <span style={{ fontSize: 12, color: "#aaa", display: "block", marginBottom: 4 }}>
            DM Token
          </span>
          <input
            type="password"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            disabled={loading}
            placeholder="From DM_TOKEN in .env, or the API startup logs"
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
          <span style={{ fontSize: 11, color: "#666", display: "block", marginTop: 4 }}>
            Only the DM creates sessions — players just open the invite link.
          </span>
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
