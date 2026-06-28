import { useCallback, useState } from "react";
import { api, type CombatStateResponse } from "../../api/client";
import { useGameStore, type ActiveCombat, type CharacterData, type Combatant } from "../../store/gameStore";

// Build the ActiveCombat view by zipping initiative_order (has initiative score)
// with combatants (has hp/ac). Both lists share the same index order set by
// start_combat and never reordered afterward.
function mapCombatResponse(result: CombatStateResponse): ActiveCombat {
  const order = result.initiative_order ?? [];
  const data = result.combatants ?? [];
  const combatants: Combatant[] = order.map((entry, i) => ({
    char_id: entry.character_id,
    name: entry.name,
    hp_current: data[i]?.hp_current ?? 0,
    hp_max: data[i]?.hp_max ?? 0,
    ac: data[i]?.ac ?? 10,
    initiative: entry.initiative,
    is_current_turn: i === result.current_turn_index,
  }));
  return {
    id: result.id,
    round_number: result.round_number,
    current_turn_index: result.current_turn_index,
    combatants,
  };
}

function CombatantRow({ combatant }: { combatant: Combatant }) {
  const pct =
    combatant.hp_max > 0
      ? Math.max(0, Math.min(100, (combatant.hp_current / combatant.hp_max) * 100))
      : 0;
  const color = pct > 50 ? "#4caf50" : pct > 25 ? "#ff9800" : "#f44336";
  return (
    <div
      style={{
        padding: "8px 10px",
        marginBottom: 4,
        borderRadius: 6,
        background: combatant.is_current_turn ? "#2a2a4e" : "#1a1a2e",
        borderLeft: combatant.is_current_turn
          ? "3px solid #7c6af7"
          : "3px solid transparent",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <span style={{ fontWeight: combatant.is_current_turn ? "bold" : "normal" }}>
          {combatant.is_current_turn ? "▶ " : ""}
          {combatant.name}
        </span>
        <span style={{ fontSize: 12, color: "#aaa" }}>Init {combatant.initiative}</span>
      </div>
      <div
        style={{ background: "#333", borderRadius: 3, height: 6, margin: "4px 0" }}
      >
        <div
          style={{
            width: `${pct}%`,
            background: color,
            height: "100%",
            borderRadius: 3,
          }}
        />
      </div>
      <div style={{ fontSize: 11, color: "#aaa" }}>
        HP {combatant.hp_current}/{combatant.hp_max} · AC {combatant.ac}
      </div>
    </div>
  );
}

// ActionType enum values from the backend (case must match exactly).
const ACTION_BUTTONS = [
  { label: "Attack", action: "Attack" },
  { label: "Dash", action: "Dash" },
  { label: "Dodge", action: "Dodge" },
] as const;

function CombatActions({
  sessionId,
  currentActorId,
  disabled,
}: {
  sessionId: string;
  currentActorId: string | undefined;
  disabled: boolean;
}) {
  const { setCombat } = useGameStore();

  const handleAction = useCallback(
    async (actionType: string) => {
      if (!currentActorId) return;
      try {
        const result = await api.submitAction(sessionId, {
          actor_id: currentActorId,
          action_type: actionType,
        });
        setCombat(mapCombatResponse(result));
      } catch (err) {
        console.error(`Failed to submit action ${actionType}:`, err);
      }
    },
    [sessionId, currentActorId, setCombat]
  );

  const handleNextTurn = useCallback(async () => {
    try {
      const result = await api.nextTurn(sessionId);
      setCombat(mapCombatResponse(result));
    } catch (err) {
      console.error("Failed to advance turn:", err);
    }
  }, [sessionId, setCombat]);

  return (
    <div style={{ marginTop: 8 }}>
      <div style={{ display: "flex", gap: 6 }}>
        {ACTION_BUTTONS.map(({ label, action }) => (
          <button
            key={action}
            onClick={() => handleAction(action)}
            disabled={disabled || !currentActorId}
            style={{
              flex: 1,
              padding: "5px 0",
              background: disabled || !currentActorId ? "#333" : "#2c3e50",
              color: disabled || !currentActorId ? "#666" : "#fff",
              border: "1px solid #444",
              borderRadius: 4,
              cursor: disabled || !currentActorId ? "not-allowed" : "pointer",
              fontSize: 12,
            }}
          >
            {label}
          </button>
        ))}
      </div>
      <button
        onClick={handleNextTurn}
        disabled={disabled}
        style={{
          width: "100%",
          marginTop: 6,
          padding: "5px 0",
          background: disabled ? "#333" : "#1a5276",
          color: disabled ? "#666" : "#fff",
          border: "1px solid #444",
          borderRadius: 4,
          cursor: disabled ? "not-allowed" : "pointer",
          fontSize: 12,
        }}
      >
        Next Turn ▶
      </button>
    </div>
  );
}

// ---- Start Combat dialog ----

interface CombatantEntry {
  char: CharacterData;
  selected: boolean;
  // Overrides for characters missing combat stats — filled in by DM before starting.
  hpMaxOverride: string;
  acOverride: string;
}

function needsStats(char: CharacterData): boolean {
  return char.hp_max === null || char.ac === null;
}

function StatInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <label style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 11 }}>
      <span style={{ color: "#aaa", minWidth: 28 }}>{label}</span>
      <input
        type="number"
        min={1}
        max={999}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        style={{
          width: 48,
          padding: "2px 4px",
          background: "#111",
          border: "1px solid #555",
          borderRadius: 3,
          color: "#fff",
          fontSize: 11,
        }}
      />
    </label>
  );
}

