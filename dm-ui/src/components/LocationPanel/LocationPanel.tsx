import { useState } from "react";
import { useGameStore } from "../../store/gameStore";
import CreateLocationDialog from "../CreateLocationDialog/CreateLocationDialog";

const TYPE_COLORS: Record<string, string> = {
  realm: "#9b59b6",
  country: "#8e44ad",
  region: "#27ae60",
  town: "#2980b9",
  district: "#16a085",
  building: "#d35400",
  room: "#c0392b",
  dungeon: "#7f8c8d",
  wilderness: "#27ae60",
};

export default function LocationPanel() {
  const { currentLocation, isDM, worldId, sessionId, setLocation } = useGameStore();
  const [showCreate, setShowCreate] = useState(false);

  const typeColor = currentLocation
    ? (TYPE_COLORS[currentLocation.type] ?? "#888")
    : "#888";

  return (
    <section>
      <h3
        style={{
          fontSize: 14,
          color: "#ccc",
          textTransform: "uppercase",
          margin: "0 0 8px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        Location
        {isDM && worldId && sessionId && (
          <button
            onClick={() => setShowCreate(true)}
            title="Create a new location and optionally set it as the current location"
            style={{
              fontSize: 11,
              padding: "2px 8px",
              background: "#333",
              color: "#aaa",
              border: "none",
              borderRadius: 4,
              cursor: "pointer",
            }}
          >
            + New
          </button>
        )}
      </h3>

      {!currentLocation ? (
        <p style={{ color: "#555", fontSize: 13 }}>No location set.</p>
      ) : (
        <div style={{ background: "#1a1a2e", borderRadius: 6, padding: 10 }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 6,
            }}
          >
            <span style={{ fontWeight: "bold", fontSize: 15 }}>{currentLocation.name}</span>
            <span
              style={{
                fontSize: 11,
                padding: "2px 6px",
                borderRadius: 10,
                background: typeColor + "33",
                color: typeColor,
                textTransform: "uppercase",
              }}
            >
              {currentLocation.type}
            </span>
          </div>
          {currentLocation.description && (
            <p style={{ fontSize: 13, color: "#bbb", margin: 0, lineHeight: 1.5 }}>
              {currentLocation.description}
            </p>
          )}
        </div>
      )}

      {showCreate && worldId && sessionId && (
        <CreateLocationDialog
          worldId={worldId}
          sessionId={sessionId}
          onCreated={(loc) => {
            setLocation({ id: loc.id, name: loc.name, type: loc.type, description: loc.description });
            setShowCreate(false);
          }}
          onCancel={() => setShowCreate(false)}
        />
      )}
    </section>
  );
}
