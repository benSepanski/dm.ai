import { useCallback, useState } from "react";
import { api } from "../../api/client";
import { useGameStore } from "../../store/gameStore";

// Top-bar control for entering the DM token. The token is verified against
// GET /api/auth/role before being kept; a wrong token never sticks around.
export default function DMUnlock() {
  const { setDmToken, setIsDM } = useGameStore();
  const [open, setOpen] = useState(false);
  const [token, setToken] = useState("");
  const [error, setError] = useState(false);
  const [checking, setChecking] = useState(false);

  const submit = useCallback(async () => {
    const candidate = token.trim();
    if (!candidate || checking) return;
    setChecking(true);
    setError(false);
    // Store the candidate so the API client sends it, then ask the server
    // what role it grants.
    setDmToken(candidate);
    try {
      const res = await api.getRole();
      if (res.role === "dm") {
        setIsDM(true);
        setOpen(false);
        setToken("");
      } else {
        setDmToken(null);
        setError(true);
      }
    } catch {
      setDmToken(null);
      setError(true);
    } finally {
      setChecking(false);
    }
  }, [token, checking, setDmToken, setIsDM]);

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        title="Enter the DM token (from .env or the API startup logs) to unlock DM controls"
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
        Unlock DM
      </button>
    );
  }

  return (
    <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <input
        type="password"
        value={token}
        onChange={(e) => {
          setToken(e.target.value);
          setError(false);
        }}
        onKeyDown={(e) => e.key === "Enter" && submit()}
        placeholder="DM token"
        autoFocus
        style={{
          padding: "4px 8px",
          borderRadius: 4,
          border: error ? "1px solid #f44336" : "1px solid #555",
          background: "#111",
          color: "#fff",
          fontSize: 12,
          width: 140,
        }}
      />
      {error && <span style={{ color: "#f44336", fontSize: 11 }}>Invalid token</span>}
      <button
        onClick={submit}
        disabled={checking || !token.trim()}
        style={{
          padding: "4px 10px",
          background: checking || !token.trim() ? "#444" : "#7c6af7",
          color: "#fff",
          border: "none",
          borderRadius: 4,
          cursor: checking || !token.trim() ? "not-allowed" : "pointer",
          fontSize: 12,
        }}
      >
        {checking ? "…" : "Unlock"}
      </button>
      <button
        onClick={() => {
          setOpen(false);
          setToken("");
          setError(false);
        }}
        style={{
          padding: "4px 8px",
          background: "#333",
          color: "#aaa",
          border: "none",
          borderRadius: 4,
          cursor: "pointer",
          fontSize: 12,
        }}
      >
        Cancel
      </button>
    </span>
  );
}