function StartCombatDialog({
  sessionId,
  onClose,
}: {
  sessionId: string;
  onClose: () => void;
}) {
  const { characters, setCombat, upsertCharacter } = useGameStore();

  const [entries, setEntries] = useState<CombatantEntry[]>(() =>
    characters.map((char) => ({
      char,
      selected: char.type === "PC",
      hpMaxOverride: char.hp_max?.toString() ?? "",
      acOverride: char.ac?.toString() ?? "",
    }))
  );
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const update = (id: string, patch: Partial<CombatantEntry>) =>
    setEntries((prev) => prev.map((e) => (e.char.id === id ? { ...e, ...patch } : e)));

  const selected = entries.filter((e) => e.selected);

  // Validate: every selected character must have effective hp_max and ac.
  const missingStats = selected.filter((e) => {
    const hp = e.char.hp_max ?? parseInt(e.hpMaxOverride, 10);
    const ac = e.char.ac ?? parseInt(e.acOverride, 10);
    return !hp || !ac || isNaN(hp) || isNaN(ac);
  });
  const canBegin = selected.length > 0 && missingStats.length === 0 && !loading;

  const handleBegin = async () => {
    setLoading(true);
    setError(null);
    try {
      // PATCH stats for characters whose stats were entered in the dialog.
      for (const entry of selected) {
        if (!needsStats(entry.char)) continue;
        const hp = parseInt(entry.hpMaxOverride, 10);
        const ac = parseInt(entry.acOverride, 10);
        const updated = await api.patchCharacter(entry.char.id, {
          hp_max: hp,
          hp_current: entry.char.hp_current ?? hp,
          ac,
        });
        upsertCharacter({
          id: updated.id,
          type: updated.type,
          name: updated.name,
          char_class: updated.char_class,
          race: updated.race,
          level: updated.level,
          hp_current: updated.hp_current,
          hp_max: updated.hp_max,
          ac: updated.ac,
          stats: updated.stats,
        });
      }

      const result = await api.startCombat(
        sessionId,
        selected.map((e) => e.char.id)
      );
      setCombat(mapCombatResponse(result));
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start combat");
    } finally {
      setLoading(false);
    }
  };

  const pcs = entries.filter((e) => e.char.type === "PC");
  const nonPcs = entries.filter((e) => e.char.type !== "PC");

  const renderEntry = (entry: CombatantEntry) => {
    const missing = entry.selected && needsStats(entry.char);
    return (
      <div
        key={entry.char.id}
        style={{
          background: "#1a1a2e",
          borderRadius: 5,
          padding: "7px 10px",
          marginBottom: 6,
          border: missing ? "1px solid #c0392b" : "1px solid transparent",
        }}
      >
        <label
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            cursor: "pointer",
          }}
        >
          <input
            type="checkbox"
            checked={entry.selected}
            onChange={(e) => update(entry.char.id, { selected: e.target.checked })}
            style={{ accentColor: "#7c6af7" }}
          />
          <span style={{ fontWeight: "bold", fontSize: 13 }}>{entry.char.name}</span>
          <span style={{ fontSize: 11, color: "#888" }}>
            {[entry.char.race, entry.char.char_class].filter(Boolean).join(" ")}
          </span>
          {!needsStats(entry.char) && (
            <span style={{ fontSize: 11, color: "#aaa", marginLeft: "auto" }}>
              HP {entry.char.hp_max} · AC {entry.char.ac}
            </span>
          )}
        </label>
        {entry.selected && needsStats(entry.char) && (
          <div
            style={{
              display: "flex",
              gap: 12,
              marginTop: 6,
              paddingLeft: 24,
            }}
          >
            <StatInput
              label="HP"
              value={entry.hpMaxOverride}
              onChange={(v) => update(entry.char.id, { hpMaxOverride: v })}
            />
            <StatInput
              label="AC"
              value={entry.acOverride}
              onChange={(v) => update(entry.char.id, { acOverride: v })}
            />
            <span style={{ fontSize: 11, color: "#c0392b", alignSelf: "center" }}>
              Required
            </span>
          </div>
        )}
      </div>
    );
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.7)",
        zIndex: 200,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        style={{
          background: "#16213e",
          borderRadius: 8,
          padding: 20,
          width: 380,
          maxHeight: "80vh",
          overflow: "auto",
          boxShadow: "0 8px 32px rgba(0,0,0,0.6)",
        }}
      >
        <h3 style={{ margin: "0 0 4px", fontSize: 16, color: "#e0d7ff" }}>Start Combat</h3>
        <p style={{ margin: "0 0 16px", fontSize: 12, color: "#888" }}>
          Select who joins the encounter. Enter HP and AC for characters without stats.
        </p>

        {pcs.length > 0 && (
          <>
            <div style={{ fontSize: 11, color: "#aaa", textTransform: "uppercase", marginBottom: 6 }}>
              Party
            </div>
            {pcs.map(renderEntry)}
          </>
        )}

        {nonPcs.length > 0 && (
          <>
            <div
              style={{
                fontSize: 11,
                color: "#aaa",
                textTransform: "uppercase",
                marginTop: 12,
                marginBottom: 6,
              }}
            >
              Monsters & NPCs
            </div>
            {nonPcs.map(renderEntry)}
          </>
        )}

        {entries.length === 0 && (
          <p style={{ color: "#555", fontSize: 13, textAlign: "center", padding: 16 }}>
            No characters in this world yet.
          </p>
        )}

        {error && (
          <p
            style={{
              color: "#f44336",
              fontSize: 12,
              background: "#2a1010",
              padding: "6px 10px",
              borderRadius: 4,
              margin: "8px 0",
            }}
          >
            {error}
          </p>
        )}

        <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
          <button
            onClick={onClose}
            style={{
              flex: 1,
              padding: "8px 0",
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
            onClick={handleBegin}
            disabled={!canBegin}
            title={
              selected.length === 0
                ? "Select at least one combatant"
                : missingStats.length > 0
                  ? "Fill in HP and AC for all selected combatants"
                  : ""
            }
            style={{
              flex: 2,
              padding: "8px 0",
              background: canBegin ? "#c0392b" : "#555",
              color: canBegin ? "#fff" : "#888",
              border: "none",
              borderRadius: 4,
              cursor: canBegin ? "pointer" : "not-allowed",
              fontSize: 13,
              fontWeight: "bold",
            }}
          >
            {loading ? "Starting…" : `Begin Combat (${selected.length})`}
          </button>
        </div>
      </div>
    </div>
  );
}

