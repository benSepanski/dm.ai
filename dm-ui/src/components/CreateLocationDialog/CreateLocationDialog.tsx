import { useState } from "react";
import { api, type LocationResponse } from "../../api/client";

const LOCATION_TYPES = [
  "realm",
  "country",
  "region",
  "town",
  "district",
  "building",
  "room",
  "dungeon",
  "wilderness",
] as const;

interface Props {
  worldId: string;
  sessionId: string;
  onCreated: (location: LocationResponse) => void;
  onCancel: () => void;
}

export default function CreateLocationDialog({ worldId, sessionId, onCreated, onCancel }: Props) {
  const [name, setName] = useState("");
  const [type, setType] = useState<string>("town");
  const [description, setDescription] = useState("");
  const [setAsCurrent, setSetAsCurrent] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!name.trim()) {
      setError("Name is required.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const location = await api.createLocation({
        world_id: worldId,
        type,
        name: name.trim(),
        description: description.trim() || undefined,
      });
      if (setAsCurrent) {
        await api.patchSession(sessionId, { current_location_id: location.id });
      }
      onCreated(location);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create location.");
    } finally {
      setBusy(false);
    }
  };

  const inputStyle: React.CSSProperties = {
    width: "100%",
    padding: "6px 8px",
    borderRadius: 4,
    border: "1px solid #555",
    background: "#111",
    color: "#fff",
    fontSize: 13,
    boxSizing: "border-box",
    marginBottom: 10,
  };

  return (
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
          borderRadius: 8,
          padding: 24,
          width: 360,
          boxShadow: "0 8px 32px rgba(0,0,0,0.6)",
        }}
      >
        <h3 style={{ margin: "0 0 16px", fontSize: 16, color: "#e0d7ff" }}>Create Location</h3>

        <label style={{ fontSize: 12, color: "#aaa", display: "block", marginBottom: 4 }}>
          Name *
        </label>
        <input
          style={inputStyle}
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. The Saltmarsh Light"
          autoFocus
        />

        <label style={{ fontSize: 12, color: "#aaa", display: "block", marginBottom: 4 }}>
          Type
        </label>
        <select
          style={{ ...inputStyle, cursor: "pointer" }}
          value={type}
          onChange={(e) => setType(e.target.value)}
        >
          {LOCATION_TYPES.map((t) => (
            <option key={t} value={t}>
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </option>
          ))}
        </select>

        <label style={{ fontSize: 12, color: "#aaa", display: "block", marginBottom: 4 }}>
          Description (optional)
        </label>
        <textarea
          style={{ ...inputStyle, resize: "vertical", minHeight: 64 }}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Brief description…"
          rows={3}
        />

        <label
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            fontSize: 13,
            color: "#ccc",
            marginBottom: 14,
            cursor: "pointer",
          }}
        >
          <input
            type="checkbox"
            checked={setAsCurrent}
            onChange={(e) => setSetAsCurrent(e.target.checked)}
          />
          Set as current location
        </label>

        {error && (
          <p style={{ color: "#f44336", fontSize: 12, margin: "0 0 10px" }}>{error}</p>
        )}

        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <button
            onClick={onCancel}
            disabled={busy}
            style={{
              padding: "7px 16px",
              background: "#333",
              color: "#ccc",
              border: "none",
              borderRadius: 4,
              cursor: "pointer",
              fontSize: 13,
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={busy || !name.trim()}
            style={{
              padding: "7px 16px",
              background: busy || !name.trim() ? "#444" : "#27ae60",
              color: busy || !name.trim() ? "#666" : "#fff",
              border: "none",
              borderRadius: 4,
              cursor: busy || !name.trim() ? "not-allowed" : "pointer",
              fontSize: 13,
              fontWeight: "bold",
            }}
          >
            {busy ? "Creating…" : "Create"}
          </button>
        </div>
      </div>
    </div>
  );
}
