import { useState } from "react";
import { api, type CharacterResponse } from "../../api/client";

/** Clamps a numeric text input to [min, max] (or [min, +inf) if max is omitted); blank stays blank. */
function clampInput(raw: string, min: number, max?: number): string {
  if (raw.trim() === "") return "";
  const parsed = Number(raw);
  if (Number.isNaN(parsed)) return "";
  const clamped = Math.max(min, max !== undefined ? Math.min(max, parsed) : parsed);
  return String(clamped);
}

interface Props {
  worldId: string;
  sessionId: string;
  onCreated: (character: CharacterResponse) => void;
  onCancel: () => void;
}

export default function CreateNpcDialog({ worldId, sessionId, onCreated, onCancel }: Props) {
  const [charType, setCharType] = useState<"NPC" | "MONSTER">("NPC");
  const [name, setName] = useState("");
  const [race, setRace] = useState("");
  const [charClass, setCharClass] = useState("");
  const [level, setLevel] = useState("1");
  const [hpMax, setHpMax] = useState("");
  const [ac, setAc] = useState("");
  const [personalityTraits, setPersonalityTraits] = useState("");
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
      const character = await api.createCharacter(
        {
          world_id: worldId,
          type: charType,
          name: name.trim(),
          race: race.trim() || undefined,
          char_class: charClass.trim() || undefined,
          level: parseInt(level) || 1,
          hp_max: hpMax ? parseInt(hpMax) : undefined,
          hp_current: hpMax ? parseInt(hpMax) : undefined,
          ac: ac ? parseInt(ac) : undefined,
          personality_traits: personalityTraits.trim() || undefined,
        },
        sessionId,
      );
      onCreated(character);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create character.");
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

  const numberInputStyle: React.CSSProperties = {
    ...inputStyle,
    width: "100%",
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
          width: 380,
          boxShadow: "0 8px 32px rgba(0,0,0,0.6)",
          maxHeight: "90vh",
          overflow: "auto",
        }}
      >
        <h3 style={{ margin: "0 0 16px", fontSize: 16, color: "#e0d7ff" }}>
          Create NPC / Monster
        </h3>

        <label style={{ fontSize: 12, color: "#aaa", display: "block", marginBottom: 4 }}>
          Type
        </label>
        <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
          {(["NPC", "MONSTER"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setCharType(t)}
              style={{
                flex: 1,
                padding: "6px 0",
                background: charType === t ? "#2980b9" : "#333",
                color: charType === t ? "#fff" : "#aaa",
                border: "none",
                borderRadius: 4,
                cursor: "pointer",
                fontSize: 13,
                fontWeight: charType === t ? "bold" : "normal",
              }}
            >
              {t}
            </button>
          ))}
        </div>

        <label style={{ fontSize: 12, color: "#aaa", display: "block", marginBottom: 4 }}>
          Name *
        </label>
        <input
          style={inputStyle}
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder={charType === "NPC" ? "e.g. Harbormaster Aldric" : "e.g. Giant Spider"}
          autoFocus
        />

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          <div>
            <label style={{ fontSize: 12, color: "#aaa", display: "block", marginBottom: 4 }}>
              Race
            </label>
            <input
              style={inputStyle}
              value={race}
              onChange={(e) => setRace(e.target.value)}
              placeholder="e.g. Human"
            />
          </div>
          <div>
            <label style={{ fontSize: 12, color: "#aaa", display: "block", marginBottom: 4 }}>
              Class / Role
            </label>
            <input
              style={inputStyle}
              value={charClass}
              onChange={(e) => setCharClass(e.target.value)}
              placeholder="e.g. Guard"
            />
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
          <div>
            <label style={{ fontSize: 12, color: "#aaa", display: "block", marginBottom: 4 }}>
              Level
            </label>
            <input
              type="number"
              min={1}
              max={20}
              style={numberInputStyle}
              value={level}
              onChange={(e) => setLevel(clampInput(e.target.value, 1, 20))}
            />
          </div>
          <div>
            <label style={{ fontSize: 12, color: "#aaa", display: "block", marginBottom: 4 }}>
              HP Max
            </label>
            <input
              type="number"
              min={1}
              style={numberInputStyle}
              value={hpMax}
              onChange={(e) => setHpMax(clampInput(e.target.value, 1))}
              placeholder="—"
            />
          </div>
          <div>
            <label style={{ fontSize: 12, color: "#aaa", display: "block", marginBottom: 4 }}>
              AC
            </label>
            <input
              type="number"
              min={1}
              style={numberInputStyle}
              value={ac}
              onChange={(e) => setAc(clampInput(e.target.value, 1))}
              placeholder="—"
            />
          </div>
        </div>
        <p style={{ margin: "-4px 0 10px", fontSize: 11, color: "#888" }}>
          Level, HP Max, and AC must be positive — values below 1 are clamped.
        </p>

        <label style={{ fontSize: 12, color: "#aaa", display: "block", marginBottom: 4 }}>
          Notes / Personality (optional)
        </label>
        <textarea
          style={{ ...inputStyle, resize: "vertical", minHeight: 54 }}
          value={personalityTraits}
          onChange={(e) => setPersonalityTraits(e.target.value)}
          placeholder="Brief description or personality notes…"
          rows={2}
        />

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
              background: busy || !name.trim() ? "#444" : "#2980b9",
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