// ---- Main CombatTracker ----

export default function CombatTracker() {
  // Players see the initiative tracker live but only the DM gets the
  // controls — the server enforces this too (combat mutations are DM-only).
  const { sessionId, combat, setCombat, isDM } = useGameStore();
  const [showDialog, setShowDialog] = useState(false);

  const handleEnd = useCallback(async () => {
    if (!sessionId) return;
    try {
      await api.endCombat(sessionId);
      setCombat(null);
    } catch (err) {
      console.error("Failed to end combat:", err);
    }
  }, [sessionId, setCombat]);

  if (!combat) {
    return (
      <section>
        <h3
          style={{
            fontSize: 14,
            color: "#ccc",
            textTransform: "uppercase",
            margin: "0 0 8px",
          }}
        >
          Combat
        </h3>
        <p style={{ color: "#555", fontSize: 13 }}>No active combat.</p>
        {sessionId && isDM && (
          <>
            <button
              onClick={() => setShowDialog(true)}
              style={{
                padding: "6px 12px",
                background: "#c0392b",
                color: "#fff",
                border: "none",
                borderRadius: 4,
                cursor: "pointer",
              }}
            >
              Start Combat
            </button>
            {showDialog && (
              <StartCombatDialog
                sessionId={sessionId}
                onClose={() => setShowDialog(false)}
              />
            )}
          </>
        )}
      </section>
    );
  }

  const currentActorId = combat.combatants[combat.current_turn_index]?.char_id;

  return (
    <section>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 8,
        }}
      >
        <h3 style={{ margin: 0, fontSize: 14, color: "#ccc", textTransform: "uppercase" }}>
          Combat · Round {combat.round_number}
        </h3>
        {isDM && (
        <button
          onClick={handleEnd}
          style={{
            padding: "4px 8px",
            background: "#555",
            color: "#fff",
            border: "none",
            borderRadius: 4,
            cursor: "pointer",
            fontSize: 12,
          }}
        >
          End
        </button>
        )}
      </div>
      {combat.combatants.length === 0 ? (
        <p style={{ color: "#555", fontSize: 13 }}>No combatants in initiative order.</p>
      ) : (
        combat.combatants.map((c) => (
          <CombatantRow key={c.char_id} combatant={c} />
        ))
      )}
      {sessionId && isDM && (
        <CombatActions
          sessionId={sessionId}
          currentActorId={currentActorId}
          disabled={combat.combatants.length === 0}
        />
      )}
    </section>
  );
}
