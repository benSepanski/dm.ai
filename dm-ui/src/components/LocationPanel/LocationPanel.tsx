import { useState } from "react";
import { api, type LocationResponse } from "../../api/client";
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
  const [showBrowse, setShowBrowse] = useState(false);
  const [allLocations, setAllLocations] = useState<LocationResponse[] | null>(null);
  const [browseError, setBrowseError] = useState<string | null>(null);

  const typeColor = currentLocation
    ? (TYPE_COLORS[currentLocation.type] ?? "#888")
    : "#888";

  // A location created via "+ New" without "Set as current" is otherwise
  // unreachable from the UI — this is the only place a DM can browse and
  // switch to it later.
  const toggleBrowse = () => {
    if (showBrowse) {
      setShowBrowse(false);
      return;
    }
    setShowBrowse(true);
    if (allLocations === null && worldId) {
      api
        .listWorldLocations(worldId)
        .then(setAllLocations)
        .catch((err) =>
          setBrowseError(err instanceof Error ? err.message : "Failed to load locations.")
        );
    }
  };

  const selectLocation = (loc: LocationResponse) => {
    if (!sessionId) return;
    api
      .patchSession(sessionId, { current_location_id: loc.id })
      .then(() => {
        setLocation({ id: loc.id, name: loc.name, type: loc.type, description: loc.description });
        setShowBrowse(false);
      })
      .catch((err) => setBrowseError(err instanceof Error ? err.message : "Failed to switch location."));
  };

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
          <span style={{ display: "flex", gap: 6 }}>
            <button
              onClick={toggleBrowse}
              title="Browse and switch to a previously created location"
              style={{
                fontSize: 11,
                padding: "2px 8px",
                background: showBrowse ? "#444" : "#333",
                color: "#aaa",
                border: "none",
                borderRadius: 4,
                cursor: "pointer",
              }}
            >
              Change
            </button>
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
          </span>
        )}
      </h3>

      {showBrowse && (
        <div style={{ background: "#1a1a2e", borderRadius: 6, padding: 10, marginBottom: 8 }}>
          {browseError && (
            <p style={{ color: "#f44336", fontSize: 12, margin: "0 0 8px" }}>{browseError}</p>
          )}
          {allLocations === null ? (
            <p style={{ color: "#777", fontSize: 12, margin: 0 }}>Loading…</p>
          ) : allLocations.length === 0 ? (
            <p style={{ color: "#777", fontSize: 12, margin: 0 }}>No locations yet.</p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {allLocations.map((loc) => (
                <button
                  key={loc.id}
                  onClick={() => selectLocation(loc)}
                  disabled={loc.id === currentLocation?.id}
                  style={{
                    textAlign: "left",
                    fontSize: 13,
                    padding: "5px 8px",
                    background: loc.id === currentLocation?.id ? "#27ae6033" : "#222",
                    color: loc.id === currentLocation?.id ? "#27ae60" : "#ddd",
                    border: "none",
                    borderRadius: 4,
                    cursor: loc.id === currentLocation?.id ? "default" : "pointer",
                  }}
                >
                  {loc.name} <span style={{ color: "#777" }}>({loc.type})</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

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
          onCreated={(loc, wasSetAsCurrent) => {
            if (wasSetAsCurrent) {
              setLocation({
                id: loc.id,
                name: loc.name,
                type: loc.type,
                description: loc.description,
              });
            }
            setAllLocations(null);
            setShowCreate(false);
          }}
          onCancel={() => setShowCreate(false)}
        />
      )}
    </section>
  );
}
