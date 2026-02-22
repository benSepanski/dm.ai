import { useCallback } from "react";
import { api, type CombatStateResponse } from "../../api/client";
import { useGameStore, type ActiveCombat, type Combatant } from "../../store/gameStore";

function mapCombatResponse(result: CombatStateResponse): ActiveCombat {
  const combatants: Combatant[] = (result.combatants ?? []).map((c, i) => ({
    char_id: c.char_id,
    name: c.name,
    hp_current: c.hp_current,
    hp_max: c.hp_max,
    ac: c.ac,
    initiative: c.initiative,
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

const ACTION_BUTTONS = [
  { label: "Attack", action: "attack" },
  { label: "Dash", action: "dash" },
  { label: "Dodge", action: "dodge" },
] as const;

function ActionButtons({
  sessionId,
  disabled,
}: {
  sessionId: string;
  disabled: boolean;
}) {
  const setCombat = useGameStore((s) => s.setCombat);

  const handleAction = useCallback(
    async (action: string) => {
      try {
        const result = await api.submitAction(sessionId, { action_type: action });
        setCombat(mapCombatResponse(result));
      } catch (err) {
        console.error(`Failed to submit action ${action}:`, err);
      }
    },
    [sessionId, setCombat]
  );

  return (
    <div style={{ display: "flex", gap: 6, marginTop: 8 }}>
      {ACTION_BUTTONS.map(({ label, action }) => (
        <button
          key={action}
          onClick={() => handleAction(action)}
          disabled={disabled}
          style={{
            flex: 1,
            padding: "5px 0",
            background: disabled ? "#333" : "#2c3e50",
            color: disabled ? "#666" : "#fff",
            border: "1px solid #444",
            borderRadius: 4,
            cursor: disabled ? "not-allowed" : "pointer",
            fontSize: 12,
          }}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

export default function CombatTracker() {
  const { sessionId, combat, setCombat } = useGameStore();

  const handleStart = useCallback(async () => {
    if (!sessionId) return;
    try {
      const result = await api.startCombat(sessionId);
      setCombat(mapCombatResponse(result));
    } catch (err) {
      console.error("Failed to start combat:", err);
    }
  }, [sessionId, setCombat]);

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
        {sessionId && (
          <button
            onClick={handleStart}
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
        )}
      </section>
    );
  }

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
      </div>
      {combat.combatants.length === 0 ? (
        <p style={{ color: "#555", fontSize: 13 }}>No combatants in initiative order.</p>
      ) : (
        combat.combatants.map((c) => (
          <CombatantRow key={c.char_id} combatant={c} />
        ))
      )}
      {sessionId && (
        <ActionButtons sessionId={sessionId} disabled={combat.combatants.length === 0} />
      )}
    </section>
  );
}
